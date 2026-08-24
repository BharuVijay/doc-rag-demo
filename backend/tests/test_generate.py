from app import generate, retrieval
from app.retrieval import ScoredChunk
from app.schemas import EvidenceSpan
from tests.conftest import FakeOpenAI


def _patch_openai(monkeypatch, query_vector, answer_text="Réponse simulée."):
    monkeypatch.setattr(retrieval, "OpenAI", lambda api_key=None: FakeOpenAI(query_vector))
    monkeypatch.setattr(
        generate, "OpenAI", lambda api_key=None: FakeOpenAI(query_vector, answer_text=answer_text)
    )


def test_confident_match_returns_answer_with_citations(fake_index, monkeypatch):
    _patch_openai(monkeypatch, query_vector=[0.95, 0.05, 0.0], answer_text="La franchise auto est de 350 EUR.")

    response = generate.answer_question("Quelle est la franchise auto tous accidents ?")

    assert response.refused is False
    assert response.confidence in ("medium", "high")
    assert response.citations
    assert response.citations[0].doc_id == "auto_policy"
    assert "350 EUR" in response.answer


def test_weak_match_is_refused_not_hallucinated(fake_index, monkeypatch):
    # a query vector far from every indexed chunk -> low combined score
    _patch_openai(monkeypatch, query_vector=[-1.0, -1.0, -1.0])

    response = generate.answer_question("Quel est le prix d'un billet d'avion pour Tokyo ?")

    assert response.refused is True
    assert response.confidence == "low"
    assert response.citations == []
    assert response.question_type == "out_of_scope"


def test_comparative_question_routes_to_diverse_retrieval(fake_index, monkeypatch):
    _patch_openai(monkeypatch, query_vector=[0.5, 0.5, 0.5], answer_text="Les franchises diffèrent selon le produit.")

    response = generate.answer_question(
        "Quelle est la différence de franchise entre l'auto et l'habitation ?"
    )

    assert response.question_type in ("comparative", "out_of_scope")
    if not response.refused:
        doc_ids = {c.doc_id for c in response.citations}
        assert len(doc_ids) == len(response.citations)


def test_evidence_validation_rejects_quotes_not_in_context():
    chunk = ScoredChunk("auto", "Auto", "Franchise", 1, "Franchise de 350 EUR.", 0.9)
    valid = generate._GenerationResult(
        "350 EUR", True, True, [EvidenceSpan(doc_id="auto", page=1, quote="350 EUR")], ["Franchise de 350 EUR."]
    )
    invalid = generate._GenerationResult(
        "500 EUR", True, True, [EvidenceSpan(doc_id="auto", page=1, quote="500 EUR")], ["500 EUR"]
    )

    assert generate._validate_evidence(valid, [chunk]) is True
    assert generate._validate_evidence(invalid, [chunk]) is False


def test_factual_generation_escalates_until_complete(monkeypatch):
    chunks = [
        ScoredChunk("auto", "Auto", "Franchise", 1, "Montant partiel.", 0.9),
        ScoredChunk("auto", "Auto", "Franchise", 2, "Franchise de 350 EUR.", 0.8),
    ]

    class FakeIndex:
        def search(self, query, k):
            return chunks

    calls = []

    def fake_call(client, question, candidates):
        calls.append(candidates)
        if len(calls) == 1:
            return generate._GenerationResult("Partiel", True, False, [], [])
        return generate._GenerationResult(
            "350 EUR",
            True,
            True,
            [EvidenceSpan(doc_id="auto", page=2, quote="Franchise de 350 EUR.")],
            ["Franchise de 350 EUR."],
        )

    monkeypatch.setattr(generate, "get_index", lambda: FakeIndex())
    monkeypatch.setattr(generate, "OpenAI", lambda api_key=None: object())
    monkeypatch.setattr(generate, "_call_llm", fake_call)
    monkeypatch.setattr(generate.settings, "top_k", 2)

    response = generate.answer_question("Quelle est la franchise auto ?")

    assert response.refused is False
    assert response.retrieval_rank == 2
    assert len(calls) == 2
