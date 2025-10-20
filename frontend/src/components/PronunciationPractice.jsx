import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  Mic,
  MicOff,
  Send,
  RotateCcw,
  Volume2,
  Play,
  X,
  BookOpen,
  Loader2,
  RefreshCw,
} from "lucide-react";
import axios from "axios";
import HeaderNav from "./HeaderNav";
import Result from "./Result";
import WordPhonemeComparison from "./WordPhonemeComparison";

// ===== IndexedDB Helper Functions =====
const DB_NAME = "PronunciationAppDB";
const STORE_NAME = "practiceHistory";

const initDB = () => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onerror = () => reject("Error opening DB");
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
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

const PhonemeTooltip = ({ word, phoneme, onClose }) => (
  <div
    className="absolute bottom-full mb-2 w-max max-w-xs bg-gray-800 text-white text-sm rounded-lg py-2 px-4 shadow-lg z-20"
    onClick={(e) => e.stopPropagation()}>
    <span className="font-bold">{word}:</span>{" "}
    <span className="italic">/{phoneme}/</span>
    <button
      onClick={onClose}
      className="absolute -top-1 -right-1 p-1 text-gray-400 hover:text-white bg-gray-700 rounded-full w-5 h-5 flex items-center justify-center">
      &times;
    </button>
  </div>
);


