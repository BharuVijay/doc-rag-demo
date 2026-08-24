from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from openai import RateLimitError

from app.config import INDEX_PATH
from app.generate import answer_question
from app.retrieval import get_index
from app.schemas import ChatRequest, ChatResponse, DocumentSummary

app = FastAPI(title="Foyer RAG Demo")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "index_ready": INDEX_PATH.exists()}


@app.get("/api/documents", response_model=list[DocumentSummary])
def list_documents() -> list[DocumentSummary]:
    index = get_index()
    pages_per_doc: Counter[str] = Counter()
    titles: dict[str, str] = {}
    for r in index.records:
        pages_per_doc[r["doc_id"]] = max(pages_per_doc[r["doc_id"]], r["page"])
        titles[r["doc_id"]] = r["doc_title"]

    return [
        DocumentSummary(doc_id=doc_id, doc_title=titles[doc_id], pages=pages)
        for doc_id, pages in sorted(pages_per_doc.items())
    ]


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question vide.")
    if not INDEX_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="The search index is not ready. Run `python -m app.build_index` first.",
        )
    try:
        return answer_question(question)
    except RateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "OpenAI quota exceeded. Check the API account billing/quota "
                "and replace OPENAI_API_KEY if needed."
            ),
        ) from exc


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
