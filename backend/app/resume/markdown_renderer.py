"""Markdown -> DOCX and PDF converter for tailored resumes.
Maintains identical ATS-friendly styling, typography (Calibri), margins, and borders as the core engine.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

import docx
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from resume_builder.render.docx_renderer import (
    BODY_PT,
    FONT,
    HEADING_PT,
    MARGIN_IN,
    NAME_PT,
    PAPER_IN,
    _bottom_border,
    _remove_border,
    _round_bullets,
    _set_style_font,
)
from resume_builder.render.pdf import docx_to_pdf

INLINE_RE = re.compile(
    r"(\*\*\*(.+?)\*\*\*"
    r"|\*\*(.+?)\*\*"
    r"|\*(.+?)\*"
    r"|\[(.+?)\]\((.+?)\))"
)


def _add_hyperlink(paragraph, url: str, text: str, color: str = "004F9F", underline: bool = True) -> None:
    """Adds a clickable external hyperlink to a python-docx paragraph."""
    try:
        part = paragraph.part
        r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)
        new_run = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        if color:
            c = OxmlElement("w:color")
            c.set(qn("w:val"), color)
            rPr.append(c)
        if underline:
            u = OxmlElement("w:u")
            u.set(qn("w:val"), "single")
            rPr.append(u)
        new_run.append(rPr)
        new_run.text = text
        hyperlink.append(new_run)
        paragraph._p.append(hyperlink)
    except Exception:
        # Fallback to plain run if relationship creation fails
        r = paragraph.add_run(text)
        if underline:
            r.underline = True


def _add_formatted_runs(paragraph, text: str) -> None:
    """Parses inline bold, italic, and links, appending runs to paragraph."""
    pos = 0
    for m in INLINE_RE.finditer(text):
        start, end = m.span()
        if start > pos:
            paragraph.add_run(text[pos:start])
        full = m.group(0)
        if full.startswith("***") and full.endswith("***"):
            r = paragraph.add_run(m.group(2))
            r.bold = True
            r.italic = True
        elif full.startswith("**") and full.endswith("**"):
            r = paragraph.add_run(m.group(3))
            r.bold = True
        elif full.startswith("*") and full.endswith("*"):
            r = paragraph.add_run(m.group(4))
            r.italic = True
        elif full.startswith("[") and full.endswith(")"):
            label = m.group(5)
            url = m.group(6)
            if url.startswith(("http://", "https://", "mailto:")):
                _add_hyperlink(paragraph, url, label)
            else:
                paragraph.add_run(label)
        pos = end
    if pos < len(text):
        paragraph.add_run(text[pos:])


def markdown_to_docx(md_text: str, out_path: str | Path, paper_size: str = "Letter") -> Path:
    """Converts a Markdown resume into an ATS-optimized Word (.docx) document."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()

    # Extract author name from first level-1 heading if present
    lines = [ln.strip() for ln in md_text.splitlines()]
    author = "Candidate"
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            author = line.lstrip("#").strip()
            break

    # Setup page geometry & margins
    sec = doc.sections[0]
    w, h = PAPER_IN.get(paper_size, (8.5, 11.0))
    sec.page_width, sec.page_height = Inches(w), Inches(h)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(MARGIN_IN))

    # Setup default typographic styles
    normal = doc.styles["Normal"]
    _set_style_font(normal, BODY_PT)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0

    title = doc.styles["Title"]
    _set_style_font(title, NAME_PT, bold=True)
    _remove_border(title)
    title.paragraph_format.space_after = Pt(2)
    title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    h1 = doc.styles["Heading 1"]
    _set_style_font(h1, HEADING_PT, bold=True)
    h1.paragraph_format.space_before = Pt(7)
    h1.paragraph_format.space_after = Pt(3)
    h1.paragraph_format.keep_with_next = True

    lb = doc.styles["List Bullet"]
    _set_style_font(lb, BODY_PT)
    lb.paragraph_format.space_after = Pt(1)
    _round_bullets(doc)

    doc.core_properties.author = author
    doc.core_properties.title = f"{author} - Resume"

    # Line-by-line parsing
    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        if not line:
            idx += 1
            continue

        if line.startswith("# ") and not line.startswith("## "):
            title_text = line[2:].strip()
            doc.add_paragraph(title_text, style="Title")
        elif line.startswith("## ") and not line.startswith("### "):
            heading_text = line[3:].strip()
            p = doc.add_paragraph(heading_text, style="Heading 1")
            _bottom_border(p)
        elif line.startswith("### "):
            sub_text = line[4:].strip()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.keep_with_next = True
            if " | " in sub_text:
                parts = sub_text.split(" | ", 1)
                p.add_run(parts[0]).bold = True
                _add_formatted_runs(p, f" | {parts[1]}")
            elif " — " in sub_text:
                parts = sub_text.split(" — ", 1)
                p.add_run(parts[0]).bold = True
                _add_formatted_runs(p, f" — {parts[1]}")
            elif " · " in sub_text:
                parts = sub_text.split(" · ", 1)
                p.add_run(parts[0]).bold = True
                _add_formatted_runs(p, f" · {parts[1]}")
            else:
                _add_formatted_runs(p, sub_text)
        elif line.startswith(("-", "*", "•")) and not (
            line.startswith("**") or (line.startswith("*") and not line.startswith("* "))
        ):
            bullet_text = line.lstrip("-*•").strip()
            p = doc.add_paragraph(style="List Bullet")
            # Strip single trailing period if present, keeping acronyms safe
            clean_text = (
                bullet_text.rstrip().rstrip(".")
                if not bullet_text.rstrip().endswith("..")
                else bullet_text
            )
            _add_formatted_runs(p, clean_text)
        elif line.startswith("*") and line.endswith("*") and len(line) > 2 and not line.startswith("**"):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(line[1:-1].strip())
            r.italic = True
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            _add_formatted_runs(p, line)
        idx += 1

    doc.save(out_path)
    return out_path


def compile_markdown_to_artifacts(
    md_text: str,
    docx_path: str | Path,
    pdf_path: Optional[str | Path] = None,
    paper_size: str = "Letter",
) -> Tuple[Path, Optional[Path]]:
    """Generates DOCX and corresponding PDF from Markdown."""
    out_docx = markdown_to_docx(md_text, docx_path, paper_size=paper_size)
    out_pdf = Path(pdf_path) if pdf_path else out_docx.with_suffix(".pdf")
    try:
        produced_pdf = docx_to_pdf(out_docx, out_pdf)
        return out_docx, produced_pdf
    except Exception:
        return out_docx, None
