from __future__ import annotations

from pathlib import Path

from .agents import OrchestratorAgent
from .config import Settings
from .indexing import build_index
from .llm import create_chat_model
from .models import Answer
from .retrieval import HybridRetriever


class PolicyAssistant:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()
        retriever = HybridRetriever(self.settings.index_dir)
        self.orchestrator = OrchestratorAgent(
            create_chat_model(self.settings), retriever, self.settings.top_k
        )

    @staticmethod
    def index(
        source_paths: list[Path], index_dir: Path, embedding_model: str
    ) -> int:
        return build_index(source_paths, index_dir, embedding_model)

    def ask(self, question: str) -> Answer:
        if not question.strip():
            raise ValueError("Question cannot be empty")
        return self.orchestrator.run(question.strip())
