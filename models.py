from pydantic import BaseModel
from typing import List, Optional

# --- Các model hiện có (không thay đổi nhiều) ---

class PronunciationScore(BaseModel):
    pronunciation: float; fluency: float; intonation: float; stress: float; overall: float

class WordError(BaseModel):
    word: str; position: int; error_type: str; expected: str; actual: str
    severity: Optional[str] = "moderate"

class PronunciationRequest(BaseModel):
    audio_base64: str; sentence: str

class PhonemeData(BaseModel):
    word: str
    phoneme: str

class WordAccuracyData(BaseModel):
    word: str; accuracy_percentage: float; pronunciation_score: float; rhythm_score: float

class SubAlignment(BaseModel):
    ref: Optional[str]; learner: Optional[str]; is_match: bool

class AlignmentItem(BaseModel):
    ref: Optional[str]; learner: Optional[str]; is_match: bool
    sub_alignment: List[SubAlignment] = []

class PhoneticPronunciationResponse(BaseModel):
    original_sentence: str; transcribed_text: str
    reference_phonemes: List[PhonemeData]
    learner_phonemes: List[PhonemeData]
    word_accuracy: List[WordAccuracyData]
    scores: PronunciationScore
    phoneme_errors: List[dict]
    phoneme_alignment: List[AlignmentItem]
    feedback: str; wer_score: float; confidence: float

# --- MODELS MỚI CHO API /phonemes-for-sentence ---

class SentencePhonemesRequest(BaseModel):
    """Request model để lấy phonemes cho cả câu."""
    sentence: str

class SentencePhonemesResponse(BaseModel):
    """Response model chứa danh sách phonemes cho cả câu."""
    phonemes: List[PhonemeData]

