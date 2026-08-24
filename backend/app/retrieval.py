"""Hybrid retrieval: BM25 keyword score + OpenAI embedding cosine similarity.

Kept as two explicit, inspectable signals combined by a fixed weight rather
than a single opaque similarity search -- this is the point the demo is
built to make: retrieval quality is what determines whether the model can
hallucinate, so the retrieval step needs to be legible, not a black box.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import numpy as np
from openai import OpenAI
from rank_bm25 import BM25Okapi

from app.build_index import EMBEDDING_DIMENSIONS
from app.config import INDEX_PATH, settings

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class ScoredChunk:
    doc_id: str
    doc_title: str
    section: str
    page: int
    text: str
    score: float


class RetrievalIndex:
    def __init__(self) -> None:
        records = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        self.records = records
        self.texts = [r["text"] for r in records]

        embeddings = np.array([r["embedding"] for r in records], dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        self._unit_embeddings = embeddings / np.clip(norms, 1e-8, None)

        self._bm25 = BM25Okapi([_tokenize(t) for t in self.texts])
        self._client = OpenAI(api_key=settings.openai_api_key)

    def _embed_query(self, query: str) -> np.ndarray:
        resp = self._client.embeddings.create(
            model=settings.embedding_model,
            input=[query],
            dimensions=EMBEDDING_DIMENSIONS,
        )
        vec = np.array(resp.data[0].embedding, dtype=np.float32)
        return vec / max(float(np.linalg.norm(vec)), 1e-8)

    @staticmethod
    def _squash_bm25(raw_scores: np.ndarray) -> np.ndarray:
        """Scale BM25 to roughly [0, 1] without min-max: min-max is relative
        to the current candidate set, so with a small corpus the best-of-a-
        bad-lot chunk always lands near 1.0 even when nothing actually
        matches. A fixed squash keeps "no keyword overlap" close to 0
        regardless of what else is in the index."""
        positive = np.clip(raw_scores, 0.0, None)
        return positive / (positive + 4.0)

    def search(self, query: str, k: int) -> list[ScoredChunk]:
        bm25_scores = np.array(self._bm25.get_scores(_tokenize(query)), dtype=np.float32)
        cosine_scores = self._unit_embeddings @ self._embed_query(query)

        combined = 0.5 * self._squash_bm25(bm25_scores) + 0.5 * np.clip(cosine_scores, 0.0, 1.0)

        top_idx = np.argsort(-combined)[:k]
        return [
            ScoredChunk(
                doc_id=self.records[i]["doc_id"],
                doc_title=self.records[i]["doc_title"],
                section=self.records[i]["section"],
                page=self.records[i]["page"],
                text=self.records[i]["text"],
                score=float(combined[i]),
            )
            for i in top_idx
        ]

    def search_diverse(self, query: str, max_docs: int) -> list[ScoredChunk]:
        """For comparative questions: best chunk per distinct document,
        instead of the top-k which could all come from one doc."""
        ranked = self.search(query, k=len(self.records))
        seen_docs: set[str] = set()
        picked: list[ScoredChunk] = []
        for chunk in ranked:
            if chunk.doc_id in seen_docs:
                continue
            seen_docs.add(chunk.doc_id)
            picked.append(chunk)
            if len(picked) >= max_docs:
                break
        return picked


_index: RetrievalIndex | None = None


def get_index() -> RetrievalIndex:
    global _index
    if _index is None:
        _index = RetrievalIndex()
    return _index
