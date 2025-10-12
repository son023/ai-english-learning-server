// src/components/PronunciationPractice.jsx

import React, { useState, useRef, useEffect } from "react"; // LỖI ĐÃ ĐƯỢC SỬA Ở ĐÂY
import {
  Mic,
  MicOff,
  Send,
  RotateCcw,
  Volume2,
  Play,
  X,
  History,
} from "lucide-react";
import axios from "axios";

// Helper functions for LocalStorage
const HISTORY_KEY = "pronunciationHistory";

const getHistory = () => {
  try {
    const historyJson = localStorage.getItem(HISTORY_KEY);
    return historyJson ? JSON.parse(historyJson) : [];
  } catch (error) {
    console.error("Could not get history from LocalStorage", error);
    return [];
  }
};

const saveToHistory = (newItem) => {
  try {
    const history = getHistory();
    const updatedHistory = [newItem, ...history].slice(0, 20); // Keep last 20 items
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updatedHistory));
  } catch (error) {
    console.error("Could not save to history in LocalStorage", error);
  }
};

const PronunciationPractice = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [practiceText, setPracticeText] = useState(
    "Hello everyone, welcome to our English pronunciation practice session today."
  );
  const [showResultsModal, setShowResultsModal] = useState(false);

  // New states for new features
  const [activePhoneme, setActivePhoneme] = useState({ word: "", phoneme: "" });
  const [history, setHistory] = useState([]);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioUrlRef = useRef(null);

  // Load history from localStorage when component mounts
  useEffect(() => {
    setHistory(getHistory());
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      let options = { mimeType: "audio/webm;codecs=opus" };
      if (MediaRecorder.isTypeSupported("audio/wav"))
        options = { mimeType: "audio/wav" };
      else if (MediaRecorder.isTypeSupported("audio/webm"))
        options = { mimeType: "audio/webm" };
      else if (MediaRecorder.isTypeSupported("audio/mp4"))
        options = { mimeType: "audio/mp4" };

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType,
        });
        setAudioBlob(audioBlob);
        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = URL.createObjectURL(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };
      mediaRecorder.start();
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

  const convertToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64data = reader.result.split(",")[1];
        resolve(base64data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const submitAudio = async () => {
    if (!audioBlob) {
      alert("Vui lòng ghi âm trước khi gửi!");
      return;
    }
    setIsLoading(true);
    try {
      const base64Audio = await convertToBase64(audioBlob);
      const response = await axios.post(
        "http://localhost:8000/evaluate-pronunciation-phonetic",
        {
          audio_base64: base64Audio,
          sentence: practiceText,
        }
      );
      setResults(response.data);
      setShowResultsModal(true);

      const newItem = {
        id: Date.now(),
        sentence: practiceText,
        date: new Date().toISOString(),
        audioBase64: `data:${audioBlob.type};base64,${base64Audio}`,
        results: response.data,
      };
      saveToHistory(newItem);
      setHistory(getHistory());
    } catch (error) {
      console.error("Error submitting audio:", error);
      alert("Có lỗi xảy ra khi gửi âm thanh. Vui lòng thử lại.");
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setAudioBlob(null);
    setResults(null);
    setIsRecording(false);
    setActivePhoneme({ word: "", phoneme: "" });
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  };

  const playRecordedAudio = () => {
    if (audioUrlRef.current) {
      const audio = new Audio(audioUrlRef.current);
      audio.play().catch((e) => console.error("Error playing audio:", e));
    }
  };

  const handleWordClick = (word, phoneme) => {
    if ("speechSynthesis" in window && word && word.trim() !== "") {
      const utterance = new SpeechSynthesisUtterance(
        word.replace(/[.,!?]/g, "")
      );
      utterance.lang = "en-US";
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    }
    setActivePhoneme({ word, phoneme });
  };

  const getScoreColor = (score) => {
    if (score >= 90) return "score-excellent";
    if (score >= 75) return "score-good";
    if (score >= 60) return "score-fair";
    return "score-poor";
  };

  const getScoreLabel = (score) => {
    if (score >= 90) return "Xuất sắc";
    if (score >= 75) return "Tốt";
    if (score >= 60) return "Khá";
    return "Cần cải thiện";
  };

  const playTextToSpeech = () => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(practiceText);
      utterance.lang = "en-US";
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    }
  };

  const renderColoredPracticeTextWithPhonemes = () => {
    if (!results?.word_accuracy?.length) {
      const words = practiceText.split(/(\s+)/);
      return (
        <div>
          <p className="text-lg text-gray-800 leading-relaxed font-medium">
            {words.map((word, index) => {
              if (word.trim() === "") return <span key={index}>{word}</span>;
              return (
                <span
                  key={index}
                  className="cursor-pointer hover:bg-blue-100 rounded px-1 transition-colors"
                  onClick={() =>
                    handleWordClick(word, "Chưa có dữ liệu phoneme")
                  }>
                  {word}
                </span>
              );
            })}
          </p>
          {activePhoneme.word && (
            <div className="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg animate-fade-in">
              <span className="font-bold text-indigo-800">
                {activePhoneme.word}:{" "}
              </span>
              <span className="text-lg text-indigo-600 font-mono">
                {activePhoneme.phoneme}
              </span>
            </div>
          )}
        </div>
      );
    }
    return (
      <div>
        <p className="text-lg text-gray-800 leading-relaxed font-medium">
          {results.word_accuracy.map((wordData, index) => {
            const { word, accuracy_percentage } = wordData;

            // SỬA LỖI: Lấy phoneme theo index, không dùng .find()
            const phonemeData = results.reference_phonemes[index];

            let colorClass = "text-gray-700";
            if (accuracy_percentage >= 90)
              colorClass = "text-green-600 font-medium";
            else if (accuracy_percentage >= 75) colorClass = "text-blue-600";
            else if (accuracy_percentage >= 60) colorClass = "text-yellow-600";
            else colorClass = "text-red-600 font-semibold";
            return (
              <span
                key={index}
                className={`cursor-pointer hover:bg-blue-100 rounded px-1 transition-colors ${colorClass}`}
                onClick={() =>
                  handleWordClick(
                    word,
                    phonemeData?.phoneme || "Không tìm thấy"
                  )
                }>
                {word}{" "}
              </span>
            );
          })}
        </p>
        {activePhoneme.word && (
          <div className="mt-4 p-3 bg-indigo-50 border border-indigo-200 rounded-lg animate-fade-in">
            <span className="font-bold text-indigo-800">
              {activePhoneme.word}:{" "}
            </span>
            <span className="text-lg text-indigo-600 font-mono">
              {activePhoneme.phoneme}
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              AI English Pronunciation Practice
            </h1>
            <p className="text-gray-600 mt-1">
              Luyện tập phát âm tiếng Anh với AI thông minh
            </p>
          </div>
          <button
            onClick={() => setShowHistoryModal(true)}
            className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold px-4 py-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400"
            aria-label="Xem lịch sử luyện tập">
            <History size={20} />
            Lịch sử
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6 h-[calc(100vh-140px)]">
          <section className="space-y-6 overflow-y-auto">
            <article
              className="card p-6"
              role="region"
              aria-labelledby="practice-heading">
              <div className="flex items-center justify-between mb-4">
                <h2
                  id="practice-heading"
                  className="text-xl font-semibold text-gray-800">
                  Câu cần luyện tập
                </h2>
                <button
                  onClick={playTextToSpeech}
                  className="flex items-center gap-2 text-blue-600 hover:text-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg px-2 py-1"
                  aria-label="Nghe phát âm mẫu">
                  <Volume2 size={20} />
                  <span className="text-sm">Nghe mẫu</span>
                </button>
              </div>
              <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 mb-4 border border-gray-200">
                {renderColoredPracticeTextWithPhonemes()}
              </div>
              <label htmlFor="practice-input" className="sr-only">
                Nhập câu luyện tập
              </label>
              <textarea
                id="practice-input"
                value={practiceText}
                onChange={(e) => setPracticeText(e.target.value)}
                className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-all duration-200"
                rows="4"
                placeholder="Nhập câu bạn muốn luyện tập phát âm..."
              />
            </article>

            <article
              className="card p-6"
              role="region"
              aria-labelledby="recording-heading">
              <h2
                id="recording-heading"
                className="text-xl font-semibold text-gray-800 mb-6">
                Ghi âm phát âm
              </h2>
              <div className="flex flex-col items-center space-y-4">
                <div className="flex justify-center">
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      className="flex items-center gap-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-green-600 hover:to-emerald-700 transform hover:scale-105 transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-green-300"
                      aria-label="Bắt đầu ghi âm">
                      <Mic size={24} />
                      Bắt đầu ghi âm
                    </button>
                  ) : (
                    <button
                      onClick={stopRecording}
                      className="flex items-center gap-3 bg-gradient-to-r from-red-500 to-pink-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-red-600 hover:to-pink-700 transform hover:scale-105 transition-all duration-200 animate-pulse-slow focus:outline-none focus:ring-4 focus:ring-red-300"
                      aria-label="Dừng ghi âm">
                      <MicOff size={24} />
                      Dừng ghi âm
                    </button>
                  )}
                </div>
                {audioBlob && (
                  <div className="flex flex-wrap justify-center gap-3">
                    <button
                      onClick={playRecordedAudio}
                      className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold shadow-md hover:from-purple-600 hover:to-indigo-700 transform hover:scale-105 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-300"
                      aria-label="Nghe lại audio vừa ghi">
                      <Play size={18} />
                      Nghe lại
                    </button>
                    <button
                      onClick={submitAudio}
                      disabled={isLoading}
                      className="btn-primary flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
                      aria-label="Gửi audio để đánh giá">
                      {isLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
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
                      onClick={reset}
                      className="btn-secondary flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                      aria-label="Thử lại từ đầu">
                      <RotateCcw size={18} />
                      Thử lại
                    </button>
                  </div>
                )}
                {audioBlob && (
                  <div className="flex justify-center">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                      <span className="text-green-700 font-medium">
                        Đã ghi âm thành công!
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </article>
          </section>

          {showResultsModal && results && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center"
              role="dialog"
              aria-modal="true"
              aria-labelledby="results-heading"
              onClick={(e) => {
                if (e.target === e.currentTarget) setShowResultsModal(false);
              }}>
              <div className="absolute inset-0 bg-black/50" />
              <div className="relative bg-white rounded-xl shadow-2xl w-[70vw] max-w-[70vw] max-h-[85vh] overflow-y-auto border">
                <div className="sticky top-0 flex items-center justify-between p-4 border-b bg-white rounded-t-xl">
                  <h2
                    id="results-heading"
                    className="text-xl font-semibold text-gray-800">
                    Kết quả đánh giá
                  </h2>
                  <button
                    onClick={() => setShowResultsModal(false)}
                    className="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    aria-label="Đóng">
                    <X size={20} />
                  </button>
                </div>
                <div className="p-6">
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-lg font-medium">
                        Điểm tổng quát
                      </span>
                      <span className="text-3xl font-bold text-gray-800">
                        {results.scores?.overall?.toFixed(1) || 0}/100
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                      <div
                        className={`h-4 rounded-full ${getScoreColor(
                          results.scores?.overall || 0
                        )} transition-all duration-1000 ease-out`}
                        style={{ width: `${results.scores?.overall || 0}%` }}
                        role="progressbar"
                        aria-valuenow={results.scores?.overall || 0}
                        aria-valuemin="0"
                        aria-valuemax="100"></div>
                    </div>
                    <p className="text-center font-semibold text-gray-700">
                      {getScoreLabel(results.scores?.overall || 0)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 text-center border border-blue-200">
                      <div className="text-2xl font-bold text-blue-600 mb-1">
                        {results.scores?.pronunciation?.toFixed(1) || 0}/100
                      </div>
                      <div className="text-sm font-medium text-blue-800">
                        Phát âm
                      </div>
                      <div className="text-xs text-blue-600 mt-1">
                        Pronunciation
                      </div>
                    </div>
                    <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 text-center border border-green-200">
                      <div className="text-2xl font-bold text-green-600 mb-1">
                        {results.scores?.fluency?.toFixed(1) || 0}/100
                      </div>
                      <div className="text-sm font-medium text-green-800">
                        Lưu loát
                      </div>
                      <div className="text-xs text-green-600 mt-1">Fluency</div>
                    </div>
                    <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 text-center border border-purple-200">
                      <div className="text-2xl font-bold text-purple-600 mb-1">
                        {results.scores?.intonation?.toFixed(1) || 0}/100
                      </div>
                      <div className="text-sm font-medium text-purple-800">
                        Ngữ điệu
                      </div>
                      <div className="text-xs text-purple-600 mt-1">
                        Intonation
                      </div>
                    </div>
                    <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4 text-center border border-orange-200">
                      <div className="text-2xl font-bold text-orange-600 mb-1">
                        {results.scores?.stress?.toFixed(1) || 0}/100
                      </div>
                      <div className="text-sm font-medium text-orange-800">
                        Trọng âm
                      </div>
                      <div className="text-xs text-orange-600 mt-1">Stress</div>
                    </div>
                  </div>
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-3">
                      Văn bản nhận diện
                    </h3>
                    <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-200">
                      <p className="text-gray-800 italic font-medium">
                        "{results.transcribed_text}"
                      </p>
                    </div>
                  </div>
                  {results.feedback && (
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-gray-800 mb-3">
                        Nhận xét từ AI
                      </h3>
                      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                        <p className="text-gray-700 leading-relaxed">
                          {results.feedback}
                        </p>
                      </div>
                    </div>
                  )}
                  {results.word_accuracy &&
                    results.word_accuracy.length > 0 && (
                      <div>
                        <h3 className="text-lg font-semibold text-gray-800 mb-3">
                          Độ chính xác từng từ
                        </h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                          {results.word_accuracy.map((wordData, index) => (
                            <div
                              key={index}
                              className="bg-gray-50 rounded-lg p-3 text-center border border-gray-200 hover:shadow-md transition-shadow">
                              <div className="text-sm font-medium text-gray-800 mb-1 truncate">
                                {wordData.word}
                              </div>
                              <div
                                className={`text-lg font-bold ${
                                  wordData.accuracy_percentage >= 90
                                    ? "text-green-600"
                                    : wordData.accuracy_percentage >= 75
                                    ? "text-blue-600"
                                    : wordData.accuracy_percentage >= 60
                                    ? "text-yellow-600"
                                    : "text-red-600"
                                }`}>
                                {wordData.accuracy_percentage?.toFixed(0) || 0}%
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              </div>
            </div>
          )}

          {showHistoryModal && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center"
              onClick={(e) => {
                if (e.target === e.currentTarget) setShowHistoryModal(false);
              }}>
              <div className="absolute inset-0 bg-black/50" />
              <div className="relative bg-white rounded-xl shadow-2xl w-[90vw] max-w-2xl max-h-[85vh] flex flex-col">
                <div className="sticky top-0 flex items-center justify-between p-4 border-b bg-white rounded-t-xl">
                  <h2 className="text-xl font-semibold text-gray-800">
                    Lịch sử luyện tập
                  </h2>
                  <button
                    onClick={() => setShowHistoryModal(false)}
                    className="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    aria-label="Đóng">
                    <X size={20} />
                  </button>
                </div>
                <div className="p-6 overflow-y-auto">
                  {history.length > 0 ? (
                    <ul className="space-y-4">
                      {history.map((item) => (
                        <li
                          key={item.id}
                          className="p-4 border rounded-lg hover:bg-gray-50">
                          <p className="font-semibold text-gray-700 break-words">
                            "{item.sentence}"
                          </p>
                          <p className="text-sm text-gray-500 mt-1">
                            {new Date(item.date).toLocaleString("vi-VN")}
                          </p>
                          <p className="text-sm text-gray-500">
                            Điểm tổng quát:{" "}
                            <span className="font-bold">
                              {item.results.scores.overall.toFixed(1)}/100
                            </span>
                          </p>
                          <button
                            onClick={() => {
                              if (item.audioBase64) {
                                const audio = new Audio(item.audioBase64);
                                audio.play();
                              }
                            }}
                            className="mt-2 flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm font-semibold">
                            <Play size={16} /> Nghe lại
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-center text-gray-500">
                      Chưa có lịch sử luyện tập.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default PronunciationPractice;
