"""Run a small end-to-end evaluation set and print JSON results.

Usage:
    python -m evaluate
    python -m evaluate --cases eval_cases.json --output eval_results.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.generate import answer_question
from app.retrieval import get_index

DEFAULT_CASES = Path(__file__).with_name("eval_cases.json")


def _gold_rank(question: str, expected_doc_ids: list[str]) -> int | None:
    if not expected_doc_ids:
        return None
    ranked = get_index().search(question, k=len(get_index().records))
    for rank, chunk in enumerate(ranked, start=1):
        if chunk.doc_id in expected_doc_ids:
            return rank
    return None


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    expected_doc_ids = case.get("expected_doc_ids", [])
    response = answer_question(case["question"])
    citation_doc_ids = {citation.doc_id for citation in response.citations}
    expected_citation = bool(citation_doc_ids & set(expected_doc_ids)) if expected_doc_ids else not response.citations
    return {
        "id": case["id"],
        "question": case["question"],
        "retrieval_rank": _gold_rank(case["question"], expected_doc_ids),
        "refused": response.refused,
        "refusal_expected": case.get("should_refuse", False),
        "refusal_correct": response.refused == case.get("should_refuse", False),
        "answer_found": response.answer_found,
        "complete_answer_found": response.complete_answer_found,
        "citation_hit": expected_citation,
        "citation_count": len(response.citations),
        "latency_ms": response.latency_ms,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "total_tokens": response.total_tokens,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(field: str) -> float:
        return round(sum(bool(result[field]) for result in results) / len(results), 3) if results else 0.0

    token_values = [result["total_tokens"] for result in results if result["total_tokens"] is not None]
    latency_values = [result["latency_ms"] for result in results if result["latency_ms"] is not None]
    return {
        "cases": len(results),
        "refusal_accuracy": rate("refusal_correct"),
        "citation_hit_rate": rate("citation_hit"),
        "complete_answer_rate": rate("complete_answer_found"),
        "mean_latency_ms": round(sum(latency_values) / len(latency_values), 2) if latency_values else None,
        "total_tokens": sum(token_values) if token_values else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    results = [evaluate_case(case) for case in cases]
    report = {"summary": summarize(results), "results": results}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
