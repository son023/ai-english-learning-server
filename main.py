import uvicorn
import os
import logging
import time
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from phonemizer.backend.espeak.wrapper import EspeakWrapper
from phonemizer.separator import Separator

from models import  PronunciationRequest, PhoneticPronunciationResponse, PronunciationResponse, WordAccuracyData

from services.whisper_service import WhisperService
from services.pronunciation_service import PronunciationService
from services.llm_service import LLMService

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

@app.get("/")
async def root():
    return {"message": "Welcome to AI English Learning Server v2.1!"}

@app.post("/evaluate-pronunciation-phonetic", response_model=PhoneticPronunciationResponse)
async def evaluate_pronunciation_phonetic(request: PronunciationRequest):
    return pronunciation_service.process_phonetic_evaluation(request, whisper_service, llm_service)

if __name__ == "__main__":
    try:
        whisper_service.warmup()
    except Exception:
        pass
    try:
        pronunciation_service.warmup()
    except Exception:
        pass
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)