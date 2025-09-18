import string
import difflib
from typing import List, Tuple
from jiwer import wer
from models import PronunciationScore, WordError

class PronunciationService:
    """
    Simple pronunciation service with phonetic comparison
    - Text-to-phonetic conversion
    - WER calculation on phonetics
    - Word-level error highlighting
    """
    
    def __init__(self):
        self.phonetic_map = {
            # Vowels
            'a': 'æ', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɔ', 'u': 'ʊ',
            'ai': 'aɪ', 'ay': 'eɪ', 'oo': 'u', 'ou': 'aʊ', 'ow': 'aʊ',
            'ea': 'i', 'ee': 'i', 'ie': 'aɪ', 'oa': 'oʊ', 'ue': 'u',
            # Consonants  
            'th': 'θ', 'sh': 'ʃ', 'ch': 'tʃ', 'ph': 'f', 'gh': 'f',
            'ck': 'k', 'qu': 'kw', 'x': 'ks', 'ng': 'ŋ'
        }
    
    def evaluate_pronunciation(self, original_text: str, transcribed_text: str, confidence: float = 1.0) -> Tuple[PronunciationScore, List[WordError], float]:
        """
        Evaluate pronunciation using phonetic comparison
        """
        
        # Convert to phonetic representation
        original_phonetic = self.text_to_phonetic(original_text)
        transcribed_phonetic = self.text_to_phonetic(transcribed_text)
        
        # Calculate WER on phonetic level
        wer_score = self.calculate_wer(original_phonetic, transcribed_phonetic)
        
        # Get word-level errors
        word_errors = self.get_word_errors(original_text, transcribed_text)
        
        # Calculate scores
        scores = self.calculate_scores(wer_score, confidence, len(word_errors))

        return scores, word_errors, wer_score
    
    def text_to_phonetic(self, text: str) -> str:
        """Convert text to simplified phonetic representation"""
        text = text.lower().strip()
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Apply phonetic mappings
        for pattern, phonetic in sorted(self.phonetic_map.items(), key=len, reverse=True):
            text = text.replace(pattern, phonetic)
        
        return ' '.join(text.split())
    
    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """Calculate Word Error Rate"""
        try:
            return wer(reference, hypothesis)
        except:
            ref_words = reference.split()
            hyp_words = hypothesis.split()
            if len(ref_words) == 0:
                return 1.0 if len(hyp_words) > 0 else 0.0
            
            correct = sum(1 for r, h in zip(ref_words, hyp_words) if r == h)
            return 1.0 - (correct / len(ref_words))
    
    def get_word_errors(self, original: str, transcribed: str) -> List[WordError]:
        """Find word-level pronunciation errors"""
        orig_words = original.lower().strip().translate(str.maketrans('', '', string.punctuation)).split()
        trans_words = transcribed.lower().strip().translate(str.maketrans('', '', string.punctuation)).split()
        
        matcher = difflib.SequenceMatcher(None, orig_words, trans_words)
        errors = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                for k, (orig_word, trans_word) in enumerate(zip(orig_words[i1:i2], trans_words[j1:j2])):
                    severity = self.get_phonetic_similarity(orig_word, trans_word)
                    errors.append(WordError(
                        word=orig_word,
                        position=i1 + k,
                        error_type="substitution",
                        expected=orig_word,
                        actual=trans_word,
                        severity=severity
                    ))
            elif tag == 'delete':
                for k, orig_word in enumerate(orig_words[i1:i2]):
                    errors.append(WordError(
                        word=orig_word,
                        position=i1 + k,
                        error_type="deletion",
                        expected=orig_word,
                        actual="[missing]",
                        severity="high"
                    ))
            elif tag == 'insert':
                for k, trans_word in enumerate(trans_words[j1:j2]):
                    errors.append(WordError(
                        word=trans_word,
                        position=i1,
                        error_type="insertion", 
                        expected="[none]",
                        actual=trans_word,
                        severity="moderate"
                    ))
        return errors
    
    def get_phonetic_similarity(self, word1: str, word2: str) -> str:
        """Calculate phonetic similarity between two words"""
        phonetic1 = self.text_to_phonetic(word1)
        phonetic2 = self.text_to_phonetic(word2)
        similarity = difflib.SequenceMatcher(None, phonetic1, phonetic2).ratio()
        
        if similarity >= 0.8:
            return "low"
        elif similarity >= 0.5:
            return "moderate"
        else:
            return "high"
    
    def calculate_scores(self, wer_score: float, confidence: float, error_count: int) -> PronunciationScore:
        """Calculate pronunciation scores"""
        pronunciation = max(0, (1 - wer_score) * 100)
        fluency = 0
        intonation = 0
        stress = 0
        overall = pronunciation
        
        return PronunciationScore(
            pronunciation=round(pronunciation, 1),
            fluency=round(fluency, 1),
            intonation=round(intonation, 1),
            stress=round(stress, 1),
            overall=round(overall, 1)
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