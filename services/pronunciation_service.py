import difflib
import string
from typing import List, Tuple, Dict, Any
import time
import logging
import math
from fastapi import HTTPException
from phonemizer import phonemize
from phonemizer.separator import Separator
import os
from jiwer import wer
from .word_matching import get_best_mapped_words_dtw
from .word_metrics import edit_distance_python as wm_edit_distance
from models import (
    PhonemeData,
    PronunciationScore,
    WordAccuracyData,
    AlignmentItem,
    SubAlignment,
    PhoneticPronunciationResponse
)


class PronunciationService:

    def warmup(self) -> None:
        try:
            test_words = ["hello", "world"]
            sep = Separator(phone=" ", syllable="", word="|")
            _ = phonemize(
                test_words, language="en-us", backend="espeak", with_stress=True, strip=True, separator=sep, njobs=1
            )
            _ = get_best_mapped_words_dtw(["a"], ["a"])
        except Exception:
            pass

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        return wer(reference, hypothesis)

    def evaluate_pronunciation_phonemes_aligned(
        self, 
        reference_phonemes: List[PhonemeData], 
        learner_phonemes: List[PhonemeData],
        learner_words_with_ts: List[Dict[str, Any]]
    ) -> Tuple[PronunciationScore, List[dict], float, List[WordAccuracyData]]:
        ref_words = [p.word for p in reference_phonemes]
        est_words = [p.word for p in learner_phonemes]

        mapped_words, mapped_indices = get_best_mapped_words_dtw(est_words, ref_words)
        
        word_accuracy = []
        phoneme_errors = []
        total_phonemes = 0
        total_mismatches = 0

        for i, ref in enumerate(reference_phonemes):
            ref_seq = ref.phoneme.replace(" ", "")
            total_phonemes += len(ref_seq) or 1
            
            phon_est = ""
            pronunciation_score = 0.0
            rhythm_score = 0.0

            if i < len(mapped_indices) and mapped_indices[i] >= 0:
                learner_word_index = mapped_indices[i]
                phon_est = learner_phonemes[learner_word_index].phoneme.replace(" ", "")
                
                # Tính điểm phát âm (phoneme accuracy)
                dist = wm_edit_distance(ref_seq, phon_est)
                total_mismatches += dist
                pronunciation_score = max(0.0, (len(ref_seq) - dist) / max(len(ref_seq), 1)) * 100

                # Tính điểm nhịp điệu (rhythm score)
                if learner_word_index < len(learner_words_with_ts):
                    learner_word_info = learner_words_with_ts[learner_word_index]
                    if 'start' in learner_word_info and 'end' in learner_word_info:
                        learner_duration = learner_word_info['end'] - learner_word_info['start']
                        
                        # Ước tính thời gian chuẩn dựa trên số lượng âm vị
                        ref_phoneme_count = len(ref_seq)
                        standard_duration = 0.08 * ref_phoneme_count + 0.15 # Heuristic: 80ms/phoneme + 150ms base
                        
                        if standard_duration > 0:
                            ratio = learner_duration / standard_duration
                            # Dùng hàm Gaussian để tính điểm, điểm cao nhất khi ratio=1
                            # sigma=0.4 -> cho phép sai lệch khoảng 40%
                            sigma = 0.4 
                            rhythm_score = math.exp(-0.5 * ((ratio - 1) / sigma) ** 2) * 100

                if dist > 0:
                    phoneme_errors.append({
                        "type": "pronunciation",
                        "expected_phoneme": ref.phoneme,
                        "actual_phoneme": learner_phonemes[learner_word_index].phoneme if phon_est else "",
                    })
            
            # Kết hợp điểm
            # Trọng số: 70% cho phát âm, 30% cho nhịp điệu
            final_accuracy = pronunciation_score * 0.7 + rhythm_score * 0.3

            word_accuracy.append(
                WordAccuracyData(
                    word=ref.word, 
                    accuracy_percentage=round(final_accuracy, 1),
                    pronunciation_score=round(pronunciation_score, 1),
                    rhythm_score=round(rhythm_score, 1)
                )
            )

        ref_seq_all = " ".join([p.phoneme for p in reference_phonemes])
        est_seq_all = " ".join(
            [learner_phonemes[mapped_indices[i]].phoneme for i in range(len(ref_words)) if mapped_indices[i] >= 0]
        )
        wer_score = self.calculate_wer(ref_seq_all, est_seq_all)

        overall = (
            round((total_phonemes - total_mismatches) / total_phonemes * 100, 1)
            if total_phonemes
            else 0.0
        )
        scores = PronunciationScore(
            pronunciation=overall, fluency=0.0, intonation=0.0, stress=0.0, overall=overall
        )

        return scores, phoneme_errors, wer_score, word_accuracy

    def _align_sequences(self, ref_seq: List[str], learner_seq: List[str]) -> List[AlignmentItem]:
        # Implementation không đổi...
        m, n = len(ref_seq), len(learner_seq)
        match_score, mismatch_penalty, gap_penalty = 2, -1, -1
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        back = [[None] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            dp[i][0] = i * gap_penalty; back[i][0] = "up"
        for j in range(1, n + 1):
            dp[0][j] = j * gap_penalty; back[0][j] = "left"
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = dp[i-1][j-1] + (match_score if ref_seq[i-1] == learner_seq[j-1] else mismatch_penalty)
                delete = dp[i-1][j] + gap_penalty
                insert = dp[i][j-1] + gap_penalty
                best = max(match, delete, insert)
                dp[i][j] = best
                if best == delete: back[i][j] = "up"
                elif best == insert: back[i][j] = "left"
                else: back[i][j] = "diag"
        i, j = m, n
        aligned: List[AlignmentItem] = []
        while i > 0 or j > 0:
            direction = back[i][j]
            if direction == "diag":
                ref_val, learner_val = ref_seq[i-1], learner_seq[j-1]
                aligned.append(self._build_alignment_item(ref_val, learner_val, ref_val == learner_val))
                i -= 1; j -= 1
            elif direction == "up":
                aligned.append(self._build_alignment_item(ref_seq[i-1], None, False)); i -= 1
            else:
                aligned.append(self._build_alignment_item(None, learner_seq[j-1], False)); j -= 1
        aligned.reverse()
        return aligned

    def _build_alignment_item(self, ref_val: str | None, learner_val: str | None, is_match: bool) -> AlignmentItem:
        # Implementation không đổi...
        sub_alignment: List[SubAlignment] = []
        if not is_match:
            ref_chars, learner_chars = list(ref_val or ""), list(learner_val or "")
            sub_alignment = self._align_chars(ref_chars, learner_chars)
        return AlignmentItem(ref=ref_val, learner=learner_val, is_match=is_match and (ref_val is not None and learner_val is not None), sub_alignment=sub_alignment)

    def _align_chars(self, ref_chars: List[str], learner_chars: List[str]) -> List[SubAlignment]:
        # Implementation không đổi...
        m, n = len(ref_chars), len(learner_chars)
        match_score, mismatch_penalty, gap_penalty = 2, -1, -1
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        back = [[None] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            dp[i][0] = i * gap_penalty; back[i][0] = "up"
        for j in range(1, n + 1):
            dp[0][j] = j * gap_penalty; back[0][j] = "left"
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = dp[i-1][j-1] + (match_score if ref_chars[i-1] == learner_chars[j-1] else mismatch_penalty)
                delete = dp[i-1][j] + gap_penalty
                insert = dp[i][j-1] + gap_penalty
                best = max(match, delete, insert)
                dp[i][j] = best
                if best == delete: back[i][j] = "up"
                elif best == insert: back[i][j] = "left"
                else: back[i][j] = "diag"
        i, j = m, n
        aligned: List[SubAlignment] = []
        while i > 0 or j > 0:
            direction = back[i][j]
            if direction == "diag":
                r, l = ref_chars[i-1], learner_chars[j-1]
                aligned.append(SubAlignment(ref=r, learner=l, is_match=(r == l)))
                i -= 1; j -= 1
            elif direction == "up":
                aligned.append(SubAlignment(ref=ref_chars[i-1], learner=None, is_match=False)); i -= 1
            else:
                aligned.append(SubAlignment(ref=None, learner=learner_chars[j-1], is_match=False)); j -= 1
        aligned.reverse()
        return aligned

    def process_phonetic_evaluation(self, request, whisper_service, llm_service):
        logger = logging.getLogger("api_logger")
        request_id = os.urandom(4).hex()
        logger.info(f"[{request_id}] Received request for: '{request.sentence}'")
        try:
            t0 = time.perf_counter()
            transcribed_text, confidence, learner_words_with_ts = whisper_service.transcribe_audio_base64(request.audio_base64)
            t1 = time.perf_counter()
            logger.info(f"[{request_id}] Whisper transcribed in {(t1-t0)*1000:.1f} ms")
            if transcribed_text is None:
                raise HTTPException(status_code=500, detail="Could not transcribe audio.")

            original_words = request.sentence.split()
            sep = Separator(phone=" ", syllable="", word="|")
            ref_phonemes_batched = phonemize(
                original_words, language="en-us", backend="espeak", with_stress=True, strip=True, separator=sep, njobs=1
            )
            reference_phonemes_list = [PhonemeData(word=w, phoneme=p.strip()) for w, p in zip(original_words, ref_phonemes_batched)]

            learner_words = transcribed_text.split()
            learner_phonemes_batched = phonemize(
                learner_words, language="en-us", backend="espeak", with_stress=True, strip=True, separator=sep, njobs=1
            )
            learner_phonemes_list = [PhonemeData(word=w, phoneme=p.strip()) for w, p in zip(learner_words, learner_phonemes_batched)]
            
            t0 = time.perf_counter()
            scores, phoneme_errors, wer_score, word_accuracy = self.evaluate_pronunciation_phonemes_aligned(
                reference_phonemes=reference_phonemes_list,
                learner_phonemes=learner_phonemes_list,
                learner_words_with_ts=learner_words_with_ts
            )
            t1 = time.perf_counter()
            logger.info(f"[{request_id}] Pronunciation evaluated in {(t1-t0)*1000:.1f} ms")

            ref_seq = [(p.phoneme or "").strip() for p in reference_phonemes_list if (p.phoneme or "").strip()]
            learner_seq = [(p.phoneme or "").strip() for p in learner_phonemes_list if (p.phoneme or "").strip()]
            phoneme_alignment = self._align_sequences(ref_seq, learner_seq)

            feedback = "Default feedback."
            try:
                word_errors_for_llm = [
                    {"error_type": err.get("type", "unknown"), "expected": err.get("expected_phoneme", ""), "actual": err.get("actual_phoneme", "")}
                    for err in phoneme_errors
                ]
                feedback = llm_service.generate_pronunciation_feedback(
                    request.sentence, transcribed_text, scores, word_errors_for_llm, wer_score
                )
                if not feedback or not feedback.strip():
                    feedback = "AI feedback is currently unavailable."
            except Exception:
                logger.exception(f"[{request_id}] LLM feedback generation failed.")
                feedback = "Could not generate AI feedback at this time."

            logger.info(f"[{request_id}] Request processed successfully.")
            return PhoneticPronunciationResponse(
                original_sentence=request.sentence,
                transcribed_text=transcribed_text,
                reference_phonemes=reference_phonemes_list,
                learner_phonemes=learner_phonemes_list,
                word_accuracy=word_accuracy,
                scores=scores,
                phoneme_errors=phoneme_errors,
                phoneme_alignment=phoneme_alignment,
                feedback=feedback,
                wer_score=wer_score,
                confidence=confidence,
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception(f"[{request_id}] An unexpected error occurred.")
            raise HTTPException(status_code=500, detail="An internal server error occurred.")
