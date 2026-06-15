"""
LLM generation — Gemma 4 31B via Google AI Studio.

Takes a user question and retrieved context documents,
builds a medical prompt, and generates an answer with citations.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.config import LLM_TEMPERATURE

load_dotenv()

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set in environment.")
        _client = genai.Client(api_key=api_key)
    return _client


def _build_prompt(query: str, documents: list[dict], role: str) -> str:
    """
    Build the generation prompt with retrieved context.

    Each document is numbered as [Source N] so the LLM can cite them.
    """
    context_parts = []
    for i, doc in enumerate(documents, start=1):
        meta = doc.get("metadata", {})

        # Medical collection has focus/source; document collections have source/collection
        focus = meta.get("focus", "")
        source = meta.get("source", "")
        label = f"{focus} | {source}" if focus else source

        context_parts.append(f"[Source {i} | {label}]\n{doc['text']}")

    context = "\n\n".join(context_parts)

    return f"""You are a medical information assistant at a hospital.
You answer questions using ONLY the provided context documents.
The user's role is: {role}.

Rules:
- Answer using ONLY the context below. Do not add outside knowledge.
- Cite sources like [Source 1], [Source 2] when referencing information.
- If the context does not contain enough information, say:
  "I don't have enough information to answer this question."
- Be concise and accurate.
- Always end with the disclaimer below.

Disclaimer: This information is for educational and research purposes only.
Always consult a qualified physician or specialist for medical decisions.

---
Context:
{context}
---

Question: {query}

Answer:"""


def generate(query: str, documents: list[dict], role: str = "doctor") -> str:
    """
    Generate an answer using Gemma 4 31B.

    Args:
        query:      User question.
        documents:  Reranked documents from the retrieval pipeline.
                    Each dict must have 'text' and 'metadata' keys.
        role:       User's role (included in prompt for context).

    Returns:
        Generated answer string.
    """
    if not documents:
        return "I don't have enough information to answer this question."

    client = _get_client()
    prompt = _build_prompt(query, documents, role)

    response = client.models.generate_content(
        model="gemma-4-31b-it",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=LLM_TEMPERATURE),
    )

    return response.text
