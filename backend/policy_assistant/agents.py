from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from .models import (
    AnalysisSchema,
    Answer,
    DecompositionSchema,
    QuerySchema,
    QueryUnderstanding,
    SearchResult,
)
from .retrieval import HybridRetriever


class AgentState(TypedDict, total=False):
    question: str
    history: list[dict[str, str]]
    query: QueryUnderstanding
    subquestions: list[str]
    retrieved: list[SearchResult]
    analysis: dict[str, Any]
    validated: dict[str, Any]
    answer: Answer


class QueryUnderstandingAgent:
    def __init__(self, model: Any) -> None:
        self.model = model.with_structured_output(QuerySchema)

    def run(
        self, question: str, history: list[dict[str, str]] | None = None
    ) -> QueryUnderstanding:
        recent_history = "\n".join(
            f"{item['role'].upper()}: {item['content']}"
            for item in (history or [])[-12:]
        )
        result = self.model.invoke(
            [
                SystemMessage(
                    content=(
                        f"CHAT HISTORY:\n{recent_history or '(empty)'}\n\n"
                        "Dùng history chỉ để giải quyết đại từ và tham chiếu như 'ngành đó', "
                        "'mức này' hoặc 'còn cái kia'. rewritten_query phải là câu hỏi độc lập "
                        "và đầy đủ ngữ cảnh. Không xem câu trả lời cũ là policy evidence."
                    )
                ),
                SystemMessage(
                    content=(
                        "Bạn phân tích câu hỏi về quy chế đại học VinUni. Giữ lại "
                        "các từ khóa quan trọng từ câu gốc khi viết rewritten_query; "
                        "không đổi chủ đề và không suy diễn ý định. Tạo keywords gồm "
                        "cụm từ gốc và từ đồng nghĩa Việt/Anh hữu ích cho retrieval. "
                        "Chỉ trích target_articles khi người dùng nêu rõ tên, mã hoặc "
                        "số Điều. Câu hỏi về khung giờ học/lớp nói chung thuộc policy "
                        "và phải được tìm theo Class Meeting Times. Chỉ xem thời khóa "
                        "biểu của một lớp/ngày cụ thể, thực đơn hoặc thời tiết là dữ "
                        "liệu vận hành out_of_scope. Không bịa số Điều hay chi tiết."
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

    def run(
        self,
        original_question: str,
        query: QueryUnderstanding,
        subquestions: list[str] | None = None,
    ) -> list[SearchResult]:
        questions = subquestions or [original_question]
        merged: dict[str, SearchResult] = {}
        for item in dict.fromkeys([original_question, *questions]):
            results = self.retriever.search(
                item,
                query.keywords,
                query.target_articles,
                self.top_k,
                original_query=item,
            )
            for result in results:
                previous = merged.get(result.chunk.id)
                if previous is None or result.score > previous.score:
                    merged[result.chunk.id] = result
        limit = self.top_k if len(questions) == 1 else self.top_k * 2
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:limit]


class QuestionDecompositionAgent:
    """Splits compound questions so every requested fact gets retrieval coverage."""

    def __init__(self, model: Any) -> None:
        self.model = model.with_structured_output(DecompositionSchema)

    def run(self, question: str) -> list[str]:
        result = self.model.invoke(
            [
                SystemMessage(
                    content=(
                        "Phân rã câu hỏi VinUni có nhiều ý thành tối đa 4 câu hỏi độc lập. "
                        "Giữ nguyên ngôn ngữ và điều kiện quan trọng, không tự thêm dữ kiện. "
                        "Ví dụ câu hỏi vừa hỏi số ngành vừa hỏi học phí phải thành hai câu. "
                        "Nếu chỉ có một ý, trả lại đúng một câu hỏi gốc."
                    )
                ),
                HumanMessage(content=question),
            ]
        )
        if isinstance(result, dict):
            result = DecompositionSchema.model_validate(result)
        questions = [item.strip() for item in result.subquestions if item.strip()]
        return questions or [question]


class PolicyAnalysisAgent:
    def __init__(self, model: Any) -> None:
        self.model = model.with_structured_output(AnalysisSchema)

    def run(
        self,
        question: str,
        results: list[SearchResult],
        subquestions: list[str] | None = None,
    ) -> dict[str, Any]:
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
                        "EVIDENCE được cung cấp; không dùng kiến thức ngoài. Evidence "
                        "phải trả lời trực tiếp câu hỏi, không chỉ có vài từ liên quan. "
                        "Không được suy ra giờ học, deadline, số tiền, đầu mối liên hệ "
                        "hoặc quy trình cụ thể từ một quy định trách nhiệm chung. Nếu "
                        "câu hỏi là out-of-scope, evidence không nêu chi tiết được hỏi, "
                        "hoặc các nguồn mâu thuẫn, đặt evidence_sufficient=false và "
                        "không tạo citation. Nếu đủ căn cứ, mọi khẳng định thực tế phải "
                        "được hỗ trợ bởi citation chunk_id có thật trong EVIDENCE. Chỉ "
                        "nêu tên/mã tài liệu thực sự được citation. BẮT BUỘC trả lời "
                        "bằng cùng ngôn ngữ với QUESTION: câu hỏi tiếng Việt thì toàn "
                        "bộ câu trả lời bằng tiếng Việt; câu hỏi tiếng Anh thì trả lời "
                        "bằng tiếng Anh. Dịch nội dung evidence sang ngôn ngữ câu hỏi, "
                        "nhưng giữ nguyên tên riêng, mã tài liệu, con số và thuật ngữ "
                        "cần thiết. Không được chọn ngôn ngữ theo ngôn ngữ của EVIDENCE. "
                        "Phân biệt 'chuyển ngành' hoặc 'đổi ngành' (Program Change nội "
                        "bộ VinUni) với 'chuyển trường' (Institutional Transfer sang "
                        "một trường đại học khác). Không trả lời về chuyển trường khi "
                        "QUESTION chỉ hỏi chuyển ngành."
                    )
                ),
                SystemMessage(
                    content=(
                        "Với câu hỏi nhiều ý, trả lời từng SUBQUESTION riêng. Nếu evidence "
                        "chỉ đủ cho một số ý, vẫn trả lời các ý có căn cứ, nói rõ ý nào chưa "
                        "có dữ liệu, đặt evidence_sufficient=true và chỉ citation các phần "
                        "được hỗ trợ. Chỉ đặt false khi không có ý nào được trả lời trực tiếp. "
                        "Không tự tính học phí trung bình nếu tài liệu không nêu cách tính "
                        "hoặc cơ cấu sinh viên."
                    )
                ),
                HumanMessage(
                    content=(
                        f"QUESTION:\n{question}\n\nSUBQUESTIONS:\n"
                        + "\n".join(
                            f"- {item}" for item in (subquestions or [question])
                        )
                        + f"\n\nEVIDENCE:\n{evidence}"
                    )
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
            citations = []
            confidence = 0.0
        else:
            citations = validated["citations"]
            confidence = validated["confidence"]
        return Answer(
            answer=text,
            citations=citations,
            confidence=confidence,
            evidence_sufficient=validated["evidence_sufficient"],
            query_understanding=query.__dict__,
        )


class OrchestratorAgent:
    """LangGraph multi-agent orchestrator."""

    def __init__(
        self, model: Any, retriever: HybridRetriever, top_k: int
    ) -> None:
        self.query_agent = QueryUnderstandingAgent(model)
        self.decomposition_agent = QuestionDecompositionAgent(model)
        self.retrieval_agent = RetrievalAgent(retriever, top_k)
        self.analysis_agent = PolicyAnalysisAgent(model)
        self.validation_agent = CitationValidationAgent()
        self.response_agent = ResponseAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentState)
        builder.add_node("query_understanding", self._understand)
        builder.add_node("question_decomposition", self._decompose)
        builder.add_node("retrieval", self._retrieve)
        builder.add_node("policy_analysis", self._analyze)
        builder.add_node("citation_validation", self._validate)
        builder.add_node("response", self._respond)
        builder.add_edge(START, "query_understanding")
        builder.add_edge("query_understanding", "question_decomposition")
        builder.add_edge("question_decomposition", "retrieval")
        builder.add_edge("retrieval", "policy_analysis")
        builder.add_edge("policy_analysis", "citation_validation")
        builder.add_edge("citation_validation", "response")
        builder.add_edge("response", END)
        return builder.compile()

    def _understand(self, state: AgentState) -> dict:
        return {
            "query": self.query_agent.run(
                state["question"], state.get("history", [])
            )
        }

    def _retrieve(self, state: AgentState) -> dict:
        return {
            "retrieved": self.retrieval_agent.run(
                state["question"], state["query"], state["subquestions"]
            )
        }

    def _decompose(self, state: AgentState) -> dict:
        return {
            "subquestions": self.decomposition_agent.run(
                state["query"].rewritten_query
            )
        }

    def _analyze(self, state: AgentState) -> dict:
        return {
            "analysis": self.analysis_agent.run(
                state["question"], state["retrieved"], state["subquestions"]
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

    def run(
        self, question: str, history: list[dict[str, str]] | None = None
    ) -> Answer:
        return self.graph.invoke(
            {"question": question, "history": history or []}
        )["answer"]
