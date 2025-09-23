from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from models import PronunciationRequest, PronunciationResponse
from services.whisper_service import WhisperService
from services.pronunciation_service import PronunciationService
from services.llm_service import LLMService
from services.audio_service import AudioService
from services.prosody_service import ProsodyService

app = FastAPI(
    title="AI English Learning Server",
    description="AI-powered English pronunciation assessment and learning platform",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
whisper_service = WhisperService(
    model_size="small"
)  # Upgrade to small for better accuracy
pronunciation_service = PronunciationService()
llm_service = LLMService()
audio_service = AudioService()
prosody_service = ProsodyService()


@app.get("/")
async def root():
    return {"message": "Welcome to AI English Learning Server!"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Server is running",
        "services": {
            "whisper": whisper_service.get_model_info(),
            "pronunciation": "available",
            "llm": "disabled_temporarily",
            "audio": "available",
        },
    }


@app.post("/evaluate-pronunciation", response_model=PronunciationResponse)
async def evaluate_pronunciation(request: PronunciationRequest):
    try:
        if not request.audio_base64:
            raise HTTPException(status_code=400, detail="Audio data is required")

        if not request.sentence:
            raise HTTPException(
                status_code=400, detail="Reference sentence is required"
            )

        # Step 1: Analyze audio quality
        audio_analysis = audio_service.analyze_audio_base64(request.audio_base64)

        if not audio_analysis.is_valid:
            print(f"Audio validation failed: {audio_analysis.issues}")
            raise HTTPException(
                status_code=400,
                detail=f"Audio quality issues: {', '.join(audio_analysis.issues)}",
            )

        # Step 2: Transcribe audio using Whisper
        transcribed_text, confidence = whisper_service.transcribe_audio_base64(
            request.audio_base64
        )

        if not transcribed_text:
            print("Transcription failed - empty result")
            raise HTTPException(
                status_code=400,
                detail="Could not transcribe audio. Please ensure clear speech.",
            )

        # Step 3: Phonetic pronunciation evaluation
        scores, word_errors, wer_score = pronunciation_service.evaluate_pronunciation(
            request.sentence, transcribed_text, confidence
        )

        # Step 2.5: Analyze prosody (intonation)
        prosody_result = prosody_service.analyze_prosody_base64(request.audio_base64)
        # Gán điểm intonation và stress vào scores nếu có
        if prosody_result:
            if prosody_result.get("intonation_score") is not None:
                scores.intonation = prosody_result["intonation_score"]
            if prosody_result.get("stress_score") is not None:
                scores.stress = prosody_result["stress_score"]

        # Generate highlighted sentence showing errors
        highlighted_sentence = pronunciation_service.highlight_errors(
            request.sentence, word_errors
        )

        # Step 4: Generate feedback
        feedback = pronunciation_service.get_feedback(scores, word_errors)

        try:
            llm_feedback = llm_service.generate_pronunciation_feedback(
                request.sentence, transcribed_text, scores, word_errors, wer_score
            )
            if llm_feedback and llm_feedback.strip():
                feedback = llm_feedback
        except Exception as e:
            print(f"LLM feedback unavailable, using built-in feedback: {e}")

        return PronunciationResponse(
            original_sentence=request.sentence,
            transcribed_text=transcribed_text,
            scores=scores,
            word_errors=word_errors,
            feedback=feedback,
            wer_score=wer_score,
            confidence=confidence,
            highlighted_sentence=highlighted_sentence,
            # Có thể mở rộng: prosody=prosody_result
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Pronunciation evaluation error: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during evaluation"
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
