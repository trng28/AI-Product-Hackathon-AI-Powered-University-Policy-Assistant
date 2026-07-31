from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.policy_assistant.config import Settings
from src.policy_assistant.service import PolicyAssistant

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = PROJECT_ROOT / "src" / "data" / (
    "VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-theo-he-thong-tin-chi.pdf"
)
DEFAULT_PUBLIC_CHUNKS = (
    PROJECT_ROOT / "src" / "data" / "vinuni-policies"
    / "processed" / "chunks.jsonl"
)
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class CitationResponse(BaseModel):
    chunk_id: str
    article: str
    clause: str
    page: int
    document: str
    source_url: str = ""
    support: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    confidence: float
    evidence_sufficient: bool
    query_understanding: dict


class IndexRequest(BaseModel):
    source_paths: list[str] = Field(default_factory=list)
    # Kept for compatibility with the existing frontend/API clients.
    pdf_paths: list[str] = Field(default_factory=list)
    force: bool = False


class IndexResponse(BaseModel):
    chunks: int
    index_dir: str
    documents: list[str]


class Runtime:
    def __init__(self) -> None:
        self.assistant: PolicyAssistant | None = None
        self.lock = Lock()

    def reset(self) -> None:
        with self.lock:
            self.assistant = None

    def get_assistant(self) -> PolicyAssistant:
        with self.lock:
            if self.assistant is None:
                self.assistant = PolicyAssistant()
            return self.assistant


runtime = Runtime()


def _ask_sync(question: str):
    return runtime.get_assistant().ask(question)


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _index_ready(settings: Settings) -> bool:
    if settings.retrieval_mode == "lexical":
        return (settings.index_dir / "chunks.json").is_file()
    required = (
        settings.index_dir / "vectors.faiss",
        settings.index_dir / "chunks.json",
        settings.index_dir / "config.json",
    )
    if not all(path.is_file() for path in required):
        return False
    try:
        config = json.loads(required[2].read_text(encoding="utf-8"))
        return config.get("embedding_model") == settings.embedding_model
    except (OSError, json.JSONDecodeError):
        return False


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    runtime.reset()


app = FastAPI(
    title="VinUni Policy Assistant API",
    version="1.0.0",
    description="LangGraph multi-agent RAG API for VinUni policies.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    try:
        settings = Settings.from_env()
        index_ready = _index_ready(settings)
        return {
            "status": "ready" if index_ready else "index_required",
            "provider": settings.provider,
            "model": settings.model,
            "retrieval_mode": settings.retrieval_mode,
            "index_ready": index_ready,
        }
    except ValueError as exc:
        return {
            "status": "configuration_required",
            "index_ready": False,
            "detail": str(exc),
        }


@app.post("/api/index", response_model=IndexResponse)
async def create_index(request: IndexRequest) -> IndexResponse:
    from src.policy_assistant.indexing import build_index

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    default_source = (
        DEFAULT_PUBLIC_CHUNKS if DEFAULT_PUBLIC_CHUNKS.is_file() else DEFAULT_PDF
    )
    raw_paths = request.source_paths or request.pdf_paths or [str(default_source)]
    paths = [Path(path).expanduser().resolve() for path in raw_paths]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise HTTPException(status_code=404, detail=f"Index source not found: {missing}")
    supported = all(
        path.is_dir() or path.suffix.lower() in {".pdf", ".jsonl"}
        for path in paths
    )
    if not supported:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JSONL, or processed directories are supported",
        )
    if (
        not request.force
        and _index_ready(settings)
    ):
        raise HTTPException(
            status_code=409, detail="Index already exists; set force=true to rebuild"
        )
    try:
        chunks = await asyncio.to_thread(
            build_index, paths, settings.index_dir, settings.embedding_model
        )
        runtime.reset()
        return IndexResponse(
            chunks=chunks,
            index_dir=str(settings.index_dir),
            documents=[str(path) for path in paths],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}") from exc


@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    try:
        answer = await asyncio.to_thread(_ask_sync, request.question)
        return AskResponse(**answer.to_dict())
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503, detail="Knowledge index is missing. Build the index first."
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}") from exc


# Register this catch-all mount after every API route so /api/* keeps taking
# precedence while the Render service can serve the compiled React frontend.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
