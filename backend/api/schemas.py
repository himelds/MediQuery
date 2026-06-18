"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel


# --- Requests ---


class LoginRequest(BaseModel):
    username: str
    password: str


# --- Responses ---


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    display_name: str


class SourceResponse(BaseModel):
    id: str
    collection: str
    text: str
    metadata: dict
    rerank_score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    role: str
    collections_searched: list[str]


class HealthResponse(BaseModel):
    status: str
    collections: dict[str, int]


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []
