import whisper
import base64
import io
import numpy as np
import soundfile as sf
from pydub import AudioSegment
from typing import Tuple

class WhisperService:
    """
    Whisper-based speech-to-text service for pronunciation evaluation
    """
    
    def __init__(self, model_size: str = "tiny"):
        self.model = whisper.load_model(model_size)
        self.model_size = model_size
    
    def transcribe_audio_base64(self, audio_base64: str) -> Tuple[str, float]:
        """
        Transcribe audio from base64 encoded data with enhanced preprocessing
        
        Args:
            audio_base64: Base64 encoded audio data
            
        Returns:
            Tuple of (transcribed_text, confidence_score)
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            
            # Dùng pydub để handle nhiều format (WebM, MP4, WAV, etc.)
            try:
                # Thử đọc với pydub trước
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                
                # Convert to WAV format in memory
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                
                # Bây giờ dùng soundfile để đọc WAV
                audio_data, sample_rate = sf.read(wav_buffer)
                
            except Exception as pydub_error:
                print(f"Pydub failed, trying soundfile directly: {pydub_error}")
                # Fallback to soundfile (for WAV files)
                audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
            
            # Ensure mono audio and correct dtype for Whisper
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            
            # Convert to float32
            audio_data = audio_data.astype(np.float32)
            
            # Enhanced audio preprocessing for low-quality audio
            audio_data = self._enhance_audio(audio_data)
            
            # Transcribe with Whisper (more robust settings)
            result = self.model.transcribe(
                audio_data,
                language="en",  # Force English
                task="transcribe",
                fp16=False,  # Use FP32 for better accuracy
                condition_on_previous_text=False,  # Don't depend on previous context
                temperature=0.0,  # Deterministic output
                compression_ratio_threshold=2.4,  # More lenient compression
                logprob_threshold=-1.0,  # More lenient probability threshold
                no_speech_threshold=0.6  # Lower threshold for detecting speech
            )
            
            # Extract text and confidence
            transcribed_text = result["text"].strip()
            
            # Calculate average confidence from segments
            confidence = self._calculate_confidence(result.get("segments", []))
            
            return transcribed_text, confidence
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return "", 0.0
    
    def _enhance_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Enhance audio quality for better transcription
        """
        # Remove DC offset
        audio_data = audio_data - np.mean(audio_data)
        
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio_data**2))
        
        # If audio is too quiet, boost it
        if rms < 0.05:
            # Boost to target RMS of 0.1
            boost_factor = 0.1 / (rms + 1e-8)
            boost_factor = min(boost_factor, 10.0)  # Cap boost to 10x
            audio_data = audio_data * boost_factor
        
        # Normalize to [-1, 1] range with some headroom
        max_val = np.max(np.abs(audio_data))
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95  # Leave 5% headroom
        
        return audio_data
    
    def _calculate_confidence(self, segments: list) -> float:
        """Calculate average confidence from Whisper segments"""
        if not segments:
            return 0.8  # Default confidence for successful transcription
        
        confidences = []
        for segment in segments:
            # Use average confidence of words in segment
            words = segment.get("words", [])
            if words:
                word_confidences = [w.get("probability", 0.8) for w in words]
                confidences.extend(word_confidences)
            else:
                # Convert avg_logprob to confidence (logprob is negative, higher = better)
                avg_logprob = segment.get("avg_logprob", -1.0)
                # Convert logprob to confidence (rough approximation)
                confidence = max(0.1, min(1.0, np.exp(avg_logprob + 1.0)))
                confidences.append(confidence)
        
        avg_confidence = np.mean(confidences) if confidences else 0.8
        return max(0.1, min(1.0, avg_confidence))  # Clamp between 0.1 and 1.0
    
    def get_model_info(self) -> dict:
        """Get information about the loaded Whisper model"""
        return {
            "model_size": self.model_size,
            "status": "loaded",
            "language": "en"
        }
