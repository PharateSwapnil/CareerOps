from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    issue_tokens,
    refresh_access_token,
    register_user,
    revoke_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        user = register_user(session, payload.full_name, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    access_token, refresh_token = issue_tokens(session, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        user = authenticate_user(session, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    access_token, refresh_token = issue_tokens(session, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> AccessTokenResponse:
    try:
        access_token = refresh_access_token(session, payload.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", status_code=204)
async def logout(payload: LogoutRequest, session: Session = Depends(get_session)) -> None:
    revoke_refresh_token(session, payload.refresh_token)
