"""SQLite engine + session factory. Local-first: creates ./data/ automatically."""
import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

# Ensure the local data directory exists for the default SQLite path.
if settings.database_url.startswith("sqlite:///./"):
    db_dir = os.path.dirname(settings.database_url.replace("sqlite:///./", ""))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=settings.debug, connect_args=connect_args)


def init_db() -> None:
    """Create all tables. Called on app startup.

    NOTE: this is a simple create_all for now. A migration tool (Alembic) should
    be introduced before the schema needs to evolve in production.
    """
    # Import models so they're registered on SQLModel.metadata before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
