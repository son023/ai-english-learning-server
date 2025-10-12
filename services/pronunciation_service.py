# services/pronunciation_service.py

import difflib
import string
from typing import List, Tuple
import time
import logging
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
)


class PronunciationService:

    def warmup(self) -> None:
        """Warm up phonemizer and DTW path to avoid cold-start latency."""
        try:
            # Trigger espeak/phonemizer load
            test_words = ["hello", "world"]
            sep = Separator(phone=" ", syllable="", word="|")
            _ = phonemize(
                test_words,
                language="en-us",
                backend="espeak",
                with_stress=True,
                strip=True,
                separator=sep,
                njobs=1,
            )
        except Exception:
            pass
        try:
            # Trigger DTW import path and a tiny compute
            _ = get_best_mapped_words_dtw(["a"], ["a"])
        except Exception:
            pass

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """Tính toán Word Error Rate (trong trường hợp này là Phoneme Error Rate)."""
        return wer(reference, hypothesis)

    def evaluate_pronunciation_phonemes_aligned(
        self, reference_phonemes: List[PhonemeData], learner_phonemes: List[PhonemeData]
    ) -> Tuple[PronunciationScore, List[dict], float, List[WordAccuracyData]]:
        # 1. Tách từ
        ref_words = [p.word for p in reference_phonemes]
        est_words = [p.word for p in learner_phonemes]

        # 2. Align từ
        mapped_words, mapped_indices = get_best_mapped_words_dtw(est_words, ref_words)
        # print(mapped_words, mapped_indices)
        # 3. Đánh giá phoneme per word
        word_accuracy = []
        phoneme_errors = []
        total_phonemes = 0
        total_mismatches = 0

        for i, ref in enumerate(reference_phonemes):
            ref_seq = ref.phoneme.replace(" ", "")
            total_phonemes += len(ref_seq) or 1

            # Lấy phoneme của từ map
            phon_est = ""
            if i < len(mapped_indices) and mapped_indices[i] >= 0:
                phon_est = learner_phonemes[mapped_indices[i]].phoneme.replace(" ", "")
            # Tính edit distance
            dist = wm_edit_distance(ref_seq, phon_est)
            total_mismatches += dist

            # Tính accuracy và lưu
            acc = max(0.0, (len(ref_seq) - dist) / max(len(ref_seq), 1)) * 100
            word_accuracy.append(
                WordAccuracyData(word=ref.word, accuracy_percentage=round(acc, 1))
            )

            if dist > 0:
                phoneme_errors.append(
                    {
                        "type": "pronunciation",
                        "expected_phoneme": ref.phoneme,
                        "actual_phoneme": (
                            learner_phonemes[mapped_indices[i]].phoneme
                            if phon_est
                            else ""
                        ),
                    }
                )

        # 4. WER trên phoneme sequence
        ref_seq_all = " ".join([p.phoneme for p in reference_phonemes])
        est_seq_all = " ".join(
            [mapped_words[i] for i in range(len(ref_words)) if mapped_indices[i] >= 0]
        )
        wer_score = self.calculate_wer(ref_seq_all, est_seq_all)

        # 5. Điểm tổng thể
        overall = (
            round((total_phonemes - total_mismatches) / total_phonemes * 100, 1)
            if total_phonemes
            else 0.0
        )
        scores = PronunciationScore(
            pronunciation=overall,
            fluency=0.0,
            intonation=0.0,
            stress=0.0,
            overall=overall,
        )

        return scores, phoneme_errors, wer_score, word_accuracy

    def _align_sequences(
        self, ref_seq: List[str], learner_seq: List[str]
    ) -> List[AlignmentItem]:
        """Needleman-Wunsch alignment for sequences of strings with simple scoring."""
        m, n = len(ref_seq), len(learner_seq)
        match_score = 2
        mismatch_penalty = -1
        gap_penalty = -1

        dp = [[0] * (n + 1) for _ in range(m + 1)]
        back = [[None] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            dp[i][0] = i * gap_penalty
            back[i][0] = "up"
        for j in range(1, n + 1):
            dp[0][j] = j * gap_penalty
            back[0][j] = "left"

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = dp[i - 1][j - 1] + (
                    match_score
                    if ref_seq[i - 1] == learner_seq[j - 1]
                    else mismatch_penalty
                )
                delete = dp[i - 1][j] + gap_penalty
                insert = dp[i][j - 1] + gap_penalty
                best = max(match, delete, insert)
                dp[i][j] = best
                if best == delete:
                    back[i][j] = "up"
                elif best == insert:
                    back[i][j] = "left"
                else:
                    back[i][j] = "diag"

        i, j = m, n
        aligned: List[AlignmentItem] = []
        while i > 0 or j > 0:
            direction = back[i][j]
            if direction == "diag":
                ref_val = ref_seq[i - 1]
                learner_val = learner_seq[j - 1]
                is_match = ref_val == learner_val
                aligned.append(
                    self._build_alignment_item(ref_val, learner_val, is_match)
                )
                i -= 1
                j -= 1
            elif direction == "up":
                ref_val = ref_seq[i - 1]
                aligned.append(self._build_alignment_item(ref_val, None, False))
                i -= 1
            else:  # "left"
                learner_val = learner_seq[j - 1]
                aligned.append(self._build_alignment_item(None, learner_val, False))
                j -= 1

        aligned.reverse()
        return aligned

    def _build_alignment_item(
        self, ref_val: str | None, learner_val: str | None, is_match: bool
    ) -> AlignmentItem:
        # If matched or either side is None, sub-alignment is empty or trivial
        sub_alignment: List[SubAlignment] = []
        if not is_match:
            ref_chars = list(ref_val) if ref_val else []
            learner_chars = list(learner_val) if learner_val else []
            # Character-level alignment for visualization
            sub_alignment = self._align_chars(ref_chars, learner_chars)
        return AlignmentItem(
            ref=ref_val,
            learner=learner_val,
            is_match=is_match and (ref_val is not None and learner_val is not None),
            sub_alignment=sub_alignment,
        )

    def _align_chars(
        self, ref_chars: List[str], learner_chars: List[str]
    ) -> List[SubAlignment]:
        m, n = len(ref_chars), len(learner_chars)
        match_score = 2
        mismatch_penalty = -1
        gap_penalty = -1

        dp = [[0] * (n + 1) for _ in range(m + 1)]
        back = [[None] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            dp[i][0] = i * gap_penalty
            back[i][0] = "up"
        for j in range(1, n + 1):
            dp[0][j] = j * gap_penalty
            back[0][j] = "left"

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = dp[i - 1][j - 1] + (
                    match_score
                    if ref_chars[i - 1] == learner_chars[j - 1]
                    else mismatch_penalty
                )
                delete = dp[i - 1][j] + gap_penalty
                insert = dp[i][j - 1] + gap_penalty
                best = max(match, delete, insert)
                dp[i][j] = best
                if best == delete:
                    back[i][j] = "up"
                elif best == insert:
                    back[i][j] = "left"
                else:
                    back[i][j] = "diag"

        i, j = m, n
        aligned: List[SubAlignment] = []
        while i > 0 or j > 0:
            direction = back[i][j]
            if direction == "diag":
                r = ref_chars[i - 1]
                l = learner_chars[j - 1]
                aligned.append(SubAlignment(ref=r, learner=l, is_match=(r == l)))
                i -= 1
                j -= 1
            elif direction == "up":
                r = ref_chars[i - 1]
                aligned.append(SubAlignment(ref=r, learner=None, is_match=False))
                i -= 1
            else:
                l = learner_chars[j - 1]
                aligned.append(SubAlignment(ref=None, learner=l, is_match=False))
                j -= 1
        aligned.reverse()
        return aligned

    def process_phonetic_evaluation(self, request, whisper_service, llm_service):
        logger = logging.getLogger("api_logger")
        request_id = os.urandom(4).hex() if hasattr(os, "urandom") else "req"
        logger.info(
            f"[{request_id}] Nhận yêu cầu /evaluate-pronunciation-phonetic cho câu: '{request.sentence}'"
        )

        try:
            t0 = time.perf_counter()
            transcribed_text, confidence = whisper_service.transcribe_audio_base64(
                request.audio_base64
            )
            t1 = time.perf_counter()
            logger.info(
                f"[{request_id}] Whisper transcribe xong trong {(t1 - t0)*1000:.1f} ms"
            )
            if transcribed_text is None:
                raise HTTPException(
                    status_code=500, detail="Could not transcribe audio."
                )

            original_words = request.sentence.split()
            sep = Separator(phone=" ", syllable="", word="|")
            ref_phonemes_batched = phonemize(
                original_words,
                language="en-us",
                backend="espeak",
                with_stress=True,
                strip=True,
                separator=sep,
                njobs=1,
            )
            reference_phonemes_list = [
                PhonemeData(word=w, phoneme=p.strip())
                for w, p in zip(original_words, ref_phonemes_batched)
            ]

            # Phiên âm câu của người học
            learner_words = transcribed_text.split()
            sep = Separator(phone=" ", syllable="", word="|")
            learner_phonemes_batched = phonemize(
                learner_words,
                language="en-us",
                backend="espeak",
                with_stress=True,
                strip=True,
                separator=sep,
                njobs=1,
            )
            learner_phonemes_list = [
                PhonemeData(word=w, phoneme=p.strip())
                for w, p in zip(learner_words, learner_phonemes_batched)
            ]

            t0 = time.perf_counter()
            scores, phoneme_errors, wer_score, word_accuracy = (
                self.evaluate_pronunciation_phonemes_aligned(
                    reference_phonemes=reference_phonemes_list,
                    learner_phonemes=learner_phonemes_list,
                )
            )
            t1 = time.perf_counter()
            logger.info(
                f"[{request_id}] Đánh giá phát âm xong trong {(t1 - t0)*1000:.1f} ms"
            )

            # Build phoneme alignment at word-phoneme-string level for frontend coloring
            ref_seq = [
                (p.phoneme or "").strip()
                for p in reference_phonemes_list
                if (p.phoneme or "").strip()
            ]
            learner_seq = [
                (p.phoneme or "").strip()
                for p in learner_phonemes_list
                if (p.phoneme or "").strip()
            ]
            phoneme_alignment = self._align_sequences(ref_seq, learner_seq)

            feedback = "Default feedback."
            try:
                word_errors_for_llm = [
                    {
                        "error_type": err.get("type", "unknown"),
                        "expected": err.get("expected_word")
                        or err.get("expected_phoneme", ""),
                        "actual": err.get("actual_word")
                        or err.get("actual_phoneme", ""),
                    }
                    for err in phoneme_errors
                ]

                feedback = llm_service.generate_pronunciation_feedback(
                    original_sentence=request.sentence,
                    transcribed_text=transcribed_text,
                    scores=scores,
                    word_errors=word_errors_for_llm,
                    wer_score=wer_score,
                )
                if not feedback or not feedback.strip():
                    feedback = "AI feedback is currently unavailable."
            except Exception:
                logger.exception(f"[{request_id}] LLM feedback generation failed.")
                feedback = "Could not generate AI feedback at this time."

            logger.info(f"[{request_id}] Xử lý yêu cầu thành công.")
            from models import PhoneticPronunciationResponse

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
            logger.exception(f"[{request_id}] Đã xảy ra lỗi không mong muốn.")
            raise HTTPException(
                status_code=500, detail="An internal server error occurred."
            )
