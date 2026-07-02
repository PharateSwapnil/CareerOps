"""Renders a Resume's stored plain-text/markdown-lite content into a real
PDF document, using reportlab (see /mnt/skills/public/pdf/SKILL.md).

This closes a real gap flagged in Milestone 8: browser-assisted application
autofill was writing raw resume text to a `.txt` file for upload, which
most ATS resume-upload fields reject outright (they expect PDF/DOC/DOCX).
`profile_builder.py` now calls into this module instead.

Parsing is intentionally simple - a line-based markdown-lite reader, not a
full CommonMark implementation:
  - "# Heading" / "## Heading"  -> Heading1 / Heading2 styles
  - "- item" / "* item"          -> bullet list item
  - "**bold**" / "*italic*"      -> inline bold/italic
  - blank line                    -> paragraph break
  - anything else                 -> a normal paragraph

This handles typical AI-generated resume content (see
services/ai_prompts.py's resume-optimize prompt) reasonably well, but it is
NOT a resume template/design system - output is plain, single-column, and
readable, not styled. A real "resume builder" with proper templates is a
separate, larger feature than this fix is trying to be.
"""
import io
import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")


def _inline_markup(text: str) -> str:
    """Escapes XML-special characters, then re-applies a small set of
    markdown inline styles as reportlab's Paragraph XML tags. Order
    matters: escape first so literal < > & in the resume text don't get
    misinterpreted as markup, then layer bold/italic on top."""
    escaped = escape(text)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC_RE.sub(r"<i>\1</i>", escaped)
    return escaped


def render_resume_pdf(title: str, content: str) -> bytes:
    """Renders `content` (the Resume.content markdown-lite text) into a PDF
    and returns the raw PDF bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title=title,
    )

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "ResumeBody", parent=styles["Normal"], fontSize=10.5, leading=14, spaceAfter=6
    )
    h1_style = ParagraphStyle(
        "ResumeH1", parent=styles["Heading1"], fontSize=16, spaceBefore=4, spaceAfter=8
    )
    h2_style = ParagraphStyle(
        "ResumeH2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=6
    )

    story = []
    story.append(Paragraph(_inline_markup(title), h1_style))
    story.append(Spacer(1, 4))

    bullet_buffer: list[str] = []

    def flush_bullets():
        if bullet_buffer:
            items = [
                ListItem(Paragraph(_inline_markup(b), body_style)) for b in bullet_buffer
            ]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=16))
            bullet_buffer.clear()

    for raw_line in content.splitlines():
        line = raw_line.strip()

        if not line:
            flush_bullets()
            continue

        if line.startswith("## "):
            flush_bullets()
            story.append(Paragraph(_inline_markup(line[3:]), h2_style))
        elif line.startswith("# "):
            flush_bullets()
            story.append(Paragraph(_inline_markup(line[2:]), h1_style))
        elif line.startswith("- ") or line.startswith("* "):
            bullet_buffer.append(line[2:])
        else:
            flush_bullets()
            story.append(Paragraph(_inline_markup(line), body_style))

    flush_bullets()

    doc.build(story)
    return buffer.getvalue()
