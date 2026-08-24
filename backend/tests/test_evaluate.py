from evaluate import summarize


def test_summarize_reports_quality_and_operational_metrics():
    results = [
        {
            "refusal_correct": True,
            "citation_hit": True,
            "complete_answer_found": True,
            "latency_ms": 10.0,
            "total_tokens": 100,
        },
        {
            "refusal_correct": False,
            "citation_hit": False,
            "complete_answer_found": False,
            "latency_ms": 30.0,
            "total_tokens": None,
        },
    ]

    summary = summarize(results)

    assert summary == {
        "cases": 2,
        "refusal_accuracy": 0.5,
        "citation_hit_rate": 0.5,
        "complete_answer_rate": 0.5,
        "mean_latency_ms": 20.0,
        "total_tokens": 100,
    }
