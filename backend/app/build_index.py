"""Offline step: parse the PDFs, embed each chunk once with the OpenAI API,
and cache the result to data/index.json.

Run this whenever the source documents change:
    python -m app.build_index

The BM25 (keyword) side of retrieval is rebuilt from the cached chunk text
at every app startup -- it's free and deterministic. Only the embeddings
(the part that costs money and requires network access) are precomputed
and committed to the repo, so the deployed service never calls the
embeddings API at request time or at cold start.
"""

from __future__ import annotations

import json

from openai import OpenAI, RateLimitError

from app.config import INDEX_PATH, PDFS_DIR, settings
from app.ingest import parse_all

EMBEDDING_DIMENSIONS = 512


def main() -> None:
    chunks = parse_all(PDFS_DIR)
    if not chunks:
        raise SystemExit(f"No chunks parsed from {PDFS_DIR} -- run data/render_pdfs.py first.")

    client = OpenAI(api_key=settings.openai_api_key)
    texts = [c.text for c in chunks]

    embeddings: list[list[float]] = []
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            resp = client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
        except RateLimitError as exc:
            raise SystemExit(
                "OpenAI quota exceeded while building the index. "
                "Check billing/quota, replace OPENAI_API_KEY, and rerun the command."
            ) from exc
        embeddings.extend(item.embedding for item in resp.data)

    records = [
        {
            "doc_id": c.doc_id,
            "doc_title": c.doc_title,
            "section": c.section,
            "page": c.page,
            "text": c.text,
            "embedding": emb,
        }
        for c, emb in zip(chunks, embeddings)
    ]

    INDEX_PATH.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(records)} chunks -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
