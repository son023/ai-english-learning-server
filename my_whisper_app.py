# D:\STP\whisper\my_whisper_app.py

import whisper
import jiwer
import string

# Tải model một lần duy nhất để tối ưu hiệu năng
print("Loading Whisper model...")
model = whisper.load_model("tiny.en")
print("Whisper model loaded.")

def process_text_to_words(text: str) -> list[str]:
    """
    Hàm xử lý text: chuyển chữ thường, xóa dấu câu, tách từ.
    """
    if not isinstance(text, str):
        return [] # Trả về list rỗng nếu đầu vào không phải là string
    text = text.lower().strip()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return [word for word in text.split() if word]

def evaluate_pronunciation_wer(audio_path, reference_text):
    """
    PHIÊN BẢN ỔN ĐỊNH: Dùng jiwer.wer để tính điểm, tự so sánh từ để highlight.
    """
    # 1. Chuyển đổi audio thành text
    result = model.transcribe(audio_path)
    user_transcript = result["text"]

    # 2. Xử lý text thành danh sách các từ
    ref_words = process_text_to_words(reference_text)
    user_words = process_text_to_words(user_transcript)

    # Xử lý trường hợp câu rỗng
    if not ref_words:
        return {"pronunciation_score": 0, "wer": 1.0, "words": []}

    # 3. Dùng jiwer.wer để tính điểm (ổn định)
    # Nối các từ lại thành chuỗi để đưa vào hàm wer
    error = jiwer.wer(" ".join(ref_words), " ".join(user_words))
    score = max(0, (1 - error) * 100)

    # 4. Tự so sánh từ để highlight (đơn giản và ổn định)
    words_result = []
    len_ref = len(ref_words)
    len_user = len(user_words)
    max_len = max(len_ref, len_user) # Xét theo độ dài lớn hơn để không bỏ sót

    for i in range(len_ref):
        ref_word = ref_words[i]
        if i < len_user:
            user_word = user_words[i]
            if ref_word == user_word:
                words_result.append({"word": ref_word, "status": "correct"})
            else:
                words_result.append({
                    "word": ref_word,
                    "status": "mispronounced",
                    "pronounced_as": user_word
                })
        else:
            # Nếu người dùng nói ít từ hơn câu gốc
            words_result.append({"word": ref_word, "status": "missing"})

    return {
        "pronunciation_score": round(score, 2),
        "reference_text": reference_text,
        "user_transcript": user_transcript.strip(),
        "wer": error,
        "words": words_result
    }

# ... (phần if __name__ == "__main__" giữ nguyên) ...