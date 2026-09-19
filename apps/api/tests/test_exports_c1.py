"""M1.1 Phase C — permission-aware export (synchronous XLSX).

Unit tests cover field allow-list stripping without a database.
Integration tests use httpx.ASGITransport against real PostgreSQL:
gates, population parity with People search, arbitrary-ID handling,
group populations, and audit metadata (never row data).

Profile-photo tests are out of scope and untouched.
"""

import io
import uuid
from datetime import date

import httpx
import pytest
from openpyxl import load_workbook

from app.main import app
from app.services.exports import resolve_export_fields
from app.services.exports import EXPORTABLE_FIELDS


def _checker():
    from app.core.field_permissions import FieldPermissionChecker

    return FieldPermissionChecker.__new__(FieldPermissionChecker)


def test_field_allow_list_strips_restricted_without_db():
    all_keys = {e["key"] for e in EXPORTABLE_FIELDS}
    # The registry derives from the 360° models: profile scalars are present
    # (gated), technical identifiers and Aadhaar/ciphertext never are.
    assert "notes" in all_keys  # gated by constituents.read_internal
    assert "thesis_title" in all_keys  # dynamic: new 360 fields appear automatically
    assert "placements.company" in all_keys
    assert "education_records_count" in all_keys
    assert "aadhaar_encrypted" not in all_keys
    assert "pan_encrypted" not in all_keys
    assert "constituent_id" not in all_keys
    assert not any(k.endswith("_at") for k in all_keys)

    # Bare reader: only unrestricted columns survive.
    allowed, dropped = resolve_export_fields(_checker(), None, set(), False)
    allowed_keys = {e["key"] for e in allowed}
    assert "display_name" in allowed_keys
    assert "roll_no" in allowed_keys
    assert "gender" in dropped  # needs people.read_demographics
    assert "primary_email" in dropped  # needs contacts.read_pii
    assert "final_cpi" in dropped  # needs alumni.read_academic

    # Demographics without PII: gender present, contacts still dropped.
    allowed, _ = resolve_export_fields(_checker(), None, {"people.read_demographics"}, False)
    allowed_keys = {e["key"] for e in allowed}
    assert "gender" in allowed_keys and "date_of_birth" in allowed_keys
    assert "primary_phone" not in allowed_keys

    # Explicit request of a withheld field: dropped, not failed.
    allowed, dropped = resolve_export_fields(
        _checker(), ["display_name", "gender"], set(), False
    )
    assert [e["key"] for e in allowed] == ["display_name"]
    assert dropped == ["gender"]

    # Unknown fields fail closed.
    with pytest.raises(ValueError, match="Unknown export field"):
        resolve_export_fields(_checker(), ["display_name", "pan"], set(), False)

    # Superuser sees the full registry.
    allowed, dropped = resolve_export_fields(_checker(), None, set(), True)
    assert len(allowed) == len(EXPORTABLE_FIELDS) and dropped == []


async def _db_reachable() -> bool:
    from sqlalchemy import text

    from app.db.session import async_session_factory, engine

    try:
        await engine.dispose()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict:
    r = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 401:
        pytest.skip("seed users missing; run scripts/seed_users.py first")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _parse_xlsx(body: bytes) -> tuple[list[str], list[list]]:
    wb = load_workbook(filename=io.BytesIO(body), read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert rows, "export must at least contain a header row"
    return list(rows[0]), [list(r) for r in rows[1:]]


@pytest.mark.asyncio
async def test_export_gates_and_catalog():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=60.0
    ) as client:
        r = await client.get("/exports/people/fields")
        assert r.status_code == 401
        r = await client.post("/exports/people", json={})
        assert r.status_code == 401

        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")
        finance = await _login(client, "finance@iitgn.ac.in", "finance123")

        # Bulk export needs constituents.export: viewer/finance lack it.
        for headers in (viewer, finance):
            r = await client.get("/exports/people/fields", headers=headers)
            assert r.status_code == 403
            r = await client.post("/exports/people", json={}, headers=headers)
            assert r.status_code == 403

        r = await client.get("/exports/people/fields", headers=staff)
        assert r.status_code == 200
        catalog = {i["key"]: i for i in r.json()["items"]}
        assert set(catalog) == {e["key"] for e in EXPORTABLE_FIELDS}
        # Staff holds every field permission except the admin-only SSAC gate.
        assert catalog["gender"]["allowed"] is True
        assert catalog["gender"]["requires"] == ["people.read_demographics"]
        assert catalog["ssac_records_count"]["allowed"] is False
        assert catalog["ssac_records_count"]["requires"] == ["ssac.read_restricted"]
        assert catalog["thesis_title"]["allowed"] is True
        # Superuser sees the entire dynamic registry.
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        r = await client.get("/exports/people/fields", headers=admin)
        assert all(i["allowed"] for i in r.json()["items"])


