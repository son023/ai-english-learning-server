import whisper
import base64
import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from typing import Tuple, List, Dict, Any
import soxr

class WhisperService:
    """
    Whisper-based speech-to-text service for pronunciation evaluation
    """
    
    def __init__(self, model_size: str = "tiny"):
        self.model = whisper.load_model(model_size)
        self.model_size = model_size
    
    def warmup(self) -> None:
        """Run a tiny, fast transcription to warm caches and kernels."""
        try:
            # 0.2s of silence at 16kHz
            sr = 16000
            silence = np.zeros(int(0.2 * sr), dtype=np.float32)
            _ = self.model.transcribe(
                silence,
                language="en",
                task="transcribe",
                fp16=False,
                temperature=0.0,
                condition_on_previous_text=False
            )
        except Exception:
            # Warmup is best-effort; ignore failures
            pass
    
    def transcribe_audio_base64(self, audio_base64: str) -> Tuple[str, float, List[Dict[str, Any]]]:
        """
        Transcribe audio from base64 encoded data with enhanced preprocessing and word timestamps.
        
        Args:
            audio_base64: Base64 encoded audio data
            
        Returns:
            Tuple of (transcribed_text, confidence_score, word_segments)
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            try:
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                audio_data, sample_rate = sf.read(wav_buffer)
            except Exception:
                audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1, dtype=np.float32)
            else:
                audio_data = audio_data.astype(np.float32, copy=False)

            target_sr = 16000
            if sample_rate != target_sr:
                audio_data = soxr.resample(audio_data, sample_rate, target_sr)
            
            audio_data = self._enhance_audio(audio_data)
            
            result = self.model.transcribe(
                audio_data,
                language="en",
                task="transcribe",
                fp16=False,
                condition_on_previous_text=False,
                temperature=0.0,
                word_timestamps=True # Bật tính năng lấy thời gian của từng từ
            )
            
            transcribed_text = result["text"].strip()
            confidence = self._calculate_confidence(result.get("segments", []))
            
            # Trích xuất thông tin từng từ (bao gồm start, end)
            word_segments = []
            if "segments" in result:
                for segment in result["segments"]:
                    if "words" in segment:
                        word_segments.extend(segment["words"])

            return transcribed_text, confidence, word_segments
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return "", 0.0, []

    def _enhance_audio(self, audio_data: np.ndarray) -> np.ndarray:
        audio_data = audio_data.astype(np.float32, copy=False)
        audio_data = audio_data - np.mean(audio_data, dtype=np.float32)
        rms = np.sqrt(np.mean((audio_data**2), dtype=np.float32))
        if rms < 0.05:
            boost_factor = 0.1 / (rms + 1e-8)
            boost_factor = min(boost_factor, 10.0)
            audio_data = audio_data * boost_factor
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95
        return audio_data.astype(np.float32, copy=False)
    
    def _calculate_confidence(self, segments: list) -> float:
        if not segments:
            return 0.8
        
        confidences = [word.get("probability", 0.8) for segment in segments if "words" in segment for word in segment["words"]]
        
        if not confidences:
            # Fallback if word probabilities are not available
            logprobs = [s.get("avg_logprob", -1.0) for s in segments]
            confidences = [max(0.1, min(1.0, np.exp(lp + 1.0))) for lp in logprobs]

        avg_confidence = np.mean(confidences) if confidences else 0.8
        return max(0.1, min(1.0, avg_confidence))
    
    def get_model_info(self) -> dict:
        return {"model_size": self.model_size, "status": "loaded", "language": "en"}
