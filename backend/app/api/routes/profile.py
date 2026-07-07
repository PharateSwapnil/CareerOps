import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.user import UserProfileRead, UserProfileUpdate

router = APIRouter(prefix="/me", tags=["profile"])


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc


@router.get("", response_model=UserProfileRead)
async def get_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("", response_model=UserProfileRead)
async def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    current_user.updated_at = datetime.now(timezone.utc)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.post("/upload-resume", response_model=UserProfileRead)
async def upload_resume_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    """Accepts a PDF resume upload, extracts its text, and stores it on the
    user record. This text is used to:
      - Extract skills for smart job matching on the Jobs page
      - Pre-fill the resume field during browser-assisted autofill
      - Give the AI context for cover letters and resume optimisation
    Only PDF is accepted; other formats return 422."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB hard limit
        raise HTTPException(status_code=413, detail="Resume PDF must be under 10MB")

    try:
        text = _extract_text_from_pdf(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this PDF — it may be a scanned image. "
                   "Try exporting your resume as a text-based PDF instead."
        )

    current_user.base_resume_text = text
    current_user.updated_at = datetime.now(timezone.utc)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.get("/skills")
async def get_extracted_skills(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Returns skills extracted from the user's uploaded resume text.
    Used by the Jobs page smart-filter to score jobs against your skill set.
    Returns a list of lowercased skill tokens so the frontend can do
    client-side fuzzy matching without an extra round-trip."""
    if not current_user.base_resume_text:
        return {"skills": [], "has_resume": False}

    skills = _extract_skills(current_user.base_resume_text)
    return {"skills": skills, "has_resume": True}


# ── Skill extraction ────────────────────────────────────────────────────────

_SKILL_VOCAB = [
    # Languages
    "python", "sql", "java", "javascript", "typescript", "go", "golang",
    "rust", "scala", "r", "bash", "shell", "c++", "c#", "kotlin", "swift",
    # Data / ML
    "pyspark", "spark", "kafka", "airflow", "dbt", "pandas", "numpy",
    "scikit-learn", "tensorflow", "pytorch", "mlflow", "databricks",
    "snowflake", "redshift", "bigquery", "athena", "hive", "presto",
    "delta lake", "iceberg", "parquet", "avro",
    # Cloud / infra
    "aws", "gcp", "azure", "s3", "lambda", "emr", "glue", "step functions",
    "eventbridge", "cloudwatch", "dynamodb", "rds", "ec2", "ecs", "eks",
    "kubernetes", "docker", "terraform", "ansible", "jenkins", "github actions",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
    "sqlite", "sqlalchemy", "dbeaver",
    # Frameworks / tools
    "fastapi", "django", "flask", "spring", "react", "node.js",
    "git", "github", "bitbucket", "jira", "confluence",
    # GenAI
    "llm", "rag", "langchain", "bedrock", "openai", "gemini", "claude",
    "prompt engineering", "agentic", "vector database", "embeddings",
    # Methodologies
    "etl", "elt", "data warehouse", "data lake", "data mesh", "data modeling",
    "star schema", "snowflake schema", "scd", "ci/cd", "agile", "scrum",
]


def _extract_skills(resume_text: str) -> list[str]:
    """Simple keyword matching against the skill vocabulary. Returns
    deduplicated lowercase tokens that appear in the resume text."""
    lowered = resume_text.lower()
    found = []
    for skill in _SKILL_VOCAB:
        if skill in lowered:
            found.append(skill)
    return found
