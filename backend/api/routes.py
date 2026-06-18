"""
API route definitions.
"""

import chromadb
from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth.dependencies import get_current_user
from backend.auth.roles import get_allowed_collections
from backend.auth.users import authenticate
from backend.auth.jwt_handler import create_token
from backend.config import CHROMA_DIR
from backend.pipeline.rag_pipeline import ask

from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = authenticate(request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_token(user["username"], user["role"])
    return LoginResponse(
        token=token,
        username=user["username"],
        role=user["role"],
        display_name=user["display_name"],
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    result = ask(query=request.question, role=user["role"], history=request.history)
    return ChatResponse(**result)


@router.get("/health", response_model=HealthResponse)
def health():
    """System health check — reports collection document counts."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collections = client.list_collections()
        counts = {c.name: c.count() for c in collections}
    except Exception:
        counts = {}

    return HealthResponse(
        status="ok" if counts else "degraded",
        collections=counts,
    )


@router.get("/collections/{role}")
def get_role_collections(role: str, user: dict = Depends(get_current_user)):
    """List collections accessible to a given role."""
    allowed = get_allowed_collections(role)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown role: {role}",
        )
    return {"role": role, "collections": allowed}
