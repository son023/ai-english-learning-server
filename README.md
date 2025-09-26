# AI English Learning Server

🚀 **Nền tảng học phát âm tiếng Anh với AI thông minh**

Hệ thống sử dụng GOPT (Goodness of Pronunciation Transformer) để đánh giá phát âm chi tiết với các chỉ số: pronunciation, fluency, intonation, stress.

## ✨ Tính năng chính

- 🎯 **Đánh giá phát âm chính xác** với GOPT AI model
- 🎤 **Ghi âm và nhận diện** bằng Whisper AI
- 📊 **Phân tích chi tiết**: pronunciation, fluency, intonation, stress
- 🤖 **Phản hồi thông minh** từ LLM (OpenAI GPT)
- 🎨 **Giao diện web đẹp** với React + TailwindCSS
- 📱 **Responsive design** tương thích mọi thiết bị

## 🏗️ Kiến trúc hệ thống

### Backend (FastAPI)
- **Whisper**: Speech-to-text
- **GOPT**: Pronunciation assessment  
- **eSpeak-ng**: Phoneme generation
- **OpenAI GPT**: Intelligent feedback
- **FastAPI**: RESTful API

### Frontend (React)
- **React 18**: Modern UI framework
- **TailwindCSS**: Beautiful styling
- **Vite**: Fast development
- **Axios**: API communication

## 🚀 Cài đặt và chạy

### Yêu cầu hệ thống
- Python 3.8+
- Node.js 16+ (cho frontend)
- eSpeak-ng
- CUDA (optional, cho GPU acceleration)

### 1. Cài đặt eSpeak-ng
Tải và cài đặt:
```
https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-X64.msi
```

### 2. Setup Backend

#### Cài đặt dependencies
```bash
pip install -r requirements.txt
```

#### Cấu hình OpenAI API Key
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

#### Đảm bảo có GOPT model
File `best_audio_model.pth` phải có trong thư mục root.

#### Chạy backend server
```bash
python main.py
```
Backend sẽ chạy tại: `http://localhost:8000`

### 3. Setup Frontend

#### Vào thư mục frontend
```bash
cd frontend
```

#### Cài đặt dependencies
```bash
npm install
```

#### Chạy development server
```bash
npm run dev
```
Frontend sẽ chạy tại: `http://localhost:3000`

## 📋 API Documentation

### Endpoint chính: `/evaluate-pronunciation-phonetic`

**Request:**
```json
{
  "audio_base64": "base64_encoded_audio",
  "sentence": "Hello everyone, welcome to our session today."
}
```

**Response:**
```json
{
  "original_sentence": "Hello everyone...",
  "transcribed_text": "Hello everyone...",
  "scores": {
    "pronunciation": 85.2,
    "fluency": 78.5,
    "intonation": 82.1,
    "stress": 79.3,
    "overall": 81.3
  },
  "word_accuracy": [...],
  "feedback": "Your pronunciation is quite good...",
  "confidence": 0.95
}
```

### Truy cập API docs
Mở trình duyệt: `http://localhost:8000/docs`

## 🎮 Cách sử dụng

1. **Khởi động backend và frontend**
2. **Mở `http://localhost:3000`**
3. **Nhập hoặc chỉnh sửa câu cần luyện**
4. **Click "Nghe mẫu"** để nghe phát âm chuẩn
5. **Click "Bắt đầu ghi âm"** và nói câu đó
6. **Click "Gửi đánh giá"** để AI phân tích
7. **Xem kết quả chi tiết** và cải thiện

## 🔧 Cấu hình

### Backend Services
- `WhisperService`: Speech recognition
- `GOPTService`: Pronunciation assessment
- `PronunciationService`: Phoneme analysis  
- `LLMService`: AI feedback generation

### Frontend Components
- `PronunciationPractice`: Main component
- Responsive design với TailwindCSS
- Real-time audio recording
- Beautiful result visualization

## 📊 Đánh giá GOPT

GOPT model cung cấp đánh giá đa cấp độ:

- **Utterance Level**: Điểm tổng quát cho cả câu
- **Phone Level**: Điểm cho từng âm vị
- **Word Level**: Điểm cho từng từ
- **Pronunciation**: Độ chính xác phát âm
- **Fluency**: Độ lưu loát
- **Prosodic**: Ngữ điệu (intonation)
- **Completeness**: Độ hoàn thiện (stress)

## 🚨 Troubleshooting

### Backend issues
- Đảm bảo `best_audio_model.pth` tồn tại
- Kiểm tra eSpeak-ng đã cài đặt đúng
- Verify OpenAI API key

### Frontend issues  
- Kiểm tra backend đang chạy trên port 8000
- Allow microphone permissions
- Clear browser cache

## 📞 Liên hệ

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub repository.