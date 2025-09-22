# File: client_phonetic_test.py

import requests
import base64
from pathlib import Path
import json

# --- THAY ĐỔI QUAN TRỌNG: Cập nhật URL tới endpoint mới ---
API_URL = "http://localhost:8000/evaluate-pronunciation-phonetic"

def test_phonetic_pronunciation(audio_file_path: str, reference_sentence: str, test_name: str = "Test"):
    """
    Kiểm thử endpoint đánh giá phát âm dựa trên âm vị.
    """
    print(f"\n{'=' * 25} {test_name.upper()} {'=' * 25}")
    print(f"📄 Reference: '{reference_sentence}'")
    print(f"🎤 Audio File: '{audio_file_path}'")
    
    # Kiểm tra file tồn tại
    if not Path(audio_file_path).exists():
        print(f"❌ ERROR: Audio file not found at '{audio_file_path}'")
        return False
    
    try:
        # Mã hóa audio sang base64
        with open(audio_file_path, 'rb') as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
        
        request_data = {
            "audio_base64": audio_base64,
            "sentence": reference_sentence
        }
        
        print(f"🚀 Sending request to {API_URL}...")
        
        # Gửi yêu cầu POST
        response = requests.post(
            API_URL, 
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60  # Tăng timeout vì xử lý âm vị có thể lâu hơn
        )
        
        # Xử lý kết quả trả về
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Phonetic Analysis Report:")
            print("-" * 70)
            
            # Thông tin cơ bản
            print(f"   - Original Sentence  : {result['original_sentence']}")
            print(f"   - Transcribed Text   : {result['transcribed_text']} (Confidence: {result['confidence']:.2f})")
            
            # --- Hiển thị kết quả phân tích âm vị ---
            print("\n🎵 PHONETIC ANALYSIS (Word by Word):")
            reference_phonemes = result['reference_phonemes']
            learner_phonemes = result.get('learner_phonemes', []) # Dùng .get để an toàn
            
            # In phiên âm chuẩn
            print("   - Reference:")
            for item in reference_phonemes:
                print(f"     - {item['word']:<15}: {item['phoneme']}")
            
            # In phiên âm của người học
            print("   - Learner:")
            for item in learner_phonemes:
                print(f"     - {item['word']:<15}: {item['phoneme']}")

            # --- Hiển thị tỉ lệ accuracy từng từ ---
            word_accuracy = result.get('word_accuracy', [])
            if word_accuracy:
                print("\n📊 WORD ACCURACY ANALYSIS:")
                for i, accuracy_data in enumerate(word_accuracy, 1):
                    accuracy = accuracy_data['accuracy_percentage']
                    status_icon = "✅" if accuracy >= 90 else "⚠️" if accuracy >= 70 else "❌"
                    print(f"   {i:2d}. {status_icon} '{accuracy_data['word']:<15}': {accuracy:5.1f}%")

            # ... (phần hiển thị điểm số giữ nguyên) ...

            # --- Hiển thị lỗi sai chi tiết ---
            phoneme_errors = result['phoneme_errors']
            if phoneme_errors:
                print(f"\n⚠️  DETAILED ERROR ANALYSIS ({len(phoneme_errors)} issues found):")
                for i, error in enumerate(phoneme_errors, 1):
                    if error['type'] == 'pronunciation':
                        print(f"   {i}. 🗣️  Pronunciation Error in '{error['word']}':")
                        print(f"      - Expected: {error['expected_phoneme']}")
                        print(f"      - Got     : {error['actual_phoneme']}")
                    elif error['type'] == 'substitution':
                        print(f"   {i}. 🔄 Word Substituted: Expected '{error['expected_word']}' but got '{error['actual_word']}'")
                    # ... (Thêm các trường hợp delete, insert)
            else:
                print("\n✅ PERFECT! No errors detected!")

            # Điểm số
            scores = result['scores']
            print(f"\n📊 SCORES (Based on Phoneme Error Rate: {result['wer_score']:.3f}):")
            print(f"   - Pronunciation Score: {scores['pronunciation']:.1f}/100")
            print(f"   - Overall Score      : {scores['overall']:.1f}/100")
            
            # # --- Hiển thị lỗi sai âm vị ---
            # phoneme_errors = result['phoneme_errors']
            # if phoneme_errors:
            #     print(f"\n⚠️  PHONEME ERROR ANALYSIS ({len(phoneme_errors)} issues found):")
            #     for i, error in enumerate(phoneme_errors, 1):
            #         error_type = error['type']
            #         ref_seg = f"'{error['reference_segment']}'" if error['reference_segment'] else "''"
            #         trans_seg = f"'{error['transcribed_segment']}'" if error['transcribed_segment'] else "''"
                    
            #         if error_type == 'replace':
            #             print(f"   {i}. 🔄 SUBSTITUTION: Expected {ref_seg} but got {trans_seg}")
            #         elif error_type == 'delete':
            #             print(f"   {i}. ❌ DELETION: Missing phoneme(s) {ref_seg}")
            #         elif error_type == 'insert':
            #             print(f"   {i}. ➕ INSERTION: Extra phoneme(s) {trans_seg}")

            # else:
            #     print("\n✅ PERFECT PHONEMES! No errors detected!")
            
            # Phản hồi từ AI
            print("\n🤖 AI FEEDBACK:")
            print(f"   {result['feedback']}")
            
            print("-" * 70)
            return True
            
        else:
            print(f"❌ ERROR {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def main():
    """Hàm kiểm thử chính"""
    print("\n" + "=" * 70)
    print("   AI ENGLISH LEARNING SERVER - PHONETIC EVALUATION TEST CLIENT")
    print("=" * 70)
    
    # Các ca kiểm thử
    test_cases = [
        ("audios/teacher/today.wav", "Today is the 13th of May 2023", "TEACHER: 'Today...'"),
        ("audios/learner/today.wav", "Today is the 13th of May 2023", "LEARNER: 'Today...'"),
        ("audios/teacher/interesting.wav", "Interesting", "TEACHER: 'Interesting'"),
        ("audios/learner/interesting.wav", "Interesting", "LEARNER: 'Interesting'"),
        ("audios/teacher/youtube.wav", "I would like to watch YouTube", "TEACHER: 'YouTube'"),
        ("audios/learner/youtube.wav", "I would like to watch YouTube", "LEARNER: 'YouTube'"),
    ]
    
    successful_tests = 0
    
    for audio_file, reference, test_name in test_cases:
        if test_phonetic_pronunciation(audio_file, reference, test_name):
            successful_tests += 1
    
    # Tổng kết
    print(f"\n{'=' * 30} TESTING SUMMARY {'=' * 30}")
    print(f"  Total tests run: {len(test_cases)}")
    print(f"  Successful tests: {successful_tests}")
    success_rate = (successful_tests / len(test_cases)) * 100 if test_cases else 0
    print(f"  Success Rate: {success_rate:.1f}%")
    print("=" * 78)

if __name__ == "__main__":
    main()