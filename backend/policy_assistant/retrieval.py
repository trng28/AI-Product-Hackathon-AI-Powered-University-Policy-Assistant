from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .models import LegalChunk, SearchResult


class HybridRetriever:
    def __init__(self, index_dir: Path, mode: str = "semantic") -> None:
        config = json.loads((index_dir / "config.json").read_text(encoding="utf-8"))
        raw = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
        self.chunks = [LegalChunk(**item) for item in raw]
        self.mode = mode
        self.index = None
        self.model = None
        self._normalized_chunks = [
            self._normalize(f"{chunk.article} {chunk.clause} {chunk.text}")
            for chunk in self.chunks
        ]
        self._chunk_tokens = [
            set(re.findall(r"[\w.-]+", text)) for text in self._normalized_chunks
        ]
        self._document_frequency = Counter(
            token for tokens in self._chunk_tokens for token in tokens
        )
        if mode == "semantic":
            import faiss
            from sentence_transformers import SentenceTransformer

            self.index = faiss.read_index(str(index_dir / "vectors.faiss"))
            self.model = SentenceTransformer(config["embedding_model"])

    @staticmethod
    def _normalize(value: str) -> str:
        value = unicodedata.normalize("NFKD", value.casefold())
        value = "".join(
            char for char in value if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", value).strip()

    def search(
        self,
        query: str,
        keywords: list[str],
        target_articles: list[str],
        top_k: int,
        original_query: str = "",
    ) -> list[SearchResult]:
        normalize = self._normalize
        normalized_query = normalize(f"{original_query} {query}")
        domain_expansions = {
            "chuyen doi tin chi credit transfer recognition": (
                "cong nhan mon",
                "cong nhan tin chi",
                "hoc o truong khac",
                "mien tru hoc phan",
            ),
            "residential life dormitory ky tuc xa": (
                "ky tuc xa",
                "noi tru",
                "dormitory",
            ),
            "academic warning gpa canh bao hoc tap": (
                "canh bao hoc tap",
                "academic warning",
                "gpa thap",
            ),
            "grade appeal khieu nai diem phuc khao": (
                "khieu nai diem",
                "phuc khao",
                "grade appeal",
            ),
            "leave of absence tam nghi bao luu": (
                "tam nghi",
                "bao luu",
                "leave of absence",
            ),
            "postgraduate master tuition listed tuition fee financial regulations": (
                "hoc phi thac si",
                "hoc phi cao hoc",
                "master tuition",
                "postgraduate tuition",
            ),
            "class meeting times class schedule academic regulations 8:00 5:30": (
                "thoi gian hoc",
                "gio hoc",
                "bat dau tu may gio",
                "class meeting time",
                "class hours",
            ),
            "Article 20 Program Change internal transfer changing Major Degree College Faculty": (
                "chuyen nganh",
                "doi nganh",
                "thay doi nganh",
                "change major",
                "change of major",
                "program change",
            ),
        }
        expansions = [
            expansion
            for expansion, triggers in domain_expansions.items()
            if any(trigger in normalized_query for trigger in triggers)
        ]
        queries = list(
            dict.fromkeys(
                item.strip()
                for item in (
                    original_query,
                    query,
                    *(
                        f"{original_query or query} {expansion}"
                        for expansion in expansions
                    ),
                )
                if item.strip()
            )
        )
        terms = {
            normalize(term)
            for term in keywords
            if len(term.strip()) > 1
        }
        terms.update(
            token
            for expansion in expansions
            for token in expansion.split()
            if len(token) > 3
        )
        article_targets = {normalize(item) for item in target_articles}
        query_tokens = {
            token
            for token in re.findall(
                r"[\w.-]+",
                normalize(f"{original_query or query} {' '.join(expansions)}"),
            )
            if len(token) > 2
        }
        candidates: dict[int, tuple[float, float]] = {}
        if self.mode == "semantic":
            import numpy as np

            assert self.model is not None and self.index is not None
            vectors = self.model.encode(
                [f"query: {item}" for item in queries], normalize_embeddings=True
            ).astype("float32")
            limit = min(max(top_k * 4, 20), len(self.chunks))
            scores, ids = self.index.search(np.asarray(vectors), limit)
            for query_scores, query_ids in zip(scores, ids):
                for rank, (semantic, idx) in enumerate(
                    zip(query_scores, query_ids), start=1
                ):
                    if idx < 0:
                        continue
                    old_semantic, old_rrf = candidates.get(int(idx), (-1.0, 0.0))
                    candidates[int(idx)] = (
                        max(old_semantic, float(semantic)),
                        old_rrf + 1.0 / (60 + rank),
                    )
        else:
            candidates = {idx: (0.0, 0.0) for idx in range(len(self.chunks))}

        ranked: list[SearchResult] = []
        for idx, (semantic, rrf) in candidates.items():
            chunk = self.chunks[idx]
            article = normalize(chunk.article)
            reference = normalize(chunk.clause)
            haystack = self._normalized_chunks[idx]
            keyword_score = sum(term in haystack for term in terms) / max(len(terms), 1)
            article_bonus = (
                0.15
                if any(target in article or target in reference for target in article_targets)
                else 0
            )
            title_tokens = set(re.findall(r"[\w.-]+", article))
            title_overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
            if self.mode == "semantic":
                score = (
                    0.68 * semantic
                    + 0.20 * keyword_score
                    + 0.07 * title_overlap
                    + 0.05 * min(rrf * 30, 1.0)
                    + article_bonus
                )
            else:
                chunk_tokens = self._chunk_tokens[idx]
                token_weights = {
                    token: math.log(
                        (len(self.chunks) + 1)
                        / (self._document_frequency.get(token, 0) + 1)
                    ) + 1
                    for token in query_tokens
                }
                matched_weight = sum(
                    weight
                    for token, weight in token_weights.items()
                    if token in chunk_tokens
                )
                lexical_score = matched_weight / max(sum(token_weights.values()), 1)
                score = (
                    0.58 * lexical_score
                    + 0.27 * keyword_score
                    + 0.15 * title_overlap
                    + article_bonus
                )
            ranked.append(SearchResult(chunk=chunk, score=score))
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]
