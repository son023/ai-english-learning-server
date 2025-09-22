# main.py 

import uvicorn
import os
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from phonemizer.backend.espeak.wrapper import EspeakWrapper

from models import PhonemeData, PronunciationRequest, PhoneticPronunciationResponse, PronunciationResponse, WordAccuracyData

from services.whisper_service import WhisperService
from services.pronunciation_service import PronunciationService
from services.llm_service import LLMService
from services.phoneme_service import PhonemeService
from phonemizer import phonemize

# --- Cấu hình logging ---
log_file = "app.log"
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO) 
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("--- Ứng dụng FastAPI bắt đầu khởi động ---")

espeak_dll_path = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"

if os.path.exists(espeak_dll_path):
    EspeakWrapper.set_library(espeak_dll_path)
    logger.info(f"Đã thiết lập thư viện espeak-ng thành công tại: {espeak_dll_path}")
else:
    logger.error(f"LỖI CẤU HÌNH: Không tìm thấy file libespeak-ng.dll tại '{espeak_dll_path}'.")

app = FastAPI(
    title="AI English Learning Server",
    description="Nền tảng đánh giá và học phát âm tiếng Anh bằng AI",
    version="2.1.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

whisper_service = WhisperService(model_size="small")
pronunciation_service = PronunciationService()
llm_service = LLMService()
phoneme_service = PhonemeService()

# --- Các Endpoints ---

@app.get("/")
async def root():
    return {"message": "Welcome to AI English Learning Server v2.1!"}

@app.post("/evaluate-pronunciation-phonetic", response_model=PhoneticPronunciationResponse)
async def evaluate_pronunciation_phonetic(request: PronunciationRequest):
    request_id = os.urandom(4).hex()
    logger.info(f"[{request_id}] Nhận yêu cầu /evaluate-pronunciation-phonetic cho câu: '{request.sentence}'")
    
    try:
        transcribed_text, confidence = whisper_service.transcribe_audio_base64(request.audio_base64)
        if transcribed_text is None:
            raise HTTPException(status_code=500, detail="Could not transcribe audio.")

        # Dùng vòng lặp để phiên âm TỪNG TỪ MỘT ---
        
        # Phiên âm câu gốc
        original_words = request.sentence.split()
        reference_phonemes_list = []
        for word in original_words:
            phoneme = phonemize(word, language='en-us', backend='espeak', with_stress=True).strip()
            reference_phonemes_list.append(PhonemeData(word=word, phoneme=phoneme))
        logger.info(f"[{request_id}] Đã phiên âm từng từ cho câu gốc.")

        # Phiên âm câu của người học
        learner_words = transcribed_text.split()
        learner_phonemes_list = []
        for word in learner_words:
            phoneme = phonemize(word, language='en-us', backend='espeak', with_stress=True).strip()
            learner_phonemes_list.append(PhonemeData(word=word, phoneme=phoneme))
        logger.info(f"[{request_id}] Đã phiên âm từng từ cho câu của người học.")

        scores, phoneme_errors, wer_score = pronunciation_service.evaluate_pronunciation_phonemes_by_word(
            reference_phonemes=reference_phonemes_list, 
            learner_phonemes=learner_phonemes_list
        )

        # Tính accuracy cho từng từ
        word_accuracy = pronunciation_service.calculate_word_accuracy(
            reference=reference_phonemes_list,
            learner=learner_phonemes_list
        )

        feedback = "Default feedback."
        try:
            word_errors_for_llm = [{
                "error_type": err.get('type', 'unknown'), 
                "expected": err.get('expected_word') or err.get('expected_phoneme', ''), 
                "actual": err.get('actual_word') or err.get('actual_phoneme', '')
            } for err in phoneme_errors]
            
            feedback = llm_service.generate_pronunciation_feedback(
                original_sentence=request.sentence, transcribed_text=transcribed_text, scores=scores,
                word_errors=word_errors_for_llm, wer_score=wer_score
            )
            if not feedback or not feedback.strip():
                feedback = "AI feedback is currently unavailable."
        except Exception:
            logger.exception(f"[{request_id}] LLM feedback generation failed.")
            feedback = "Could not generate AI feedback at this time."

        logger.info(f"[{request_id}] Xử lý yêu cầu thành công.")
        return PhoneticPronunciationResponse(
            original_sentence=request.sentence, transcribed_text=transcribed_text,
            reference_phonemes=reference_phonemes_list, learner_phonemes=learner_phonemes_list,
            word_accuracy=word_accuracy, scores=scores, phoneme_errors=phoneme_errors, 
            feedback=feedback, wer_score=wer_score, confidence=confidence
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"[{request_id}] Đã xảy ra lỗi không mong muốn.")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)