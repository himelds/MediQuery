export default function ChatMessage({ message, onShowSources, isActive }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-2xl ${isUser ? "" : "w-full"}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? "bg-emerald-600 text-white"
              : "bg-white border border-slate-200 text-slate-700"
          }`}
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {message.text}
          </div>
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <button
            onClick={onShowSources}
            className={`mt-1.5 text-xs px-2.5 py-1 rounded-md transition ${
              isActive
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "text-slate-500 hover:bg-slate-100"
            }`}
          >
            {message.sources.length} sources
          </button>
        )}
      </div>
    </div>
  );
}
