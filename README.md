# Document Assistant — demo (Fictional Solidaris Insurance)
Foyer - A document chatbot that answers questions about a fictional corpus of
insurance contracts (auto, home, life/health, claims FAQ, and decision letters),
without LangChain or LlamaIndex — every component (chunking, indexing,
retrieval, and generation) is implemented explicitly.

## Architecture

```
PDF (6 fictional documents)
    → ingestion (pdfplumber, heading detection based on font and bold size)
    → section-based chunking
    → offline indexing: BM25 (keywords) + OpenAI embeddings (semantic search)
    → at query time:
      1. lightweight question classification (factual / comparative)
      2. hybrid retrieval (BM25 + cosine similarity), with a deterministic confidence score
      3. below the confidence threshold → explicit refusal, with no LLM call
      4. factual question → top-1 generation, then bounded escalation until complete
         evidence is found; comparisons → one batch call with diverse documents
      5. otherwise → structured generation with validated evidence
    → typed response: answer, found/completeness flags, evidence spans, quotes,
      question type, confidence, citations, refused (yes/no)
```

The confidence score is calculated from retrieval (BM25 + cosine similarity),
not self-reported by the LLM. Asking an LLM whether it is confident generally
produces a confident answer even when the context does not support it — this is
exactly how weak retrieval turns into hallucination.

A comparative question ("what is the difference between the auto and home
deductibles?") is retrieved differently from a simple factual question:
instead of global top-k retrieval (which may return results from only one
document), it retrieves the best passage from each distinct document.

## Deliberate Omissions

- No multi-turn conversation memory: each question is processed independently.
  A real product would need to resolve references ("and what about home?"
  after a question about auto insurance).
- No retraining or fine-tuning of the embedding model: the corpus is too small
  for that to be meaningful, and hybrid BM25 + embeddings is sufficient to
  demonstrate the principle.
- No authentication or tenant separation: the index covers the entire
  fictional corpus, which would not be suitable for real customer-specific
  contractual documents.
- The factual/comparative classifier is a keyword heuristic, not a learned
  model: sufficient for the demo, but fragile for wording outside the covered
  patterns.
- No response cache: every identical factual question triggers a complete LLM
  call again.
- No production evaluation store: `backend/evaluate.py` runs the checked-in
  smoke set and prints retrieval rank, refusal/completeness, citation hit,
  latency, and token usage, but does not persist results by default.

## What Would Break First at Scale

Retrieval is in memory (dense NumPy arrays, with BM25 rebuilt at startup): this
works well for a few hundred documents, but beyond a corpus of roughly
10⁴–10⁵ chunks, the cost of dense matrix multiplication and BM25 startup
reconstruction becomes the first bottleneck. The system would need an
approximate vector index (such as HNSW) and persistent BM25 instead of
rebuilding it on every deployment. The second breaking point would be heuristic
classification: with a real volume of varied business questions, false
negatives for comparative questions would likely increase quickly, creating the
silent risk already described: a misrouted question returns a partial answer
with seemingly acceptable confidence.

## Run Locally

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then set OPENAI_API_KEY
python data/render_pdfs.py   # (re)generates source PDFs if needed
python -m app.build_index    # builds the index (calls the embeddings API once)
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

## Evaluate

After building the index and setting `OPENAI_API_KEY`, run:

```bash
cd backend
python -m evaluate --output eval_results.json
```

The report contains one row per case plus aggregate refusal accuracy, citation
hit rate, complete-answer rate, mean latency, and total token usage. The cases
in `backend/eval_cases.json` intentionally include a factual lookup, a
comparison, and an out-of-scope question.

## Deployment

The multi-stage `Dockerfile` builds the Vite frontend, then creates a Python
image that serves the FastAPI API and frontend static files from the same
process — one link to share. The app is deployed on Render (Docker web
service, free plan); `OPENAI_API_KEY` is configured as an environment variable
on Render and is never committed.
