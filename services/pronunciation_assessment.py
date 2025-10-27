"""
Pronunciation Assessment V4 - Full Audio Approach (API Service)
================================================================
Key improvement: Run Wave2Phoneme on FULL audio once, then align to words
This avoids cutting issues when words are spoken continuously
"""

import os
import json
import nltk
import torch
import numpy as np
import librosa
import resampy
import whisperx
import base64
import tempfile
import logging
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
from Levenshtein import distance as levenshtein_distance
from g2p_en import G2p
from typing import Dict, List, Any

# Download required NLTK data
nltk.download('cmudict', quiet=True)
arpabet = nltk.corpus.cmudict.dict()

class PronunciationAssessmentService:
    """Service wrapper for pronunciation assessment"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = "float32" if self.device == "cuda" else "int8"
        self.target_sr = 16000
        self.processor = None
        self.model = None
        self.logger = logging.getLogger(__name__)
        
    def warmup(self):
        """Initialize and warmup the models"""
        try:
            self.logger.info("🔧 Warming up Pronunciation Assessment Service...")
            
            # Load Wave2Phoneme model
            self.processor, self.model = load_wave2phoneme_model()
            
            self.logger.info("✅ Pronunciation Assessment Service warmed up successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to warmup Pronunciation Assessment Service: {e}")

    def evaluate_pronunciation_assessment(self, audio_base64: str, reference_text: str) -> Dict[str, Any]:
        """
        Main API function to evaluate pronunciation using the assessment method
        """
        try:
            self.logger.info(f"🎯 Evaluating pronunciation for: '{reference_text}'")
            
            # STEP 1: Decode and preprocess audio
            audio_data, sr = self._preprocess_audio_from_base64(audio_base64)
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                import soundfile as sf
                sf.write(tmp_file.name, audio_data, sr)
                temp_audio_path = tmp_file.name
            
            try:
                # STEP 2: WhisperX timestamps  
                words_with_times = get_word_timestamps(temp_audio_path)
                
                # STEP 3: Reference phonemes
                reference_phonemes = get_reference_phonemes(reference_text)
                
                # STEP 4: Load Wave2Phoneme model if not loaded
                if self.processor is None or self.model is None:
                    self.processor, self.model = load_wave2phoneme_model()
                
                # STEP 5: Predict phonemes from FULL audio
                predicted_phonemes_full = predict_phonemes_full_audio(
                    audio_data, sr, self.processor, self.model
                )
                
                # STEP 6: Align phonemes to words
                word_predicted_phonemes, word_alignments = align_phonemes_to_words_v2(
                    predicted_phonemes_full, 
                    reference_phonemes,
                    words_with_times
                )
                
                # STEP 7-8: Score each word and build result
                result = self._build_comprehensive_result(
                    reference_text, words_with_times, word_predicted_phonemes, 
                    word_alignments, reference_phonemes
                )
                
                self.logger.info(f"✅ Pronunciation assessment completed. Score: {result['scores']['sentence_score']:.2f}")
                return result
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                    
        except Exception as e:
            self.logger.error(f"❌ Error in pronunciation assessment: {e}")
            return {
                'error': str(e),
                'scores': {'sentence_score': 0.0, 'grade': 'Error', 'overall': 0.0, 'pronunciation': 0.0, 'fluency': 0.0, 'intonation': 0.0, 'stress': 0.0},
                'words': [],
                'word_accuracy': [],
                'transcribed_text': '',
                'feedback': 'Có lỗi xảy ra trong quá trình đánh giá phát âm.'
            }

    def _preprocess_audio_from_base64(self, audio_base64: str):
        """Decode base64 audio and preprocess"""
        self.logger.info("🔧 STEP 1: Preprocessing audio from base64...")
        
        try:
            # Decode base64
            audio_bytes = base64.b64decode(audio_base64)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                temp_path = tmp_file.name
            
            try:
                # Load audio using existing function logic
                audio_data, sr = librosa.load(temp_path, sr=None)
                self.logger.info(f"  ✓ Loaded: {len(audio_data)} samples @ {sr} Hz")
                
                # Resample if needed
                if sr != self.target_sr:
                    audio_data = resampy.resample(audio_data, sr, self.target_sr)
                    sr = self.target_sr
                    self.logger.info(f"  ✓ Resampled to {self.target_sr} Hz")
                
                # Normalize
                if len(audio_data) > 0:
                    max_val = np.abs(audio_data).max()
                    if max_val > 0:
                        audio_data = audio_data / max_val * 0.95
                    self.logger.info("  ✓ Normalized")
                
                return audio_data, sr
                    
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            self.logger.error(f"  ❌ Error preprocessing audio: {e}")
            raise

    def _build_comprehensive_result(self, reference_text, words_with_times, word_predicted_phonemes, word_alignments, reference_phonemes):
        """Build comprehensive result with all required fields"""
        word_results = []
        
        # Get transcribed text from words_with_times
        transcribed_text = " ".join([w['word'] for w in words_with_times])
        
        # Build transcribed words dict for lookup
        transcribed_words_dict = {}
        for word_info in words_with_times:
            word_clean = word_info['word'].strip('.,!?;:').upper()
            transcribed_words_dict[word_clean] = word_info
        
        # STEP 1: Đánh giá các từ trong transcribed text (logic cũ)
        transcribed_word_results = {}
        for word_info in words_with_times:
            word = word_info['word']
            word_clean = word.strip('.,!?;:').upper()
            confidence = word_info['confidence']
            
            ref_phonemes = reference_phonemes.get(word_clean, [])
            pred_phonemes = word_predicted_phonemes.get(word_clean, [])
            
            # Use pre-computed alignment if available
            if word_clean in word_alignments:
                alignment = word_alignments[word_clean]
                word_score, phoneme_acc, details = score_word(alignment)
            elif ref_phonemes and pred_phonemes:
                alignment = align_phoneme_sequences(ref_phonemes, pred_phonemes)
                word_score, phoneme_acc, details = score_word(alignment)
            else:
                word_score = confidence * 0.8
                phoneme_acc = confidence
                details = []
            
            transcribed_word_results[word_clean] = {
                'word': word_clean,
                'start': round(word_info['start'], 2),
                'end': round(word_info['end'], 2),
                'score': round(word_score * 100, 1),  # Convert to percentage
                'phoneme_accuracy': round(phoneme_acc, 2),
                'confidence': round(confidence, 2),
                'reference_phonemes': ref_phonemes,
                'predicted_phonemes': pred_phonemes,
                'phoneme_details': details
            }
        
        # STEP 2: Build final result theo thứ tự reference, thêm missing words với điểm 0
        reference_words = reference_text.upper().split()
        
        for ref_word in reference_words:
            ref_word_clean = ref_word.strip('.,!?;:').upper()
            ref_phonemes = reference_phonemes.get(ref_word_clean, [])
            
            if ref_word_clean in transcribed_word_results:
                # Từ có trong transcribed - dùng kết quả đánh giá
                word_results.append(transcribed_word_results[ref_word_clean])
            else:
                # Từ bị thiếu - điểm = 0
                word_results.append({
                    'word': ref_word_clean,
                    'start': 0,
                    'end': 0,
                    'score': 0.0,  # Điểm = 0 cho từ bị thiếu
                    'phoneme_accuracy': 0.0,
                    'confidence': 0.0,
                    'reference_phonemes': ref_phonemes,
                    'predicted_phonemes': [],
                    'phoneme_details': []
                })
        
        # Calculate sentence score
        sentence_score = np.mean([w['score'] for w in word_results]) if word_results else 0.0
        
        # Determine grade
        if sentence_score >= 90:
            grade = "Excellent"
        elif sentence_score >= 80:
            grade = "Good"  
        elif sentence_score >= 70:
            grade = "Fair"
        else:
            grade = "Needs Improvement"
        
        # Generate feedback
        feedback_parts = []
        poor_words = [w for w in word_results if w['score'] < 70]
        if poor_words:
            feedback_parts.append(f"🔍 Cần cải thiện phát âm: {', '.join([w['word'] for w in poor_words[:5]])}")
        
        good_words = [w for w in word_results if w['score'] >= 80]  
        if good_words:
            feedback_parts.append(f"✅ Phát âm tốt: {', '.join([w['word'] for w in good_words[:3]])}")
        
        if not feedback_parts:
            feedback_parts.append("Tiếp tục luyện tập để cải thiện!")
        
        feedback = " | ".join(feedback_parts)
        
        # Build word_accuracy format for compatibility
        word_accuracy = []
        for w in word_results:
            word_accuracy.append({
                'word': w['word'],
                'accuracy_percentage': w['score'],
                'pronunciation_score': w['score'],
                'rhythm_score': w['score'] * 0.9  # Mock rhythm score
            })
        
        return {
            'scores': {
                'sentence_score': round(sentence_score, 1),
                'grade': grade,
                'overall': round(sentence_score, 1),
                'pronunciation': round(sentence_score, 1),
                'fluency': round(sentence_score * 0.9, 1),
                'intonation': round(sentence_score * 0.85, 1),
                'stress': round(sentence_score * 0.8, 1)
            },
            'words': word_results,
            'word_accuracy': word_accuracy,
            'transcribed_text': transcribed_text,
            'feedback': feedback,
            'original_sentence': reference_text
        }

# ============================================================================
# CONFIGURATION
# ============================================================================

REFERENCE_TEXT =  "hello nice to meet you"
AUDIO_FILE = "1.wav"
# Input
# 

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float32" if DEVICE == "cuda" else "int8"
TARGET_SR = 16000

print(f"🎯 Device: {DEVICE}")
print(f"📝 Reference: '{REFERENCE_TEXT}'")
print(f"🎵 Audio: {AUDIO_FILE}")
print("="*80)

# ============================================================================
# STEP 1: AUDIO PREPROCESSING
# ============================================================================

def preprocess_audio(audio_path, target_sr=16000):
    """Load and preprocess audio"""
    print("\n🔧 STEP 1: Preprocessing audio...")
    
    audio_data, sr = librosa.load(audio_path, sr=None)
    print(f"  ✓ Loaded: {len(audio_data)} samples @ {sr} Hz")
    
    if sr != target_sr:
        audio_data = resampy.resample(audio_data, sr, target_sr)
        sr = target_sr
        print(f"  ✓ Resampled to {target_sr} Hz")
    
    # Normalize
    if len(audio_data) > 0:
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val * 0.95
        print(f"  ✓ Normalized")
    
    return audio_data, sr

# ============================================================================
# STEP 2: WHISPERX - WORD TIMESTAMPS
# ============================================================================

def get_word_timestamps(audio_path):
    """Get word-level timestamps using WhisperX"""
    print("\n🎤 STEP 2: WhisperX for word timestamps...")
    
    whisper_model = whisperx.load_model("small.en", DEVICE, compute_type=COMPUTE_TYPE)
    
    audio = whisperx.load_audio(audio_path)
    result = whisper_model.transcribe(audio, batch_size=8)
    print(f"  ✓ Transcribed: {result['segments'][0]['text'] if result['segments'] else 'N/A'}")
    
    align_model, metadata = whisperx.load_align_model(
        language_code=result["language"], 
        device=DEVICE
    )
    result_aligned = whisperx.align(
        result["segments"], 
        align_model, 
        metadata, 
        audio, 
        DEVICE
    )
    
    words_with_times = []
    for segment in result_aligned["segments"]:
        for word in segment.get("words", []):
            words_with_times.append({
                "word": word["word"].strip().upper(),
                "start": word["start"],
                "end": word["end"],
                "confidence": word.get("score", 0.9)
            })
    
    print(f"  ✓ Detected {len(words_with_times)} words")
    for w in words_with_times:
        print(f"    {w['word']:12} [{w['start']:.2f}s - {w['end']:.2f}s]")
    
    return words_with_times

# ============================================================================
# STEP 3: G2P - REFERENCE PHONEMES
# ============================================================================

def get_reference_phonemes(text):
    """Generate reference phonemes using G2P"""
    print("\n📚 STEP 3: Generating reference phonemes...")
    
    g2p = G2p()
    words = text.upper().split()
    
    phoneme_dict = {}
    for word in words:
        word_lower = word.lower()
        
        if word_lower in arpabet:
            phonemes = arpabet[word_lower][0]
            phonemes = [p.rstrip('012') for p in phonemes]
        else:
            phonemes = g2p(word_lower)
            phonemes = [p.upper() for p in phonemes if p.isalnum()]
        
        phoneme_dict[word] = phonemes
        print(f"  {word:12} → {' '.join(phonemes)}")
    
    return phoneme_dict

# ============================================================================
# STEP 4: WAVE2PHONEME - FULL AUDIO PHONEME PREDICTION
# ============================================================================

def load_wave2phoneme_model():
    """Load Wav2Vec2 phoneme recognition model"""
    print("\n🧠 STEP 4: Loading Wave2Phoneme model...")
    
    model_name = "facebook/wav2vec2-lv-60-espeak-cv-ft"
    
    try:
        from transformers import Wav2Vec2CTCTokenizer, Wav2Vec2FeatureExtractor
        
        tokenizer = Wav2Vec2CTCTokenizer.from_pretrained(model_name)
        feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
        
        class SimpleProcessor:
            def __init__(self, tokenizer, feature_extractor):
                self.tokenizer = tokenizer
                self.feature_extractor = feature_extractor
            
            def __call__(self, audio, sampling_rate, return_tensors="pt", padding=True):
                return self.feature_extractor(
                    audio, 
                    sampling_rate=sampling_rate, 
                    return_tensors=return_tensors, 
                    padding=padding
                )
            
            def batch_decode(self, token_ids):
                return self.tokenizer.batch_decode(token_ids)
        
        processor = SimpleProcessor(tokenizer, feature_extractor)
        model = Wav2Vec2ForCTC.from_pretrained(model_name)
        model.eval()
        
        if DEVICE == "cuda":
            model = model.to(DEVICE)
        
        print(f"  ✓ Loaded: {model_name}")
        return processor, model
        
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return None, None

# IPA to ARPAbet mapping
IPA_TO_ARPABET = {
    # Vowels
    'i': 'IY', 'iː': 'IY', 'ɪ': 'IH',
    'e': 'EY', 'eː': 'EY', 'ɛ': 'EH', 'æ': 'AE',
    'ɑ': 'AA', 'ɑː': 'AA', 'a': 'AA', 'ɐ': 'AH',
    'ɔ': 'AO', 'ɔː': 'AO', 'o': 'OW', 'oː': 'OW', 'oʊ': 'OW',
    'u': 'UW', 'uː': 'UW', 'ʊ': 'UH',
    'ʌ': 'AH', 'ə': 'AH', 'ɜ': 'ER', 'ɜː': 'ER',
    'aɪ': 'AY', 'aʊ': 'AW', 'ɔɪ': 'OY', 'eɪ': 'EY',
    # Consonants
    'p': 'P', 'b': 'B', 't': 'T', 'd': 'D', 'k': 'K', 'ɡ': 'G', 'g': 'G',
    'f': 'F', 'v': 'V', 'θ': 'TH', 'ð': 'DH',
    's': 'S', 'z': 'Z', 'ʃ': 'SH', 'ʒ': 'ZH', 'h': 'HH',
    'm': 'M', 'n': 'N', 'ŋ': 'NG',
    'l': 'L', 'r': 'R', 'w': 'W', 'j': 'Y',
    'tʃ': 'CH', 'dʒ': 'JH',
}

def ipa_to_arpabet(ipa_string):
    """Convert IPA string to ARPAbet list"""
    if not ipa_string:
        return []
    
    result = []
    i = 0
    while i < len(ipa_string):
        if i < len(ipa_string) - 1:
            two_char = ipa_string[i:i+2]
            if two_char in IPA_TO_ARPABET:
                result.append(IPA_TO_ARPABET[two_char])
                i += 2
                continue
        
        one_char = ipa_string[i]
        if one_char in IPA_TO_ARPABET:
            result.append(IPA_TO_ARPABET[one_char])
        elif one_char.isalpha():
            result.append(one_char.upper())
        
        i += 1
    
    return result

def predict_phonemes_full_audio(audio_data, sr, processor, model):
    """
    Predict phonemes from FULL audio (not segmented)
    This preserves context and avoids cutting issues
    """
    print("\n🔬 STEP 5: Predicting phonemes from FULL audio...")
    
    if processor is None or model is None:
        print("  ⚠️  No model available")
        return []
    
    try:
        # Ensure 16kHz
        if sr != 16000:
            audio_data = resampy.resample(audio_data, sr, 16000)
        
        # Process full audio
        inputs = processor(
            audio_data, 
            sampling_rate=16000, 
            return_tensors="pt", 
            padding=True
        )
        
        if isinstance(inputs, dict):
            input_values = inputs['input_values']
        else:
            input_values = inputs.input_values
        
        if DEVICE == "cuda":
            input_values = input_values.to(DEVICE)
        
        # Inference on full audio
        with torch.no_grad():
            logits = model(input_values).logits
        
        # Decode to IPA
        predicted_ids = torch.argmax(logits, dim=-1)
        ipa_phonemes = processor.batch_decode(predicted_ids)[0]
        
        print(f"  ✓ IPA output: {ipa_phonemes[:100]}...")
        
        # Convert to ARPAbet
        arpabet_phonemes = ipa_to_arpabet(ipa_phonemes)
        
        print(f"  ✓ Total phonemes predicted: {len(arpabet_phonemes)}")
        print(f"  ✓ Phoneme sequence: {' '.join(arpabet_phonemes[:20])}...")
        
        return arpabet_phonemes
    
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return []

# ============================================================================
# STEP 6: ALIGN FULL PREDICTED WITH FULL REFERENCE, THEN SPLIT BY WORDS
# ============================================================================

def align_phonemes_to_words_v2(predicted_phonemes, reference_phoneme_dict, words_with_times):
    """
    Improved alignment strategy:
    1. Build full reference phoneme sequence from words
    2. Align full predicted vs full reference using Levenshtein
    3. Split aligned sequence back into words based on reference boundaries
    """
    print("\n🎯 STEP 6: Aligning phonemes (improved method)...")
    
    if not predicted_phonemes:
        print("  ⚠️  No predicted phonemes")
        return {}
    
    # Build full reference sequence with word boundaries
    full_reference = []
    word_boundaries = []  # Track where each word starts/ends in reference
    current_pos = 0
    
    for word_info in words_with_times:
        word_clean = word_info['word'].strip('.,!?;:').upper()
        ref_phonemes = reference_phoneme_dict.get(word_clean, [])
        
        if ref_phonemes:
            word_boundaries.append({
                'word': word_clean,
                'start_idx': current_pos,
                'end_idx': current_pos + len(ref_phonemes),
                'phonemes': ref_phonemes
            })
            full_reference.extend(ref_phonemes)
            current_pos += len(ref_phonemes)
    
    print(f"  Full reference: {' '.join(full_reference)}")
    print(f"  Full predicted: {' '.join(predicted_phonemes)}")
    
    # Align full sequences
    alignment = align_phoneme_sequences(full_reference, predicted_phonemes)
    
    print(f"  Total alignment pairs: {len(alignment)}")
    
    # Split alignment back into words
    word_phonemes = {}
    word_alignments = {}
    
    ref_idx = 0
    for boundary in word_boundaries:
        word = boundary['word']
        start_idx = boundary['start_idx']
        end_idx = boundary['end_idx']
        
        # Extract alignment pairs for this word
        word_alignment = []
        word_pred_phonemes = []
        
        # Count through alignment until we've covered this word's reference phonemes
        ref_count = 0
        align_idx = ref_idx
        
        while ref_count < (end_idx - start_idx) and align_idx < len(alignment):
            ref_ph, pred_ph, is_correct = alignment[align_idx]
            
            if ref_ph != '-':  # This counts as a reference phoneme
                word_alignment.append((ref_ph, pred_ph, is_correct))
                if pred_ph != '-':
                    word_pred_phonemes.append(pred_ph)
                ref_count += 1
                align_idx += 1
            else:
                # Insertion - doesn't count toward reference but include it
                word_alignment.append((ref_ph, pred_ph, is_correct))
                if pred_ph != '-':
                    word_pred_phonemes.append(pred_ph)
                align_idx += 1
        
        ref_idx = align_idx
        
        word_phonemes[word] = word_pred_phonemes
        word_alignments[word] = word_alignment
        
        print(f"  {word:12} Ref: {' '.join(boundary['phonemes']):20} Pred: {' '.join(word_pred_phonemes)}")
    
    return word_phonemes, word_alignments

# ============================================================================
# STEP 7: PHONEME ALIGNMENT (Levenshtein)
# ============================================================================

def align_phoneme_sequences(reference, predicted):
    """Align two phoneme sequences using dynamic programming"""
    if not reference or not predicted:
        return []
    
    ref = list(reference)
    pred = list(predicted)
    
    m, n = len(ref), len(pred)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if ref[i-1] == pred[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    
    # Backtrack
    alignment = []
    i, j = m, n
    
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i-1] == pred[j-1]:
            alignment.append((ref[i-1], pred[j-1], True))
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i-1][j-1] + 1:
            alignment.append((ref[i-1], pred[j-1], False))
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or dp[i][j] == dp[i-1][j] + 1):
            alignment.append((ref[i-1], '-', False))
            i -= 1
        else:
            alignment.append(('-', pred[j-1], False))
            j -= 1
    
    alignment.reverse()
    return alignment

# ============================================================================
# STEP 8: PHONEME SCORING
# ============================================================================

def score_phoneme(ref, pred):
    """Score individual phoneme match"""
    if ref == pred:
        return 1.0
    if ref == '-' or pred == '-':
        return 0.0
    
    # Similar phonemes get partial credit
    similar_groups = [
        {'P', 'B'}, {'T', 'D'}, {'K', 'G'},
        {'F', 'V'}, {'S', 'Z'}, {'TH', 'DH'}, {'SH', 'ZH'},
        {'M', 'N', 'NG'}, {'IY', 'IH'}, {'EH', 'AE'},
        {'AH', 'AX'}, {'UW', 'UH'}, {'AO', 'AA'},
    ]
    
    for group in similar_groups:
        if ref in group and pred in group:
            return 0.5
    
    return 0.0

def score_word(alignment):
    """Calculate word score from phoneme alignment"""
    if not alignment:
        return 0.0, 0.0, []
    
    phoneme_scores = []
    details = []
    
    for ref, pred, is_correct in alignment:
        score = score_phoneme(ref, pred)
        phoneme_scores.append(score)
        
        details.append({
            'reference': ref,
            'predicted': pred,
            'score': score,
            'correct': is_correct
        })
    
    word_score = np.mean(phoneme_scores) if phoneme_scores else 0.0
    phoneme_accuracy = sum(1 for _, _, c in alignment if c) / len(alignment)
    
    return word_score, phoneme_accuracy, details

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Execute pronunciation assessment pipeline"""
    
    # STEP 1: Preprocess
    audio_data, sr = preprocess_audio(AUDIO_FILE)
    audio_duration = len(audio_data) / sr
    
    # STEP 2: WhisperX timestamps
    words_with_times = get_word_timestamps(AUDIO_FILE)
    
    # STEP 3: Reference phonemes
    reference_phonemes = get_reference_phonemes(REFERENCE_TEXT)
    
    # STEP 4: Load Wave2Phoneme model
    phoneme_processor, phoneme_model = load_wave2phoneme_model()
    
    # STEP 5: Predict phonemes from FULL audio (key improvement!)
    predicted_phonemes_full = predict_phonemes_full_audio(
        audio_data, sr, phoneme_processor, phoneme_model
    )
    
    # STEP 6: Align phonemes to words (improved method)
    word_predicted_phonemes, word_alignments = align_phonemes_to_words_v2(
        predicted_phonemes_full, 
        reference_phonemes,
        words_with_times
    )
    
    # STEP 7-8: Score each word
    print("\n📊 STEP 7-8: Scoring words...")
    word_results = []
    
    for word_info in words_with_times:
        word = word_info['word']
        word_clean = word.strip('.,!?;:').upper()
        confidence = word_info['confidence']
        
        print(f"\n  {word_clean}:")
        
        ref_phonemes = reference_phonemes.get(word_clean, [])
        pred_phonemes = word_predicted_phonemes.get(word_clean, [])
        
        print(f"    Ref:  {' '.join(ref_phonemes)}")
        print(f"    Pred: {' '.join(pred_phonemes)}")
        
        # Use pre-computed alignment if available
        if word_clean in word_alignments:
            alignment = word_alignments[word_clean]
            word_score, phoneme_acc, details = score_word(alignment)
        elif ref_phonemes and pred_phonemes:
            alignment = align_phoneme_sequences(ref_phonemes, pred_phonemes)
            word_score, phoneme_acc, details = score_word(alignment)
        else:
            word_score = confidence * 0.8
            phoneme_acc = confidence
            details = []
        
        print(f"    Score: {word_score:.2f} (acc: {phoneme_acc:.2f})")
        
        word_results.append({
            'word': word_clean,
            'start': round(word_info['start'], 2),
            'end': round(word_info['end'], 2),
            'score': round(word_score, 2),
            'phoneme_accuracy': round(phoneme_acc, 2),
            'confidence': round(confidence, 2),
            'reference_phonemes': ref_phonemes,
            'predicted_phonemes': pred_phonemes,
            'phoneme_details': details
        })
    
    # Calculate sentence score
    sentence_score = np.mean([w['score'] for w in word_results]) if word_results else 0.0
    
    if sentence_score >= 0.9:
        grade = "Excellent"
    elif sentence_score >= 0.8:
        grade = "Good"
    elif sentence_score >= 0.7:
        grade = "Fair"
    else:
        grade = "Needs Improvement"
    
    # Generate feedback
    feedback = []
    for w in word_results:
        if w['score'] < 0.7 and w['phoneme_details']:
            errors = [p for p in w['phoneme_details'] if p['score'] < 0.8 and p['reference'] != '-']
            if errors:
                error_str = ', '.join([f"{p['reference']}→{p['predicted']}" for p in errors[:3]])
                feedback.append({
                    'word': w['word'],
                    'issue': 'pronunciation_error',
                    'details': f"Phonemes need improvement: {error_str}",
                    'score': w['score']
                })
    
    # Build result
    result = {
        'metadata': {
            'reference_text': REFERENCE_TEXT,
            'audio_file': AUDIO_FILE,
            'method': 'WhisperX + Wave2Phoneme (Full Audio) + Timestamp Alignment',
            'device': DEVICE
        },
        'scores': {
            'sentence_score': round(sentence_score, 2),
            'grade': grade,
            'word_count': len(word_results),
            'avg_phoneme_accuracy': round(np.mean([w['phoneme_accuracy'] for w in word_results]), 2)
        },
        'words': word_results,
        'feedback': feedback if feedback else ['Great pronunciation!']
    }
    
    # Save
    output_file = 'pronunciation_result_v4.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"Reference: {REFERENCE_TEXT}")
    print(f"Sentence Score: {sentence_score:.2f}")
    print(f"Grade: {grade}")
    print(f"\nWords:")
    for w in word_results:
        status = "✓" if w['score'] >= 0.8 else "⚠" if w['score'] >= 0.6 else "✗"
        print(f"  {status} {w['word']:12} {w['score']:.2f} (acc: {w['phoneme_accuracy']:.2f})")
    
    if feedback:
        print(f"\n💡 Feedback:")
        for fb in feedback:
            print(f"  • {fb['word']}: {fb['details']}")
    
    print("="*80)

if __name__ == "__main__":
    main()
