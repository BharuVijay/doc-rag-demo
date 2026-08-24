from app import retrieval
from tests.conftest import FakeOpenAI


def test_search_ranks_matching_chunk_first(fake_index, monkeypatch):
    monkeypatch.setattr(
        retrieval, "OpenAI", lambda api_key=None: FakeOpenAI(query_vector=[0.95, 0.05, 0.0])
    )
    index = retrieval.get_index()
    results = index.search("franchise auto tous accidents", k=2)
    assert results[0].doc_id == "auto_policy"


def test_search_diverse_returns_one_chunk_per_document(fake_index, monkeypatch):
    monkeypatch.setattr(
        retrieval, "OpenAI", lambda api_key=None: FakeOpenAI(query_vector=[0.4, 0.4, 0.4])
    )
    index = retrieval.get_index()
    results = index.search_diverse("franchise", max_docs=3)
    assert len({c.doc_id for c in results}) == len(results)
    assert len(results) == 3
