"""Tests for link formatting in Markdown, DOCX, and PDF rendering."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from resume_builder.ats_check import extract_docx_lines, extract_pdf_text
from resume_builder.models import (
    Basics,
    Link,
    Resume,
    ResumeBullet,
    ResumeExperience,
    ResumeProject,
)
from resume_builder.render import docx_to_pdf, render_docx, resume_to_markdown
from resume_builder.render.pdf import find_soffice
from resume_builder.textutil import clean_display_url, normalize_url


def test_url_helpers():
    # normalize_url
    assert normalize_url("") == ""
    assert normalize_url("   ") == ""
    assert normalize_url("linkedin.com/in/johndoe") == "https://linkedin.com/in/johndoe"
    assert normalize_url("https://linkedin.com/in/johndoe") == "https://linkedin.com/in/johndoe"
    assert normalize_url("http://example.com") == "http://example.com"
    assert normalize_url("mailto:test@example.com") == "mailto:test@example.com"

    # clean_display_url
    assert clean_display_url("") == ""
    assert clean_display_url("https://linkedin.com/in/johndoe/") == "linkedin.com/in/johndoe"
    assert clean_display_url("http://www.github.com/johndoe") == "github.com/johndoe"
    assert clean_display_url("johndoe.vercel.app") == "johndoe.vercel.app"
    assert clean_display_url("https://github.com/user/myproject/") == "github.com/user/myproject"


def _sample_resume() -> Resume:
    return Resume(
        basics=Basics(
            name="Alex Morgan",
            email="alex@example.com",
            phone="+1-555-0199",
            location="Seattle, WA",
            links=[
                Link(label="LinkedIn", url="linkedin.com/in/alexmorgan"),
                Link(label="GitHub", url="https://github.com/alexmorgan"),
                Link(label="Portfolio", url="alexmorgan.dev"),
            ],
        ),
        projects=[
            ResumeProject(
                id="proj-1",
                name="CloudSync",
                url="github.com/alexmorgan/cloudsync",
                bullets=[ResumeBullet(source_id="b1", text="High-throughput distributed cache sync")],
            ),
            ResumeProject(
                id="proj-2",
                name="InternalTool",
                url="",
                bullets=[ResumeBullet(source_id="b2", text="Internal command-line utility")],
            ),
        ],
    )


def test_resume_to_markdown_renders_real_links_not_placeholders():
    r = _sample_resume()
    md = resume_to_markdown(r)

    # Profile section has clean display links with hrefs
    assert "[linkedin.com/in/alexmorgan](https://linkedin.com/in/alexmorgan)" in md
    assert "[github.com/alexmorgan](https://github.com/alexmorgan)" in md
    assert "[alexmorgan.dev](https://alexmorgan.dev)" in md

    # Profile section does NOT have plain labels as link text
    assert "[LinkedIn](" not in md
    assert "[GitHub](" not in md
    assert "[Portfolio](" not in md

    # Project section has real link, not placeholder
    assert "### CloudSync — [github.com/alexmorgan/cloudsync](https://github.com/alexmorgan/cloudsync)" in md
    assert "[Project Link]" not in md

    # Project without URL has only name
    assert "### InternalTool\n" in md


def test_docx_renders_clean_links(tmp_path):
    r = _sample_resume()
    docx_path = tmp_path / "resume.docx"
    render_docx(r, docx_path)

    lines = extract_docx_lines(docx_path)
    assert lines[0] == "Alex Morgan"
    # Contact line contains the real clean display URLs
    assert "alex@example.com" in lines[1]
    assert "linkedin.com/in/alexmorgan" in lines[1]
    assert "github.com/alexmorgan" in lines[1]
    assert "alexmorgan.dev" in lines[1]

    # Projects contain the clean display URL and no "Project Link" placeholder
    assert any("CloudSync" in l and "github.com/alexmorgan/cloudsync" in l for l in lines)
    assert not any("Project Link" in l for l in lines)


def test_markdown_to_docx_preserves_clean_links(tmp_path):
    from backend.app.resume.markdown_renderer import markdown_to_docx

    r = _sample_resume()
    md = resume_to_markdown(r)
    docx_path = tmp_path / "md_resume.docx"
    markdown_to_docx(md, docx_path)

    lines = extract_docx_lines(docx_path)
    assert lines[0] == "Alex Morgan"
    assert "alex@example.com" in lines[1]
    assert "linkedin.com/in/alexmorgan" in lines[1]
    assert "github.com/alexmorgan" in lines[1]
    assert any("CloudSync" in l and "github.com/alexmorgan/cloudsync" in l for l in lines)


@pytest.mark.skipif(find_soffice() is None, reason="LibreOffice not installed")
def test_pdf_extracts_clean_links(tmp_path):
    r = _sample_resume()
    docx_path = tmp_path / "resume.docx"
    pdf_path = tmp_path / "resume.pdf"
    render_docx(r, docx_path)
    docx_to_pdf(docx_path, pdf_path)

    pdf_text = extract_pdf_text(pdf_path)
    assert "alex@example.com" in pdf_text
    assert "linkedin.com/in/alexmorgan" in pdf_text
    assert "github.com/alexmorgan" in pdf_text
    assert "github.com/alexmorgan/cloudsync" in pdf_text
    assert "Project Link" not in pdf_text
