const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function login(username, password) {
  const res = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Login failed");
  }

  return res.json();
}

export async function chat(question, token, history = []) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ question, history }),
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Chat request failed");
  }

  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_URL}/health`);
  return res.json();
}
