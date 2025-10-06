import React from "react";
import { Mic, Map } from "lucide-react";

export default function HeaderNav({ title, page, setPage }) {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          {title}
        </h1>
        <div className="bg-gray-100 border rounded-full p-1 shadow-inner flex items-center">
          <button
            onClick={() => setPage && setPage('practice')}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
              page === 'practice'
                ? 'bg-white text-blue-600 shadow ring-1 ring-blue-200'
                : 'text-gray-600 hover:bg-white/70'
            }`}
          >
            <Mic size={16} /> Tự Luyện
          </button>
          <button
            onClick={() => setPage && setPage('three-step')}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
              page === 'three-step'
                ? 'bg-white text-blue-600 shadow ring-1 ring-blue-200'
                : 'text-gray-600 hover:bg-white/70'
            }`}
          >
            <Map size={16} /> Luyện Theo Chủ Đề
          </button>
        </div>
      </div>
    </header>
  );
}


