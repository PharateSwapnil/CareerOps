import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import get_session
from app.models.saved_search import SavedSearch
from app.providers.embedding_providers.registry import get_provider as get_embedding_provider
from app.schemas.embedding import SavedSearchCreate, SavedSearchRead, SemanticSearchResult
from app.services.default_user import get_or_create_default_user
from app.services.embeddings import match_saved_search

router = APIRouter(prefix="/saved-searches", tags=["saved-searches"])


def _get_or_404(session: Session, saved_search_id: int) -> SavedSearch:
    saved_search = session.get(SavedSearch, saved_search_id)
    if saved_search is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return saved_search


@router.get("", response_model=list[SavedSearchRead])
async def list_saved_searches(session: Session = Depends(get_session)) -> list[SavedSearch]:
    user = get_or_create_default_user(session)
    return session.exec(select(SavedSearch).where(SavedSearch.user_id == user.id)).all()


@router.post("", response_model=SavedSearchRead, status_code=201)
async def create_saved_search(
    payload: SavedSearchCreate, session: Session = Depends(get_session)
) -> SavedSearch:
    """Embeds `query_text` once and stores it, so future matching doesn't
    need to re-embed on every read."""
    user = get_or_create_default_user(session)
    settings = get_settings()
    provider_name = payload.provider_name or settings.embedding_default_provider
    provider = get_embedding_provider(provider_name)

    vectors = await provider.embed([payload.query_text], input_type="query")

    saved_search = SavedSearch(
        user_id=user.id,
        name=payload.name,
        query_text=payload.query_text,
        embedding_provider=provider.name,
        embedding_model=provider.model,
        embedding_dimension=provider.dimension,
        embedding_vector=json.dumps(vectors[0]),
    )
    session.add(saved_search)
    session.commit()
    session.refresh(saved_search)
    return saved_search


@router.get("/{saved_search_id}/matches", response_model=list[SemanticSearchResult])
async def get_matches(
    saved_search_id: int, limit: int = 20, session: Session = Depends(get_session)
) -> list[SemanticSearchResult]:
    saved_search = _get_or_404(session, saved_search_id)
    vector = json.loads(saved_search.embedding_vector)

    results = match_saved_search(session, vector, saved_search.embedding_provider, limit)
    return [SemanticSearchResult(job=job, score=score) for job, score in results]


@router.delete("/{saved_search_id}", status_code=204)
async def delete_saved_search(
    saved_search_id: int, session: Session = Depends(get_session)
) -> None:
    saved_search = _get_or_404(session, saved_search_id)
    session.delete(saved_search)
    session.commit()
