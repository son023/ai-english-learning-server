import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Mic,
  MicOff,
  Send,
  RotateCcw,
  Volume2,
  Play,
  Loader2,
  RefreshCw,
  Trophy,
  Target,
  CheckCircle2,
  XCircle,
  AlertCircle,
  BookOpen,
} from "lucide-react";
import axios from "axios";
import HeaderNav from "./HeaderNav";
import WordResult from "./WordResult";

const API_BASE_URL = "http://localhost:8000";

// ===== IndexedDB Helper Functions =====
const DB_NAME = "PronunciationAppDB";
const STORE_NAME = "wordPracticeHistory";

const initDB = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 2); // Tăng version lên 2
    request.onerror = () => reject("Error opening DB");
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Tạo store cho PronunciationPractice nếu chưa có
      if (!db.objectStoreNames.contains("practiceHistory")) {
        db.createObjectStore("practiceHistory", {
          keyPath: "id",
          autoIncrement: true,
        });
      }
      
      // Tạo store cho WordPronunciationLearning
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, {
          keyPath: "id",
          autoIncrement: true,
        });
      }
    };
  });
};

const saveDataToDB = (db, data) => {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.put(data);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject("Error saving data");
  });
};

const getAllDataFromDB = (db) => {
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], "readonly");
    const store = transaction.objectStore(STORE_NAME);
    const request = store.getAll();
    request.onsuccess = () => resolve(request.result.reverse()); // Sắp xếp mới nhất lên đầu
    request.onerror = () => reject("Error fetching data");
  });
};
// =====================================


// Danh sách từ mẫu để luyện tập
const SAMPLE_WORDS = [
  { word: "hello", level: "Cơ bản", category: "Chào hỏi" },
  { word: "world", level: "Cơ bản", category: "Danh từ" },
  { word: "pronunciation", level: "Khó", category: "Giáo dục" },
  { word: "beautiful", level: "Trung bình", category: "Tính từ" },
  { word: "communication", level: "Khó", category: "Kỹ năng" },
  { word: "development", level: "Khó", category: "Phát triển" },
  { word: "important", level: "Trung bình", category: "Tính từ" },
  { word: "technology", level: "Trung bình", category: "Công nghệ" },
  { word: "understand", level: "Trung bình", category: "Động từ" },
  { word: "opportunity", level: "Khó", category: "Danh từ" },
];

const WordSuggestions = ({ onSelectWord, currentWord }) => (
  <div>
    <div className="flex items-center gap-3 mb-4">
      <Target className="w-6 h-6 text-indigo-600" />
      <h4 className="text-lg font-semibold text-gray-800">Từ gợi ý luyện tập</h4>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      {SAMPLE_WORDS.map((item, index) => (
        <button
          key={index}
          onClick={() => onSelectWord(item.word)}
          className={`p-3 text-sm rounded-lg border-2 transition-all shadow-sm hover:shadow-md transform hover:scale-105 ${
            currentWord === item.word 
              ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white border-blue-500 shadow-lg' 
              : 'bg-white border-gray-200 text-gray-700 hover:border-blue-300 hover:bg-blue-50'
          }`}
          title={`${item.category} - Độ khó: ${item.level}`}
        >
          <div className="font-medium">{item.word}</div>
          <div className={`text-xs ${currentWord === item.word ? 'text-blue-100' : 'text-gray-500'}`}>
            {item.level}
          </div>
        </button>
      ))}
    </div>
  </div>
);

