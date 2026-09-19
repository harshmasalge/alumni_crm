"""Identity-provider adapter — the auth seam.

Sign-in is the only step that differs between environments:

- **Production:** Sign in with Google. The Google ID token is verified
  (signature, audience, expiry) and the verified email is checked against
  the local users table. No passwords are stored or accepted.
- **Dev/staging:** password check against the local users table, so the
  product works today with zero external dependencies. This provider
  refuses to run when `environment == "production"`.

Everything downstream — session JWTs, RBAC, field-level permissions, audit —
is provider-agnostic and unchanged by the swap.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User


class IdentityVerificationError(Exception):
    def __init__(self, detail: str, status_code: int = 401):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class IdentityClaims:
    email: str
    full_name: Optional[str]
    provider: str
    provider_subject: Optional[str] = None


class IdentityProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def authenticate(self, db: AsyncSession, **kwargs) -> User:
        """Verify credentials and return the authorized local user.

        Raises IdentityVerificationError (401 unknown/invalid, 403 known but
        not authorized, 503 provider not configured).
        """


async def _find_active_user(db: AsyncSession, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    user = result.scalars().first()
    if not user:
        raise IdentityVerificationError(
            "This email is not authorized for the CRM. Ask an administrator for access.",
            status_code=403,
        )
    if not user.is_active:
        raise IdentityVerificationError("Inactive user.", status_code=403)
    return user


class PasswordIdentityProvider(IdentityProvider):
    """Dev/staging-only credential check. Never enabled in production."""

    name = "password"

    async def authenticate(
        self, db: AsyncSession, email: str = "", password: str = ""
    ) -> User:
        from app.core.security import verify_password

        if settings.environment == "production":
            raise IdentityVerificationError(
                "Password sign-in is disabled in production; use Sign in with Google.",
                status_code=403,
            )
        result = await db.execute(select(User).where(User.email == email.strip().lower()))
        user = result.scalars().first()
        if not user or not verify_password(password, user.hashed_password):
            raise IdentityVerificationError("Incorrect email or password.")
        if not user.is_active:
            raise IdentityVerificationError("Inactive user.", status_code=403)
        return user


class GoogleIdentityProvider(IdentityProvider):
    """Production provider: Sign in with Google.

    Verifies the Google ID token, then authorizes by email allowlist — the
    user row must already exist in the local users table. IITGN staff are
    never auto-provisioned.
    """

    name = "google"

    async def authenticate(self, db: AsyncSession, id_token: str = "") -> User:
        if not settings.google_client_id:
            raise IdentityVerificationError(
                "Google sign-in is not configured (GOOGLE_CLIENT_ID missing).",
                status_code=503,
            )
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token
        except ImportError as exc:
            raise IdentityVerificationError(
                "Google sign-in is unavailable (google-auth not installed).",
                status_code=503,
            ) from exc

        try:
            claims = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), settings.google_client_id
            )
        except Exception:
            raise IdentityVerificationError("Invalid Google credential.") from None

        if not claims.get("email_verified"):
            raise IdentityVerificationError("Google email is not verified.")
        email = (claims.get("email") or "").strip().lower()
        if not email:
            raise IdentityVerificationError("Google credential has no email.")
        return await _find_active_user(db, email)


def get_identity_provider() -> IdentityProvider:
    if settings.identity_provider == "google":
        return GoogleIdentityProvider()
    return PasswordIdentityProvider()
