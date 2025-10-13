import React, { useEffect, useMemo, useRef, useState } from "react";
import { Volume2, Mic, MicOff, Send, RotateCcw, Play, X } from "lucide-react";
import axios from "axios";
import HeaderNav from "./HeaderNav";
import Result from "./Result";
import AlignmentVisualization from "./AlignmentVisualization";
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

  const renderColoredTextWithPhonemes = () => {
    if (!results || !results.phoneme_alignment) return null;
    
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

    const refSentenceColored = buildColoredSentence(currentSentence, "ref");
    const learnerSentenceColored = results.transcribed_text || "";

    return (
      <div className="space-y-3">
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-2">
            Câu gốc
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-800 font-medium">
            {refSentenceColored}
          </div>
        </div>
        <div>
          <div className="text-sm font-semibold text-gray-600 mb-2">
            Câu bạn đọc
          </div>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-gray-800 font-medium">
            {learnerSentenceColored}
          </div>
        </div>
      </div>
    );
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

      <Result
        show={showResultsModal}
        results={results}
        onClose={() => {
          setShowResultsModal(false);
          reset();
        }}
        historyAudioUrl={audioUrlRef.current}
        renderColoredText={renderColoredTextWithPhonemes}
        alignmentVisualization={
          results?.phoneme_alignment?.length > 0 ? (
            <AlignmentVisualization
              alignmentData={results.phoneme_alignment}
            />
          ) : null
        }
      />
    </div>
  );
}


