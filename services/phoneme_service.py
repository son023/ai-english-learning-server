import base64
import io
import numpy as np
import soundfile as sf
import librosa
import traceback
import tempfile
import os
import subprocess
from typing import Optional, List, Tuple
from pydub import AudioSegment
import io 
from transformers import pipeline, Wav2Vec2Processor
from gtts import gTTS
from difflib import SequenceMatcher

class PhonemeService:
    """
    Dịch vụ chuyển đổi giọng nói thành chuỗi phiên âm (phoneme)
    sử dụng mô hình Wav2Vec2-Phoneme của Facebook (facebook/wav2vec2-lv-60-espeak-cv-ft)
    Model này được train để trực tiếp output phoneme từ audio.
    """
    def __init__(self, model_name: str = "facebook/wav2vec2-lv-60-espeak-cv-ft"):
        try:
            print(f"--- Khởi tạo PhonemeService với model: {model_name} ---")
            
            print("Đang tải Processor (tokenizer, feature extractor)...")
            processor = Wav2Vec2Processor.from_pretrained(model_name)
            print("Tải Processor thành công.")

            print("Đang khởi tạo ASR pipeline...")
            self.transcriber = pipeline(
                "automatic-speech-recognition",
                model=model_name,
                tokenizer=processor.tokenizer,
                feature_extractor=processor.feature_extractor
            )
            self.model_name = model_name
            print("✅ Khởi tạo PhonemeService thành công!")

        except Exception as e:
            print(f"LỖI KHỞI TẠO PHONEMESERVICE:")
            traceback.print_exc()
            raise e

    def load_audio_from_base64(self, audio_base64: str) -> Optional[tuple]:
        """
        Tải audio từ base64 string, hỗ trợ nhiều format (mp3, webm, v.v.)
        *** TỐI ƯU: Dùng pydub để xử lý file trong bộ nhớ ***
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            audio_file = io.BytesIO(audio_bytes)
            
            audio_segment = AudioSegment.from_file(audio_file)
            
            audio_segment = audio_segment.set_frame_rate(16000)
            audio_segment = audio_segment.set_channels(1) # 1 = Mono
            
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)

            audio_data, sample_rate = librosa.load(wav_io, sr=None) 
            audio_data = np.array(audio_data, dtype=np.float32)
            max_abs_val = np.max(np.abs(audio_data))
            if max_abs_val > 0:
                audio_data /= max_abs_val
            
            return audio_data, sample_rate
            
        except Exception as e:
            print(f"Lỗi khi load audio (với pydub): {e}") 
            traceback.print_exc()
            return None

    def transcribe_audio_base64(self, audio_base64: str) -> Optional[str]:
        """
        Nhận âm thanh dạng base64, chuyển đổi và trả về chuỗi phiên âm.
        """
        try:
            audio_result = self.load_audio_from_base64(audio_base64)
            if audio_result is None:
                return None
                
            audio_data, sample_rate = audio_result
            
            if len(audio_data) == 0:
                return ""

            input_dict = {"sampling_rate": sample_rate, "raw": audio_data}
            result = self.transcriber(input_dict)
            
            phonetic_transcription = result.get("text", "")
            phonetic_transcription = phonetic_transcription.strip()
            
            return phonetic_transcription

        except Exception as e:
            print(f"Lỗi khi phiên âm sang âm vị: {e}")
            traceback.print_exc()
            return None

    def text_to_audio_base64(self, text: str, lang: str = 'en') -> Optional[str]:
        """
        Chuyển đổi text thành audio bằng gTTS và trả về dạng base64.
        *** TỐI ƯU: Dùng io.BytesIO, không ghi ra đĩa ***
        """
        try:
            audio_file = io.BytesIO()
            tts = gTTS(text=text, lang=lang, slow=False)
            
            tts.write_to_fp(audio_file) 
            
            audio_file.seek(0)
            audio_bytes = audio_file.read()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return audio_base64
            
        except Exception as e:
            print(f"Lỗi khi chuyển text thành audio: {e}")
            traceback.print_exc()
            return None

    def compare_phonemes(self, reference_phonemes: str, learner_phonemes: str) -> Tuple[List[dict], float, int, int]:
        """
        So sánh hai chuỗi phoneme và trả về chi tiết so sánh.
        """
        try:
            ref_phonemes = reference_phonemes.split()
            learner_phonemes_list = learner_phonemes.split()
            
            matcher = SequenceMatcher(None, ref_phonemes, learner_phonemes_list, autojunk=False)
            comparisons = []
            correct_count = 0
            total_count = len(ref_phonemes)
            
            if total_count == 0 and len(learner_phonemes_list) > 0:
                for k, learner_phoneme in enumerate(learner_phonemes_list):
                    comparisons.append({
                        "position": -1,
                        "reference_phoneme": "",
                        "learner_phoneme": learner_phoneme,
                        "is_correct": False,
                        "error_type": "insertion"
                    })
                return comparisons, 0.0, 0, 0

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    for k in range(i2 - i1):
                        comparisons.append({
                            "position": i1 + k,
                            "reference_phoneme": ref_phonemes[i1 + k],
                            "learner_phoneme": learner_phonemes_list[j1 + k],
                            "is_correct": True,
                            "error_type": None
                        })
                        correct_count += 1
                        
                elif tag == 'delete':
                    # Phoneme bị thiếu
                    for k in range(i2 - i1):
                        comparisons.append({
                            "position": i1 + k,
                            "reference_phoneme": ref_phonemes[i1 + k],
                            "learner_phoneme": "",
                            "is_correct": False,
                            "error_type": "deletion"
                        })
                        
                elif tag == 'insert':
                    # Phoneme thừa (không tính vào total_count)
                    for k in range(j2 - j1):
                        comparisons.append({
                            "position": -1,  # Không có vị trí trong reference
                            "reference_phoneme": "",
                            "learner_phoneme": learner_phonemes_list[j1 + k],
                            "is_correct": False,
                            "error_type": "insertion"
                        })
                        
                elif tag == 'replace':
                    ref_slice = ref_phonemes[i1:i2]
                    learner_slice = learner_phonemes_list[j1:j2]
                    len_ref = len(ref_slice)
                    len_learner = len(learner_slice)
                    max_len = max(len_ref, len_learner)

                    for k in range(max_len):
                        ref_phoneme = ref_slice[k] if k < len_ref else ""
                        learner_phoneme = learner_slice[k] if k < len_learner else ""
                        
                        is_correct = False
                        
                        if k >= len_ref:
                            error_type = "insertion"
                            position = -1 
                        elif k >= len_learner:
                            error_type = "deletion"
                            position = i1 + k
                        else:
                            error_type = "substitution"
                            position = i1 + k

                        comparisons.append({
                            "position": position,
                            "reference_phoneme": ref_phoneme,
                            "learner_phoneme": learner_phoneme,
                            "is_correct": is_correct,
                            "error_type": error_type
                        })
            
            comparisons.sort(key=lambda x: x['position'] if x['position'] != -1 else float('inf'))
            
            pronunciation_score = (correct_count / total_count * 100) if total_count > 0 else 0
            
            return comparisons, pronunciation_score, correct_count, total_count
            
        except Exception as e:
            print(f"Lỗi khi so sánh phoneme: {e}")
            traceback.print_exc()
            return [], 0.0, 0, 1


    def evaluate_word_pronunciation(self, audio_base64: str, word: str) -> dict:
        """
        Đánh giá phát âm của một từ bằng cách:
        1. Chuyển từ thành audio bằng gTTS -> wav2vec2 (phoneme model) để có reference phonemes
        2. Chuyển audio learner thành phonemes trực tiếp bằng wav2vec2 (phoneme model)
        3. So sánh và tính điểm
        """
        try:
            # Bước 1: Text -> gTTS -> Audio -> Wav2Vec2 Phoneme Model (reference)
            reference_audio_base64 = self.text_to_audio_base64(word)
            if not reference_audio_base64:
                return {"error": "Không thể tạo audio reference"}
            
            reference_phonemes = self.transcribe_audio_base64(reference_audio_base64)
            if not reference_phonemes:
                return {"error": "Không thể tạo phonemes reference"}
            
            # Bước 2: Audio -> Wav2Vec2 Phoneme Model (learner)
            learner_phonemes = self.transcribe_audio_base64(audio_base64)
            if not learner_phonemes:
                return {"error": "Không thể chuyển đổi audio thành phonemes"}
            
            print(f"Reference phonemes: '{reference_phonemes}'")
            print(f"Learner phonemes: '{learner_phonemes}'")
            
            # Bước 3: So sánh phoneme
            comparisons, score, correct, total = self.compare_phonemes(
                reference_phonemes, learner_phonemes
            )
            
            # Tạo feedback
            if score >= 90:
                feedback = "Xuất sắc! Phát âm rất chính xác."
            elif score >= 75:
                feedback = "Tốt! Có một vài lỗi nhỏ cần cải thiện."
            elif score >= 50:
                feedback = "Khá! Cần luyện tập thêm để cải thiện phát âm."
            else:
                feedback = "Cần cải thiện nhiều. Hãy nghe và luyện tập lại."
            
            return {
                "word": word,
                "reference_phonemes": reference_phonemes,
                "learner_phonemes": learner_phonemes,
                "pronunciation_score": round(score, 2),
                "phoneme_comparisons": comparisons,
                "correct_phonemes": correct,
                "total_phonemes": total,
                "feedback": feedback
            }
            
        except Exception as e:
            print(f"Lỗi khi đánh giá phát âm từ '{word}': {e}")
            traceback.print_exc()
            return {"error": f"Lỗi xử lý: {str(e)}"}

    def get_processor_and_model(self):
        """
        Trả về processor và model để sử dụng lại cho các service khác
        Tránh phải load lại model nhiều lần
        """
        try:
            model = self.transcriber.model
            tokenizer = self.transcriber.tokenizer
            feature_extractor = self.transcriber.feature_extractor
            
            class SimpleProcessor:
                def __init__(self, tokenizer, feature_extractor):
                    self.tokenizer = tokenizer
                    self.feature_extractor = feature_extractor
                
                def __call__(self, audio, sampling_rate, return_tensors="pt", padding=True):
                    return self.feature_extractor(
                        audio, 
                        sampling_rate=sampling_rate, 
                        return_tensors=return_tensors, 
                        padding=padding
                    )
                
                def batch_decode(self, token_ids):
                    return self.tokenizer.batch_decode(token_ids)
            
            processor = SimpleProcessor(tokenizer, feature_extractor)
            return processor, model
            
        except Exception as e:
            print(f"Lỗi khi lấy processor và model: {e}")
            traceback.print_exc()
            return None, None

    def get_model_info(self) -> dict:
        return {"model": self.model_name, "status": "loaded"}