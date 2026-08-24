"""Retrieval -> confidence gate -> generation, wired together explicitly.

Confidence is derived from the retrieval score, not from the LLM's own
self-report. An LLM asked "how confident are you" tends to answer
confidently regardless of whether the retrieved context actually supports
it -- that's the retrieval-failure-looks-like-a-hallucination problem this
demo exists to show. Gating on retrieval score means a weak match refuses
before the model ever gets a chance to invent something plausible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from time import perf_counter

from openai import OpenAI

from app.classify import is_comparative
from app.config import settings
from app.retrieval import ScoredChunk, get_index
from app.schemas import ChatResponse, Citation, Confidence, EvidenceSpan, QuestionType

REFUSAL_TEXT = (
    "Je ne trouve pas d'information suffisamment fiable dans les documents "
    "disponibles pour répondre à cette question. Merci de la reformuler ou "
    "de contacter le service client."
)

_ANSWER_SCHEMA = {
    "name": "policy_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": (
                    "Réponse en français, basée strictement sur le contexte fourni. "
                    "Si le contexte ne permet pas de répondre, le dire explicitement."
                ),
            },
            "answer_found": {"type": "boolean"},
            "complete_answer_found": {"type": "boolean"},
            "evidence_spans": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string"},
                        "page": {"type": "integer"},
                        "quote": {"type": "string"},
                    },
                    "required": ["doc_id", "page", "quote"],
                    "additionalProperties": False,
                },
            },
            "quotes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["answer", "answer_found", "complete_answer_found", "evidence_spans", "quotes"],
        "additionalProperties": False,
    },
}

_SYSTEM_PROMPT = (
    "Tu es un assistant qui répond aux questions sur des documents "
    "d'assurance à partir d'extraits fournis. Réponds uniquement à partir "
    "du contexte donné, en citant les valeurs exactes (montants, délais, "
    "pourcentages) telles qu'elles apparaissent. Retourne answer_found=true "
    "si le contexte contient une réponse, complete_answer_found=true seulement "
    "si la réponse est complète, et une evidence_span par affirmation importante. "
    "Chaque quote doit être recopiée mot pour mot depuis le contexte. Si le "
    "contexte ne couvre pas la question, dis-le clairement au lieu d'inventer."
)


@dataclass
class _GenerationResult:
    answer: str
    answer_found: bool
    complete_answer_found: bool
    evidence_spans: list[EvidenceSpan]
    quotes: list[str]
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def _confidence_bucket(score: float) -> Confidence:
    if score >= settings.confidence_high_threshold:
        return "high"
    if score >= settings.confidence_low_threshold:
        return "medium"
    return "low"


def _to_citation(chunk: ScoredChunk) -> Citation:
    snippet = chunk.text if len(chunk.text) <= 240 else chunk.text[:237] + "..."
    return Citation(
        doc_id=chunk.doc_id,
        doc_title=chunk.doc_title,
        section=chunk.section,
        page=chunk.page,
        snippet=snippet,
    )


def _parse_generation(payload: dict) -> _GenerationResult:
    return _GenerationResult(
        answer=payload.get("answer", ""),
        # Defaults keep old test doubles compatible; production calls use the full schema.
        answer_found=payload.get("answer_found", True),
        complete_answer_found=payload.get("complete_answer_found", True),
        evidence_spans=[EvidenceSpan.model_validate(span) for span in payload.get("evidence_spans", [])],
        quotes=payload.get("quotes", []),
    )


def _call_llm(client: OpenAI, question: str, chunks: list[ScoredChunk]) -> _GenerationResult:
    context = "\n\n".join(
        f"[{c.doc_title} - {c.section}]\n{c.text}" for c in chunks
    )
    resp = client.chat.completions.create(
        model=settings.chat_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Contexte:\n{context}\n\nQuestion: {question}",
            },
        ],
        response_format={"type": "json_schema", "json_schema": _ANSWER_SCHEMA},
    )
    payload = json.loads(resp.choices[0].message.content)
    result = _parse_generation(payload)
    usage = getattr(resp, "usage", None)
    if usage is not None:
        result.prompt_tokens = getattr(usage, "prompt_tokens", None)
        result.completion_tokens = getattr(usage, "completion_tokens", None)
        result.total_tokens = getattr(usage, "total_tokens", None)
    return result


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _validate_evidence(result: _GenerationResult, chunks: list[ScoredChunk]) -> bool:
    by_location = {(chunk.doc_id, chunk.page): chunk.text for chunk in chunks}
    for span in result.evidence_spans:
        source = by_location.get((span.doc_id, span.page))
        if source is None or _normalise_text(span.quote) not in _normalise_text(source):
            return False
    for quote in result.quotes:
        if not any(_normalise_text(quote) in _normalise_text(chunk.text) for chunk in chunks):
            return False
    return True


def _response_from_result(
    question: str,
    question_type: QuestionType,
    confidence: Confidence,
    result: _GenerationResult,
    chunks: list[ScoredChunk],
    started: float,
) -> ChatResponse:
    valid_evidence = _validate_evidence(result, chunks)
    accepted = result.answer_found and result.complete_answer_found and valid_evidence
    return ChatResponse(
        question=question,
        question_type=question_type if accepted else "out_of_scope",
        answer=result.answer if accepted else REFUSAL_TEXT,
        confidence=confidence if accepted else "low",
        refused=not accepted,
        citations=[_to_citation(c) for c in chunks] if accepted else [],
        answer_found=accepted,
        complete_answer_found=accepted,
        evidence_spans=result.evidence_spans if accepted else [],
        quotes=result.quotes if accepted else [],
        latency_ms=round((perf_counter() - started) * 1000, 2),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        retrieval_rank=1 if accepted else None,
    )


def answer_question(question: str) -> ChatResponse:
    started = perf_counter()
    index = get_index()
    comparative = is_comparative(question)

    if comparative:
        chunks = index.search_diverse(question, max_docs=settings.top_k)
    else:
        chunks = index.search(question, k=settings.top_k)

    top_score = chunks[0].score if chunks else 0.0
    confidence = _confidence_bucket(top_score)
    question_type: QuestionType = "comparative" if comparative else "single_fact"

    if confidence == "low" or not chunks:
        return ChatResponse(
            question=question,
            question_type="out_of_scope",
            answer=REFUSAL_TEXT,
            confidence="low",
            refused=True,
            citations=[],
        )

    client = OpenAI(api_key=settings.openai_api_key)

    if comparative:
        result = _call_llm(client, question, chunks)
        return _response_from_result(question, question_type, confidence, result, chunks, started)

    # Factual lookups use the cheapest sufficient context first, with a hard bound.
    last_result: _GenerationResult | None = None
    for rank, chunk in enumerate(chunks, start=1):
        result = _call_llm(client, question, [chunk])
        last_result = result
        if result.answer_found and result.complete_answer_found and _validate_evidence(result, [chunk]):
            response = _response_from_result(question, question_type, confidence, result, [chunk], started)
            response.retrieval_rank = rank
            return response

    if last_result is None:
        return ChatResponse(
            question=question,
            question_type="out_of_scope",
            answer=REFUSAL_TEXT,
            confidence="low",
            refused=True,
            citations=[],
            latency_ms=round((perf_counter() - started) * 1000, 2),
        )
    response = _response_from_result(question, question_type, confidence, last_result, [chunks[-1]], started)
    response.retrieval_rank = len(chunks)
    return response
