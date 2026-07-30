from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .models import (
    AnalysisSchema,
    Answer,
    QuerySchema,
    QueryUnderstanding,
    SearchResult,
)
from .retrieval import HybridRetriever


class AgentState(TypedDict, total=False):
    question: str
    query: QueryUnderstanding
    retrieved: list[SearchResult]
    analysis: dict[str, Any]
    validated: dict[str, Any]
    answer: Answer


class QueryUnderstandingAgent:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model.with_structured_output(QuerySchema)

    def run(self, question: str) -> QueryUnderstanding:
        result = self.model.invoke(
            [
                SystemMessage(
                    content=(
                        "Bạn phân tích câu hỏi về quy chế đại học. Không bịa số Điều. "
                        "Trích target_articles chỉ khi người dùng nêu rõ."
                    )
                ),
                HumanMessage(content=f"Phân tích câu hỏi:\n{question}"),
            ]
        )
        if isinstance(result, dict):
            result = QuerySchema.model_validate(result)
        return QueryUnderstanding(**result.model_dump())


class RetrievalAgent:
    def __init__(self, retriever: HybridRetriever, top_k: int) -> None:
        self.retriever, self.top_k = retriever, top_k

    def run(self, query: QueryUnderstanding) -> list[SearchResult]:
        return self.retriever.search(
            query.rewritten_query, query.keywords, query.target_articles, self.top_k
        )


class PolicyAnalysisAgent:
    def __init__(self, model: BaseChatModel) -> None:
        self.model = model.with_structured_output(AnalysisSchema)

    def run(self, question: str, results: list[SearchResult]) -> dict[str, Any]:
        evidence = "\n\n".join(
            f"[{r.chunk.id}] {r.chunk.document}, {r.chunk.article}, "
            f"{r.chunk.clause}"
            f"{f', trang {r.chunk.page}' if r.chunk.page > 0 else ''}\n"
            f"{r.chunk.text}"
            for r in results
        )
        result = self.model.invoke(
            [
                SystemMessage(
                    content=(
                        "Bạn là chuyên viên phân tích quy chế VinUni. Chỉ dùng "
                        "EVIDENCE được cung cấp; không dùng kiến thức ngoài. Nếu thiếu "
                        "căn cứ, đặt evidence_sufficient=false. Mọi khẳng định phải "
                        "tham chiếu chunk_id có thật."
                    )
                ),
                HumanMessage(
                    content=f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence}"
                ),
            ]
        )
        if isinstance(result, dict):
            result = AnalysisSchema.model_validate(result)
        return result.model_dump()


class CitationValidationAgent:
    """Deterministic guardrail node; an LLM cannot approve its own citation."""

    def run(self, analysis: dict, results: list[SearchResult]) -> dict[str, Any]:
        available = {result.chunk.id: result for result in results}
        valid = []
        for citation in analysis.get("citations", []):
            chunk_id = str(citation.get("chunk_id", ""))
            if chunk_id in available:
                result = available[chunk_id]
                source_url = (
                    result.chunk.document
                    if result.chunk.document.startswith(("https://", "http://"))
                    else ""
                )
                valid.append(
                    {
                        "chunk_id": chunk_id,
                        "article": result.chunk.article,
                        "clause": result.chunk.clause,
                        "page": result.chunk.page,
                        "document": result.chunk.document,
                        "source_url": source_url,
                        "support": str(citation.get("support", "")),
                    }
                )
        sufficient = bool(analysis.get("evidence_sufficient")) and bool(valid)
        confidence = min(max(float(analysis.get("confidence", 0)), 0), 1)
        if len(valid) < len(analysis.get("citations", [])):
            confidence *= 0.75
        return {
            "answer": str(analysis.get("answer", "")),
            "citations": valid,
            "confidence": round(confidence, 2),
            "evidence_sufficient": sufficient,
        }


class ResponseAgent:
    def run(self, validated: dict, query: QueryUnderstanding) -> Answer:
        text = validated["answer"]
        if not validated["evidence_sufficient"]:
            text = (
                "Chưa tìm thấy đủ căn cứ trong tài liệu được lập chỉ mục để trả lời "
                "chính xác. Vui lòng cung cấp thêm ngữ cảnh hoặc liên hệ đơn vị phụ trách."
            )
        return Answer(
            answer=text,
            citations=validated["citations"],
            confidence=validated["confidence"],
            evidence_sufficient=validated["evidence_sufficient"],
            query_understanding=query.__dict__,
        )


class OrchestratorAgent:
    """LangGraph multi-agent orchestrator."""

    def __init__(
        self, model: BaseChatModel, retriever: HybridRetriever, top_k: int
    ) -> None:
        self.query_agent = QueryUnderstandingAgent(model)
        self.retrieval_agent = RetrievalAgent(retriever, top_k)
        self.analysis_agent = PolicyAnalysisAgent(model)
        self.validation_agent = CitationValidationAgent()
        self.response_agent = ResponseAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("query_understanding", self._understand)
        builder.add_node("retrieval", self._retrieve)
        builder.add_node("policy_analysis", self._analyze)
        builder.add_node("citation_validation", self._validate)
        builder.add_node("response", self._respond)
        builder.add_edge(START, "query_understanding")
        builder.add_edge("query_understanding", "retrieval")
        builder.add_edge("retrieval", "policy_analysis")
        builder.add_edge("policy_analysis", "citation_validation")
        builder.add_edge("citation_validation", "response")
        builder.add_edge("response", END)
        return builder.compile()

    def _understand(self, state: AgentState) -> dict:
        return {"query": self.query_agent.run(state["question"])}

    def _retrieve(self, state: AgentState) -> dict:
        return {"retrieved": self.retrieval_agent.run(state["query"])}

    def _analyze(self, state: AgentState) -> dict:
        return {
            "analysis": self.analysis_agent.run(
                state["question"], state["retrieved"]
            )
        }

    def _validate(self, state: AgentState) -> dict:
        return {
            "validated": self.validation_agent.run(
                state["analysis"], state["retrieved"]
            )
        }

    def _respond(self, state: AgentState) -> dict:
        return {
            "answer": self.response_agent.run(state["validated"], state["query"])
        }

    def run(self, question: str) -> Answer:
        return self.graph.invoke({"question": question})["answer"]
