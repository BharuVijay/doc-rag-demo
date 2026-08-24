"""PDF -> section-aware chunks.

Real policy PDFs don't carry semantic tags, so headings are detected from
layout signal (bold + font size) rather than assumed markup. This mirrors
how the source PDFs were produced: title = bold 16pt, section heading =
bold 13pt, everything else is body text belonging to the preceding section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

TITLE_SIZE_MIN = 15.0
HEADING_SIZE_MIN = 12.5
BOLD_MARKER = "Bold"


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    section: str
    page: int
    text: str


@dataclass
class _Line:
    text: str
    top: float
    page: int
    is_bold: bool
    size: float


def _lines_for_page(page, page_number: int) -> list[_Line]:
    words = page.extract_words(extra_attrs=["fontname", "size"])
    lines: dict[float, list[dict]] = {}
    for w in words:
        # group words into visual lines by rounded vertical position
        key = round(w["top"] / 3) * 3
        lines.setdefault(key, []).append(w)

    result = []
    for top in sorted(lines):
        line_words = lines[top]
        text = " ".join(w["text"] for w in line_words)
        is_bold = all(BOLD_MARKER in w["fontname"] for w in line_words)
        size = max(w["size"] for w in line_words)
        result.append(_Line(text=text, top=top, page=page_number, is_bold=is_bold, size=size))
    return result


def parse_pdf(pdf_path: Path) -> list[Chunk]:
    doc_id = pdf_path.stem
    chunks: list[Chunk] = []

    with pdfplumber.open(pdf_path) as pdf:
        all_lines: list[_Line] = []
        for i, page in enumerate(pdf.pages, start=1):
            all_lines.extend(_lines_for_page(page, i))

    if not all_lines:
        return chunks

    doc_title = all_lines[0].text
    current_section = doc_title
    current_page = all_lines[0].page
    current_body: list[str] = []

    def flush():
        body = " ".join(current_body).strip()
        if body:
            chunks.append(
                Chunk(
                    doc_id=doc_id,
                    doc_title=doc_title,
                    section=current_section,
                    page=current_page,
                    text=body,
                )
            )

    for line in all_lines[1:]:
        if line.is_bold and line.size >= HEADING_SIZE_MIN:
            flush()
            current_section = line.text
            current_page = line.page
            current_body = []
        else:
            current_body.append(line.text)

    flush()
    return chunks


def parse_all(pdf_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        chunks.extend(parse_pdf(pdf_path))
    return chunks
