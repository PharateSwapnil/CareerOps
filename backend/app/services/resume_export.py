"""Renders a Resume's stored content into a real PDF document.

Two rendering paths:
1. Structured template (preferred): if Resume.content starts with
   "__structured__\n", the rest is JSON matching StructuredResume's schema.
   Renders using services/resume_templates.py — which replicates the exact
   visual layout of Swapnil Pharate's resume (blue accent, Skills table,
   company+date side-by-side, blue italic role, project subheadings, etc.)
2. Markdown-lite fallback: everything else is rendered with the original
   simple line-based parser (headings, bullets, bold/italic inline styles).
   Functional but plain — no designed template.

The API endpoint (GET /resumes/{id}/export.pdf) detects which path to use
automatically from the content prefix, so both formats continue to work.
"""
import io
import json
import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

STRUCTURED_PREFIX = "__structured__\n"

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")


def _inline_markup(text: str) -> str:
    escaped = escape(text)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC_RE.sub(r"<i>\1</i>", escaped)
    return escaped


def _render_markdown_fallback(title: str, content: str) -> bytes:
    """Original plain renderer - used when no template is selected."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch, title=title)

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle("ResumeBody", parent=styles["Normal"],
        fontSize=10.5, leading=14, spaceAfter=6)
    h1_style = ParagraphStyle("ResumeH1", parent=styles["Heading1"],
        fontSize=16, spaceBefore=4, spaceAfter=8)
    h2_style = ParagraphStyle("ResumeH2", parent=styles["Heading2"],
        fontSize=12.5, spaceBefore=10, spaceAfter=6)

    story = []
    story.append(Paragraph(_inline_markup(title), h1_style))
    story.append(Spacer(1, 4))

    bullet_buffer: list[str] = []

    def flush_bullets():
        if bullet_buffer:
            items = [ListItem(Paragraph(_inline_markup(b), body_style))
                     for b in bullet_buffer]
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=16))
            bullet_buffer.clear()

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            flush_bullets(); continue
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


def render_resume_pdf(title: str, content: str) -> bytes:
    """Main entry point - detects format and routes to the right renderer."""
    if content.startswith(STRUCTURED_PREFIX):
        from app.services.resume_data_model import StructuredResume
        from app.services.resume_templates import render_resume_from_structured
        import dataclasses

        raw_json = content[len(STRUCTURED_PREFIX):]
        data = json.loads(raw_json)

        # Reconstruct dataclasses from the plain JSON dict
        from app.services.resume_data_model import (
            ContactInfo, SkillRow, Experience, Project, BulletPoint, EducationEntry
        )

        contact = ContactInfo(**data["contact"])
        skills = [SkillRow(**s) for s in data.get("skills", [])]
        experience = []
        for exp_data in data.get("experience", []):
            projects = [
                Project(
                    name=p["name"],
                    tech_stack=p.get("tech_stack", ""),
                    bullets=[BulletPoint(b["text"]) for b in p.get("bullets", [])],
                )
                for p in exp_data.get("projects", [])
            ]
            experience.append(Experience(
                company=exp_data["company"],
                location=exp_data.get("location", ""),
                role=exp_data["role"],
                date_range=exp_data["date_range"],
                bullets=[BulletPoint(b["text"]) for b in exp_data.get("bullets", [])],
                projects=projects,
            ))
        education = [EducationEntry(**e) for e in data.get("education", [])]
        certifications = data.get("certifications", [])

        resume = StructuredResume(
            contact=contact,
            summary=data["summary"],
            skills=skills,
            experience=experience,
            certifications=certifications,
            education=education,
        )
        return render_resume_from_structured(resume)

    return _render_markdown_fallback(title, content)

