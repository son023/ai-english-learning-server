import os
from typing import List
from models import PronunciationScore, WordError
import requests

# Load environment variables from .env.new file
def load_env_new():
    """Load environment variables from .env.new file"""
    try:
        import os
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.new')
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except Exception as e:
        print(f"Warning: Could not load .env.new file: {e}")

load_env_new()

class LLMService:
    """LLM service sử dụng Gemini API để tạo phản hồi phát âm bằng tiếng Việt"""
    
    def __init__(self):
        """Initialize LLM service"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if self.gemini_api_key:
            print("LLM service đã khởi tạo với Gemini API - Phản hồi bằng tiếng Việt")
        else:
            print("LLM service đã khởi tạo nhưng không có API key - Sử dụng feedback mặc định")
    
    def generate_pronunciation_feedback(self,
                                      original_sentence: str,
                                      transcribed_text: str,
                                      scores: PronunciationScore,
                                      word_errors: List[WordError],
                                      wer_score: float) -> str:
        """Tạo phản hồi phát âm bằng tiếng Việt từ Gemini AI"""
        
        # Return empty if no API key
        if not self.gemini_api_key:
            return ""
        
        try:
            # Tạo prompt chi tiết bằng tiếng Việt
            error_summary = self._format_errors(word_errors)
            
            prompt = f"""Bạn là một giáo viên tiếng Anh chuyên nghiệp, chuyên giúp học viên người Việt cải thiện phát âm. Hãy cung cấp phản hồi chi tiết, mang tính xây dựng về lỗi phát âm với cách tiếp cận động viên và giáo dục.

**Thông tin học viên:**
- Ngôn ngữ mẹ đẻ: Tiếng Việt
- Câu mục tiêu: "{original_sentence}"
- Cách phát âm của học viên: "{transcribed_text}"
- Điểm phát âm: Tổng thể {scores.overall}/100, Phát âm {scores.pronunciation}/100, Độ trôi chảy {scores.fluency}/100, Ngữ điệu {scores.intonation}/100, Trọng âm {scores.stress}/100
- Lỗi phát hiện: {error_summary}

**Hướng dẫn:** Viết báo cáo phản hồi toàn diện theo cấu trúc chính xác sau đây (bằng tiếng Việt):

**Phản Hồi Về Lỗi Phát Âm Và Chiến Lược Cải Thiện 🌟**

**Lời Giới Thiệu:**
Cung cấp lời động viên về hành trình học tiếng Anh của họ, thừa nhận nỗ lực và tạo ra tông màu tích cực cho việc cải thiện.

**Phân Tích Lỗi:**
Đối với mỗi lỗi phát âm được phát hiện:
1. Xác định rõ ràng từ nào được phát âm sai (mong đợi vs thực tế)
2. Giải thích sự khác biệt ngữ âm cụ thể, sử dụng ký hiệu IPA khi hữu ích
3. Cung cấp giải thích ngôn ngữ học về lý do người Việt thường mắc lỗi này
4. Đề cập đến tác động lên giao tiếp/hiểu biết

**Hành Động Khắc Phục:**
Đối với mỗi lỗi, cung cấp các bài tập cụ thể, thực tế:
1. Kỹ thuật phát âm từng bước
2. Hướng dẫn vị trí miệng/lưỡi
3. Phương pháp luyện tập (ghi âm, lặp lại, cặp từ tối thiểu)
4. Tiến triển từ âm riêng lẻ đến từ đến câu

**Tài Nguyên Bổ Sung:**
- Đề xuất các công cụ trực tuyến, ứng dụng hoặc trang web cụ thể để luyện phát âm
- Khuyến nghị các bài tập phù hợp với người Việt học tiếng Anh
- Đề cập đến các kỹ thuật hữu ích như shadowing, drills ngữ âm, v.v.

**Lời Động Viên:**
Kết thúc bằng thông điệp động viên nhấn mạnh tiến bộ, sự kiên trì và tư duy tích cực. Sử dụng emoji khích lệ.

**Yêu cầu:**
- Giữ dưới 500 từ nhưng phải kỹ lưỡng và cụ thể
- Sử dụng giọng điệu hỗ trợ, giáo dục xuyên suốt
- Bao gồm emoji liên quan để làm cho phản hồi hấp dẫn
- Tập trung vào lời khuyên có thể hành động mà học viên có thể áp dụng ngay lập tức
- Thừa nhận tiến bộ và nỗ lực của họ

Hãy tạo phản hồi bằng tiếng Việt:"""

            # Call Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 600,
                    "candidateCount": 1
                }
            }
            
            response = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            return ""
                
        except Exception as e:
            print(f"Tạo phản hồi LLM thất bại: {e}")
            return ""
    
    def _format_errors(self, word_errors: List[WordError]) -> str:
        """Định dạng lỗi từ cho prompt"""
        if not word_errors:
            return "Không phát hiện lỗi đáng kể"
        
        errors = []
        for error in word_errors[:3]:  # Top 3 errors
            if error.error_type == "substitution":
                errors.append(f"'{error.expected}' → '{error.actual}'")
            elif error.error_type == "deletion":
                errors.append(f"Missing '{error.expected}'")
            elif error.error_type == "insertion":
                errors.append(f"Extra '{error.actual}'")
        
        return "; ".join(errors)