# File: services/pronunciation_service.py

import difflib
import string
from typing import List, Tuple
from jiwer import wer
from models import PhonemeData, PronunciationScore, WordError # WordError có thể đổi tên thành PhonemeError

class PronunciationService:
    """
    Dịch vụ đánh giá phát âm bằng cách so sánh trực tiếp hai chuỗi phiên âm.
    """
    def evaluate_pronunciation_phonemes(
        self, 
        reference_phonemes: str, 
        transcribed_phonemes: str
    ) -> Tuple[PronunciationScore, List[dict], float]:
        """
        Đánh giá sự tương đồng giữa hai chuỗi phiên âm.
        """
        # 1. Tính toán WER trực tiếp trên chuỗi phiên âm
        wer_score = self.calculate_wer(reference_phonemes, transcribed_phonemes)

        # 2. Tìm các lỗi sai khác biệt giữa hai chuỗi phiên âm
        phoneme_errors = self.get_phoneme_errors(reference_phonemes, transcribed_phonemes)

        # 3. Tính điểm số
        scores = self.calculate_scores(wer_score)

        return scores, phoneme_errors, wer_score

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """Tính toán Word Error Rate (trong trường hợp này là Phoneme Error Rate)."""
        return wer(reference, hypothesis)

    def get_phoneme_errors(self, reference: str, transcribed: str) -> List[dict]:
        """Tìm sự khác biệt giữa hai chuỗi phiên âm."""
        ref_phonemes = reference.split()
        trans_phonemes = transcribed.split()

        matcher = difflib.SequenceMatcher(None, ref_phonemes, trans_phonemes)
        errors = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                errors.append({
                    "type": tag, # 'replace', 'delete', 'insert'
                    "reference_segment": " ".join(ref_phonemes[i1:i2]),
                    "transcribed_segment": " ".join(trans_phonemes[j1:j2])
                })
        return errors

    def calculate_scores(self, wer_score: float) -> PronunciationScore:
        """Tính toán điểm số phát âm dựa trên PER (Phoneme Error Rate)."""
        pronunciation_score = max(0, (1 - wer_score) * 100)
        
        return PronunciationScore(
            pronunciation=round(pronunciation_score, 1),
            fluency=0.0, # Sẽ cần mô hình khác để đánh giá
            intonation=0.0, # Sẽ cần mô hình khác để đánh giá
            stress=0.0, # Sẽ cần mô hình khác để đánh giá
            overall=round(pronunciation_score, 1)
        )
    
    def highlight_errors(self, original_text: str, word_errors: List[WordError]) -> str:
        """Highlight pronunciation errors in the original text"""
        if not word_errors:
            return original_text
        
        words = original_text.lower().strip().translate(str.maketrans('', '', string.punctuation)).split()
        highlighted = words.copy()
        
        # Sort by position descending to avoid index issues
        for error in sorted(word_errors, key=lambda x: x.position, reverse=True):
            if error.position < len(highlighted):
                if error.error_type == "substitution":
                    highlighted[error.position] = f"[{error.expected}→{error.actual}]"
                elif error.error_type == "deletion":
                    highlighted[error.position] = f"[THIẾU:{error.expected}]"
            elif error.error_type == "insertion":
                highlighted.append(f"[THÊM:{error.actual}]")
        
        return " ".join(highlighted)
    
    def get_feedback(self, scores: PronunciationScore, word_errors: List[WordError]) -> str:
        """Generate simple feedback"""
        if scores.overall >= 90:
            return "Xuất sắc! 🎉"
        elif scores.overall >= 75:
            feedback = "Tốt, "
        elif scores.overall >= 60:
            feedback = "Khá, "
        else:
            feedback = "Cần cải thiện, "
        
        if word_errors:
            error_types = {}
            for error in word_errors:
                error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
            
            issues = []
            if error_types.get('substitution', 0) > 0:
                issues.append(f"{error_types['substitution']} từ phát âm sai")
            if error_types.get('deletion', 0) > 0:
                issues.append(f"thiếu {error_types['deletion']} từ")
            if error_types.get('insertion', 0) > 0:
                issues.append(f"thêm {error_types['insertion']} từ")
            
            feedback += ", ".join(issues) + "."
        
        return feedback
    
    def evaluate_pronunciation_phonemes_by_word(
        self, 
        reference_phonemes: List[PhonemeData], 
        learner_phonemes: List[PhonemeData]
    ) -> Tuple[PronunciationScore, List[dict], float]:
        """
        Đánh giá bằng cách so sánh phiên âm của từng từ tương ứng.
        """
        # Lấy ra chỉ chuỗi phiên âm để tính WER tổng thể
        ref_phoneme_sequence = " ".join([p.phoneme for p in reference_phonemes])
        learner_phoneme_sequence = " ".join([p.phoneme for p in learner_phonemes])
        wer_score = self.calculate_wer(ref_phoneme_sequence, learner_phoneme_sequence)

        # So sánh từng từ để tìm lỗi chi tiết
        phoneme_errors = self.get_word_by_word_errors(reference_phonemes, learner_phonemes)
        
        scores = self.calculate_scores(wer_score)
        return scores, phoneme_errors, wer_score

    def get_word_by_word_errors(self, reference: List[PhonemeData], learner: List[PhonemeData]) -> List[dict]:
        """So sánh từng từ và phiên âm tương ứng để tìm lỗi."""
        ref_words = [item.word for item in reference]
        learner_words = [item.word for item in learner]
        
        matcher = difflib.SequenceMatcher(None, ref_words, learner_words)
        errors = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Ngay cả khi từ giống nhau, hãy kiểm tra phiên âm
                for i in range(i1, i2):
                    if reference[i].phoneme != learner[i].phoneme:
                        errors.append({
                            "type": "pronunciation",
                            "word": reference[i].word,
                            "expected_phoneme": reference[i].phoneme,
                            "actual_phoneme": learner[i].phoneme
                        })
            elif tag == 'replace':
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    errors.append({
                        "type": "substitution",
                        "expected_word": reference[i].word,
                        "actual_word": learner[j].word
                    })
            elif tag == 'delete':
                for i in range(i1, i2):
                    errors.append({"type": "deletion", "missing_word": reference[i].word})
            elif tag == 'insert':
                for j in range(j1, j2):
                    errors.append({"type": "insertion", "extra_word": learner[j].word})
        return errors