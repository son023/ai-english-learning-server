import React, { useState, useRef } from "react";
import {
  Mic,
  MicOff,
  Send,
  RotateCcw,
  Volume2,
  Play,
  X,
  Map,
} from "lucide-react";
import axios from "axios";
import HeaderNav from "./HeaderNav";

const PronunciationPractice = ({ page, setPage }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [practiceText, setPracticeText] = useState(
    "Hello everyone, welcome to our English pronunciation practice session today."
  );
  const [showResultsModal, setShowResultsModal] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioUrlRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Thử dùng WAV nếu supported, nếu không thì dùng format default
      let options = { mimeType: "audio/webm;codecs=opus" };
      if (MediaRecorder.isTypeSupported("audio/wav")) {
        options = { mimeType: "audio/wav" };
      } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        options = { mimeType: "audio/webm" };
      } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
        options = { mimeType: "audio/mp4" };
      }

      const mediaRecorder = new MediaRecorder(stream, options);
      console.log("Recording with format:", mediaRecorder.mimeType);

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType,
        });
        console.log("Audio blob created:", audioBlob.type, audioBlob.size);
        setAudioBlob(audioBlob);

        // Tạo URL cho audio playback
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
        }
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

    // Dọn dẹp audio URL
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
    const alignment = results.phoneme_alignment || [];

    function buildColoredSentence(targetText, advanceOn) {
      const words = (targetText || "").split(/\s+/);
      let wordIndex = 0;
      const coloredSegments = [];

      alignment.forEach((pair) => {
        const shouldAdvance =
          advanceOn === "ref" ? pair.ref !== null : pair.learner !== null;
        if (!shouldAdvance) return;

        const word = words[wordIndex] ?? "";
        let wordSpans = [];

        const refSym = pair.ref;
        const learnerSym = pair.learner;
        const emphasisClass =
          advanceOn === "ref" ? "font-bold underline" : "underline";
        if (
          (advanceOn === "ref" && learnerSym === null) ||
          (advanceOn === "learner" && refSym === null)
        ) {
          wordSpans.push(
            <span
              key={`word-${advanceOn}-${wordIndex}`}
              className={`text-red-600 ${emphasisClass}`}
            >
              {word}
            </span>
          );
        } else if (pair.is_match) {
          wordSpans.push(
            <span
              key={`word-${advanceOn}-${wordIndex}`}
              className={`text-green-600 ${emphasisClass}`}
            >
              {word}
            </span>
          );
        } else {
          const subAlignment = pair.sub_alignment || [];
          const charCount =
            (advanceOn === "ref"
              ? (refSym || "").length
              : (learnerSym || "").length) || 1;
          let subIdxCount = 0;

          subAlignment.forEach((subPair, subIdx) => {
            const consider =
              advanceOn === "ref"
                ? subPair.ref !== null
                : subPair.learner !== null;
            if (!consider) return;
            const isCorrect = !!subPair.is_match;
            const colorClass = isCorrect
              ? `text-green-600 ${emphasisClass}`
              : `text-red-600 ${emphasisClass}`;

            const start = Math.floor((subIdxCount * word.length) / charCount);
            const end = Math.floor(
              ((subIdxCount + 1) * word.length) / charCount
            );
            const part = word.substring(start, end);
            if (part) {
              wordSpans.push(
                <span
                  key={`sub-${advanceOn}-${wordIndex}-${subIdx}`}
                  className={colorClass}
                >
                  {part}
                </span>
              );
            }
            subIdxCount++;
          });

          const lastEnd = Math.floor((charCount * word.length) / charCount);
          if (lastEnd < word.length) {
            const remaining = word.substring(lastEnd);
            if (wordSpans.length > 0) {
              const lastSpan = wordSpans[wordSpans.length - 1];
              wordSpans[wordSpans.length - 1] = (
                <span key={lastSpan.key} className={lastSpan.props.className}>
                  {lastSpan.props.children + remaining}
                </span>
              );
            } else {
              wordSpans.push(
                <span
                  key={`remain-${advanceOn}-${wordIndex}`}
                  className="text-red-600 font-bold underline"
                >
                  {remaining}
                </span>
              );
            }
          }
        }

        coloredSegments.push(...wordSpans);
        wordIndex++;
        if (wordIndex < words.length) coloredSegments.push(" ");
      });

      return coloredSegments.length > 0 ? coloredSegments : [targetText];
    }

    const refSentenceColored = buildColoredSentence(practiceText, "ref");
    const learnerSentenceColored = results.transcribed_text || "";

    return (
      <div className="space-y-3">
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-1">
            Câu gốc
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-800 font-medium">
            {refSentenceColored}
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-1">
            Câu bạn đọc
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-800 font-medium">
            {learnerSentenceColored}
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-1">
            Phoneme câu gốc
          </div>
          <div className="flex flex-wrap gap-x-1 text-base mt-1 text-gray-700">
            {(results.reference_phonemes || []).map((item, idx) => (
              <span
                key={"ref-phoneme-" + idx}
                className="inline-block"
                style={{ marginRight: 8 }}
              >
                {item.phoneme}
              </span>
            ))}
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-1">
            Phoneme bạn đọc
          </div>
          <div className="flex flex-wrap gap-x-1 text-base text-blue-700">
            {(results.learner_phonemes || []).map((item, idx) => (
              <span
                key={"learner-phoneme-" + idx}
                className="inline-block"
                style={{ marginRight: 8 }}
              >
                {item.phoneme}
              </span>
            ))}
          </div>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Màu xanh: đúng; Màu đỏ: cần cải thiện (mismatch, thiếu hoặc thừa
          phoneme)
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <HeaderNav
        title="AI English Pronunciation Practice"
        page={page}
        setPage={setPage}
      />

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6 h-[calc(100vh-140px)]">
          {/* LEFT COLUMN - Practice Section */}
          <section className="space-y-6 overflow-y-auto">
            {/* Practice Text Card */}
            <article
              className="card p-6"
              role="region"
              aria-labelledby="practice-heading"
            >
              <div className="flex items-center justify-between mb-4">
                <h2
                  id="practice-heading"
                  className="text-xl font-semibold text-gray-800"
                >
                  Câu cần luyện tập
                </h2>
                <button
                  onClick={playTextToSpeech}
                  className="flex items-center gap-2 text-blue-600 hover:text-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg px-2 py-1"
                  aria-label="Nghe phát âm mẫu"
                >
                  <Volume2 size={20} />
                  <span className="text-sm">Nghe mẫu</span>
                </button>
              </div>

              <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 mb-4 border border-gray-200">
                <p className="text-lg text-gray-800 leading-relaxed font-medium">
                  {practiceText}
                </p>
              </div>

              <label htmlFor="practice-input" className="sr-only">
                Nhập câu luyện tập
              </label>
              <textarea
                id="practice-input"
                value={practiceText}
                onChange={(e) => {
                  setPracticeText(e.target.value);
                  setResults((prev) => ({
                    ...prev,
                    reference_phonemes: [],
                    learner_phonemes: [],
                  }));
                }}
                className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-all duration-200"
                rows="4"
                placeholder="Nhập câu bạn muốn luyện tập phát âm..."
              />
            </article>

            {/* Recording Controls */}
            <article
              className="card p-6"
              role="region"
              aria-labelledby="recording-heading"
            >
              <h2
                id="recording-heading"
                className="text-xl font-semibold text-gray-800 mb-6"
              >
                Ghi âm phát âm
              </h2>

              <div className="flex flex-col items-center space-y-4">
                {/* Main recording button */}
                <div className="flex justify-center">
                  {!isRecording ? (
                    <button
                      onClick={startRecording}
                      className="flex items-center gap-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-green-600 hover:to-emerald-700 transform hover:scale-105 transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-green-300"
                      aria-label="Bắt đầu ghi âm"
                    >
                      <Mic size={24} />
                      Bắt đầu ghi âm
                    </button>
                  ) : (
                    <button
                      onClick={stopRecording}
                      className="flex items-center gap-3 bg-gradient-to-r from-red-500 to-pink-600 text-white px-8 py-4 rounded-full font-semibold shadow-lg hover:from-red-600 hover:to-pink-700 transform hover:scale-105 transition-all duration-200 animate-pulse-slow focus:outline-none focus:ring-4 focus:ring-red-300"
                      aria-label="Dừng ghi âm"
                    >
                      <MicOff size={24} />
                      Dừng ghi âm
                    </button>
                  )}
                </div>

                {/* Action buttons */}
                {audioBlob && (
                  <div className="flex flex-wrap justify-center gap-3">
                    <button
                      onClick={playRecordedAudio}
                      className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold shadow-md hover:from-purple-600 hover:to-indigo-700 transform hover:scale-105 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-purple-300"
                      aria-label="Nghe lại audio vừa ghi"
                    >
                      <Play size={18} />
                      Nghe lại
                    </button>

                    <button
                      onClick={submitAudio}
                      disabled={isLoading}
                      className="btn-primary flex items-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
                      aria-label="Gửi audio để đánh giá"
                    >
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
                      aria-label="Thử lại từ đầu"
                    >
                      <RotateCcw size={18} />
                      Thử lại
                    </button>
                  </div>
                )}

                {/* Status indicator */}
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

          {/* RESULTS MODAL */}
          {showResultsModal && results && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center"
              role="dialog"
              aria-modal="true"
              aria-labelledby="results-heading"
              onClick={(e) => {
                if (e.target === e.currentTarget) setShowResultsModal(false);
              }}
            >
              <div className="absolute inset-0 bg-black/50" />
              <div className="relative bg-white rounded-xl shadow-2xl w-[70vw] max-w-[70vw] max-h-[85vh] overflow-y-auto border">
                <div className="sticky top-0 flex items-center justify-between p-4 border-b bg-white rounded-t-xl">
                  <h2
                    id="results-heading"
                    className="text-xl font-semibold text-gray-800"
                  >
                    Kết quả đánh giá
                  </h2>
                  <button
                    onClick={() => setShowResultsModal(false)}
                    className="p-2 rounded-md hover:bg-gray-100 text-gray-500"
                    aria-label="Đóng"
                  >
                    <X size={20} />
                  </button>
                </div>

                <div className="p-6">
                  {/* Overall Score */}
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
                        aria-valuemax="100"
                      ></div>
                    </div>
                    <p className="text-center font-semibold text-gray-700">
                      {getScoreLabel(results.scores?.overall || 0)}
                    </p>
                  </div>

                  {/* Detailed Scores Grid */}
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

                  {/* Highlighted Comparison */}
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-gray-800 mb-3">
                      So sánh theo highlight
                    </h3>
                    <div className="bg-white rounded-lg p-4 border border-gray-200">
                      {renderColoredPracticeTextWithPhonemes()}
                    </div>
                  </div>

                  {/* Transcription */}
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

                  {/* AI Feedback */}
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

                  {/* Word Accuracy */}
                  {results.word_accuracy &&
                    results.word_accuracy.length > 0 && (
                      <div>
                        <h3 className="text-lg font-semibold text-gray-800 mb-3">
                          Độ chính xác từng từ
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                          {results.word_accuracy.map((wordData, index) => (
                            <div
                              key={index}
                              className="bg-gray-50 rounded-lg p-3 text-center border border-gray-200 hover:shadow-md transition-shadow"
                            >
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
                                }`}
                              >
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
        </div>
      </main>
    </div>
  );
};

export default PronunciationPractice;
