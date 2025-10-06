from pydantic import BaseModel
from typing import List, Optional, Any


class PronunciationScore(BaseModel):
    """Pronunciation scoring results"""

    pronunciation: float
    fluency: float
    intonation: float
    stress: float
    overall: float


class WordError(BaseModel):
    """Word-level pronunciation error with position highlighting"""

    word: str
    position: int  # Position của từ trong câu (0-based)
    error_type: str  # substitution, insertion, deletion
    expected: str
    actual: str
    severity: Optional[str] = "moderate"

    def get_description(self) -> str:
        """Get human-readable error description"""
        if self.error_type == "substitution":
            return f"Từ '{self.expected}' được phát âm thành '{self.actual}'"
        elif self.error_type == "deletion":
            return f"Thiếu từ '{self.expected}'"
        elif self.error_type == "insertion":
            return f"Thêm từ '{self.actual}' không cần thiết"
        return f"Lỗi {self.error_type} tại từ '{self.word}'"


class PronunciationRequest(BaseModel):
    """Request model for pronunciation evaluation"""

    audio_base64: str  # Base64 encoded audio data
    sentence: str  # Reference sentence to compare against


class PronunciationResponse(BaseModel):
    """Response model for pronunciation evaluation"""

    original_sentence: str
    transcribed_text: str
    scores: PronunciationScore
    word_errors: List[WordError]
    feedback: str
    wer_score: float
    confidence: float
    highlighted_sentence: Optional[str] = None


class SentenceRequest(BaseModel):
    """Request for getting practice sentences"""

    difficulty_level: str = "beginner"
    topic: Optional[str] = "general"


class SentenceResponse(BaseModel):
    """Response with practice sentences"""

    sentence: str
    phonetic_transcription: str
    difficulty_level: str
    topic: str


class AudioAnalysis(BaseModel):
    """Audio quality analysis results"""

    is_valid: bool
    duration: float
    sample_rate: int
    channels: int
    issues: List[str]
    quality_score: float


class PhoneticPronunciationResponse(BaseModel):
    """
    Mô hình response cho việc đánh giá phát âm dựa trên âm vị.
    """

    original_sentence: str
    transcribed_text: str  # Văn bản được Whisper phiên âm
    reference_phonemes: str  # Chuỗi âm vị chuẩn
    learner_phonemes: str  # Chuỗi âm vị của người học
    scores: PronunciationScore
    phoneme_errors: List[dict]  # Danh sách các lỗi sai về âm vị
    feedback: str  # Phản hồi từ LLM
    wer_score: float  # Tỷ lệ lỗi âm vị (Phoneme Error Rate)
    confidence: float  # Độ tin cậy của Whisper


class PhonemeData(BaseModel):
    word: str
    phoneme: str


class WordAccuracyData(BaseModel):
    word: str
    accuracy_percentage: float  # Tỉ lệ % phiên âm đúng (0.0 - 100.0)


class SubAlignment(BaseModel):
    ref: Optional[str]
    learner: Optional[str]
    is_match: bool


class AlignmentItem(BaseModel):
    ref: Optional[str]
    learner: Optional[str]
    is_match: bool
    sub_alignment: List[SubAlignment] = []


class PhoneticPronunciationResponse(BaseModel):
    original_sentence: str
    transcribed_text: str
    reference_phonemes: List[PhonemeData]
    learner_phonemes: List[PhonemeData]
    word_accuracy: List[WordAccuracyData]  # Thêm trường accuracy cho từng từ
    scores: PronunciationScore
    phoneme_errors: List[dict]
    phoneme_alignment: List[AlignmentItem]  # DP alignment kết quả từ backend
    feedback: str
    wer_score: float
    confidence: float
