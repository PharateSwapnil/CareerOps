"""Renders a StructuredResume into a PDF that precisely replicates the
visual layout of Swapnil Pharate's resume.

Layout details observed from the original:
  - Name: center, 22pt bold
  - Title subtitle: center, 10pt, blue #1F4E8B
  - Contact line: center, 8.5pt, gray, pipe-separated
  - Full-width gray rule under header
  - Section headings: 9pt bold, ALL CAPS, with full-width blue rule below
  - Technical Skills: bold label (1.65in col), plain value
  - Experience: company left + date right on same line, role in blue italic below
  - Project sub-sections: bold heading, italic gray tech-stack line, bullets
  - Bullets: dot prefix, left-indented, justified
  - Education: bold degree left + date right, italic institution below
  - Page margins: 0.55in all sides (A4)
"""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.resume_data_model import StructuredResume

BLUE  = colors.HexColor("#1F4E8B")
GRAY  = colors.HexColor("#555555")
BLACK = colors.HexColor("#1A1A1A")

_NAME = ParagraphStyle("Name", fontName="Helvetica-Bold", fontSize=22,
    leading=26, alignment=1, textColor=BLACK, spaceAfter=2)
_TITLE = ParagraphStyle("Title", fontName="Helvetica", fontSize=10,
    leading=14, alignment=1, textColor=BLUE, spaceAfter=2)
_CONTACT = ParagraphStyle("Contact", fontName="Helvetica", fontSize=8.5,
    leading=12, alignment=1, textColor=GRAY, spaceAfter=6)
_SECTION_HEADING = ParagraphStyle("SH", fontName="Helvetica-Bold", fontSize=9,
    leading=12, textColor=BLACK, spaceBefore=10, spaceAfter=1)
_BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=9, leading=13,
    textColor=BLACK, alignment=4)
_COMPANY = ParagraphStyle("Company", fontName="Helvetica-Bold", fontSize=10,
    leading=14, textColor=BLACK)
_ROLE = ParagraphStyle("Role", fontName="Helvetica-Oblique", fontSize=9,
    leading=12, textColor=BLUE, spaceAfter=3)
_PROJECT_HEADING = ParagraphStyle("PH", fontName="Helvetica-Bold", fontSize=9,
    leading=13, textColor=BLACK, spaceBefore=6)
_TECH_STACK = ParagraphStyle("TS", fontName="Helvetica-Oblique", fontSize=8.5,
    leading=12, textColor=GRAY, spaceAfter=2)
_BULLET = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=9, leading=13,
    textColor=BLACK, alignment=4, leftIndent=12, spaceAfter=2)
_SKILL_LABEL = ParagraphStyle("SL", fontName="Helvetica-Bold", fontSize=9, leading=13)
_SKILL_VALUE = ParagraphStyle("SV", fontName="Helvetica", fontSize=9, leading=13)
_EDU_DEGREE = ParagraphStyle("EduD", fontName="Helvetica-Bold", fontSize=9, leading=13)
_EDU_INST   = ParagraphStyle("EduI", fontName="Helvetica", fontSize=8.5, leading=12,
    textColor=GRAY, spaceAfter=4)
_DATE = ParagraphStyle("Date", fontName="Helvetica-Oblique", fontSize=9,
    leading=13, textColor=GRAY, alignment=2)


def _e(t):
    return escape(str(t))

def _hr(story, color=BLUE, thickness=0.75):
    story.append(HRFlowable(width="100%", thickness=thickness, color=color, spaceAfter=4, spaceBefore=0))

def _section(story, title):
    story.append(Paragraph(_e(title), _SECTION_HEADING))
    _hr(story)

def _bullet(story, text):
    story.append(Paragraph(f"• {_e(text)}", _BULLET))

def _side_by_side(story, left_para, right_para, right_w=1.5*inch):
    t = Table([[left_para, right_para]], colWidths=["*", right_w])
    t.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1),"BOTTOM"),
        ("LEFTPADDING",  (0,0),(-1,-1),0),
        ("RIGHTPADDING", (0,0),(-1,-1),0),
        ("TOPPADDING",   (0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    story.append(t)


def render_resume_from_structured(resume: StructuredResume) -> bytes:
    buffer = io.BytesIO()
    m = 0.55 * inch
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        topMargin=m, bottomMargin=m, leftMargin=m, rightMargin=m,
        title=resume.contact.name)
    story = []

    # Header
    story.append(Paragraph(_e(resume.contact.name), _NAME))
    story.append(Paragraph(_e(resume.contact.title), _TITLE))
    parts = [p for p in [resume.contact.phone, resume.contact.email,
                          resume.contact.linkedin, resume.contact.location] if p]
    story.append(Paragraph(" | ".join(_e(p) for p in parts), _CONTACT))
    _hr(story, color=GRAY, thickness=0.5)

    # Summary
    _section(story, "PROFESSIONAL SUMMARY")
    story.append(Spacer(1, 2))
    story.append(Paragraph(_e(resume.summary), _BODY))

    # Technical Skills
    if resume.skills:
        _section(story, "TECHNICAL SKILLS")
        story.append(Spacer(1, 2))
        for row in resume.skills:
            data = [[Paragraph(_e(row.category), _SKILL_LABEL),
                     Paragraph(_e(row.items),    _SKILL_VALUE)]]
            t = Table(data, colWidths=[1.65*inch, "*"])
            t.setStyle(TableStyle([
                ("VALIGN",  (0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",  (0,0),(-1,-1),0),
                ("RIGHTPADDING", (0,0),(-1,-1),4),
                ("TOPPADDING",   (0,0),(-1,-1),1),
                ("BOTTOMPADDING",(0,0),(-1,-1),1),
            ]))
            story.append(t)

    # Professional Experience
    if resume.experience:
        _section(story, "PROFESSIONAL EXPERIENCE")
        story.append(Spacer(1, 2))
        for exp in resume.experience:
            label = f"{_e(exp.company)}{', ' + _e(exp.location) if exp.location else ''}"
            _side_by_side(story, Paragraph(label, _COMPANY),
                          Paragraph(_e(exp.date_range), _DATE))
            story.append(Paragraph(_e(exp.role), _ROLE))
            for b in exp.bullets:
                _bullet(story, b.text)
            for proj in exp.projects:
                story.append(Paragraph(_e(proj.name), _PROJECT_HEADING))
                if proj.tech_stack:
                    story.append(Paragraph(_e(proj.tech_stack), _TECH_STACK))
                for b in proj.bullets:
                    _bullet(story, b.text)
            story.append(Spacer(1, 4))

    # Certifications
    if resume.certifications:
        _section(story, "CERTIFICATIONS")
        story.append(Spacer(1, 2))
        for cert in resume.certifications:
            _bullet(story, cert)

    # Education
    if resume.education:
        _section(story, "EDUCATION")
        story.append(Spacer(1, 2))
        for edu in resume.education:
            _side_by_side(story, Paragraph(_e(edu.degree), _EDU_DEGREE),
                          Paragraph(_e(edu.date_range), _DATE))
            story.append(Paragraph(_e(edu.institution), _EDU_INST))

    doc.build(story)
    return buffer.getvalue()
