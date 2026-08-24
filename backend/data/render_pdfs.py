"""Render the authored Markdown sources in sources/ into real PDFs in pdfs/.
Kept deliberately simple: '# ' -> title, '## ' -> section heading, blank-line
separated paragraphs -> body text. Just enough structure for the ingestion
pipeline to parse real PDF files with headings and page numbers, mirroring
how the actual policy documents would look.
"""

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

SOURCES_DIR = Path(__file__).parent / "sources"
PDFS_DIR = Path(__file__).parent / "pdfs"


def _latin1_safe(text: str) -> str:
    """Core Helvetica font is latin-1 only; swap the few characters we use
    that fall outside it rather than embedding a Unicode TTF."""
    return text.replace("—", "-").replace("–", "-")


def render(md_path: Path) -> Path:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    for raw_line in md_path.read_text(encoding="utf-8").splitlines():
        line = _latin1_safe(raw_line.strip())
        if not line:
            pdf.ln(4)
            continue
        if line.startswith("## "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 8, line.removeprefix("## "), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=11)
        elif line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 10, line.removeprefix("# "), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=11)
        else:
            pdf.multi_cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    out_path = PDFS_DIR / (md_path.stem + ".pdf")
    pdf.output(str(out_path))
    return out_path


def main() -> None:
    PDFS_DIR.mkdir(exist_ok=True)
    for md_path in sorted(SOURCES_DIR.glob("*.md")):
        out_path = render(md_path)
        print(f"{md_path.name} -> {out_path.name}")


if __name__ == "__main__":
    main()
