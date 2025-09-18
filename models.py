from pydantic import BaseModel
from typing import List, Optional

class PronunciationScore(BaseModel):
    """Pronunciation scoring results"""
    pronunciation: float  # 0-100
    fluency: float       # 0-100  
    intonation: float    # 0-100
    stress: float        # 0-100
    overall: float       # 0-100

class WordError(BaseModel):
    """Word-level pronunciation error with position highlighting"""
    word: str
    position: int        # Position của từ trong câu (0-based)
    error_type: str      # substitution, insertion, deletion
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
    audio_base64: str    # Base64 encoded audio data
    sentence: str        # Reference sentence to compare against
    
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