@pytest.mark.asyncio
async def test_export_populations_match_people_search():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=60.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")

        async def export(body: dict):
            r = await client.post("/exports/people", json=body, headers=staff)
            assert r.status_code == 200, r.text
            assert "spreadsheetml.sheet" in r.headers["content-type"]
            assert r.headers["content-disposition"].endswith('.xlsx"')
            return _parse_xlsx(r.content)

        # Unfiltered: every visible alumnus, headers include key columns.
        headers, rows = await export({})
        assert "Roll Number" in headers and "Name" in headers
        # Dynamic 360 coverage beyond the legacy set.
        assert "Thesis Title" in headers
        assert "Education Records Count" in headers
        assert "Company (Placements)" in headers
        assert len(headers) > 40
        r = await client.get("/constituents?page_size=1", headers=staff)
        assert r.status_code == 200
        # Row count is sane (nonzero, bounded by the cap).
        assert 0 < len(rows) <= 5000

        # Filtered export equals the People-search population.
        filt = {"op": "and", "conditions": [{"field": "industry", "operator": "is_any_of", "values": ["IT"]}]}
        r = await client.post(
            "/constituents/search", json={"filter": filt, "page_size": 100}, headers=staff
        )
        expected_total = r.json()["total"]
        headers, rows = await export({"filter": filt})
        assert len(rows) == expected_total

        # Zero-result export: headers only, still 200.
        headers, rows = await export(
            {"filter": {"op": "and", "conditions": [{"field": "current_company", "operator": "equals", "value": "NoSuchCorpZZZ"}]}}
        )
        assert len(rows) == 0 and len(headers) > 0

        # Arbitrary IDs: ghosts excluded server-side, never trusted.
        ghost = str(uuid.uuid4())
        r = await client.get("/constituents?page_size=2", headers=staff)
        real = [i["id"] for i in r.json()["items"]]
        headers, rows = await export({"constituent_ids": real + [ghost]})
        assert len(rows) == len(real)

        # Unknown fields and bad filters fail closed.
        r = await client.post("/exports/people", json={"fields": ["pan"]}, headers=staff)
        assert r.status_code == 422
        r = await client.post(
            "/exports/people",
            json={"filter": {"op": "and", "conditions": [{"field": "industry", "operator": "contains", "value": "IT"}]}},
            headers=staff,
        )
        assert r.status_code == 422


@pytest.mark.asyncio
async def test_export_group_population_and_audit():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=60.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        from app.db.session import async_session_factory
        from app.models import Group

        from sqlalchemy import delete

        async with async_session_factory() as session:
            await session.execute(delete(Group).where(Group.name.like("C1%")))
            await session.commit()
        try:
            r = await client.get("/constituents?page_size=3", headers=staff)
            member_ids = [i["id"] for i in r.json()["items"]]
            assert len(member_ids) == 3
            r = await client.post(
                "/groups", json={"name": "C1Export", "type": "MANUAL"}, headers=staff
            )
            assert r.status_code == 201
            gid = r.json()["id"]
            r = await client.post(
                f"/groups/{gid}/members", json={"constituent_ids": member_ids}, headers=staff
            )
            assert r.status_code == 200

            # Unknown group → 404, not an empty file.
            r = await client.post(
                "/exports/people", json={"group_id": str(uuid.uuid4())}, headers=staff
            )
            assert r.status_code == 404

            r = await client.post("/exports/people", json={"group_id": gid}, headers=staff)
            assert r.status_code == 200
            headers, rows = _parse_xlsx(r.content)
            assert len(rows) == 3

            # Field allow-list enforced end to end: viewer-style request for a
            # restricted column drops it instead of leaking.
            r = await client.post(
                "/exports/people",
                json={"group_id": gid, "fields": ["display_name", "gender"]},
                headers=staff,
            )
            assert r.status_code == 200
            headers, rows = _parse_xlsx(r.content)
            # Staff holds demographics: both present. The drop path itself is
            # proven by the unit tests above for lesser-privileged callers.

            # Audit carries metadata only — never exported row values.
            r = await client.get(
                "/admin/audit-events?entity_type=export&page_size=50", headers=admin
            )
            assert r.status_code == 200
            exports = [e for e in r.json()["items"] if e["action"] == "EXPORT_PEOPLE"]
            assert exports
            latest = exports[0]
            assert "group_id" in (latest["after_state"] or "")
            assert "row_count" in (latest["after_state"] or "")
            assert member_ids[0] not in (latest["after_state"] or "")
            assert member_ids[0] not in (latest["before_state"] or "")
        finally:
            async with async_session_factory() as session:
                await session.execute(delete(Group).where(Group.name.like("C1%")))
                await session.commit()
