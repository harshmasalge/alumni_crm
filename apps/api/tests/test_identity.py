"""Tests for the identity-provider seam (ADR-003).

Unit tests below need no database: provider selection, the production
refusal of password sign-in, and the unconfigured-Google 503 all happen
before any DB access. Live Google verification is covered in the
integration suite with a stubbed verifier.
"""

import httpx
import pytest

from app.core.config import settings
from app.core.identity import (
    GoogleIdentityProvider,
    IdentityVerificationError,
    PasswordIdentityProvider,
    get_identity_provider,
)
from app.main import app


def test_factory_defaults_to_dev_password_provider(monkeypatch):
    monkeypatch.setattr(settings, "identity_provider", "password")
    assert isinstance(get_identity_provider(), PasswordIdentityProvider)


def test_factory_selects_google(monkeypatch):
    monkeypatch.setattr(settings, "identity_provider", "google")
    assert isinstance(get_identity_provider(), GoogleIdentityProvider)


async def test_password_provider_refused_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(IdentityVerificationError) as exc:
        await PasswordIdentityProvider().authenticate(db=None, email="a@b.c", password="x")
    assert exc.value.status_code == 403


async def test_google_provider_requires_client_id(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    with pytest.raises(IdentityVerificationError) as exc:
        await GoogleIdentityProvider().authenticate(db=None, id_token="anything")
    assert exc.value.status_code == 503


async def test_google_endpoint_503_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        r = await client.post("/auth/google", json={"id_token": "stub"})
        assert r.status_code == 503
