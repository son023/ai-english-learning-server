import difflib
import string
from typing import List, Tuple, Dict, Any
import time
import logging
import math
import numpy as np
from fastapi import HTTPException
from phonemizer import phonemize
from phonemizer.separator import Separator
import os
from jiwer import wer
from dtwalign import dtw_from_distance_matrix
from .word_matching import get_best_mapped_words_dtw
from .word_metrics import edit_distance_python as wm_edit_distance
from models import (
    PhonemeData,
    PronunciationScore,
    WordAccuracyData,
    AlignmentItem,
    SubAlignment,
    PhoneticPronunciationResponse,
)
from difflib import SequenceMatcher

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

        # Tính điểm tổng thể bằng trung bình cộng của điểm từng từ
        if not word_accuracy:
            overall_accuracy = 0.0
            overall_pronunciation = 0.0
        else:
            total_accuracy_sum = sum(wa.accuracy_percentage for wa in word_accuracy)
            overall_accuracy = round(total_accuracy_sum / len(word_accuracy), 1)

            # Bạn cũng có thể tính điểm phát âm tổng thể riêng nếu muốn
            total_pron_sum = sum(wa.pronunciation_score for wa in word_accuracy)
            overall_pronunciation = round(total_pron_sum / len(word_accuracy), 1)

        scores = PronunciationScore(
            # Sử dụng điểm phát âm trung bình cho 'pronunciation'
            pronunciation=overall_pronunciation, 
            fluency=0.0, 
            intonation=0.0, 
            stress=0.0, 
            # Sử dụng điểm kết hợp trung bình cho 'overall'
            overall=overall_accuracy
        )

        return scores, phoneme_errors, wer_score, word_accuracy

    def _align_sequences_dtw_patched(
        self, ref_seq: List[str], learner_seq: List[str]
    ) -> List[AlignmentItem]:
        """
        Sử dụng DTW để tìm đường đi, sau đó hậu xử lý để xác định các cặp ghép không hợp lệ
        dựa trên ngưỡng khoảng cách Levenshtein.
        """
        if not ref_seq and not learner_seq:
            return []
        if not ref_seq:
            return [self._build_alignment_item(None, l, False) for l in learner_seq]
        if not learner_seq:
            return [self._build_alignment_item(r, None, False) for r in ref_seq]

        # --- Bước 1: Tính ma trận khoảng cách Levenshtein đã chuẩn hóa ---
        m, n = len(learner_seq), len(ref_seq)
        distance_matrix = np.zeros((m, n))
        for i in range(m):
            for j in range(n):
                # Sử dụng hàm edit distance có sẵn của bạn
                dist = wm_edit_distance(learner_seq[i], ref_seq[j])
                # Chuẩn hóa khoảng cách về khoảng [0, 1]
                max_len = max(len(learner_seq[i]), len(ref_seq[j]), 1)
                distance_matrix[i, j] = dist / max_len

        # --- Bước 2: Chạy DTW như cũ ---
        # Lưu ý: dtw_from_distance_matrix tìm đường đi tối thiểu hóa chi phí,
        # nên ma trận khoảng cách của chúng ta là phù hợp.
        dtw_result = dtw_from_distance_matrix(distance_matrix)
        path = dtw_result.path

        # --- Bước 3 & 4: Hậu xử lý và tổng hợp kết quả ---
        # Đặt ngưỡng, nếu khoảng cách > ngưỡng -> cặp ghép không hợp lệ
        THRESHOLD = 0.6  

        ref_mapped = [False] * n
        learner_mapped = [False] * m
        good_alignments = []

        # Tìm các cặp ghép "tốt" (dưới ngưỡng)
        for learner_idx, ref_idx in path:
            # Chỉ xử lý các cặp chưa được khớp để tránh trùng lặp
            if not learner_mapped[learner_idx] and not ref_mapped[ref_idx]:
                if distance_matrix[learner_idx, ref_idx] < THRESHOLD:
                    ref_mapped[ref_idx] = True
                    learner_mapped[learner_idx] = True
                    is_match = ref_seq[ref_idx] == learner_seq[learner_idx]
                    good_alignments.append(
                        self._build_alignment_item(ref_seq[ref_idx], learner_seq[learner_idx], is_match)
                    )

        # Xây dựng kết quả cuối cùng
        final_alignment: List[AlignmentItem] = []
        ref_ptr, learner_ptr = 0, 0
        
        # Sử dụng SequenceMatcher để hợp nhất các phần đã được xử lý (khớp, thừa, thiếu)
        # thành một chuỗi duy nhất.
        sm = SequenceMatcher(None, ref_seq, learner_seq)
        
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal': # Khớp hoàn toàn
                for i in range(i2 - i1):
                    final_alignment.append(self._build_alignment_item(ref_seq[i1+i], learner_seq[j1+i], True))
            elif tag == 'replace': # Thay thế (có thể là tốt hoặc xấu)
                # Đây là phần phức tạp, chúng ta có thể dùng lại logic THRESHOLD ở trên
                # hoặc đơn giản hóa bằng cách coi tất cả replace là mismatch
                # Để đơn giản và hiệu quả, ta sẽ align 2 đoạn con này
                sub_ref = ref_seq[i1:i2]
                sub_learner = learner_seq[j1:j2]
                # Bạn có thể gọi một hàm align nhỏ hơn ở đây nếu cần, hoặc xử lý đơn giản
                max_len = max(len(sub_ref), len(sub_learner))
                for i in range(max_len):
                    ref_val = sub_ref[i] if i < len(sub_ref) else None
                    learner_val = sub_learner[i] if i < len(sub_learner) else None
                    is_match = ref_val == learner_val
                    final_alignment.append(self._build_alignment_item(ref_val, learner_val, is_match))
            elif tag == 'delete': # Thiếu từ (có trong ref, không có trong learner)
                for i in range(i1, i2):
                    final_alignment.append(self._build_alignment_item(ref_seq[i], None, False))
            elif tag == 'insert': # Thừa từ (không có trong ref, có trong learner)
                for i in range(j1, j2):
                    final_alignment.append(self._build_alignment_item(None, learner_seq[i], False))

        return final_alignment

    def _build_alignment_item(
        self, ref_val: str | None, learner_val: str | None, is_match: bool
    ) -> AlignmentItem:
        # Implementation không đổi...
        sub_alignment: List[SubAlignment] = []
        if not is_match:
            ref_chars, learner_chars = list(ref_val or ""), list(learner_val or "")
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
        """Align characters using DTW algorithm"""
        if not ref_chars and not learner_chars:
            return []
        if not ref_chars:
            return [
                SubAlignment(ref=None, learner=l, is_match=False) for l in learner_chars
            ]
        if not learner_chars:
            return [
                SubAlignment(ref=r, learner=None, is_match=False) for r in ref_chars
            ]

        # Tạo distance matrix (learner x ref)
        m, n = len(learner_chars), len(ref_chars)
        distance_matrix = np.zeros((m, n))
        for i in range(m):
            for j in range(n):
                # Distance = 0 nếu match, 1 nếu mismatch
                distance_matrix[i, j] = 0.0 if learner_chars[i] == ref_chars[j] else 1.0

        # Chạy DTW
        dtw_result = dtw_from_distance_matrix(distance_matrix)

        # Parse alignment path
        aligned: List[SubAlignment] = []
        path = (
            dtw_result.path
        )  # shape: [path_length, 2], columns: [learner_idx, ref_idx]

        for i in range(len(path)):
            learner_idx, ref_idx = path[i]

            # Kiểm tra nếu là valid index
            if learner_idx < len(learner_chars) and ref_idx < len(ref_chars):
                # Match/mismatch
                ref_val = ref_chars[ref_idx]
                learner_val = learner_chars[learner_idx]
                is_match = ref_val == learner_val
                aligned.append(
                    SubAlignment(ref=ref_val, learner=learner_val, is_match=is_match)
                )
            elif learner_idx >= len(learner_chars) and ref_idx < len(ref_chars):
                # Deletion (missing in learner)
                aligned.append(
                    SubAlignment(ref=ref_chars[ref_idx], learner=None, is_match=False)
                )
            elif learner_idx < len(learner_chars) and ref_idx >= len(ref_chars):
                # Insertion (extra in learner)
                aligned.append(
                    SubAlignment(
                        ref=None, learner=learner_chars[learner_idx], is_match=False
                    )
                )

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
            phoneme_alignment = self._align_sequences_dtw_patched(ref_seq, learner_seq)

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
