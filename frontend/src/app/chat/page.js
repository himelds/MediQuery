"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { chat } from "@/lib/api";
import ChatMessage from "@/components/ChatMessage";
import SourceCard from "@/components/SourceCard";
import RoleBadge from "@/components/RoleBadge";
import ExampleQueries from "@/components/ExampleQueries";

const ROLE_COLLECTIONS = {
  doctor: ["medical", "clinical", "nursing", "general"],
  nurse: ["medical", "nursing", "general"],
  billing_executive: ["billing", "general"],
  technician: ["equipment", "general"],
  admin: ["medical", "clinical", "billing", "equipment", "nursing", "general"],
};

function Logo({ className }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="12" fill="#059669" />
      <path d="M10 26 L17 26 L20 19 L24 31 L28 22 L31 26 L38 26" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M24 8 L24 14 M21 11 L27 11" stroke="#A7F3D0" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [activeSources, setActiveSources] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("role");
    const displayName = localStorage.getItem("displayName");
    if (!token) {
      router.push("/");
      return;
    }
    setUserInfo({ token, role, displayName });
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(question) {
    const q = question || input.trim();
    if (!q || loading) return;
    setInput("");

    const userMsg = { role: "user", text: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    const history = messages
      .filter((m) => m.text)
      .map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.text }));

    try {
      const data = await chat(q, userInfo.token, history);
      const assistantMsg = {
        role: "assistant",
        text: data.answer,
        sources: data.sources,
        collections: data.collections_searched,
      };
      setMessages((prev) => {
        const updated = [...prev, assistantMsg];
        if (data.sources && data.sources.length > 0) {
          setActiveSources({ index: updated.length - 1, sources: data.sources });
        }
        return updated;
      });
    } catch (err) {
      const errorMsg = {
        role: "assistant",
        text: err.message === "Invalid or expired token."
          ? "Session expired. Please login again."
          : `Error: ${err.message}`,
        sources: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
      if (err.message === "Invalid or expired token.") {
        setTimeout(() => { localStorage.clear(); router.push("/"); }, 2000);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleNewChat() {
    setMessages([]);
    setActiveSources(null);
  }

  function handleLogout() {
    localStorage.clear();
    router.push("/");
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  if (!userInfo) return null;

  const collections = ROLE_COLLECTIONS[userInfo.role] || [];

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <Logo className="w-9 h-9" />
            <div>
              <p className="text-sm font-semibold text-slate-800 leading-tight">MediQuery</p>
              <p className="text-xs text-slate-400">Clinical Assistant</p>
            </div>
          </div>
        </div>

        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Conversation
          </button>
        </div>

        <div className="px-4 py-2">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Accessible Departments
          </p>
          <div className="space-y-1">
            {collections.map((c) => (
              <div key={c} className="flex items-center gap-2 px-2.5 py-1.5 text-sm text-slate-600 rounded-md">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span className="capitalize">{c}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-auto p-4 border-t border-slate-100">
          <div className="flex items-center justify-between mb-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-700 truncate">{userInfo.displayName}</p>
              <RoleBadge role={userInfo.role} />
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-2.5 py-2 text-sm text-slate-500 hover:bg-slate-50 hover:text-red-600 rounded-md transition"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main chat */}
      <main className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex-shrink-0">
          <h1 className="text-base font-medium text-slate-700">Clinical Knowledge Assistant</h1>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-6">
              <Logo className="w-16 h-16 opacity-90" />
              <div>
                <h2 className="text-lg font-semibold text-slate-700">
                  Welcome, {userInfo.displayName}
                </h2>
                <p className="text-sm text-slate-500 mt-1 max-w-sm">
                  Ask clinical questions. Answers are restricted to your authorized departments and cited from source documents.
                </p>
              </div>
              <div className="w-full max-w-md">
                <ExampleQueries role={userInfo.role} onSelect={handleSend} />
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  message={msg}
                  isActive={activeSources?.index === i}
                  onShowSources={() => setActiveSources({ index: i, sources: msg.sources })}
                />
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-200 rounded-2xl px-4 py-3 flex items-center gap-2 text-sm text-slate-500">
                    <span className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></span>
                    Searching departments and generating answer...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="bg-white border-t border-slate-200 px-6 py-4 flex-shrink-0">
          <div className="max-w-3xl mx-auto flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a clinical question..."
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:bg-white outline-none transition disabled:opacity-60"
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-60 transition"
            >
              Send
            </button>
          </div>
        </div>
      </main>

      {/* Sources panel */}
      {activeSources && (
        <aside className="w-80 bg-white border-l border-slate-200 flex flex-col flex-shrink-0">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
            <h3 className="text-sm font-medium text-slate-700">
              Sources ({activeSources.sources.length})
            </h3>
            <button
              onClick={() => setActiveSources(null)}
              className="text-slate-400 hover:text-slate-600 transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {activeSources.sources.map((source, i) => (
              <SourceCard key={source.id} source={source} index={i} />
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}
