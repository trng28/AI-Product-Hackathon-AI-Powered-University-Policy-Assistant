from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .models import LegalChunk, SearchResult


class HybridRetriever:
    def __init__(self, index_dir: Path) -> None:
        import faiss

        config = json.loads((index_dir / "config.json").read_text(encoding="utf-8"))
        raw = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
        self.chunks = [LegalChunk(**item) for item in raw]
        self.index = faiss.read_index(str(index_dir / "vectors.faiss"))
        self.model = SentenceTransformer(config["embedding_model"])

    def search(
        self, query: str, keywords: list[str], target_articles: list[str], top_k: int
    ) -> list[SearchResult]:
        vector = self.model.encode(
            [f"query: {query}"], normalize_embeddings=True
        ).astype("float32")
        limit = min(max(top_k * 4, 20), len(self.chunks))
        scores, ids = self.index.search(np.asarray(vector), limit)
        terms = {term.lower() for term in keywords if len(term) > 1}
        article_targets = {item.lower() for item in target_articles}
        ranked: list[SearchResult] = []
        for semantic, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            haystack = f"{chunk.article} {chunk.text}".lower()
            keyword_score = sum(term in haystack for term in terms) / max(len(terms), 1)
            article_bonus = 0.15 if any(a in chunk.article.lower() for a in article_targets) else 0
            score = 0.75 * float(semantic) + 0.25 * keyword_score + article_bonus
            ranked.append(SearchResult(chunk=chunk, score=score))
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]
