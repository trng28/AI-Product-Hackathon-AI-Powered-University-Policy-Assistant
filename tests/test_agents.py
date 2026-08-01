from backend.policy_assistant.agents import (
    CitationValidationAgent,
    QueryUnderstandingAgent,
    RetrievalAgent,
)
from backend.policy_assistant.models import LegalChunk, QueryUnderstanding, SearchResult


def test_citation_validator_rejects_unknown_chunk() -> None:
    chunk = LegalChunk("known", "policy.pdf", 13, "Điều 11", "Khoản 2", "Evidence")
    result = SearchResult(chunk, 0.9)
    analysis = {
        "answer": "Claim",
        "evidence_sufficient": True,
        "citations": [{"chunk_id": "invented", "support": "none"}],
        "confidence": 0.97,
    }
    validated = CitationValidationAgent().run(analysis, [result])
    assert validated["evidence_sufficient"] is False
    assert validated["citations"] == []


def test_citation_validator_enriches_valid_citation() -> None:
    chunk = LegalChunk("known", "policy.pdf", 13, "Điều 11", "Khoản 2", "Evidence")
    analysis = {
        "answer": "Grounded claim",
        "evidence_sufficient": True,
        "citations": [{"chunk_id": "known", "support": "Evidence"}],
        "confidence": 0.9,
    }
    validated = CitationValidationAgent().run(analysis, [SearchResult(chunk, 0.9)])
    assert validated["evidence_sufficient"] is True
    assert validated["citations"][0]["page"] == 13


def test_retrieval_agent_merges_compound_subquestions() -> None:
    tuition = SearchResult(
        LegalChunk("tuition", "fee", 0, "Financial Regulations", "VUNI_TS03", "815,850,000 VND/year"),
        0.9,
    )
    programs = SearchResult(
        LegalChunk("programs", "academic", 0, "Academic Programs", "", "Degree programs"),
        0.8,
    )

    class StubRetriever:
        def search(self, query, keywords, target_articles, top_k, original_query=""):
            if "học phí" in query:
                return [tuition]
            if "ngành" in query:
                return [programs]
            return []

    query = QueryUnderstanding("policy_lookup", "programs and tuition", [], [], "VinUni")
    results = RetrievalAgent(StubRetriever(), top_k=3).run(
        "VinUni đào tạo bao nhiêu ngành, học phí trung bình bao nhiêu một năm?",
        query,
        ["VinUni đào tạo bao nhiêu ngành?", "Học phí VinUni một năm bao nhiêu?"],
    )
    assert {result.chunk.id for result in results} == {"programs", "tuition"}


def test_query_understanding_receives_bounded_chat_history() -> None:
    class StubModel:
        messages = []

        def with_structured_output(self, schema):
            return self

        def invoke(self, messages):
            self.messages = messages
            return {
                "intent": "policy_lookup",
                "topic": "tuition",
                "keywords": ["tuition"],
                "target_articles": [],
                "rewritten_query": "Học phí ngành Computer Science là bao nhiêu?",
            }

    model = StubModel()
    QueryUnderstandingAgent(model).run(
        "Còn ngành đó thì sao?",
        [
            {"role": "user", "content": "Học phí Computer Science là bao nhiêu?"},
            {"role": "assistant", "content": "Thông tin học phí..."},
        ],
    )
    prompt = "\n".join(str(message.content) for message in model.messages)
    assert "Học phí Computer Science" in prompt
    assert "Còn ngành đó thì sao?" in prompt
