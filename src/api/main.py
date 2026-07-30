from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.policy_assistant.config import Settings
from src.policy_assistant.indexing import build_index
from src.policy_assistant.service import PolicyAssistant

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDF = PROJECT_ROOT / "src" / "data" / (
    "VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-theo-he-thong-tin-chi.pdf"
)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class CitationResponse(BaseModel):
    chunk_id: str
    article: str
    clause: str
    page: int
    document: str
    support: str


class AskResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    confidence: float
    evidence_sufficient: bool
    query_understanding: dict


class IndexRequest(BaseModel):
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
    try:
        settings = Settings.from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raw_paths = request.pdf_paths or [str(DEFAULT_PDF)]
    paths = [Path(path).expanduser().resolve() for path in raw_paths]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise HTTPException(status_code=404, detail=f"PDF not found: {missing}")
    if not all(path.suffix.lower() == ".pdf" for path in paths):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported")
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
            documents=[path.name for path in paths],
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
