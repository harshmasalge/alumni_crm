"""Unit tests for the demo bootstrap — all run without a database."""

import asyncio

import pytest
from faker import Faker

from app.core.config import settings
from app.db import demo_bootstrap as bootstrap
from app.db.access_catalog import DEMO_USERS, PERMISSIONS, ROLE_PERMS, ROLES


def test_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "demo_seed", False)
    assert asyncio.run(bootstrap.run_demo_bootstrap()) is None


def test_refuses_production(monkeypatch):
    monkeypatch.setattr(settings, "demo_seed", True)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "demo_password", "whatever")
    with pytest.raises(RuntimeError, match="production"):
        asyncio.run(bootstrap.run_demo_bootstrap())


def test_requires_password(monkeypatch):
    monkeypatch.setattr(settings, "demo_seed", True)
    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "demo_password", "")
    with pytest.raises(RuntimeError, match="DEMO_PASSWORD"):
        asyncio.run(bootstrap.run_demo_bootstrap())


def test_stale_plan_spread():
    assert bootstrap.stale_plan(0) == 0
    assert all(0 <= bootstrap.stale_plan(i) < 700 for i in range(200))
    stale = sum(1 for i in range(100) if bootstrap.stale_plan(i) > 365)
    assert 30 <= stale <= 60  # dashboard drill-down must have material


def test_catalog_consistent():
    names = [p[0] for p in PERMISSIONS]
    assert len(names) == len(set(names))
    for role, granted in ROLE_PERMS.items():
        assert role in {r[0] for r in ROLES}
        if granted != ["*"]:
            assert set(granted) <= set(names)
    for _email, _full, role, _super in DEMO_USERS:
        assert role in {r[0] for r in ROLES}


def test_faker_seed_reproducible():
    Faker.seed(bootstrap.FAKER_SEED)
    first_a = Faker("en_IN").first_name()
    Faker.seed(bootstrap.FAKER_SEED)
    first_b = Faker("en_IN").first_name()
    assert first_a == first_b
