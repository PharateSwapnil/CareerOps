"""Typed data model for a structured resume.

The markdown-lite content format used for simple export (services/resume_export.py)
is kept for the basic case. This richer model is used when rendering with
the Swapnil template (services/resume_templates.py), which requires
structured data - not just flat text - to correctly place each section in
the right visual position.

Resume.content stores the data as JSON when using structured templates
(prefix: "__structured__\n"), or raw markdown text for the basic renderer.
The export endpoint detects which format is stored and routes accordingly.
"""
from dataclasses import dataclass, field


@dataclass
class ContactInfo:
    name: str
    title: str          # subtitle line e.g. "SENIOR DATA ENGINEER · AI ENGINEER"
    phone: str = ""
    email: str = ""
    linkedin: str = ""
    location: str = ""


@dataclass
class SkillRow:
    category: str
    items: str          # comma-separated or free text


@dataclass
class BulletPoint:
    text: str


@dataclass
class Project:
    name: str           # e.g. "Project 1 — ALF (Advanced Load Forecasting)"
    tech_stack: str     # italic subtitle line
    bullets: list[BulletPoint] = field(default_factory=list)


@dataclass
class Experience:
    company: str
    location: str
    role: str           # rendered in blue italic
    date_range: str
    bullets: list[BulletPoint] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)


@dataclass
class EducationEntry:
    degree: str
    institution: str
    date_range: str


@dataclass
class StructuredResume:
    contact: ContactInfo
    summary: str
    skills: list[SkillRow] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    education: list[EducationEntry] = field(default_factory=list)
