"use client";

import { useState } from "react";

function RelevanceBadge({ score }) {
  let label, color;
  if (score > 2) {
    label = "High relevance";
    color = "text-emerald-600";
  } else if (score > -3) {
    label = "Relevant";
    color = "text-slate-500";
  } else {
    label = "Related";
    color = "text-slate-400";
  }
  return <span className={color}>{label}</span>;
}

const COLLECTION_COLORS = {
  medical: "bg-emerald-100 text-emerald-700",
  clinical: "bg-blue-100 text-blue-700",
  nursing: "bg-indigo-100 text-indigo-700",
  billing: "bg-amber-100 text-amber-700",
  equipment: "bg-purple-100 text-purple-700",
  general: "bg-slate-100 text-slate-600",
};

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  const meta = source.metadata || {};
  const title = meta.focus || meta.source || source.collection;
  const question = meta.question || "";
  const collClass = COLLECTION_COLORS[source.collection] || "bg-slate-100 text-slate-600";

  return (
    <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2.5 flex items-start gap-2 text-left hover:bg-slate-50 transition"
      >
        <span className="flex-shrink-0 w-5 h-5 rounded bg-slate-100 text-slate-500 text-xs flex items-center justify-center font-medium mt-0.5">
          {index + 1}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-700 truncate">{title}</p>
          <span className={`inline-block mt-1 px-1.5 py-0.5 rounded text-xs ${collClass}`}>
            {source.collection}
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 flex-shrink-0 mt-1 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-0 border-t border-slate-100">
          {question && (
            <p className="text-xs text-slate-500 italic mt-2 mb-1">{question}</p>
          )}
          <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">
            {source.text}
          </p>
          <div className="flex items-center gap-3 text-xs mt-2 pt-2 border-t border-slate-50">
            <RelevanceBadge score={source.rerank_score} />
            {meta.qtype && <span className="text-slate-400">Type: {meta.qtype}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
