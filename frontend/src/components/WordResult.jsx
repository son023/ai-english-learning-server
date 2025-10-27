import React from "react";
import { X, Play, Volume2, Trophy, Target, BookOpen, RefreshCw } from "lucide-react";

const WordResult = ({ show, results, onClose, historyAudioUrl, onPracticeAgain, sentencePracticeMode, onBackToSentence }) => {
  if (!show || !results) return null;

  const getScoreColor = () => {
    if (results.pronunciation_score >= 90) return "text-green-600";
    if (results.pronunciation_score >= 75) return "text-blue-600";
    if (results.pronunciation_score >= 50) return "text-yellow-600";
    return "text-red-600";
  };

  const getScoreIcon = () => {
    if (results.pronunciation_score >= 90) return <Trophy className="text-yellow-500" size={32} />;
    if (results.pronunciation_score >= 75) return <Target className="text-blue-500" size={32} />;
    return <BookOpen className="text-gray-500" size={32} />;
  };

  const playHistoryAudio = () => {
    if (historyAudioUrl) {
      const audio = new Audio(historyAudioUrl);
      audio.play().catch(console.error);
    }
  };

  // Component hiển thị so sánh phoneme đơn giản
  const PhonemeComparisonView = ({ comparisons, referencePhonemes, learnerPhonemes }) => {
    if (!comparisons || comparisons.length === 0) {
      return (
        <div className="text-center text-gray-500 py-8">
          <p>Không có dữ liệu so sánh phoneme</p>
        </div>
      );
    }

    // Tách phoneme thành mảng để có thể highlight từng cái
    const refPhonemes = referencePhonemes.split(/\s+/);
    const learnerPhonemesList = learnerPhonemes.split(/\s+/);

    // Tạo map để biết phoneme nào đúng/sai
    const comparisonMap = new Map();
    comparisons.forEach((comp, index) => {
      if (comp.position >= 0) {
        comparisonMap.set(comp.position, comp);
      }
    });

    const renderPhonemeSequence = (phonemes, isReference = true) => {
      return phonemes.map((phoneme, index) => {
        const comparison = comparisonMap.get(index);
        const isCorrect = comparison?.is_correct !== false;
        
        return (
          <span
            key={index}
            className={`inline-block mx-1 px-2 py-1 rounded font-mono text-lg ${
              isReference 
                ? 'bg-blue-50 text-blue-800' 
                : isCorrect 
                  ? 'bg-green-50 text-green-800'
                  : 'bg-red-100 text-red-700 font-bold'
            }`}
          >
            {phoneme}
          </span>
        );
      });
    };

    return (
      <div className="space-y-6">
        {/* Phiên âm chuẩn */}
        <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-200">
          <h4 className="font-semibold text-gray-700 mb-3">Phiên âm chuẩn:</h4>
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <span className="text-xl">
              /{renderPhonemeSequence(refPhonemes, true)}/
            </span>
          </div>
        </div>

        {/* Phiên âm của bạn */}
        <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-200">
          <h4 className="font-semibold text-gray-700 mb-3">Phiên âm của bạn:</h4>
          <div className="bg-white p-4 rounded-lg shadow-sm">
            <span className="text-xl">
              /{renderPhonemeSequence(learnerPhonemesList, false)}/
            </span>
          </div>
        </div>

        {/* Chú thích màu sắc */}
        <div className="flex gap-4 text-sm bg-white p-3 rounded-lg border border-gray-200">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-green-100 border border-green-300 rounded"></span>
            <span className="text-gray-700">Phát âm đúng</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-red-100 border border-red-300 rounded"></span>
            <span className="text-gray-700">Phát âm sai</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-6 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Kết quả phát âm từ</h2>
            <p className="text-blue-100 text-lg">"{results.word}"</p>
          </div>
          <button
            onClick={onClose}
            className="hover:bg-white/20 p-2 rounded-full transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
          <div className="space-y-6">
            {/* Score Section */}
            <div className="text-center">
              <div className="flex justify-center mb-3">
                {getScoreIcon()}
              </div>
              <h3 className="text-2xl font-bold text-gray-800 mb-2">Điểm số</h3>
              <div className={`text-6xl font-bold ${getScoreColor()}`}>
                {results.pronunciation_score.toFixed(1)}
              </div>
              <div className="text-gray-600 mt-2 text-lg">
                {results.correct_phonemes}/{results.total_phonemes} phoneme đúng
              </div>
            </div>

            <div className="text-center">
              <div className="flex flex-wrap justify-center gap-4">
                {historyAudioUrl && (
                  <button
                    onClick={playHistoryAudio}
                    className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-6 py-3 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all"
                  >
                    <Volume2 size={20} />
                    Nghe lại bản ghi
                  </button>
                )}
                
                {onPracticeAgain && (
                  <button
                    onClick={() => {
                      onPracticeAgain(results.word);
                      onClose();
                    }}
                    className="flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-6 py-3 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all"
                  >
                    <RefreshCw size={20} />
                    Luyện lại từ này
                  </button>
                )}
                
                {/* Nút quay lại chế độ câu khi trong sentence practice mode */}
                {sentencePracticeMode && onBackToSentence && (
                  <button
                    onClick={onBackToSentence}
                    className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all"
                  >
                    <BookOpen size={20} />
                    Quay lại chế độ câu
                  </button>
                )}
              </div>
            </div>

            {/* Feedback */}
            <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg p-4 border border-gray-200">
              <h4 className="font-semibold text-gray-700 mb-2">Nhận xét:</h4>
              <p className="text-gray-700 text-lg">{results.feedback}</p>
            </div>

            {/* Phoneme Comparison */}
            <div>
              <h4 className="text-xl font-semibold text-gray-800 mb-4">
                So sánh phiên âm chi tiết
              </h4>
              <PhonemeComparisonView
                comparisons={results.phoneme_comparisons}
                referencePhonemes={results.reference_phonemes}
                learnerPhonemes={results.learner_phonemes}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WordResult;
