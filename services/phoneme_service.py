# File: services/phoneme_service.py (Phiên bản Sửa lỗi Cuối cùng)

import base64
import io
import numpy as np
import soundfile as sf
import traceback
from typing import Optional

# Thêm import cho Processor và Pipeline
from transformers import pipeline, Wav2Vec2Processor

class PhonemeService:
    """
    Dịch vụ chuyển đổi giọng nói thành chuỗi phiên âm (phoneme)
    sử dụng mô hình Wav2Vec2 của Facebook/Hugging Face.
    """
    def __init__(self, model_name: str = "jonatasgrosman/wav2vec2-large-xlsr-53-english"):
        try:
            print(f"--- Khởi tạo PhonemeService với model: {model_name} ---")
            
            # BƯỚC 1: Tải Processor một cách tường minh.
            # Processor chứa cả tokenizer và feature_extractor cần thiết.
            print("Đang tải Processor (tokenizer, feature extractor)...")
            processor = Wav2Vec2Processor.from_pretrained(model_name)
            print("Tải Processor thành công.")

            # BƯỚC 2: Khởi tạo pipeline và truyền processor vào.
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
            print(f"❌ GẶP LỖI NGHIÊM TRỌNG KHI KHỞI TẠO PHONEMESERVICE:")
            traceback.print_exc()
            # Ném lại lỗi để server không khởi động nếu service này bị hỏng
            raise e

    def transcribe_audio_base64(self, audio_base64: str) -> Optional[str]:
        """
        Nhận âm thanh dạng base64, chuyển đổi và trả về chuỗi phiên âm.
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))

            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)
            audio_data = audio_data.astype(np.float32)

            max_abs_val = np.max(np.abs(audio_data))
            if max_abs_val > 0:
                audio_data /= max_abs_val
            else:
                return "" # Trả về rỗng nếu audio im lặng

            input_dict = {"sampling_rate": sample_rate, "raw": audio_data}
            result = self.transcriber(input_dict)
            
            phonetic_transcription = result.get("text", "")
            # Chuẩn hóa output từ model
            phonetic_transcription = phonetic_transcription.replace(" ", "").replace("|", " ").strip()
            
            return phonetic_transcription

        except Exception as e:
            print(f"Lỗi khi phiên âm sang âm vị: {e}")
            traceback.print_exc()
            return None

    def get_model_info(self) -> dict:
        return {"model": self.model_name, "status": "loaded"}