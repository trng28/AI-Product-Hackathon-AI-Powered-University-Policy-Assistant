from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path | None = None) -> None:
    if path is None:
        candidates = (PROJECT_ROOT / ".env", PROJECT_ROOT / "src" / ".env")
        for candidate in candidates:
            _load_dotenv(candidate)
        return
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    embedding_model: str
    retrieval_mode: str
    index_dir: Path
    top_k: int
    api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        defaults = {
            "openai": ("OPENAI_API_KEY", "gpt-5.6"),
            "groq": ("GROQ_API", "llama-3.3-70b-versatile"),
            "gemini": ("GEMINI_API_KEY", "gemini-2.5-flash"),
        }
        if provider not in defaults:
            raise ValueError("LLM_PROVIDER must be openai, groq, or gemini")
        retrieval_mode = os.getenv("RETRIEVAL_MODE", "semantic").lower()
        if retrieval_mode not in {"semantic", "lexical"}:
            raise ValueError("RETRIEVAL_MODE must be semantic or lexical")
        key_name, default_model = defaults[provider]
        api_key = os.getenv(key_name, "")
        if not api_key:
            raise ValueError(f"Missing {key_name} for LLM_PROVIDER={provider}")
        index_dir = Path(os.getenv("INDEX_DIR", "data/policy-index"))
        if not index_dir.is_absolute():
            index_dir = PROJECT_ROOT / index_dir
        return cls(
            provider=provider,
            model=os.getenv("LLM_MODEL", default_model),
            embedding_model=os.getenv(
                "EMBEDDING_MODEL", "intfloat/multilingual-e5-small"
            ),
            retrieval_mode=retrieval_mode,
            index_dir=index_dir.resolve(),
            top_k=int(os.getenv("TOP_K", "6")),
            api_key=api_key,
        )
