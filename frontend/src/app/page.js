"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

const DEMO_USERS = [
  { username: "dr.bijoy", password: "doctor123", role: "Doctor", dept: "General Medicine" },
  { username: "nurse.priya", password: "nurse123", role: "Nurse", dept: "ICU" },
  { username: "billing.niloy", password: "billing123", role: "Billing", dept: "Finance" },
  { username: "tech.fatima", password: "tech123", role: "Technician", dept: "Biomedical" },
  { username: "admin.sys", password: "admin123", role: "Admin", dept: "IT Systems" },
];

function Logo({ className }) {
  return (
    <svg viewBox="0 0 48 48" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="12" fill="#059669" />
      <path d="M10 26 L17 26 L20 19 L24 31 L28 22 L31 26 L38 26" stroke="#FFFFFF" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M24 8 L24 14 M21 11 L27 11" stroke="#A7F3D0" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(username, password);
      localStorage.setItem("token", data.token);
      localStorage.setItem("role", data.role);
      localStorage.setItem("username", data.username);
      localStorage.setItem("displayName", data.display_name);
      router.push("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function fill(user) {
    setUsername(user.username);
    setPassword(user.password);
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-emerald-700 text-emerald-50 text-xs px-4 py-1.5 rounded-t-lg flex items-center justify-between">
          <span>Secure Staff Portal</span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-300 animate-pulse"></span>
            System Online
          </span>
        </div>
      </div>

      <div className="w-full max-w-md bg-white shadow-sm border border-slate-200 border-t-0 rounded-b-lg overflow-hidden">
        <div className="p-8">
          <div className="flex flex-col items-center mb-7">
            <Logo className="w-14 h-14 mb-3" />
            <h1 className="text-xl font-semibold text-slate-800">MediQuery</h1>
            <p className="text-sm text-slate-500 mt-0.5">Clinical Knowledge Assistant</p>
          </div>

          <div className="flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-slate-100"></div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Staff Sign In</span>
            <div className="flex-1 h-px bg-slate-100"></div>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Staff ID / Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:bg-white outline-none transition"
                placeholder="e.g. dr.bijoy"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:ring-2 focus:ring-emerald-500 focus:border-transparent focus:bg-white outline-none transition"
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 bg-red-50 text-red-700 text-sm px-3 py-2.5 rounded-lg border border-red-100">
                <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 disabled:opacity-60 transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Authenticating...
                </>
              ) : (
                "Sign In"
              )}
            </button>
          </form>
        </div>

        <div className="border-t border-slate-100 bg-slate-50/50">
          <button
            onClick={() => setShowDemo(!showDemo)}
            className="w-full px-8 py-3 flex items-center justify-between text-xs text-slate-500 hover:text-slate-700 transition"
          >
            <span className="uppercase tracking-wider">Demo Accounts (Portfolio)</span>
            <svg className={`w-4 h-4 transition-transform ${showDemo ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showDemo && (
            <div className="px-8 pb-5 space-y-1.5">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.username}
                  onClick={() => fill(u)}
                  className="w-full flex items-center justify-between px-3 py-2 text-sm bg-white rounded-lg border border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/50 transition group"
                >
                  <div className="text-left">
                    <span className="text-slate-700 font-medium group-hover:text-emerald-700">{u.role}</span>
                    <span className="text-slate-400 text-xs ml-2">{u.dept}</span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">{u.username}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400 mt-6 text-center max-w-md">
        Authorized personnel only. Access is role-restricted and logged.
      </p>
    </div>
  );
}
