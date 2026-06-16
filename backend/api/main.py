"""
FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="MedRagAssistant API",
        description="Role-based Medical RAG Q&A System",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
