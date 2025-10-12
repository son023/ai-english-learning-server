import uvicorn
import os
import logging
import platform
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from services.sentences_service import SentencesService
from fastapi.middleware.cors import CORSMiddleware

from phonemizer.backend.espeak.wrapper import EspeakWrapper
from phonemizer import phonemize
from phonemizer.separator import Separator

from models import (
    PronunciationRequest, 
    PhoneticPronunciationResponse,
    # Các model dưới đây được thêm vào/sửa đổi cho API mới
    SentencePhonemesRequest,
    SentencePhonemesResponse,
    PhonemeData
)

from services.whisper_service import WhisperService
from services.pronunciation_service import PronunciationService
from services.llm_service import LLMService

# --- Cấu hình logging (không đổi) ---
log_file = "app.log"
logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info("--- Ứng dụng FastAPI bắt đầu khởi động ---")

# --- Cấu hình eSpeak (không đổi) ---
espeak_dll_path = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
if platform.system() == "Darwin":
    espeak_dll_path = "/opt/homebrew/bin/espeak-ng"
if os.path.exists(espeak_dll_path):
    EspeakWrapper.set_library(espeak_dll_path)
    logger.info(f"Đã thiết lập thư viện espeak-ng thành công tại: {espeak_dll_path}")
else:
    logger.error(f"LỖI CẤU HÌNH: Không tìm thấy espeak-ng tại '{espeak_dll_path}'.")

app = FastAPI(
    title="AI English Learning Server",
    description="Nền tảng đánh giá và học phát âm tiếng Anh bằng AI",
    version="2.3.0", # Cập nhật phiên bản
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Khởi tạo services (không đổi) ---
whisper_service = WhisperService(model_size="small")
pronunciation_service = PronunciationService()
llm_service = LLMService()
sentences_service = SentencesService(csv_path=os.path.join(os.path.dirname(__file__), "docs", "sentences.csv"))

@app.on_event("startup")
async def startup_event():
    logger.info("Bắt đầu quá trình warmup...")
    try:
        whisper_service.warmup()
        pronunciation_service.warmup()
        logger.info("Warmup thành công.")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình warmup: {e}")

# --- Các API Endpoint hiện có (không đổi) ---
@app.get("/")
async def root():
    return {"message": "Welcome to AI English Learning Server v2.3!"}

@app.post("/evaluate-pronunciation-phonetic", response_model=PhoneticPronunciationResponse)
async def evaluate_pronunciation_phonetic(request: PronunciationRequest):
    return pronunciation_service.process_phonetic_evaluation(request, whisper_service, llm_service)

@app.get("/sentences")
async def get_sentences():
    rows = sentences_service.load_sentences()
    if not rows:
        raise HTTPException(status_code=404, detail="sentences.csv not found or empty")
    return JSONResponse(content=rows)

# --- API ENDPOINT MỚI TỐI ƯU HÓA ---
@app.post("/phonemes-for-sentence", response_model=SentencePhonemesResponse)
async def get_phonemes_for_sentence(request: SentencePhonemesRequest):
    """
    API hiệu quả hơn để lấy phiên âm phoneme cho tất cả các từ trong một câu.
    """
    sentence = request.sentence.strip()
    if not sentence:
        raise HTTPException(status_code=400, detail="Sentence cannot be empty.")
    
    try:
        # Tách câu thành các từ, giữ lại dấu câu
        import re
        words = re.findall(r"[\w']+|[.,!?;]", sentence)
        
        # Lọc ra các từ thực sự để phiên âm
        words_to_phonemize = [word for word in words if word.isalnum()]

        if not words_to_phonemize:
            return SentencePhonemesResponse(phonemes=[])

        sep = Separator(phone=" ", syllable="", word="|")
        phonemes_list = phonemize(
            words_to_phonemize,
            language="en-us",
            backend="espeak",
            with_stress=True,
            strip=True,
            separator=sep,
            njobs=1,
        )

        # Map kết quả phiên âm trở lại danh sách từ gốc
        phoneme_map = dict(zip(words_to_phonemize, phonemes_list))
        
        result_data = [
            PhonemeData(word=word, phoneme=phoneme_map.get(word, "").strip())
            for word in words
        ]
        
        return SentencePhonemesResponse(phonemes=result_data)

    except Exception as e:
        logger.error(f"Lỗi khi lấy phoneme cho câu '{sentence}': {e}")
        raise HTTPException(status_code=500, detail="Could not generate phonemes for the sentence.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

