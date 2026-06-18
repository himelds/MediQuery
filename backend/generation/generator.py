"""
LLM generation — supports Groq (primary) and Google AI Studio (fallback).
"""

import os

from dotenv import load_dotenv
from groq import Groq

from backend.config import LLM_TEMPERATURE

load_dotenv()

_client: Groq | None = None

GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment.")
        _client = Groq(api_key=api_key)
    return _client


def _build_prompt(
    query: str,
    documents: list[dict],
    role: str,
    history: list[dict] = None,
) -> list[dict]:
    """
    Build chat messages for the LLM.
    """
    context_parts = []
    for i, doc in enumerate(documents, start=1):
        meta = doc.get("metadata", {})
        focus = meta.get("focus", "")
        source = meta.get("source", "")
        label = f"{focus} | {source}" if focus else source
        text = doc["text"][:500]
        context_parts.append(f"[Source {i} | {label}]\n{text}")

    context = "\n\n".join(context_parts)

    system_msg = f"""You are a medical information assistant at a hospital.
You answer questions using ONLY the provided context documents.
The user's role is: {role}.

"Rules:\n"
"- Answer using ONLY the context below. Do not add outside knowledge.\n"
"- Be direct and concise. State the answer in clean prose. "
"Do NOT write meta-commentary like 'Source 2 specifically mentions' "
"or 'According to Source 1' — just state the fact.\n"
"- Add a compact citation marker like [1] or [2] right after the "
"relevant statement, where the number matches the source order. "
"Cite only sources that directly support the statement.\n"
"- Do NOT add a 'References' list at the end — sources are shown separately.\n"
"- If the context does not contain enough information, say:\n"
"  \"I don't have enough information to answer this question.\"\n"
"- Use the conversation history to understand follow-up questions.\n"
"- Always end with the disclaimer below.\n"

Disclaimer: This information is for educational and research purposes only.
Always consult a qualified physician or specialist for medical decisions.

Context:
{context}"""

    messages = [{"role": "system", "content": system_msg}]

    # Add conversation history
    if history:
        for msg in history[-6:]:
            r = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": r, "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    return messages


def generate(
    query: str,
    documents: list[dict],
    role: str = "doctor",
    history: list[dict] = None,
) -> str:
    """
    Generate an answer using Groq (Llama 3.3 70B).
    """
    if not documents:
        return "I don't have enough information to answer this question."

    client = _get_client()
    messages = _build_prompt(query, documents, role, history)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower():
            return "Rate limit reached. Please wait a moment and try again."
        return f"Generation failed: {error_msg}"
