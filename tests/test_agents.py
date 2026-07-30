from src.policy_assistant.agents import CitationValidationAgent
from src.policy_assistant.models import LegalChunk, SearchResult


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
