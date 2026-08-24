'''
Schemas for the backend API.
'''

from typing import Literal

from pydantic import BaseModel, Field

QuestionType = Literal["single_fact", "comparative", "out_of_scope"]
Confidence = Literal["high", "medium", "low"]


class ChatRequest(BaseModel):
    question: str


class Citation(BaseModel):
    doc_id: str
    doc_title: str
    section: str
    page: int
    snippet: str


class EvidenceSpan(BaseModel):
    doc_id: str
    page: int
    quote: str


class ChatResponse(BaseModel):
    question: str
    question_type: QuestionType
    answer: str
    confidence: Confidence
    refused: bool
    citations: list[Citation]
    answer_found: bool = False
    complete_answer_found: bool = False
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    retrieval_rank: int | None = None


class DocumentSummary(BaseModel):
    doc_id: str
    doc_title: str
    pages: int
