# AI English Learning Server - Luồng Hoạt Động Chi Tiết

## Tổng Quan Hệ Thống

Hệ thống AI English Learning Server là một nền tảng đánh giá phát âm tiếng Anh sử dụng trí tuệ nhân tạo, được xây dựng với FastAPI và tích hợp nhiều service AI tiên tiến.

### Kiến Trúc Tổng Thể
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│   FastAPI        │───▶│   Services      │
│   (Frontend)    │    │   (main.py)      │    │   (Microservices│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌──────────────┐        ┌─────────────────┐
                       │   Models     │        │ • WhisperService│
                       │ (Data Types) │        │ • AudioService  │
                       └──────────────┘        │ • PronuncService│
                                              │ • LLMService    │
                                              └─────────────────┘
```

---

## 1. MAIN.PY - API Gateway & Orchestrator

### Chức Năng Chính
`main.py` đóng vai trò là **API Gateway** và **Service Orchestrator**, quản lý tất cả các endpoints và điều phối luồng xử lý giữa các services.

### Chi Tiết Các Endpoints

#### 1.1. `GET /` - Root Endpoint
```python
@app.get("/")
async def root():
```
- **Chức năng**: Endpoint chào mừng cơ bản
- **Response**: Thông điệp chào mừng JSON

#### 1.2. `GET /health` - Health Check
```python
@app.get("/health")
async def health_check():
```
- **Chức năng**: Kiểm tra trạng thái hoạt động của toàn bộ hệ thống
- **Response**: Trạng thái của từng service (Whisper, Pronunciation, LLM, Audio)
- **Chi tiết kiểm tra**:
  - Whisper model status và thông tin
  - Pronunciation service availability  
  - LLM service status (tạm thời disabled)
  - Audio service availability

#### 1.3. `POST /evaluate-pronunciation` - Pipeline Chính
```python
@app.post("/evaluate-pronunciation", response_model=PronunciationResponse)
async def evaluate_pronunciation(request: PronunciationRequest):
```

**LUỒNG XỬ LÝ CHI TIẾT - 5 BƯỚC:**

##### Bước 1: Validation Input
```python
if not request.audio_base64:
    raise HTTPException(status_code=400, detail="Audio data is required")
if not request.sentence:
    raise HTTPException(status_code=400, detail="Reference sentence is required")
```
- Kiểm tra dữ liệu đầu vào
- Đảm bảo có audio và câu tham chiếu

##### Bước 2: Audio Quality Analysis
```python
audio_analysis = audio_service.analyze_audio_base64(request.audio_base64)
```
- **Mục đích**: Phân tích chất lượng audio trước khi xử lý
- **Service**: `AudioService`
- **Kiểm tra**: 
  - Độ dài audio (0.5s - 30s)
  - Sample rate (≥8kHz, tối ưu 16kHz)
  - Mức âm lượng (tránh quá nhỏ/quá lớn)
  - Noise level (SNR estimation)
  - Audio clipping detection
- **Kết quả**: `AudioAnalysis` object với quality score và danh sách issues
- **Xử lý lỗi**: Reject nếu audio không đạt chất lượng tối thiểu

##### Bước 3: Speech-to-Text Transcription
```python
transcribed_text, confidence = whisper_service.transcribe_audio_base64(
    request.audio_base64
)
```
- **Mục đích**: Chuyển đổi giọng nói thành văn bản
- **Service**: `WhisperService` (model: "small")
- **Xử lý**:
  - Audio preprocessing (mono conversion, normalization)
  - Audio enhancement (boost quiet audio, remove DC offset)
  - Whisper transcription với settings tối ưu
  - Confidence calculation từ segments
- **Kết quả**: Transcribed text + confidence score (0-1)
- **Xử lý lỗi**: Reject nếu transcription thất bại

##### Bước 4: Pronunciation Evaluation  
```python
scores, word_errors, wer_score = pronunciation_service.evaluate_pronunciation(
    request.sentence, transcribed_text, confidence
)
```
- **Mục đích**: So sánh phát âm với câu tham chiếu
- **Service**: `PronunciationService`
- **Thuật toán**:
  - Phonetic conversion (text → IPA-like phonetics)
  - Word Error Rate (WER) calculation
  - Word-level error detection (substitution/insertion/deletion)
  - Scoring calculation (pronunciation/fluency/intonation/stress)
- **Kết quả**: Scores, word errors list, WER score

##### Bước 5: Error Highlighting & Feedback Generation
```python
highlighted_sentence = pronunciation_service.highlight_errors(request.sentence, word_errors)
feedback = pronunciation_service.get_feedback(scores, word_errors)

# Enhanced LLM feedback (nếu có API key)
llm_feedback = llm_service.generate_pronunciation_feedback(
    request.sentence, transcribed_text, scores, word_errors, wer_score
)
```
- **Error Highlighting**: Tạo câu với lỗi được đánh dấu
- **Built-in Feedback**: Feedback cơ bản dựa trên scores và errors
- **LLM Enhancement**: Feedback chi tiết từ Gemini AI (optional)

#### 1.4. `POST /debug-pronunciation` - Debug Pipeline
```python
@app.post("/debug-pronunciation")
async def debug_pronunciation(request: PronunciationRequest):
```
- **Chức năng**: Endpoint debug với thông tin chi tiết từng bước
- **Sử dụng**: Development và troubleshooting
- **Response**: JSON với chi tiết từng bước xử lý

---

## 2. SERVICES - Microservices Architecture

### 2.1. WhisperService (`services/whisper_service.py`)

#### Chức Năng
Speech-to-Text service sử dụng OpenAI Whisper model.

#### Methods Chi Tiết

##### `__init__(model_size="tiny")`
```python
def __init__(self, model_size: str = "tiny"):
    self.model = whisper.load_model(model_size)
```
- Load Whisper model (tiny/small/medium/large)
- Main.py sử dụng "small" cho độ chính xác tốt hơn

##### `transcribe_audio_base64(audio_base64)`
**LUỒNG XỬ LÝ:**

1. **Audio Decoding**:
   ```python
   audio_bytes = base64.b64decode(audio_base64)
   audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
   ```

2. **Audio Preprocessing**:
   ```python
   # Convert to mono
   if len(audio_data.shape) > 1:
       audio_data = np.mean(audio_data, axis=1)
   
   # Convert to float32
   audio_data = audio_data.astype(np.float32)
   ```

3. **Audio Enhancement** (`_enhance_audio()`):
   ```python
   # Remove DC offset
   audio_data = audio_data - np.mean(audio_data)
   
   # Boost quiet audio
   if rms < 0.05:
       boost_factor = 0.1 / (rms + 1e-8)
       audio_data = audio_data * boost_factor
   
   # Normalize với headroom
   audio_data = audio_data / max_val * 0.95
   ```

4. **Whisper Transcription**:
   ```python
   result = self.model.transcribe(
       audio_data,
       language="en",
       task="transcribe", 
       fp16=False,
       condition_on_previous_text=False,
       temperature=0.0,
       compression_ratio_threshold=2.4,
       logprob_threshold=-1.0,
       no_speech_threshold=0.6
   )
   ```

5. **Confidence Calculation** (`_calculate_confidence()`):
   - Sử dụng word-level probabilities từ segments
   - Convert avg_logprob thành confidence score
   - Clamp giữa 0.1-1.0

### 2.2. AudioService (`services/audio_service.py`)

#### Chức Năng
Audio quality analysis và validation service.

#### Methods Chi Tiết

##### `analyze_audio_base64(audio_base64)`
**LUỒNG PHÂN TÍCH:**

1. **Audio Loading**:
   ```python
   audio_bytes = base64.b64decode(audio_base64)
   audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
   ```

2. **Basic Info Extraction**:
   - Duration calculation: `len(audio_data) / sample_rate`
   - Channel detection và mono conversion
   - Sample rate validation

3. **Quality Analysis** (`_analyze_quality()`):

   **Duration Check**:
   ```python
   if duration < self.min_duration:  # 0.5s
       issues.append(f"Audio too short ({duration:.1f}s)")
   elif duration > self.max_duration:  # 30s  
       issues.append(f"Audio very long ({duration:.1f}s)")
   ```

   **Sample Rate Check**:
   ```python
   if sample_rate < 8000:
       issues.append(f"Low sample rate ({sample_rate}Hz)")
   elif sample_rate < 16000:
       issues.append(f"Sample rate could be higher")
   ```

   **Volume Level Check**:
   ```python
   rms_level = np.sqrt(np.mean(audio_data**2))
   if rms_level < 0.01:
       issues.append("Audio level very low")
   elif rms_level < 0.05:
       issues.append("Audio level low")
   ```

   **Clipping Detection**:
   ```python
   clipping_ratio = np.sum(np.abs(audio_data) > 0.95) / len(audio_data)
   if clipping_ratio > 0.01:
       issues.append("Audio clipping detected")
   ```

   **SNR Estimation** (`_estimate_snr()`):
   ```python
   # Frame-based energy analysis
   energies = []
   for i in range(0, len(audio) - frame_size, hop_size):
       frame = audio[i:i + frame_size]
       energy = np.sum(frame**2)
       energies.append(energy)
   
   # Noise vs Signal energy
   noise_energy = np.percentile(energies, 10)    # 10th percentile
   signal_energy = np.percentile(energies, 90)   # 90th percentile
   snr_db = 10 * np.log10(signal_energy / noise_energy)
   ```

4. **Quality Score Calculation**:
   ```python
   quality_score = np.mean(quality_factors) * 100
   ```

5. **Validation Decision**:
   ```python
   critical_issues = [issue for issue in issues if "warning" not in issue.lower()]
   is_valid = len(critical_issues) == 0
   ```

### 2.3. PronunciationService (`services/pronunciation_service.py`)

#### Chức Năng
Phonetic-based pronunciation evaluation service.

#### Phonetic Mapping System
```python
self.phonetic_map = {
    # Vowels
    'a': 'æ', 'e': 'ɛ', 'i': 'ɪ', 'o': 'ɔ', 'u': 'ʊ',
    'ai': 'aɪ', 'ay': 'eɪ', 'oo': 'u', 'ou': 'aʊ', 'ow': 'aʊ',
    
    # Consonants  
    'th': 'θ', 'sh': 'ʃ', 'ch': 'tʃ', 'ph': 'f', 'gh': 'f',
    'ck': 'k', 'qu': 'kw', 'x': 'ks', 'ng': 'ŋ'
}
```

#### Methods Chi Tiết

##### `evaluate_pronunciation(original_text, transcribed_text, confidence)`
**LUỒNG ĐÁNH GIÁ:**

1. **Phonetic Conversion**:
   ```python
   original_phonetic = self.text_to_phonetic(original_text)
   transcribed_phonetic = self.text_to_phonetic(transcribed_text)
   ```

2. **WER Calculation**:
   ```python
   wer_score = self.calculate_wer(original_phonetic, transcribed_phonetic)
   ```

3. **Word-level Error Detection**:
   ```python
   word_errors = self.get_word_errors(original_text, transcribed_text)
   ```

4. **Score Calculation**:
   ```python
   scores = self.calculate_scores(wer_score, confidence, len(word_errors))
   ```

##### `text_to_phonetic(text)`
```python
def text_to_phonetic(self, text: str) -> str:
    text = text.lower().strip()
    text = text.translate(str.maketrans('', '', string.punctuation))
    
    # Apply phonetic mappings (longest first)
    for pattern, phonetic in sorted(self.phonetic_map.items(), key=len, reverse=True):
        text = text.replace(pattern, phonetic)
    
    return ' '.join(text.split())
```

##### `get_word_errors(original, transcribed)`
**Sử dụng difflib.SequenceMatcher**:
```python
matcher = difflib.SequenceMatcher(None, orig_words, trans_words)

for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag == 'replace':  # Substitution
        # Calculate phonetic similarity
        severity = self.get_phonetic_similarity(orig_word, trans_word)
        
    elif tag == 'delete':  # Deletion (missing word)
        # Mark as missing word
        
    elif tag == 'insert':  # Insertion (extra word)  
        # Mark as extra word
```

##### `calculate_scores(wer_score, confidence, error_count)`
```python
def calculate_scores(self, wer_score: float, confidence: float, error_count: int):
    pronunciation = max(0, (1 - wer_score) * 100)
    fluency = min(100, confidence * 85 + (1 - wer_score) * 15)
    intonation = min(100, confidence * 70 + 30)  
    stress = max(30, pronunciation * 0.8 + confidence * 20)
    overall = pronunciation * 0.5 + fluency * 0.3 + intonation * 0.1 + stress * 0.1
```

##### `highlight_errors(original_text, word_errors)`
```python
def highlight_errors(self, original_text: str, word_errors: List[WordError]) -> str:
    for error in sorted(word_errors, key=lambda x: x.position, reverse=True):
        if error.error_type == "substitution":
            highlighted[error.position] = f"[❌{error.expected}→{error.actual}]"
        elif error.error_type == "deletion":
            highlighted[error.position] = f"[❌THIẾU:{error.expected}]"
        elif error.error_type == "insertion":
            highlighted.append(f"[❌THÊM:{error.actual}]")
```

### 2.4. LLMService (`services/llm_service.py`)

#### Chức Năng
AI-powered feedback generation sử dụng Google Gemini API.

#### Methods Chi Tiết

##### `__init__()`
```python
def __init__(self):
    self.gemini_api_key = os.getenv("GEMINI_API_KEY")
```
- Load API key từ `.env.new` file
- Graceful fallback nếu không có API key

##### `generate_pronunciation_feedback(...)`
**LUỒNG TẠO FEEDBACK:**

1. **Prompt Construction**:
   ```python
   error_summary = self._format_errors(word_errors)
   
   prompt = f"""As an English pronunciation teacher for Vietnamese learners:
   
   Original: "{original_sentence}"
   Student: "{transcribed_text}"
   Scores: Overall {scores.overall}/100, Pronunciation {scores.pronunciation}/100...
   Errors: {error_summary}
   
   Provide structured feedback with:
   🌟 Introduction with encouragement
   📊 Error Analysis  
   ✅ Corrective Actions
   📚 Additional Resources
   💪 Words of Encouragement
   """
   ```

2. **Gemini API Call**:
   ```python
   url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
   
   data = {
       "contents": [{"parts": [{"text": prompt}]}],
       "generationConfig": {
           "temperature": 0.7,
           "maxOutputTokens": 400,
           "candidateCount": 1
       }
   }
   ```

3. **Response Processing**:
   ```python
   if response.status_code == 200:
       result = response.json()
       return result["candidates"][0]["content"]["parts"][0]["text"].strip()
   ```

##### `_format_errors(word_errors)`
```python
def _format_errors(self, word_errors: List[WordError]) -> str:
    errors = []
    for error in word_errors[:3]:  # Top 3 errors
        if error.error_type == "substitution":
            errors.append(f"'{error.expected}' → '{error.actual}'")
        elif error.error_type == "deletion":
            errors.append(f"Missing '{error.expected}'")
        elif error.error_type == "insertion":
            errors.append(f"Extra '{error.actual}'")
    
    return "; ".join(errors)
```

---

## 3. MODELS.PY - Data Models

### 3.1. Core Models

#### `PronunciationScore`
```python
class PronunciationScore(BaseModel):
    pronunciation: float  # 0-100 - Độ chính xác phát âm
    fluency: float       # 0-100 - Độ trôi chảy
    intonation: float    # 0-100 - Ngữ điệu  
    stress: float        # 0-100 - Trọng âm
    overall: float       # 0-100 - Điểm tổng thể
```

#### `WordError`
```python
class WordError(BaseModel):
    word: str           # Từ bị lỗi
    position: int       # Vị trí trong câu (0-based)
    error_type: str     # substitution/insertion/deletion
    expected: str       # Từ mong đợi
    actual: str         # Từ thực tế
    severity: str       # low/moderate/high
```

#### `AudioAnalysis`
```python
class AudioAnalysis(BaseModel):
    is_valid: bool         # Audio có hợp lệ không
    duration: float        # Độ dài (giây)
    sample_rate: int       # Tần số lấy mẫu (Hz)
    channels: int          # Số kênh âm thanh
    issues: List[str]      # Danh sách vấn đề
    quality_score: float   # Điểm chất lượng (0-100)
```

### 3.2. Request/Response Models

#### `PronunciationRequest`
```python
class PronunciationRequest(BaseModel):
    audio_base64: str    # Audio data encoded base64
    sentence: str        # Câu tham chiếu để so sánh
```

#### `PronunciationResponse` 
```python
class PronunciationResponse(BaseModel):
    original_sentence: str        # Câu gốc
    transcribed_text: str        # Kết quả transcription
    scores: PronunciationScore   # Điểm số chi tiết
    word_errors: List[WordError] # Danh sách lỗi từng từ
    feedback: str               # Phản hồi từ AI
    wer_score: float           # Word Error Rate
    confidence: float          # Độ tin cậy của transcription
    highlighted_sentence: str  # Câu với lỗi được highlight
```

---

## 4. LUỒNG HOẠT ĐỘNG TỔNG THỂ

### 4.1. End-to-End Workflow

```
[Client] ──(audio + sentence)──▶ [FastAPI Gateway]
                                        │
                                        ▼
                                [Input Validation]
                                        │
                                        ▼
                               [AudioService Analysis]
                            ┌───── quality_score ──────┐
                            │                          ▼
                            │                    [REJECT if bad]
                            ▼
                    [WhisperService Transcription]
                    ┌────── transcribed_text ────────┐
                    │        confidence              │
                    ▼                                ▼
          [PronunciationService Evaluation]         │
          │                                         │
          ├─ Phonetic Conversion                    │
          ├─ WER Calculation                        │
          ├─ Word Error Detection                   │
          ├─ Score Calculation                      │
          └─ Error Highlighting                     │
                    │                                │
                    ▼                                ▼
           [Built-in Feedback] ──────────── [LLMService Enhancement]
                    │                                │
                    └────────────┬─────────────────────┘
                                 ▼
                         [Final Response]
                                 │
                                 ▼
                            [Client]
```

### 4.2. Error Handling Strategy

#### Level 1: Input Validation
- Missing audio/sentence → HTTP 400
- Invalid base64 encoding → HTTP 400

#### Level 2: Audio Quality Check  
- Duration too short/long → HTTP 400
- Low quality audio → HTTP 400  
- No speech detected → HTTP 400

#### Level 3: Service Failures
- Whisper transcription fails → HTTP 400
- Empty transcription → HTTP 400
- Service exceptions → HTTP 500

#### Level 4: Graceful Fallbacks
- LLM service unavailable → Use built-in feedback
- Pronunciation service errors → Return partial results
- Audio enhancement fails → Continue with original audio

### 4.3. Performance Optimizations

#### Audio Processing
- Audio enhancement for low-quality recordings
- Optimal Whisper model size (small = accuracy vs speed balance)
- Efficient audio format handling

#### Pronunciation Evaluation
- Simplified phonetic mapping for speed
- Optimized WER calculation
- Selective error highlighting  

#### LLM Integration
- Timeout handling (30s)
- Structured prompts for consistent output
- Error formatting for concise feedback
- Optional enhancement (graceful fallback)

---

## 5. CONFIGURATION & DEPLOYMENT

### 5.1. Environment Setup
```bash
# Required packages
whisper-openai>=20230124
fastapi>=0.68.0
uvicorn>=0.15.0
jiwer>=2.3.0
soundfile>=0.10.0
numpy>=1.21.0
requests>=2.25.0
```

### 5.2. Optional API Keys
```bash
# .env.new file
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5.3. Model Configuration
- **Whisper Model**: "small" (balance accuracy/speed)
- **Audio Requirements**: 0.5-30s, ≥8kHz, mono preferred
- **Language**: English only
- **Output Format**: JSON responses

### 5.4. Service Endpoints
```
POST /evaluate-pronunciation - Main evaluation pipeline
POST /debug-pronunciation   - Debug với detailed info  
GET  /health                - Service health check
GET  /                     - Welcome message
```

---

## 6. TROUBLESHOOTING

### Common Issues

#### Audio Problems
- **"Audio too short"**: Minimum 0.5 seconds required
- **"Audio level very low"**: Speak closer to microphone  
- **"High background noise"**: Find quieter environment
- **"Audio clipping"**: Reduce microphone gain

#### Transcription Issues
- **Empty transcription**: Check audio quality and clarity
- **Low confidence**: Improve audio quality or speak clearer
- **Wrong language**: System only supports English

#### Service Errors
- **LLM unavailable**: Check API key and internet connection
- **Whisper model loading**: Ensure sufficient disk space
- **Memory issues**: Consider smaller Whisper model

### Debug Tools
- Use `/debug-pronunciation` endpoint for step-by-step analysis
- Check `/health` endpoint for service status
- Monitor console logs for detailed error information

---

## Kết Luận

Hệ thống AI English Learning Server sử dụng kiến trúc microservices với luồng xử lý đa tầng, từ validation đầu vào đến AI feedback generation. Mỗi service có vai trò riêng biệt nhưng phối hợp chặt chẽ để tạo ra trải nghiệm học phát âm hoàn chỉnh và chính xác.

**Điểm mạnh chính**:
- Pipeline xử lý robust với multiple validation layers
- Graceful fallback cho service failures  
- Detailed error analysis và feedback
- Scalable architecture với clear separation of concerns
- Support cho multiple audio formats và quality levels
