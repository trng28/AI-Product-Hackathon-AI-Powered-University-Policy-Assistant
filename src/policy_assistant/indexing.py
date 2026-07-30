from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from .models import LegalChunk

ARTICLE = re.compile(r"(?im)^\s*(Điều\s+\d+[a-zA-Z]?\s*[.:–-]?[^\n]*)")
CLAUSE = re.compile(r"(?m)^\s*(\d+)[.)]\s+")


def _clean(text: str) -> str:
    text = text.replace("\u00ad", "").replace("\xa0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_pdf(pdf_path: Path) -> list[LegalChunk]:
    chunks: list[LegalChunk] = []
    current_article = "Phần mở đầu"
    for page_number, page in enumerate(PdfReader(str(pdf_path)).pages, start=1):
        text = _clean(page.extract_text() or "")
        if not text:
            continue
        positions = list(ARTICLE.finditer(text))
        sections: list[tuple[str, str]] = []
        if not positions:
            sections.append((current_article, text))
        else:
            if positions[0].start() > 0 and text[: positions[0].start()].strip():
                sections.append((current_article, text[: positions[0].start()].strip()))
            for index, match in enumerate(positions):
                end = positions[index + 1].start() if index + 1 < len(positions) else len(text)
                current_article = match.group(1).strip()
                sections.append((current_article, text[match.start() : end].strip()))
        for article, section in sections:
            clause_matches = list(CLAUSE.finditer(section))
            if len(section) <= 1800 or len(clause_matches) < 2:
                parts = [("", section)]
            else:
                parts = []
                for index, match in enumerate(clause_matches):
                    end = (
                        clause_matches[index + 1].start()
                        if index + 1 < len(clause_matches)
                        else len(section)
                    )
                    parts.append((f"Khoản {match.group(1)}", section[match.start() : end]))
            for clause, part in parts:
                if len(part.strip()) < 40:
                    continue
                identity = f"{pdf_path.name}:{page_number}:{article}:{clause}:{part}"
                chunks.append(
                    LegalChunk(
                        id=hashlib.sha1(identity.encode("utf-8")).hexdigest()[:12],
                        document=pdf_path.name,
                        page=page_number,
                        article=article,
                        clause=clause,
                        text=part.strip(),
                    )
                )
    return chunks


def build_index(pdf_paths: list[Path], index_dir: Path, model_name: str) -> int:
    import faiss

    chunks = [chunk for path in pdf_paths for chunk in parse_pdf(path)]
    if not chunks:
        raise ValueError("No extractable text found in the supplied PDFs")
    model = SentenceTransformer(model_name)
    texts = [f"passage: {chunk.article}\n{chunk.text}" for chunk in chunks]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    vectors = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "vectors.faiss"))
    (index_dir / "chunks.json").write_text(
        json.dumps([chunk.to_dict() for chunk in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (index_dir / "config.json").write_text(
        json.dumps({"embedding_model": model_name}, indent=2), encoding="utf-8"
    )
    return len(chunks)