const WordPronunciationLearning = ({ page, setPage }) => {
  const [word, setWord] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [validationError, setValidationError] = useState("");
  const [showResultsModal, setShowResultsModal] = useState(false);
  
  // History states
  const [practiceHistory, setPracticeHistory] = useState([]);
  const [historyAudioUrl, setHistoryAudioUrl] = useState(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const dbRef = useRef(null);
  const mainPracticeAreaRef = useRef(null);

  // Khởi tạo DB khi component mount
  useEffect(() => {
    const setupDB = async () => {
      try {
        console.log("WordPronunciationLearning: Initializing DB...");
        const db = await initDB();
        dbRef.current = db;
        console.log("WordPronunciationLearning: DB initialized, loading history...");
        const historyData = await getAllDataFromDB(db);
        console.log("WordPronunciationLearning: History loaded:", historyData);
        setPracticeHistory(historyData);
      } catch (error) {
        console.error("WordPronunciationLearning: Failed to initialize DB:", error);
      }
    };
    setupDB();
  }, []);

  const saveToHistory = async (newResults, newAudioBlob) => {
    if (!dbRef.current) {
      console.log("WordPronunciationLearning: No DB connection, cannot save history");
      return;
    }
    const newEntry = {
      results: newResults,
      audioBlob: newAudioBlob,
      date: new Date().toISOString(),
    };
    try {
      console.log("WordPronunciationLearning: Saving to history:", newEntry.results.word);
      await saveDataToDB(dbRef.current, newEntry);
      const updatedHistory = await getAllDataFromDB(dbRef.current);
      console.log("WordPronunciationLearning: Updated history:", updatedHistory);
      // Giới hạn lịch sử 10 mục
      if (updatedHistory.length > 10) {
        const transaction = dbRef.current.transaction([STORE_NAME], "readwrite");
        const store = transaction.objectStore(STORE_NAME);
        store.delete(updatedHistory[updatedHistory.length - 1].id);
        setPracticeHistory(updatedHistory.slice(0, 10));
      } else {
        setPracticeHistory(updatedHistory);
      }
    } catch (error) {
      console.error("WordPronunciationLearning: Failed to save history:", error);
    }
  };

  // Validation cho input từ
  const validateWord = (inputWord) => {
    if (!inputWord.trim()) {
      return "Vui lòng nhập một từ tiếng Anh";
    }
    if (inputWord.trim().split(' ').length > 1) {
      return "Chỉ được nhập một từ đơn";
    }
    if (!/^[a-zA-Z'-]+$/.test(inputWord.trim())) {
      return "Từ chỉ được chứa các ký tự a-z, A-Z, dấu nháy và gạch nối";
    }
    return "";
  };

  const handleWordChange = (e) => {
    const newWord = e.target.value;
    setWord(newWord);
    setValidationError(validateWord(newWord));
    if (result) setResult(null); // Clear previous results
  };

  const handleSelectWord = (selectedWord) => {
    setWord(selectedWord);
    setValidationError(validateWord(selectedWord));
    if (result) setResult(null); // Clear previous results
  };

  const startRecording = async () => {
    if (!word.trim() || validationError) {
      setValidationError(validateWord(word));
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Try to use WAV format first, fallback to WebM if not supported
      let options;
      if (MediaRecorder.isTypeSupported("audio/wav")) {
        options = { mimeType: "audio/wav" };
      } else if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        options = { mimeType: "audio/webm;codecs=opus" };
      } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        options = { mimeType: "audio/webm" };
      } else {
        options = {}; // Let browser choose default
      }
      
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const mimeType = mediaRecorderRef.current.mimeType || "audio/webm";
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        setAudioBlob(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start(100);
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Không thể truy cập microphone. Vui lòng kiểm tra quyền truy cập.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const evaluatePronunciation = async () => {
    if (!audioBlob || !word.trim()) return;

    setIsLoading(true);
    try {
      // Convert audio blob to base64
      const arrayBuffer = await audioBlob.arrayBuffer();
      const base64Audio = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

      console.log("Sending audio data:", {
        audioSize: arrayBuffer.byteLength,
        audioType: audioBlob.type,
        word: word.trim()
      });

      const response = await axios.post(`${API_BASE_URL}/evaluate-word-pronunciation`, {
        audio_base64: base64Audio,
        transcribe: word.trim()
      });

      console.log("Received response:", response.data);
      setResult(response.data);
      setShowResultsModal(true);
      
      // Lưu vào lịch sử
      await saveToHistory(response.data, audioBlob);
    } catch (error) {
      console.error("Error evaluating pronunciation:", error);
      
      let errorMessage = "Có lỗi xảy ra khi đánh giá phát âm.";
      
      if (error.response) {
        // Server responded with error status
        if (error.response.status === 500) {
          errorMessage = "Lỗi xử lý audio trên server. Vui lòng thử ghi âm lại.";
        } else if (error.response.status === 400) {
          errorMessage = "Dữ liệu audio không hợp lệ. Vui lòng thử lại.";
        } else {
          errorMessage = `Lỗi server (${error.response.status}). Vui lòng thử lại.`;
        }
      } else if (error.request) {
        // Network error
        errorMessage = "Không thể kết nối đến server. Kiểm tra kết nối mạng.";
      }
      
      alert(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const resetAll = useCallback(() => {
    setWord("");
    setAudioBlob(null);
    setResult(null);
    setValidationError("");
    setShowResultsModal(false);
    if (isRecording) {
      stopRecording();
    }
    if (historyAudioUrl) {
      URL.revokeObjectURL(historyAudioUrl);
      setHistoryAudioUrl(null);
    }
  }, [isRecording, historyAudioUrl]);

  const resetWithoutClearingWord = useCallback(() => {
    setAudioBlob(null);
    setResult(null);
    setValidationError("");
    setShowResultsModal(false);
    if (isRecording) {
      stopRecording();
    }
    if (historyAudioUrl) {
      URL.revokeObjectURL(historyAudioUrl);
      setHistoryAudioUrl(null);
    }
  }, [isRecording, historyAudioUrl]);

  // Hàm để handle click vào item lịch sử
  const handleHistoryItemClick = (historyItem) => {
    setResult(historyItem.results);
    if (historyAudioUrl) {
      URL.revokeObjectURL(historyAudioUrl);
    }
    const newAudioUrl = URL.createObjectURL(historyItem.audioBlob);
    setHistoryAudioUrl(newAudioUrl);
    setShowResultsModal(true);
  };

  // Hàm để luyện lại từ
  const handlePracticeAgain = (selectedWord) => {
    setWord(selectedWord);
    resetWithoutClearingWord();
    mainPracticeAreaRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Hàm tính màu điểm số
  const getScoreColor = (score) => {
    if (score >= 90) return "score-excellent";
    if (score >= 75) return "score-good";
    if (score >= 60) return "score-fair";
    return "score-poor";
  };

  const playRecordedAudio = () => {
    if (audioBlob) {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play().catch(console.error);
    }
  };

  const playWordPronunciation = () => {
    if (!word.trim() || validationError) return;
    
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(word.trim());
      utterance.lang = 'en-US';
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    } else {
      alert('Trình duyệt không hỗ trợ text-to-speech');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <HeaderNav 
        title="AI English Pronunciation Practice" 
        page={page} 
        setPage={setPage}
      />

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
          <section ref={mainPracticeAreaRef} className="md:col-span-2 space-y-6 overflow-y-auto pr-4 scroll-mt-4">
            {/* Word Suggestions */}
            <article className="card p-6">
              <WordSuggestions onSelectWord={handleSelectWord} currentWord={word} />
            </article>

            {/* Input Section */}
            <article className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-800">Nhập từ muốn luyện</h2>
                <button
                  onClick={playWordPronunciation}
                  disabled={!word.trim() || validationError}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                    !word.trim() || validationError
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700 transform hover:scale-105 shadow-md'
                  }`}
                  title="Nghe cách phát âm chuẩn của từ này"
                >
                  <Volume2 size={18} />
                  <span className="text-sm">Nghe từ</span>
                </button>
              </div>
          
          <div className="space-y-4">
            <div>
              <input
                type="text"
                value={word}
                onChange={handleWordChange}
                placeholder="Ví dụ: hello, world, pronunciation..."
                className={`w-full p-4 text-lg border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  validationError ? 'border-red-500' : 'border-gray-300'
                }`}
                spellCheck={true}
              />
              {validationError && (
                <p className="text-red-500 text-sm mt-2">{validationError}</p>
              )}
            </div>

            <div className="flex flex-col items-center space-y-4">
              <div className="flex justify-center">
                {!isRecording ? (
                  <button
                    onClick={startRecording}
                    disabled={!word.trim() || validationError || isLoading}
                    className={`flex items-center gap-3 px-8 py-4 rounded-full font-semibold shadow-lg transition-all ${
                      !word.trim() || validationError || isLoading
                        ? 'bg-gray-400 text-gray-600 cursor-not-allowed opacity-50'
                        : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 transform hover:scale-105'
                    }`}
                  >
                    <Mic size={24} />
                    {!word.trim() || validationError ? 'Sửa lỗi để ghi âm' : 'Bắt đầu ghi âm'}
                  </button>
                ) : (
                  <button
                    onClick={stopRecording}
                    className="flex items-center gap-3 bg-gradient-to-r from-red-500 to-pink-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-red-600 hover:to-pink-700 transform hover:scale-105 transition-all animate-pulse"
                  >
                    <MicOff size={24} />
                    Dừng ghi âm
                  </button>
                )}
              </div>

              {(!word.trim() || validationError) && (
                <div className="text-center">
                  <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg border border-red-200">
                    Vui lòng nhập từ hợp lệ trước khi ghi âm
                  </p>
                </div>
              )}

              {audioBlob && (
                <div className="flex flex-wrap justify-center gap-3 pt-4">
                  <button
                    onClick={playRecordedAudio}
                    className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-6 py-3 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all"
                  >
                    <Play size={18} />
                    Nghe lại
                  </button>
                  <button
                    onClick={evaluatePronunciation}
                    disabled={isLoading}
                    className="btn-primary flex items-center gap-2"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="animate-spin" />
                        Đang xử lý...
                      </>
                    ) : (
                      <>
                        <Send size={18} />
                        Gửi đánh giá
                      </>
                    )}
                  </button>
                  <button
                    onClick={resetAll}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <RotateCcw size={18} />
                    Thử lại
                  </button>
                </div>
              )}
             </div>
           </div>
         </article>

         {/* Instructions */}
         {!showResultsModal && (
           <article className="card p-6">
             <div className="flex items-center gap-3 mb-4">
               <BookOpen className="w-6 h-6 text-indigo-600" />
               <h3 className="text-lg font-semibold text-gray-800">Hướng dẫn sử dụng</h3>
             </div>
             <ul className="space-y-2 text-gray-700">
               <li className="flex items-start gap-2">
                 <span className="font-bold text-indigo-600">1.</span>
                 <span>Nhập một từ tiếng Anh bạn muốn luyện phát âm</span>
               </li>
               <li className="flex items-start gap-2">
                 <span className="font-bold text-indigo-600">2.</span>
                 <span>Nhấn "Bắt đầu ghi âm" và phát âm từ đó rõ ràng</span>
               </li>
               <li className="flex items-start gap-2">
                 <span className="font-bold text-indigo-600">3.</span>
                 <span>Nhấn "Dừng ghi âm" khi đã phát âm xong</span>
               </li>
               <li className="flex items-start gap-2">
                 <span className="font-bold text-indigo-600">4.</span>
                 <span>Nhấn "Đánh giá phát âm" để xem kết quả chi tiết</span>
               </li>
             </ul>
           </article>
         )}
         </section>

         {/* History Panel */}
         <aside className="card p-4 space-y-4 overflow-y-auto">
           <div className="flex items-center gap-3">
             <BookOpen className="w-6 h-6 text-indigo-600" />
             <h3 className="text-lg font-semibold text-gray-800">
               Lịch sử luyện tập ({practiceHistory.length})
             </h3>
           </div>
           {practiceHistory.length > 0 ? (
             <ul className="space-y-3">
               {practiceHistory.map((item) => (
                 <li key={item.id} className="border border-gray-200 rounded-lg p-3 mb-3 last:mb-0 hover:shadow-md transition-all bg-white">
                   <div className="space-y-3">
                     <div className="flex items-center justify-between">
                       <div className="flex items-center gap-2">
                         <BookOpen size={16} className="text-indigo-500" />
                         <p className="text-sm font-semibold text-gray-800">
                           "{item.results.word}"
                         </p>
                       </div>
                       <span
                         className={`text-xs font-bold px-3 py-1 rounded-full ${
                           item.results.pronunciation_score >= 90 
                             ? 'bg-green-500 text-white'
                             : item.results.pronunciation_score >= 75
                             ? 'bg-blue-500 text-white'
                             : item.results.pronunciation_score >= 60
                             ? 'bg-yellow-500 text-white'
                             : 'bg-red-500 text-white'
                         }`}>
                         {item.results.pronunciation_score.toFixed(1)}/100
                       </span>
                     </div>
                     <div className="flex justify-between items-center">
                       <div className="text-xs text-gray-500">
                         {item.results.correct_phonemes}/{item.results.total_phonemes} phonemes đúng
                       </div>
                       <div className="flex items-center gap-2">
                         <button
                           onClick={() => handlePracticeAgain(item.results.word)}
                           className="flex items-center gap-1 text-xs bg-gradient-to-r from-green-500 to-emerald-600 text-white px-3 py-1.5 rounded-md hover:from-green-600 hover:to-emerald-700 transform hover:scale-105 transition-all shadow-sm"
                           title="Luyện tập lại từ này">
                           <RefreshCw size={12} />
                           <span className="font-medium">Luyện lại</span>
                         </button>
                         <button
                           onClick={() => handleHistoryItemClick(item)}
                           className="text-xs text-gray-600 hover:text-gray-900 font-medium px-3 py-1.5 rounded-md hover:bg-gray-100 border border-gray-200 hover:border-gray-300 transition-all"
                           title="Xem chi tiết kết quả">
                           Chi tiết
                         </button>
                       </div>
                     </div>
                   </div>
                 </li>
               ))}
             </ul>
           ) : (
             <p className="text-sm text-gray-500 text-center pt-4">
               Chưa có lịch sử luyện tập.
             </p>
           )}
         </aside>
       </div>

       {/* Results Modal */}
       <WordResult
         show={showResultsModal}
         results={result}
         onClose={() => {
           setShowResultsModal(false);
           if (historyAudioUrl) {
             URL.revokeObjectURL(historyAudioUrl);
             setHistoryAudioUrl(null);
           }
         }}
         historyAudioUrl={historyAudioUrl}
         onPracticeAgain={handlePracticeAgain}
       />
       </main>
     </div>
  );
};

export default WordPronunciationLearning;