const PronunciationPractice = ({ page, setPage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [practiceText, setPracticeText] = useState(
    "Hello everyone, welcome to our English pronunciation practice session today."
  );
  const [showResultsModal, setShowResultsModal] = useState(false);

  const [referencePhonemes, setReferencePhonemes] = useState([]);
  const [isFetchingPhonemes, setIsFetchingPhonemes] = useState(false);
  const [tooltipData, setTooltipData] = useState(null);

  const [practiceHistory, setPracticeHistory] = useState([]);
  // Cập nhật: Thêm state để quản lý audio và modal của lịch sử
  const [historyAudioUrl, setHistoryAudioUrl] = useState(null);
  
  // Validation states
  const [validationErrors, setValidationErrors] = useState({
    required: false,
    format: false,
    length: false,
    specialChars: false
  });
  const [isValidInput, setIsValidInput] = useState(true);

  const mainPracticeAreaRef = useRef(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioUrlRef = useRef(null);
  const dbRef = useRef(null);

  // Validation functions
  const validateInput = (text) => {
    const errors = {
      required: false,
      format: false,
      length: false,
      specialChars: false
    };

    if (!text.trim()) {
      errors.required = true;
    }

    if (text.trim()) {
      const englishPattern = /^[a-zA-Z0-9\s.,!?'"()-]+$/;
      if (!englishPattern.test(text)) {
        errors.format = true;
      }

      if (text.length < 10 || text.length > 500) {
        errors.length = true;
      }

      const specialCharPattern = /[^a-zA-Z0-9\s.,!?'"()-]/g;
      const specialCharMatches = text.match(specialCharPattern);
      if (specialCharMatches && specialCharMatches.length > 5) {
        errors.specialChars = true;
      }
    }

    return errors;
  };

  const isValidFormat = (text) => {
    const errors = validateInput(text);
    return !Object.values(errors).some(error => error);
  };

  // Khởi tạo DB khi component mount
  useEffect(() => {
    const setupDB = async () => {
      try {
        const db = await initDB();
        dbRef.current = db;
        const historyData = await getAllDataFromDB(db);
        setPracticeHistory(historyData);
      } catch (error) {
        console.error("Failed to initialize DB:", error);
      }
    };
    setupDB();
  }, []);

  useEffect(() => {
    const fetchPhonemes = async () => {
      if (!practiceText.trim()) {
        setReferencePhonemes([]);
        return;
      }
      setIsFetchingPhonemes(true);
      setTooltipData(null);
      try {
        const response = await axios.post(
          "http://localhost:8000/phonemes-for-sentence",
          { sentence: practiceText }
        );
        const phonemesWithSpaces = response.data.phonemes.map(
          (p, index, arr) => ({
            ...p,
            spacing:
              index < arr.length - 1 && /[\w']/.test(arr[index + 1].word)
                ? " "
                : "",
          })
        );
        setReferencePhonemes(phonemesWithSpaces);
      } catch (error) {
        console.error("Failed to fetch phonemes for sentence:", error);
        setReferencePhonemes([]);
      } finally {
        setIsFetchingPhonemes(false);
      }
    };

    const debounceTimeout = setTimeout(fetchPhonemes, 500);
    return () => clearTimeout(debounceTimeout);
  }, [practiceText]);

  useEffect(() => {
    const errors = validateInput(practiceText);
    setValidationErrors(errors);
    setIsValidInput(!Object.values(errors).some(error => error));
  }, [practiceText]);

  const saveToHistory = async (newResults, newAudioBlob) => {
    if (!dbRef.current) return;
    const newEntry = {
      results: newResults,
      audioBlob: newAudioBlob,
      date: new Date().toISOString(),
    };
    try {
      await saveDataToDB(dbRef.current, newEntry);
      const updatedHistory = await getAllDataFromDB(dbRef.current);
      // Giới hạn lịch sử 10 mục
      if (updatedHistory.length > 10) {
        const transaction = dbRef.current.transaction(
          [STORE_NAME],
          "readwrite"
        );
        const store = transaction.objectStore(STORE_NAME);
        store.delete(updatedHistory[updatedHistory.length - 1].id);
        setPracticeHistory(updatedHistory.slice(0, 10));
      } else {
        setPracticeHistory(updatedHistory);
      }
    } catch (error) {
      console.error("Failed to save history:", error);
    }
  };

  const startRecording = async () => {
    if (!isValidInput || !isValidFormat(practiceText)) {
      alert("Vui lòng sửa lỗi trong câu nhập trước khi ghi âm!");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (e) =>
        e.data.size > 0 && audioChunksRef.current.push(e.data);
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setAudioBlob(blob);
        if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = URL.createObjectURL(blob);
        stream.getTracks().forEach((track) => track.stop());
      };
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      alert("Không thể truy cập microphone.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const convertToBase64 = (blob) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result.split(",")[1]);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });

  const handleSubmitAudio = async () => {
    if (!audioBlob) return;

    if (!isValidInput || !isValidFormat(practiceText)) {
      alert("Câu nhập sai chính tả hoặc không hợp lệ! Vui lòng kiểm tra lại.");
      return;
    }

    await submitAudio();
  };

  const submitAudio = async () => {
    setIsLoading(true);
    try {
      const base64Audio = await convertToBase64(audioBlob);
      const response = await axios.post(
        "http://localhost:8000/evaluate-pronunciation-phonetic",
        { audio_base64: base64Audio, sentence: practiceText }
      );
      setResults(response.data);
      setShowResultsModal(true);
      // Cập nhật: Lưu cả results và audioBlob
      saveToHistory(response.data, audioBlob);
    } catch (error) {
      alert("Có lỗi xảy ra khi gửi âm thanh.");
    } finally {
      setIsLoading(false);
    }
  };

  const reset = useCallback(() => {
    setAudioBlob(null);
    setResults(null);
    setIsRecording(false);
    setTooltipData(null);
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
    if (historyAudioUrl) {
      URL.revokeObjectURL(historyAudioUrl);
      setHistoryAudioUrl(null);
    }
  }, [historyAudioUrl]);

  const playRecordedAudio = () =>
    audioUrlRef.current && new Audio(audioUrlRef.current).play();

  const getScoreColor = (score) => {
    if (score >= 90) return "score-excellent";
    if (score >= 75) return "score-good";
    if (score >= 60) return "score-fair";
    return "score-poor";
  };

  const playTextToSpeech = (text) => {
    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "en-US";
      utterance.rate = 0.8;
      speechSynthesis.speak(utterance);
    }
  };

  const handleWordClick = (word, phoneme, index) => {
    if (isFetchingPhonemes) return;
    if (phoneme) {
      playTextToSpeech(word);
      setTooltipData({ index, word, phoneme });
    } else {
      setTooltipData(null);
    }
  };

  // Cập nhật: Xử lý khi bấm vào một mục trong lịch sử
  const handleHistoryItemClick = (historyItem) => {
    setResults(historyItem.results);
    if (historyAudioUrl) {
      URL.revokeObjectURL(historyAudioUrl);
    }
    const newAudioUrl = URL.createObjectURL(historyItem.audioBlob);
    setHistoryAudioUrl(newAudioUrl);
    setShowResultsModal(true);
  };

  const handlePracticeAgain = (sentence) => {
    setPracticeText(sentence);
    reset();
    mainPracticeAreaRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  const renderColoredPracticeTextWithPhonemes = () => {
    const refPhonemes = results.reference_phonemes || [];
    const learnerPhonemes = results.learner_phonemes || [];
    const alignment = results.phoneme_alignment || [];

    // Tạo map để track phoneme nào có match (dùng chung cho cả 2 câu)
    const phonemeMatchMap = new Map();
    alignment.forEach((item) => {
      if (item.ref) {
        // Nếu chưa có hoặc item hiện tại is_match = true thì update
        // Ưu tiên is_match = true (nếu có ít nhất 1 match thì coi là đúng)
        const existing = phonemeMatchMap.get(item.ref);
        if (!existing || item.is_match) {
          phonemeMatchMap.set(item.ref, item.is_match);
        }
      }
    });

    const renderReferenceSentence = () => {
      return refPhonemes.map((wordData, index) => {
        // Kiểm tra xem phoneme có match không
        const hasMatch = phonemeMatchMap.get(wordData.phoneme);
        const isError = hasMatch === false;  // Chỉ đỏ khi explicitly false

        return (
          <span
            key={`ref-word-${index}`}
            className={`inline-block px-3 py-1 m-1 rounded-md font-medium ${
              isError
                ? "bg-red-100 text-red-700 border border-red-300"
                : "bg-green-50 text-green-700 border border-green-200"
            }`}
          >
            {wordData.word}
          </span>
        );
      });
    };

    const renderLearnerSentence = () => {
      const displayedIndices = new Set();  // Track theo INDEX thay vì phoneme text
      const results = [];

      // Bước 1: Hiển thị các từ theo alignment với reference
      alignment.forEach((item, index) => {
        if (!item.learner) {
          results.push(
            <span
              key={`learner-missing-${index}`}
              className="inline-block px-3 py-1 m-1 rounded-md bg-gray-100 border border-gray-300"
            >
              <span className="text-gray-400 font-mono">____</span>
            </span>
          );
          return;
        }

        // Tìm INDEX của learner word trong learnerPhonemes (chưa được hiển thị)
        let learnerWordIndex = -1;
        for (let i = 0; i < learnerPhonemes.length; i++) {
          if (learnerPhonemes[i].phoneme === item.learner && !displayedIndices.has(i)) {
            learnerWordIndex = i;
            break;
          }
        }

        // Nếu đã hiển thị tất cả instances của phoneme này → ô trống
        if (learnerWordIndex === -1) {
          results.push(
            <span
              key={`learner-duplicate-${index}`}
              className="inline-block px-3 py-1 m-1 rounded-md bg-gray-100 border border-gray-300"
            >
              <span className="text-gray-400 font-mono">____</span>
            </span>
          );
          return;
        }

        // Đánh dấu index này đã hiển thị
        displayedIndices.add(learnerWordIndex);

        const learnerWord = learnerPhonemes[learnerWordIndex];
        const isError = !item.is_match;

        results.push(
          <span
            key={`learner-word-${index}`}
            className={`inline-block px-3 py-1 m-1 rounded-md font-medium ${
              isError
                ? "bg-red-100 text-red-700 border border-red-300"
                : "bg-green-50 text-green-700 border border-green-200"
            }`}
          >
            {learnerWord.word}
          </span>
        );
      });

      // Bước 2: Thêm các từ THỪA (extra words user nói nhưng không có trong alignment)
      learnerPhonemes.forEach((learnerWord, index) => {
        if (!displayedIndices.has(index)) {
          results.push(
            <span
              key={`learner-extra-${index}`}
              className="inline-block px-3 py-1 m-1 rounded-md font-medium bg-orange-100 text-orange-700 border border-orange-300"
            >
              {learnerWord.word}
            </span>
          );
        }
      });

      return results;
    };

    return (
      <div className="space-y-4">
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-2 flex items-center gap-2">
            <span>Câu chuẩn (Reference)</span>
            <span className="text-xs text-gray-500 font-normal">
              - Đỏ: phát âm sai, Xanh: phát âm đúng.
            </span>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            {renderReferenceSentence()}
          </div>
        </div>

        <div>
          <div className="text-sm font-semibold text-gray-600 mb-2 flex items-center gap-2">
            <span>Câu bạn đọc (Your pronunciation)</span>
            <span className="text-xs text-gray-500 font-normal">
              - <span className="font-mono bg-gray-100 px-1 rounded">____</span>
              : Thiếu từ.
            </span>
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            {renderLearnerSentence()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div
      className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100"
      onClick={() => setTooltipData(null)}>
      <HeaderNav
        title="AI English Pronunciation Practice"
        page={page}
        setPage={setPage}
      />
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[calc(100vh-140px)]">
          <section ref={mainPracticeAreaRef} className="md:col-span-2 space-y-6 overflow-y-auto pr-4 scroll-mt-4">
            <article className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-800">
                  Câu cần luyện tập
                </h2>
                <button
                  onClick={() => playTextToSpeech(practiceText)}
                  className="flex items-center gap-2 text-blue-600 hover:text-blue-700">
                  <Volume2 size={20} />{" "}
                  <span className="text-sm">Nghe cả câu</span>
                </button>
              </div>
              <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 mb-4 border border-gray-200 min-h-[80px] relative">
                {isFetchingPhonemes && (
                  <div className="absolute inset-0 bg-white/50 flex items-center justify-center">
                    <Loader2 className="animate-spin text-blue-500" />
                  </div>
                )}
                <div className="text-lg text-gray-800 leading-relaxed font-medium">
                  {referencePhonemes.map(
                    ({ word, phoneme, spacing }, index) => (
                      <span
                        key={index}
                        className="relative"
                        onClick={(e) => e.stopPropagation()}>
                        <span
                          onClick={() => handleWordClick(word, phoneme, index)}
                          className={
                            phoneme
                              ? "cursor-pointer hover:bg-blue-100 rounded p-1 transition-colors"
                              : ""
                          }>
                          {word}
                        </span>
                        {tooltipData && tooltipData.index === index && (
                          <PhonemeTooltip
                            word={tooltipData.word}
                            phoneme={tooltipData.phoneme}
                            onClose={() => setTooltipData(null)}
                          />
                        )}
                        {spacing}
                      </span>
                    )
                  )}
                </div>
              </div>
              <textarea
                value={practiceText}
                onChange={(e) => {
                  setPracticeText(e.target.value);
                  reset();
                }}
                className={`w-full p-4 border rounded-lg ${
                  !isValidInput 
                    ? 'border-red-300 bg-red-50' 
                    : 'border-gray-300'
                }`}
                rows="4"
                placeholder="Nhập câu bạn muốn luyện tập... (10-500 ký tự, chỉ tiếng Anh)"
                spellCheck={true}
              />
              
              {/* Spell check hint */}
              <div className="mt-1 text-xs text-gray-500 flex items-center gap-1">
                Trình duyệt sẽ tự động gạch chân các từ sai chính tả
              </div>
              
              {/* Validation errors display */}
              {!isValidInput && (
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <h4 className="text-sm font-semibold text-red-800 mb-2">
                    Vui lòng sửa các lỗi sau:
                  </h4>
                  <ul className="text-sm text-red-700 space-y-1">
                    {validationErrors.required && (
                      <li>• Vui lòng nhập câu cần luyện tập</li>
                    )}
                    {validationErrors.format && (
                      <li>• Chỉ được sử dụng chữ cái tiếng Anh, số và dấu câu cơ bản</li>
                    )}
                    {validationErrors.length && (
                      <li>• Câu phải có độ dài từ 10-500 ký tự</li>
                    )}
                    {validationErrors.specialChars && (
                      <li>• Quá nhiều ký tự đặc biệt (tối đa 5 ký tự)</li>
                    )}
                  </ul>
                </div>
              )}
            </article>
            <article className="card p-6">
              <div className="flex flex-col items-center space-y-4">
                <div className="flex justify-center">
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      disabled={!isValidInput}
                      className={`flex items-center gap-3 px-8 py-4 rounded-full font-semibold shadow-lg transition-all ${
                        !isValidInput
                        ? 'bg-gray-400 text-gray-600 cursor-not-allowed opacity-50'
                        : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white hover:from-green-600 hover:to-emerald-700 transform hover:scale-105'
                    }`}>
                    <Mic size={24} /> 
                    {!isValidInput ? 'Sửa lỗi để ghi âm' : 'Bắt đầu ghi âm'}
                    </button>
                  ) : (
                    <button
                      onClick={stopRecording}
                      className="flex items-center gap-3 bg-gradient-to-r from-red-500 to-pink-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-red-600 hover:to-pink-700 transform hover:scale-105 transition-all animate-pulse-slow">
                      <MicOff size={24} /> Dừng ghi âm
                    </button>
                  )}
                </div>
                
                {/* Validation message for recording */}
                {!isValidInput && (
                  <div className="text-center">
                    <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg border border-red-200">
                    Vui lòng sửa các lỗi trong câu nhập trước khi ghi âm
                    </p>
                  </div>
                )}

                {audioBlob && (
                  <div className="flex flex-wrap justify-center gap-3 pt-4">
                    <button
                      onClick={playRecordedAudio}
                      className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all">
                      <Play size={18} /> Nghe lại
                    </button>
                    <button
                      onClick={handleSubmitAudio}
                      disabled={isLoading || !isValidInput}
                      className={`btn-primary flex items-center gap-2 ${!isValidInput ? 'opacity-50 cursor-not-allowed' : ''}`}>
                      {isLoading ? (
                        <>
                          <Loader2 className="animate-spin" />
                          Đang xử lý...
                        </>
                      ) : (
                        <>
                          <Send size={18} /> Gửi đánh giá
                        </>
                      )}
                    </button>
                    <button
                      onClick={reset}
                      className="btn-secondary flex items-center gap-2">
                      <RotateCcw size={18} /> Thử lại
                    </button>
                  </div>
                )}
              </div>
            </article>
          </section>

          <aside className="card p-4 space-y-4 overflow-y-auto">
            <div className="flex items-center gap-3">
              {" "}
              <BookOpen className="w-6 h-6 text-indigo-600" />{" "}
              <h3 className="text-lg font-semibold text-gray-800">
                Lịch sử luyện tập
              </h3>
            </div>
            {practiceHistory.length > 0 ? (
              <ul className="space-y-3">
                {practiceHistory.map((item) => (
                  <li key={item.id} className="border-b pb-3 last:border-b-0">
                    {/* <button
                      onClick={() => handleHistoryItemClick(item)}
                      className="w-full text-left p-2 rounded-md hover:bg-gray-100">
                      <p className="text-sm text-gray-700 truncate">
                        {item.results.original_sentence}
                      </p>
                      <div className="flex justify-between items-center mt-1">
                        <span
                          className={`text-xs font-bold ${getScoreColor(
                            item.results.scores.overall
                          )} bg-opacity-80 text-white px-2 py-0.5 rounded-full`}>
                          {item.results.scores.overall.toFixed(1)}/100
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(item.date).toLocaleDateString("vi-VN")}
                        </span>
                      </div>
                    </button>
                     */}
                    <div className="p-2 rounded-md">
                      <p className="text-sm text-gray-700 truncate mb-2">
                        {item.results.original_sentence}
                      </p>
                      <div className="flex justify-between items-center">
                        <span
                          className={`text-xs font-bold ${getScoreColor(
                            item.results.scores.overall
                          )} bg-opacity-80 text-white px-2 py-0.5 rounded-full`}>
                          {item.results.scores.overall.toFixed(1)}/100
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handlePracticeAgain(item.results.original_sentence)}
                            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 p-1 rounded-md hover:bg-blue-100"
                            title="Luyện tập lại câu này">
                            <RefreshCw size={14} />
                            <span>Luyện lại</span>
                          </button>
                          <button
                            onClick={() => handleHistoryItemClick(item)}
                            className="text-xs text-gray-600 hover:text-gray-900 font-medium p-1 rounded-md hover:bg-gray-100"
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

        <Result
          show={showResultsModal}
          results={results}
          onClose={() => {
            setShowResultsModal(false);
            reset();
          }}
          historyAudioUrl={historyAudioUrl}
          renderColoredText={renderColoredPracticeTextWithPhonemes}
          alignmentVisualization={
            results?.phoneme_alignment?.length > 0 ? (
              <WordPhonemeComparison
                alignmentData={results.phoneme_alignment}
                refPhonemes={results.reference_phonemes}
                learnerPhonemes={results.learner_phonemes}
              />
            ) : null
          }
        />
      </main>
    </div>
  );
};

export default PronunciationPractice;
