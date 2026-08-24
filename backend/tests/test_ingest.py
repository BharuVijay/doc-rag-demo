from app.config import PDFS_DIR
from app.ingest import parse_all, parse_pdf


def test_parse_pdf_finds_sections():
    chunks = parse_pdf(PDFS_DIR / "auto_policy.pdf")
    sections = [c.section for c in chunks]
    assert any("Franchise" in s for s in sections)
    assert any("Exclusions" in s for s in sections)
    assert all(c.doc_id == "auto_policy" for c in chunks)
    assert all("Assurance Auto" in c.doc_title for c in chunks)


def test_parse_all_covers_every_document():
    chunks = parse_all(PDFS_DIR)
    doc_ids = {c.doc_id for c in chunks}
    assert doc_ids == {
        "auto_policy",
        "home_policy",
        "claims_faq",
        "claim_letter_approved",
        "claim_letter_rejected",
        "life_health_summary",
    }
    assert len(chunks) >= len(doc_ids) * 3
