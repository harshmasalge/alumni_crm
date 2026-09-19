from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    get_current_user,
    get_user_permissions,
    get_user_roles,
)
from app.core.config import settings
from app.core.identity import (
    GoogleIdentityProvider,
    IdentityVerificationError,
    PasswordIdentityProvider,
)
from app.core.security import create_access_token
from app.db.session import get_db
from app.models import User

router = APIRouter(tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class GoogleLoginRequest(BaseModel):
    id_token: str


class UserInfo(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_superuser: bool
    roles: list[str]
    permissions: list[str]


async def _mint_session_token(db: AsyncSession, user: User) -> TokenResponse:
    """Mint the short-lived session token. Provider-agnostic: identical for
    password (dev) and Google (production) sign-in."""
    roles = await get_user_roles(db, user.id)
    permissions = await get_user_permissions(db, user.id)

    access_token = create_access_token(
        subject=user.id,
        roles=roles,
        permissions=permissions,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _identity_error(exc: IdentityVerificationError) -> HTTPException:
    headers = (
        {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    )
    return HTTPException(status_code=exc.status_code, detail=exc.detail, headers=headers)


@router.post(
    "/login",
    response_model=TokenResponse,
    description="Dev/staging-only password sign-in. Disabled in production; use /auth/google.",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user = await PasswordIdentityProvider().authenticate(
            db, email=form_data.username, password=form_data.password
        )
    except IdentityVerificationError as exc:
        raise _identity_error(exc) from None
    return await _mint_session_token(db, user)


@router.post("/google", response_model=TokenResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Production sign-in: verify the Google ID token, authorize the verified
    email against the local users table, and mint a session token.

    Returns 503 until GOOGLE_CLIENT_ID is configured (IITGN action required).
    """
    try:
        user = await GoogleIdentityProvider().authenticate(db, id_token=payload.id_token)
    except IdentityVerificationError as exc:
        raise _identity_error(exc) from None
    return await _mint_session_token(db, user)


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserInfo:
    roles = await get_user_roles(db, current_user.id)
    permissions = await get_user_permissions(db, current_user.id)

    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_superuser=current_user.is_superuser,
        roles=roles,
        permissions=permissions,
    )
