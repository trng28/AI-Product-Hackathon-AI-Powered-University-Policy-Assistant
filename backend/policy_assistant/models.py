from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class LegalChunk:
    id: str
    document: str
    page: int
    article: str
    clause: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResult:
    chunk: LegalChunk
    score: float


@dataclass
class QueryUnderstanding:
    intent: str
    topic: str
    keywords: list[str]
    target_articles: list[str]
    rewritten_query: str


@dataclass
class Answer:
    answer: str
    citations: list[dict]
    confidence: float
    evidence_sufficient: bool
    query_understanding: dict

    def to_dict(self) -> dict:
        return asdict(self)


class QuerySchema(BaseModel):
    intent: Literal["policy_lookup", "procedure", "out_of_scope"]
    topic: str
    keywords: list[str] = Field(default_factory=list)
    target_articles: list[str] = Field(default_factory=list)
    rewritten_query: str


class DecompositionSchema(BaseModel):
    is_compound: bool = False
    subquestions: list[str] = Field(default_factory=list, max_length=4)


class CitationSchema(BaseModel):
    chunk_id: str
    support: str


class AnalysisSchema(BaseModel):
    answer: str
    evidence_sufficient: bool
    citations: list[CitationSchema] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
