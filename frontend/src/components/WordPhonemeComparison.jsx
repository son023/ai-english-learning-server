import React from "react";

const WordPhonemeComparison = ({
  alignmentData,
  refPhonemes,
  learnerPhonemes,
}) => {
  if (!alignmentData || alignmentData.length === 0) {
    return <p className="text-gray-500">Không có dữ liệu phiên âm.</p>;
  }

  // Tạo map từ ref phoneme -> alignment item
  // Lưu ý: nếu có nhiều alignment items cùng ref, ưu tiên item có learner
  const refToAlignment = new Map();
  alignmentData.forEach((item) => {
    if (item.ref) {
      const existing = refToAlignment.get(item.ref);
      // Ưu tiên item có learner và is_match = true
      if (!existing || (item.learner && !existing.learner) || (item.learner && item.is_match && !existing.is_match)) {
        refToAlignment.set(item.ref, item);
      }
    }
  });

  // Render phoneme với background + highlighting
  const renderPhoneme = (
    phonemeText,
    subAlignment,
    isRef = true,
    hasMatch = true,
    refPhonemeLength = 0
  ) => {
    // Nếu không có phoneme (thiếu từ) → hiển thị dấu gạch dưới với độ dài tương ứng
    if (!phonemeText) {
      // Tính số lượng dấu gạch dựa trên độ dài phoneme reference
      // Mỗi ký tự phoneme ~ 1 dấu gạch, tối thiểu 4, tối đa 20
      const underscoreCount = Math.max(
        4,
        Math.min(20, Math.floor(refPhonemeLength * 1.0))
      );
      const underscores = "_".repeat(underscoreCount);

      return (
        <span className="inline-block mr-2 px-3 py-1 bg-gray-50 border border-gray-300 rounded">
          <span className="font-mono text-base text-gray-400">
            {underscores}
          </span>
        </span>
      );
    }

    // Nếu không có sub_alignment, hiển thị phoneme đơn giản
    if (!subAlignment || subAlignment.length === 0) {
      const bgColor = hasMatch
        ? "bg-green-50 border-green-200"
        : "bg-red-50 border-red-200";

      return (
        <span
          className={`inline-block mr-2 px-2 py-1 border rounded ${bgColor}`}
        >
          <span className="font-mono text-sm">
            <span className="text-gray-700">{phonemeText}</span>
          </span>
        </span>
      );
    }

    // Có sub_alignment - bôi xanh/đỏ từng ký tự
    return (
      <span className="inline-block mr-2 px-2 py-1 bg-gray-50 border border-gray-300 rounded">
        <span className="font-mono text-sm">
          {subAlignment.map((char, charIdx) => {
            const charValue = isRef ? char.ref : char.learner;

            // Xác định màu: xanh nếu match, đỏ nếu sai
            let colorClass = "text-gray-700";
            if (charValue) {
              if (char.is_match) {
                colorClass = "text-green-600";
              } else {
                colorClass = "text-red-600 font-bold";
              }
            }

            return (
              <span key={`char-${charIdx}`} className={colorClass}>
                {charValue || " "}
              </span>
            );
          })}
        </span>
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Reference phonemes */}
      <div>
        <h4 className="text-sm font-semibold text-gray-600 mb-2">
          Phiên âm mẫu (Reference)
        </h4>
        <div className="flex flex-wrap gap-2">
          {(() => {
            const usedLearnerIndices = new Set();  // Track theo INDEX trong learnerPhonemes
            
            return refPhonemes && refPhonemes.map((refWord, refIndex) => {
              // Tìm alignment item tương ứng với phoneme này
              const alignmentItem = refToAlignment.get(refWord.phoneme);

              // Kiểm tra xem user có nói từ này không + tìm index chưa dùng
              let shouldUseAlignment = false;
              
              if (alignmentItem && alignmentItem.learner) {
                // Tìm index của learner word trong learnerPhonemes (chưa được dùng)
                const learnerIndex = learnerPhonemes.findIndex(
                  (lp, idx) => lp.phoneme === alignmentItem.learner && !usedLearnerIndices.has(idx)
                );
                
                if (learnerIndex !== -1) {
                  usedLearnerIndices.add(learnerIndex);
                  shouldUseAlignment = true;
                }
              }

              return (
                <React.Fragment key={`ref-${refIndex}`}>
                  {renderPhoneme(
                    refWord.phoneme,
                    shouldUseAlignment ? alignmentItem.sub_alignment : null,
                    true,
                    shouldUseAlignment ? alignmentItem.is_match : false
                  )}
                </React.Fragment>
              );
            });
          })()}
        </div>
      </div>

      {/* Learner phonemes */}
      <div>
        <h4 className="text-sm font-semibold text-gray-600 mb-2">
          Phiên âm của bạn (Learner)
        </h4>
        <div className="flex flex-wrap gap-2">
          {(() => {
            return alignmentData.map((item, index) => {
              // Lấy độ dài phoneme reference (để tính độ dài ô trống)
              const refLength = item.ref ? item.ref.length : 0;

              // Nếu không có learner → hiển thị dấu gạch dưới
              if (!item.learner) {
                return (
                  <React.Fragment key={`learner-missing-${index}`}>
                    {renderPhoneme(null, null, false, false, refLength)}
                  </React.Fragment>
                );
              }

              if (!item.ref) {
                return (
                  <React.Fragment key={`learner-${index}`}>
                    {renderPhoneme(
                      item.learner,
                      null,
                      false,
                      false,
                      refLength
                    )}
                  </React.Fragment>
                );
              }

              return (
                <React.Fragment key={`learner-${index}`}>
                  {renderPhoneme(
                    item.learner,
                    item.sub_alignment,
                    false,
                    item.is_match,
                    refLength
                  )}
                </React.Fragment>
              );
            });
          })()}
        </div>
      </div>

      <p className="text-xs text-gray-500 pt-2">
        <span className="text-green-600 font-semibold">Màu xanh:</span> Phát âm
        đúng.
        <span className="text-red-600 font-semibold ml-3">Màu đỏ:</span> Phát âm
        sai.
        <span className="inline-flex items-center ml-3">
          <span className="inline-block px-2 py-0.5 bg-gray-50 border border-gray-300 rounded mr-1">
            <span className="font-mono text-xs text-gray-400">____</span>
          </span>
          <span>: Thiếu từ.</span>
        </span>
      </p>
    </div>
  );
};

export default WordPhonemeComparison;
