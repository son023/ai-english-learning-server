import React from "react";
import { X, Play } from "lucide-react";

const Result = ({
  show,
  results,
  onClose,
  historyAudioUrl = null,
  renderColoredText = null,
  alignmentVisualization = null,
  onWordClick = null, // Callback để chuyển sang word practice
}) => {
  if (!show || !results) return null;

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

  // Hàm để lấy màu sắc dựa trên điểm từ (theo yêu cầu mới)
  const getWordColorClass = (score) => {
    if (score >= 80) return "text-green-600 bg-green-100"; // Xanh
    if (score >= 50) return "text-yellow-600 bg-yellow-100"; // Vàng
    if (score === 0) return "text-red-800 bg-red-200"; // Đỏ đậm cho từ bị thiếu
    return "text-red-600 bg-red-100"; // Đỏ
  };

  // Hàm render transcript với color coding
  const renderColoredTranscript = () => {
    if (!results.word_accuracy || results.word_accuracy.length === 0) {
      return <span className="text-gray-500">Không có dữ liệu từ nào</span>;
    }

    return (
      <div className="flex flex-wrap gap-2 text-lg leading-relaxed">
        {results.word_accuracy.map((wordData, index) => {
          const colorClass = getWordColorClass(wordData.accuracy_percentage);
          const isErrorWord = wordData.accuracy_percentage < 80;
          const isMissing = wordData.accuracy_percentage === 0;
          
          return (
            <button
              key={index}
              onClick={() => {
                if (isErrorWord && onWordClick) {
                  onWordClick(wordData.word);
                }
              }}
              className={`px-3 py-1 rounded-md font-medium transition-all duration-200 ${colorClass} ${
                isErrorWord ? 
                  'cursor-pointer hover:scale-105 hover:shadow-md border-2 border-dashed' : 
                  'cursor-default border border-transparent'
              } ${isMissing ? 'opacity-75 line-through' : ''}`}
              title={
                isMissing 
                  ? `Từ bị thiếu: "${wordData.word}" - Click để luyện (0%)`
                  : isErrorWord 
                    ? `Click để luyện từ "${wordData.word}" (${wordData.accuracy_percentage.toFixed(1)}%)`
                    : `Phát âm tốt: ${wordData.accuracy_percentage.toFixed(1)}%`
              }
              disabled={!isErrorWord || !onWordClick}
            >
              {wordData.word}
              <span className="ml-1 text-xs opacity-75">
                {isMissing ? '0%' : wordData.accuracy_percentage.toFixed(0) + '%'}
              </span>
            </button>
          );
        })}
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center"
      onClick={onClose}>
      <div className="absolute inset-0 bg-black/50" />
      <div
        className="relative bg-white rounded-xl shadow-2xl w-[70vw] max-w-[70vw] max-h-[85vh] overflow-y-auto border"
        onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 flex items-center justify-between p-4 border-b bg-white rounded-t-xl z-10">
          <h2 className="text-xl font-semibold text-gray-800">
            Kết quả đánh giá
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-gray-100 text-gray-500">
            <X size={20} />
          </button>
        </div>
        <div className="p-6">
          {historyAudioUrl && (
            <div className="mb-4">
              <button
                onClick={() => new Audio(historyAudioUrl).play()}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white px-4 py-2 rounded-lg font-semibold shadow-md transform hover:scale-105 transition-all">
                <Play size={18} /> Nghe lại bản ghi của bạn
              </button>
            </div>
          )}
          
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
                style={{
                  width: `${results.scores?.overall || 0}%`,
                }}
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
          
          {/* Hiển thị reference sentence với color coding */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <span>📝 Câu chuẩn với đánh giá phát âm</span>
              <span className="text-sm text-gray-500 font-normal">
                (Click từ đỏ/vàng để luyện tập)
              </span>
            </h3>
            <div className="bg-white rounded-lg p-4 border border-gray-200 mb-3">
              {renderColoredTranscript()}
            </div>
            
            {/* Hiển thị transcribed text riêng */}
            {results.transcribed_text && (
              <div className="bg-blue-50 rounded-lg p-3 border border-blue-200 mb-3">
                <p className="text-sm text-gray-600 mb-1"><strong>Bạn đã đọc:</strong></p>
                <p className="text-gray-800 italic">"{results.transcribed_text}"</p>
              </div>
            )}
            
            <div className="mt-2 text-xs text-gray-500 space-y-1">
              <div className="flex gap-4 flex-wrap">
                <span><span className="inline-block w-3 h-3 bg-green-100 rounded mr-1"></span>Xanh: Phát âm tốt (80%+)</span>
                <span><span className="inline-block w-3 h-3 bg-yellow-100 rounded mr-1"></span>Vàng: Cần cải thiện (50-79%)</span>
                <span><span className="inline-block w-3 h-3 bg-red-100 rounded mr-1"></span>Đỏ: Cần luyện tập (1-49%)</span>
                <span><span className="inline-block w-3 h-3 bg-red-200 rounded mr-1 opacity-75"></span>Gạch ngang: Từ bị thiếu (0%)</span>
              </div>
            </div>
          </div>
          
          {/* Phần văn bản nhận diện đã được thay thế bởi transcript với color coding ở trên */}
          
          {results.word_accuracy && results.word_accuracy.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                {renderColoredText ? "Phân tích từng từ" : "Độ chính xác từng từ"}
              </h3>
              <div className={`grid gap-3 ${renderColoredText ? "grid-cols-2 md:grid-cols-3 lg:grid-cols-4" : "grid-cols-2"}`}>
                {results.word_accuracy.map((wordData, index) => (
                  <div
                    key={index}
                    className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <div className="flex justify-between items-baseline">
                      <span className={`font-semibold text-gray-800 ${renderColoredText ? "text-base" : "text-sm"} ${!renderColoredText ? "mb-1 truncate" : ""}`}>
                        {wordData.word}
                      </span>
                      <span
                        className={`font-bold rounded ${getScoreColor(
                          wordData.accuracy_percentage
                        )} ${renderColoredText ? "text-lg" : "text-lg"}`}>
                        {wordData.accuracy_percentage?.toFixed(0)}%
                      </span>
                    </div>
                    {renderColoredText && (
                      <div className="mt-2 text-xs text-gray-500 space-y-1">
                        <div className="flex justify-between">
                          <span>Phát âm:</span>{" "}
                          <span>
                            {wordData.pronunciation_score.toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Nhịp điệu:</span>{" "}
                          <span>{wordData.rhythm_score.toFixed(0)}%</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.feedback && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                Nhận xét từ AI
              </h3>
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                {renderColoredText ? (
                  <div
                    className="prose max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{
                      __html: results.feedback.replace(/\n/g, "<br />"),
                    }}></div>
                ) : (
                  <p className="text-gray-700 leading-relaxed">
                    {results.feedback}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Result;