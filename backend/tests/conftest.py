import json
from types import SimpleNamespace

import pytest

from app import config, retrieval

FAKE_RECORDS = [
    {
        "doc_id": "auto_policy",
        "doc_title": "Conditions Générales - Assurance Auto",
        "section": "Section 2 - Franchise",
        "page": 1,
        "text": "La franchise auto pour dommages tous accidents est de 350 EUR par sinistre.",
        "embedding": [1.0, 0.0, 0.0],
    },
    {
        "doc_id": "home_policy",
        "doc_title": "Conditions Générales - Assurance Habitation",
        "section": "Section 2 - Franchise",
        "page": 1,
        "text": "La franchise habitation pour dégât des eaux est de 200 EUR par sinistre.",
        "embedding": [0.0, 1.0, 0.0],
    },
    {
        "doc_id": "claims_faq",
        "doc_title": "FAQ Sinistres - Toutes Garanties",
        "section": "Quel est le délai de traitement d'un dossier ?",
        "page": 1,
        "text": "Une première réponse est formulée sous 15 jours ouvrables après dossier complet.",
        "embedding": [0.0, 0.0, 1.0],
    },
]


class _FakeEmbeddings:
    def __init__(self, vector):
        self._vector = vector

    def create(self, model, input, dimensions):
        return SimpleNamespace(data=[SimpleNamespace(embedding=self._vector)])


class _FakeChatCompletions:
    def __init__(self, answer_text):
        self._answer_text = answer_text

    def create(self, **kwargs):
        content = json.dumps({"answer": self._answer_text})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeOpenAI:
    """Stand-in for openai.OpenAI: returns a fixed query embedding and a
    fixed chat answer so retrieval/generation logic can be tested without
    network access or an API key."""

    def __init__(self, query_vector, answer_text="Réponse simulée.", api_key=None):
        self.embeddings = _FakeEmbeddings(query_vector)
        self.chat = SimpleNamespace(completions=_FakeChatCompletions(answer_text))


@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(FAKE_RECORDS), encoding="utf-8")
    monkeypatch.setattr(config, "INDEX_PATH", index_path)
    monkeypatch.setattr(retrieval, "INDEX_PATH", index_path)
    retrieval._index = None
    yield index_path
    retrieval._index = None
