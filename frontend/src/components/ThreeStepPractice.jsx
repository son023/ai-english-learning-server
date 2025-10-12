import React, { useEffect, useMemo, useRef, useState } from "react";
import { Volume2, Mic, MicOff, Send, RotateCcw, Play, X } from "lucide-react";
import axios from "axios";
import HeaderNav from "./HeaderNav";
import { AcademicCapIcon, BriefcaseIcon, ChatBubbleBottomCenterTextIcon, GlobeAmericasIcon } from "@heroicons/react/24/solid";

const GOALS = [
  { key: "daily", icon: ChatBubbleBottomCenterTextIcon, title: "Giao tiếp hàng ngày", desc: "Câu mẫu thông dụng" },
  { key: "work", icon: BriefcaseIcon, title: "Công việc/Học thuật", desc: "Ngữ cảnh chuyên nghiệp" },
  { key: "travel", icon: GlobeAmericasIcon, title: "Du lịch", desc: "Tình huống đi lại" },
  { key: "exam", icon: AcademicCapIcon, title: "Thi cử", desc: "Luyện theo tiêu chí" },
];

// scenarios will be derived from CSV
const SCENARIOS_DEFAULT = {
  daily: [
    { key: "greetings-smalltalk", title: "Greetings & Small Talk" },
    { key: "shopping", title: "Shopping" },
    { key: "restaurant", title: "Restaurant" },
  ],
  work: [
    { key: "meetings", title: "Meetings" },
    { key: "email", title: "Email" },
  ],
  travel: [
    { key: "airport", title: "Airport" },
    { key: "hotel", title: "Hotel" },
    { key: "directions", title: "Directions" },
  ],
  exam: [
    { key: "opinions-linkers", title: "Opinions & Linkers" },
    { key: "describing-trends", title: "Describing Trends" },
  ],
};

// sentences will be loaded from CSV
const sampleSentences = {};

function ProgressBar({ value }) {
  return (
    <div className="w-full bg-gray-200 rounded-full h-1 mt-2">
      <div className="h-1 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 progress-animate" style={{ width: `${value}%`, "--progress-width": `${value}%` }}></div>
    </div>
  );
}

