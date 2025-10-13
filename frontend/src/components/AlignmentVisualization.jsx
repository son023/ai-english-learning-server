import React from "react";

const AlignmentVisualization = ({ alignmentData }) => {
  if (!alignmentData || alignmentData.length === 0) {
    return <p className="text-gray-500">Không có dữ liệu alignment.</p>;
  }

  const renderPhoneme = (phoneme, isMatch) => {
    let colorClass = "text-gray-800";
    if (isMatch === true) colorClass = "text-green-600 font-semibold";
    if (isMatch === false) colorClass = "text-red-600 font-semibold";

    return (
      <span
        className={`inline-block px-2 py-1 border rounded-md ${colorClass} ${
          isMatch === false
            ? "bg-red-50 border-red-200"
            : isMatch === true
            ? "bg-green-50 border-green-200"
            : "bg-gray-100 border-gray-200"
        }`}>
        {phoneme || "—"}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-semibold text-gray-600 mb-2">
          Phiên âm mẫu (Reference)
        </h4>
        <div className="flex flex-wrap gap-2">
          {alignmentData.map((item, index) => (
            <div key={`ref-${index}`}>
              {renderPhoneme(
                item.ref,
                item.ref && item.learner ? item.is_match : null
              )}
            </div>
          ))}
        </div>
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-600 mb-2">
          Phiên âm của bạn (Learner)
        </h4>
        <div className="flex flex-wrap gap-2">
          {alignmentData.map((item, index) => (
            <div key={`learner-${index}`}>
              {renderPhoneme(
                item.learner,
                item.ref && item.learner ? item.is_match : null
              )}
            </div>
          ))}
        </div>
      </div>
      <p className="text-xs text-gray-500 pt-2">
        <span className="text-green-600 font-semibold">Màu xanh:</span> Khớp
        đúng.
        <span className="text-red-600 font-semibold ml-2">Màu đỏ:</span> Sai
        hoặc thiếu/thừa.
      </p>
    </div>
  );
};

export default AlignmentVisualization;
