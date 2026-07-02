import pytest
from pypdf import PdfReader
import io

from app.services.resume_export import render_resume_pdf


def test_render_resume_pdf_produces_valid_pdf_bytes():
    pdf_bytes = render_resume_pdf("Jane Doe", "Senior Backend Engineer\n\nBuilt scalable APIs.")

    assert pdf_bytes[:4] == b"%PDF"

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_render_resume_pdf_includes_title_and_content_text():
    content = "## Experience\n\n- Led a team of 5 engineers\n- Shipped the payments platform"
    pdf_bytes = render_resume_pdf("Jane Doe Resume", content)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "".join(page.extract_text() for page in reader.pages)

    assert "Jane Doe Resume" in extracted
    assert "Experience" in extracted
    assert "Led a team of 5 engineers" in extracted


def test_render_resume_pdf_escapes_special_characters_safely():
    """Content containing < > & (e.g. 'built APIs handling <1000 req/s &
    scaled to 5M users') must not break reportlab's XML-based Paragraph
    parser or leak as literal markup."""
    content = "Built systems handling <1000ms latency & 99.9% uptime"
    pdf_bytes = render_resume_pdf("Test Resume", content)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "".join(page.extract_text() for page in reader.pages)

    assert "1000ms latency" in extracted
    assert "99.9% uptime" in extracted


def test_render_resume_pdf_handles_bold_and_italic_markdown():
    content = "**Senior Engineer** with *5 years* of experience"
    pdf_bytes = render_resume_pdf("Test Resume", content)

    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "".join(page.extract_text() for page in reader.pages)

    # The markup tags themselves shouldn't leak into extracted text, but
    # the underlying words should still be present and readable.
    assert "Senior Engineer" in extracted
    assert "5 years" in extracted
    assert "<b>" not in extracted
    assert "**" not in extracted


def test_render_resume_pdf_handles_empty_content():
    pdf_bytes = render_resume_pdf("Empty Resume", "")
    assert pdf_bytes[:4] == b"%PDF"

    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