export default function ThreeStepPractice({ page, setPage }) {
  const [activeGoal, setActiveGoal] = useState(GOALS[0].key);
  const [activeScenario, setActiveScenario] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [goalStats, setGoalStats] = useState({});
  const [dataByGoalScenario, setDataByGoalScenario] = useState({});
  const [selectedSentenceIndex, setSelectedSentenceIndex] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioUrlRef = useRef(null);

  useEffect(() => {
    axios
      .get("http://localhost:8000/sentences")
      .then((res) => {
        const rows = Array.isArray(res.data) ? res.data : [];
        const grouped = {};
        const stats = {};
        rows.forEach(({ topic, scenario, sentence }) => {
          if (!grouped[topic]) grouped[topic] = {};
          if (!grouped[topic][scenario]) grouped[topic][scenario] = [];
          grouped[topic][scenario].push(sentence);
        });
        Object.keys(grouped).forEach((topic) => {
          let total = 0;
          Object.values(grouped[topic]).forEach((arr) => (total += arr.length));
          stats[topic] = { total };
        });
        setDataByGoalScenario(grouped);
        setGoalStats(stats);
        const firstTopic = goalTitle(GOALS[0].key);
        const firstScenarioTitle = Object.keys(grouped[firstTopic] || {})[0] || null;
        setActiveScenario(firstScenarioTitle ? keyify(firstScenarioTitle) : null);
      })
      .catch(() => {
        const fallback = {};
        Object.entries(SCENARIOS_DEFAULT).forEach(([goalKey, arr]) => {
          fallback[goalTitle(goalKey)] = arr.reduce((acc, s) => {
            acc[s.title] = [];
            return acc;
          }, {});
        });
        setDataByGoalScenario(fallback);
        setGoalStats({});
      });
  }, []);

  const scenarios = useMemo(() => {
    const topicTitle = goalTitle(activeGoal);
    const scenarioMap = dataByGoalScenario[topicTitle] || {};
    const titles = Object.keys(scenarioMap);
    return titles.map((t) => ({ key: keyify(t), title: t, count: scenarioMap[t].length }));
  }, [activeGoal, dataByGoalScenario]);

  const missionInfo = useMemo(() => {
    if (!activeScenario) return null;
    const topicTitle = goalTitle(activeGoal);
    const scenarioMap = dataByGoalScenario[topicTitle] || {};
    const title = Object.keys(scenarioMap).find((t) => keyify(t) === activeScenario) || "";
    const sentences = scenarioMap[title] || [];
    return {
      title,
      newCount: Math.min(5, sentences.length),
      reviewCount: Math.max(0, Math.min(5, sentences.length - 5)),
      focusPhoneme: "/ð/",
      suggestedRate: "0.85x",
      sentences: sentences.map((s) =>s),
    };
  }, [activeGoal, activeScenario, dataByGoalScenario]);

  const totalForActive = useMemo(() => {
    const topicTitle = goalTitle(activeGoal);
    return goalStats[topicTitle]?.total || 0;
  }, [activeGoal, goalStats]);

  function keyify(title) {
    return title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
  }
  function goalTitle(goalKey) {
    switch (goalKey) {
      case "daily":
        return "Giao tiếp hàng ngày";
      case "work":
        return "Công việc/Học thuật";
      case "travel":
        return "Du lịch";
      case "exam":
        return "Thi cử (IELTS/TOEFL)";
      default:
        return goalKey;
    }
  }

  const playTTS = (text) => {
    if (!text) return;
    if ("speechSynthesis" in window) {
      const raw = text.replace(/^\[translate:|\]$/g, "");
      const utterance = new SpeechSynthesisUtterance(raw);
      utterance.lang = "en-US";
      utterance.rate = 0.85;
      speechSynthesis.speak(utterance);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const options = MediaRecorder.isTypeSupported("audio/webm")
        ? { mimeType: "audio/webm;codecs=opus" }
        : {};
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType });
        setAudioBlob(blob);
        if (audioUrlRef.current) {
          URL.revokeObjectURL(audioUrlRef.current);
        }
        audioUrlRef.current = URL.createObjectURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      mediaRecorder.start();
      setIsRecording(true);
    } catch (e) {
      alert("Không thể truy cập microphone.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const playRecordedAudio = () => {
    if (audioUrlRef.current) {
      const audio = new Audio(audioUrlRef.current);
      audio.play().catch(() => {});
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

  const currentSentence = useMemo(() => {
    if (!missionInfo || missionInfo.sentences.length === 0) return "";
    const idx = Math.max(0, Math.min(selectedSentenceIndex, missionInfo.sentences.length - 1));
    return missionInfo.sentences[idx].replace(/^\[translate:|\]$/g, "");
  }, [missionInfo, selectedSentenceIndex]);

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
          sentence: currentSentence,
        }
      );
      setResults(response.data);
      setShowResultsModal(true);
    } catch (error) {
      alert("Có lỗi xảy ra khi gửi âm thanh. Vui lòng thử lại.");
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setAudioBlob(null);
    setResults(null);
    setIsRecording(false);
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <HeaderNav title="AI English Pronunciation Practice" page={page} setPage={setPage} />

      <main className="max-w-7xl mx-auto px-4 py-6 pb-24">
        {/* 1) Header Tabs - Chọn mục tiêu */}
        <div className="grid grid-cols-1 gap-6">
          <section className="card p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {GOALS.map((g) => {
                const isActive = g.key === activeGoal;
                return (
                  <button
                    key={g.key}
                    onClick={() => {
                      setActiveGoal(g.key);
                      setActiveScenario(null);
                    }}
                    className={`text-left border rounded-xl p-4 transition-all ${
                      isActive
                        ? "border-blue-500 bg-blue-50 shadow"
                        : "border-gray-200 bg-white hover:bg-gray-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <g.icon className="w-6 h-6 text-indigo-600 mr-2" />
                      <div className="text-xs text-gray-500">{totalForActive} câu</div>
                    </div>
                    <div className="mt-1 font-semibold text-gray-800">{g.title}</div>
                    <div className="text-sm text-gray-600">{g.desc}</div>
                    <ProgressBar value={100} />
                  </button>
                );
              })}
            </div>
          </section>

          {/* 2) Scenario Card List */}
          <section className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-gray-800">Tình huống theo mục tiêu</h2>
              <span className="text-sm text-gray-500">Vuốt để xem thêm</span>
            </div>
            <div className="grid grid-flow-col auto-cols-[70%] sm:auto-cols-[45%] md:auto-cols-[30%] gap-4 overflow-x-auto pb-2">
              {scenarios.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setActiveScenario(s.key)}
                  className={`min-h-[110px] text-left border rounded-xl p-4 shrink-0 ${
                    activeScenario === s.key ? "border-indigo-500 bg-indigo-50" : "border-gray-200 bg-white hover:bg-gray-50"
                  }`}
                >
                  <div className="text-xl">{s.icon}</div>
                  <div className="mt-1 font-semibold text-gray-800">{s.title}</div>
                  <div className="text-sm text-gray-600">{s.count} câu</div>
                </button>
              ))}
            </div>
          </section>

          {/* 3) Mission Area - Luyện đọc */}
          {missionInfo && (
            <section className="card p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xl font-semibold text-gray-800">Mission: {missionInfo.title}</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Tốc độ gợi ý {missionInfo.suggestedRate}
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                {missionInfo.sentences.map((line, idx) => {
                  const isActive = idx === selectedSentenceIndex;
                  return (
                    <button
                      type="button"
                      key={idx}
                      onClick={() => setSelectedSentenceIndex(idx)}
                      className={`w-full text-left border rounded-lg p-3 bg-white flex items-center justify-between ${isActive ? 'border-indigo-500 ring-2 ring-indigo-200' : 'border-gray-200'} hover:bg-gray-50`}
                    >
                      <div className="text-gray-800 mr-3 overflow-x-auto whitespace-pre-wrap">
                        {line}
                      </div>
                      <div className="flex items-center gap-2 ml-3 shrink-0">
                        <button type="button" className="btn-secondary flex items-center gap-2" onClick={(e) => { e.stopPropagation(); playTTS(line); }} aria-label="Nghe mẫu">
                          <Volume2 size={18} />
                          Nghe mẫu
                        </button>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Floating controls moved to global fixed container below */}
            </section>
          )}
        </div>
      </main>

      {/* Global floating bar at bottom center */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            className="h-12 w-auto flex items-center justify-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 rounded-full text-base font-semibold shadow-2xl ring-1 ring-white/60 hover:from-green-600 hover:to-emerald-700 transition-all"
            aria-label="Bắt đầu ghi âm"
          >
            <Mic size={20} /> Bắt đầu ghi âm
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="h-12 w-auto flex items-center justify-center gap-2 bg-gradient-to-r from-red-500 to-pink-600 text-white px-6 rounded-full text-base font-semibold shadow-2xl ring-1 ring-white/60 hover:from-red-600 hover:to-pink-700 transition-all animate-pulse-slow"
            aria-label="Dừng ghi âm"
          >
            <MicOff size={20} /> Dừng ghi âm
          </button>
        )}

        {audioBlob && (
          <>
            <button
              onClick={playRecordedAudio}
              className="h-12 flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-6 rounded-full text-base font-semibold shadow-md hover:from-purple-600 hover:to-indigo-700 transition-all"
              aria-label="Nghe lại audio vừa ghi"
            >
              <Play size={20} /> Nghe lại
            </button>

            <button
              onClick={submitAudio}
              disabled={isLoading}
              className="btn-primary h-12 px-6 rounded-full text-base flex items-center gap-2"
              aria-label="Gửi audio để đánh giá"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Đang xử lý...
                </>
              ) : (
                <>
                  <Send size={20} /> Gửi đánh giá
                </>
              )}
            </button>

            <button
              onClick={reset}
              className="btn-secondary h-12 px-6 rounded-full text-base flex items-center gap-2"
              aria-label="Thử lại từ đầu"
            >
              <RotateCcw size={20} /> Thử lại
            </button>
          </>
        )}
      </div>

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
              <h2 id="results-heading" className="text-xl font-semibold text-gray-800">
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
                  <span className="text-lg font-medium">Điểm tổng quát</span>
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
                  <div className="text-sm font-medium text-blue-800">Phát âm</div>
                  <div className="text-xs text-blue-600 mt-1">Pronunciation</div>
                </div>

                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 text-center border border-green-200">
                  <div className="text-2xl font-bold text-green-600 mb-1">
                    {results.scores?.fluency?.toFixed(1) || 0}/100
                  </div>
                  <div className="text-sm font-medium text-green-800">Lưu loát</div>
                  <div className="text-xs text-green-600 mt-1">Fluency</div>
                </div>

                <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 text-center border border-purple-200">
                  <div className="text-2xl font-bold text-purple-600 mb-1">
                    {results.scores?.intonation?.toFixed(1) || 0}/100
                  </div>
                  <div className="text-sm font-medium text-purple-800">Ngữ điệu</div>
                  <div className="text-xs text-purple-600 mt-1">Intonation</div>
                </div>

                <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-lg p-4 text-center border border-orange-200">
                  <div className="text-2xl font-bold text-orange-600 mb-1">
                    {results.scores?.stress?.toFixed(1) || 0}/100
                  </div>
                  <div className="text-sm font-medium text-orange-800">Trọng âm</div>
                  <div className="text-xs text-orange-600 mt-1">Stress</div>
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
              {results.word_accuracy && results.word_accuracy.length > 0 && (
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
  );
}


