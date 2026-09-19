"""M1.1 Phase B1 — groups domain foundation (backend only, no UI).

Integration tests use httpx.ASGITransport against real PostgreSQL with
dedicated B1 fixtures (removed afterwards). Covers: auth matrix, manual
lifecycle + idempotency, rule versioning + two-stage approval, self-approval
prevention, stale-version rejection, preview/materialize semantics,
field-level security on member lists, and audit generation.

Profile-photo tests are out of scope and untouched.
"""

import uuid
from datetime import date

import httpx
import pytest

from app.main import app


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


async def _make_people() -> dict:
    """Two deterministic PERSON constituents with employment history."""
    from app.db.session import async_session_factory
    from app.models import (
        Affiliation,
        AffiliationSource,
        Constituent,
        ConstituentKind,
        ConstituentStatus,
        DatePrecision,
        Person,
    )

    async with async_session_factory() as session:
        ids = {}
        specs = [
            ("B1ALPHA", "B1AlphaFirst", "B1AlphaLast", "B1Corp", "IT", "Senior", "India", date(2020, 1, 15)),
            ("B1BETA", "B1BetaFirst", "B1BetaLast", "B1Other", "Finance", "Director", "United States", date(2022, 3, 1)),
        ]
        for tag, first, last, org, sector, seniority, country, start in specs:
            c = Constituent(
                kind=ConstituentKind.PERSON,
                status=ConstituentStatus.ACTIVE,
                display_name=f"B1Test {tag} Person",
                normalised_display_name=f"b1test {tag.lower()} person",
                notes="B1Secret",
            )
            session.add(c)
            await session.flush()
            session.add(Person(constituent_id=c.id, first_name=first, full_name=f"{first} {last}", last_name=last))
            session.add(
                Affiliation(
                    constituent_id=c.id,
                    organisation_name_raw=org,
                    designation="Senior Engineer" if tag == "B1ALPHA" else "Director of Finance",
                    seniority_level=seniority,
                    sector=sector,
                    country=country,
                    start_date=start,
                    is_current=True,
                    date_precision=DatePrecision.DAY,
                    source=AffiliationSource.STAFF,
                )
            )
            ids[tag] = str(c.id)
        await session.commit()
        return ids


async def _drop_fixtures() -> None:
    from sqlalchemy import delete

    from app.db.session import async_session_factory
    from app.models import Constituent, Group

    async with async_session_factory() as session:
        await session.execute(delete(Group).where(Group.name.like("B1%")))
        await session.execute(
            delete(Constituent).where(Constituent.normalised_display_name.like("b1test%"))
        )
        await session.commit()


def _industry_it() -> dict:
    return {"op": "and", "conditions": [{"field": "industry", "operator": "is_any_of", "values": ["IT"]}]}


@pytest.mark.asyncio
async def test_groups_auth_matrix():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        r = await client.get("/groups")
        assert r.status_code == 401
        r = await client.post("/groups", json={"name": "B1X", "type": "MANUAL"})
        assert r.status_code == 401

        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")

        # Viewer reads (groups.read) but cannot write anything.
        r = await client.get("/groups", headers=viewer)
        assert r.status_code == 200
        r = await client.post("/groups", json={"name": "B1Viewer", "type": "MANUAL"}, headers=viewer)
        assert r.status_code == 403
        # Viewer lacks rule/member/approval permissions everywhere.
        for method, path, body in [
            ("POST", "/groups/x/rules", {"filter": _industry_it()}),
            ("POST", "/groups/x/members", {"constituent_ids": [str(uuid.uuid4())]}),
            ("POST", "/groups/x/members/materialize", {"filter": _industry_it()}),
            ("POST", "/groups/x/proposals/approve", {"proposal_ids": [str(uuid.uuid4())]}),
        ]:
            r = await client.request(method, path, json=body, headers=viewer)
            assert r.status_code in (403, 404), (method, path, r.status_code)

        # Finance role holds no groups permissions at all.
        finance = await _login(client, "finance@iitgn.ac.in", "finance123")
        r = await client.get("/groups", headers=finance)
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_manual_lifecycle_idempotency_and_guards():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        ids = await _make_people()
        try:
            a, b = ids["B1ALPHA"], ids["B1BETA"]
            ghost = str(uuid.uuid4())

            r = await client.post(
                "/groups", json={"name": "B1Manual", "type": "MANUAL", "description": "d"}, headers=staff
            )
            assert r.status_code == 201, r.text
            gid = r.json()["id"]
            assert r.json()["member_count"] == 0

            # Duplicate name rejected.
            r = await client.post("/groups", json={"name": "B1Manual", "type": "MANUAL"}, headers=staff)
            assert r.status_code == 409

            # Manual groups take no rule.
            r = await client.post(
                "/groups",
                json={"name": "B1Manual2", "type": "MANUAL", "initial_rule": _industry_it()},
                headers=staff,
            )
            assert r.status_code == 400

            # Explicit add: added / already / invalid split, duplicates safe.
            r = await client.post(
                f"/groups/{gid}/members", json={"constituent_ids": [a, b]}, headers=staff
            )
            assert r.status_code == 200
            assert sorted(r.json()["added"]) == sorted([a, b])
            r = await client.post(
                f"/groups/{gid}/members", json={"constituent_ids": [a, b, a, ghost]}, headers=staff
            )
            assert r.status_code == 200
            assert r.json()["added"] == []
            assert sorted(r.json()["already_members"]) == sorted([a, b])
            assert r.json()["invalid"] == [ghost]

            # Members listed with field security (staff sees notes).
            r = await client.get(f"/groups/{gid}/members?page_size=100", headers=staff)
            assert r.status_code == 200
            assert r.json()["total"] == 2

            # Idempotent removal.
            r = await client.delete(f"/groups/{gid}/members/{a}", headers=staff)
            assert r.status_code == 204
            r = await client.delete(f"/groups/{gid}/members/{a}", headers=staff)
            assert r.status_code == 204
            r = await client.get(f"/groups/{gid}/members?page_size=100", headers=staff)
            assert [m["constituent_id"] for m in r.json()["items"]] == [b]

            # Rule-based groups reject direct membership edits.
            r = await client.post(
                "/groups",
                json={"name": "B1Rule", "type": "RULE_BASED", "initial_rule": _industry_it()},
                headers=staff,
            )
            assert r.status_code == 201
            rid = r.json()["id"]
            assert r.json()["active_rule_version"] is None
            assert r.json()["has_pending_rule"] is True
            r = await client.post(f"/groups/{rid}/members", json={"constituent_ids": [a]}, headers=staff)
            assert r.status_code == 400
            r = await client.delete(f"/groups/{rid}/members/{a}", headers=staff)
            assert r.status_code == 400

            # Deactivation freezes writes; reactivation restores.
            r = await client.post(f"/groups/{gid}/deactivate", headers=staff)
            assert r.status_code == 200
            assert r.json()["status"] == "DEACTIVATED"
            r = await client.post(f"/groups/{gid}/members", json={"constituent_ids": [a]}, headers=staff)
            assert r.status_code == 400
            r = await client.post(f"/groups/{gid}/reactivate", headers=staff)
            assert r.status_code == 200
            r = await client.post(f"/groups/{gid}/members", json={"constituent_ids": [a]}, headers=staff)
            assert r.status_code == 200
            assert r.json()["added"] == [a]
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_member_list_field_security_for_viewer():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")
        ids = await _make_people()
        try:
            r = await client.post("/groups", json={"name": "B1FieldSec", "type": "MANUAL"}, headers=staff)
            gid = r.json()["id"]
            await client.post(
                f"/groups/{gid}/members",
                json={"constituent_ids": [ids["B1ALPHA"]]},
                headers=staff,
            )
            r = await client.get(f"/groups/{gid}/members", headers=staff)
            assert r.json()["items"][0]["notes"] == "B1Secret"
            r = await client.get(f"/groups/{gid}/members", headers=viewer)
            assert r.status_code == 200
            # Restricted notes withheld server-side; membership itself visible.
            assert r.json()["items"][0].get("notes") is None
            assert r.json()["items"][0]["display_name"] == "B1Test B1ALPHA Person"
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_two_stage_approval_self_approval_and_stale_versions():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        ids = await _make_people()
        try:
            a = ids["B1ALPHA"]
            r = await client.post(
                "/groups",
                json={"name": "B1Gov", "type": "RULE_BASED", "initial_rule": _industry_it()},
                headers=staff,
            )
            assert r.status_code == 201
            gid = r.json()["id"]

            # Second pending rule blocked while v1 awaits review.
            r = await client.post(f"/groups/{gid}/rules", json={"filter": _industry_it()}, headers=staff)
            assert r.status_code == 409
            # Invalid rule rejected, not stored (fresh group: no pending conflict).
            r = await client.post("/groups", json={"name": "B1GovFresh", "type": "RULE_BASED"}, headers=staff)
            assert r.status_code == 201
            fresh = r.json()["id"]
            r = await client.post(
                f"/groups/{fresh}/rules",
                json={"filter": {"op": "and", "conditions": [{"field": "industry", "operator": "contains", "value": "IT"}]}},
                headers=staff,
            )
            assert r.status_code == 422
            r = await client.get(f"/groups/{fresh}/rules", headers=staff)
            assert r.json() == []

            # Stage 1: proposer cannot approve their own rule.
            r = await client.post(f"/groups/{gid}/rules/1/approve", headers=staff)
            assert r.status_code == 403
            # Admin (different actor) approves: rule ACTIVE + evaluation ran.
            r = await client.post(f"/groups/{gid}/rules/1/approve", headers=admin)
            assert r.status_code == 200, r.text
            assert r.json()["rule"]["status"] == "ACTIVE"
            assert r.json()["evaluation"]["additions"] >= 1

            # Versions immutable: v1 row keeps its tree; proposals explain themselves.
            r = await client.get(f"/groups/{gid}/rules", headers=staff)
            assert [(v["version_number"], v["status"]) for v in r.json()] == [(1, "ACTIVE")]
            r = await client.get(f"/groups/{gid}/proposals?page_size=100", headers=staff)
            assert r.status_code == 200
            pending = [p for p in r.json()["items"] if p["status"] == "PENDING"]
            assert len(pending) >= 1
            assert a in [p["constituent_id"] for p in pending if p["action"] == "ADD"]
            first = pending[0]
            assert first["reason_summary"]
            detail = first["reason_detail"]
            assert detail and "leaves" in detail and "expected" in detail and "actual" in detail
            assert first["rule_version_number"] == 1

            # Membership approval by the evaluator is self-approval (admin evaluated).
            v1_ids = [p["id"] for p in pending]
            r = await client.post(
                f"/groups/{gid}/proposals/approve", json={"proposal_ids": v1_ids}, headers=admin
            )
            assert r.status_code == 403
            # Staff (not the evaluator) approves: membership applies.
            r = await client.post(
                f"/groups/{gid}/proposals/approve", json={"proposal_ids": v1_ids}, headers=staff
            )
            assert r.status_code == 200, r.text
            assert sorted(r.json()["approved_or_rejected"]) == sorted(v1_ids)
            r = await client.get(f"/groups/{gid}/members?page_size=100", headers=staff)
            assert a in [m["constituent_id"] for m in r.json()["items"]]
            # Re-approving decided rows reports them, never duplicates membership.
            r = await client.post(
                f"/groups/{gid}/proposals/approve", json={"proposal_ids": v1_ids}, headers=staff
            )
            assert sorted(r.json()["already_decided"]) == sorted(v1_ids)
            r = await client.get(f"/groups/{gid}/members?page_size=100", headers=staff)
            assert len(r.json()["items"]) == len(
                {m["constituent_id"] for m in r.json()["items"]}
            )

            # New rule v2 supersedes v1 on approval; v1 proposals go stale.
            seniority = {
                "op": "and",
                "conditions": [{"field": "seniority_level", "operator": "is_any_of", "values": ["Senior"]}],
            }
            r = await client.post(f"/groups/{gid}/rules", json={"filter": seniority}, headers=staff)
            assert r.status_code == 201
            r = await client.post(f"/groups/{gid}/rules/2/approve", headers=admin)
            assert r.status_code == 200
            r = await client.get(f"/groups/{gid}/rules", headers=staff)
            assert [(v["version_number"], v["status"]) for v in r.json()] == [
                (1, "SUPERSEDED"),
                (2, "ACTIVE"),
            ]
            # v1 tree bytes preserved verbatim (append-only history).
            v1 = [v for v in r.json() if v["version_number"] == 1][0]
            assert v1["filter_tree"]["conditions"][0]["field"] == "industry"

            # Fresh v2 evaluation created pending rows; craft a stale case:
            # evaluate v2 as staff, then supersede with v3, then approve v2 rows.
            r = await client.post(f"/groups/{gid}/rules/2/evaluate", headers=staff)
            assert r.status_code == 200
            r = await client.get(
                f"/groups/{gid}/proposals?status=PENDING&page_size=100", headers=staff
            )
            v2_pending = [p["id"] for p in r.json()["items"] if p["rule_version_number"] == 2]
            narrow = {
                "op": "and",
                "conditions": [
                    {"field": "seniority_level", "operator": "is_any_of", "values": ["Fellow"]},
                    {"field": "industry", "operator": "is_any_of", "values": ["IT"]},
                ],
            }
            r = await client.post(f"/groups/{gid}/rules", json={"filter": narrow}, headers=staff)
            assert r.status_code == 201
            r = await client.post(f"/groups/{gid}/rules/3/approve", headers=admin)
            assert r.status_code == 200
            if v2_pending:
                r = await client.post(
                    f"/groups/{gid}/proposals/approve", json={"proposal_ids": v2_pending}, headers=admin
                )
                assert r.status_code == 200
                assert sorted(r.json()["stale"]) == sorted(v2_pending)
                assert r.json()["approved_or_rejected"] == []
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_evaluate_reject_and_preview_materialize_paths():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        ids = await _make_people()
        try:
            a = ids["B1ALPHA"]
            r = await client.post("/groups", json={"name": "B1Paths", "type": "MANUAL"}, headers=staff)
            gid = r.json()["id"]

            # Preview (dry-run): re-evaluated server-side, never mutates.
            r = await client.post(
                f"/groups/{gid}/members/preview", json={"filter": _industry_it()}, headers=staff
            )
            assert r.status_code == 200
            assert r.json()["matched"] >= 2
            assert r.json()["would_add"] == r.json()["matched"]
            r = await client.get(f"/groups/{gid}/members", headers=staff)
            assert r.json()["total"] == 0

            # Preview rejects ambiguous or invalid definitions.
            r = await client.post(
                f"/groups/{gid}/members/preview",
                json={"constituent_ids": [a], "filter": _industry_it()},
                headers=staff,
            )
            assert r.status_code == 422
            r = await client.post(
                f"/groups/{gid}/members/preview",
                json={"filter": {"op": "and", "conditions": [{"field": "groups", "operator": "is_any_of", "values": ["x"]}]}},
                headers=staff,
            )
            assert r.status_code == 400

            # Materialize adds non-members only (idempotent across repeats).
            r = await client.post(
                f"/groups/{gid}/members/materialize", json={"filter": _industry_it()}, headers=staff
            )
            assert r.status_code == 200
            first_added = len(r.json()["added"])
            assert first_added >= 2
            assert a in r.json()["added"]
            r = await client.post(
                f"/groups/{gid}/members/materialize", json={"filter": _industry_it()}, headers=staff
            )
            assert r.json()["added"] == []
            assert r.json()["already_members"] == r.json()["matched"]

            # Rule rejection path + evaluate guards.
            r = await client.post(
                "/groups", json={"name": "B1Rej", "type": "RULE_BASED", "initial_rule": _industry_it()},
                headers=staff,
            )
            rgid = r.json()["id"]
            r = await client.post(f"/groups/{rgid}/rules/1/reject", headers=staff)
            assert r.status_code == 403  # proposer cannot reject-approve own rule either
            r = await client.post(f"/groups/{rgid}/rules/1/reject", headers=admin)
            assert r.status_code == 200
            assert r.json()["status"] == "REJECTED"
            r = await client.post(f"/groups/{rgid}/rules/1/approve", headers=admin)
            assert r.status_code == 400
            r = await client.post(f"/groups/{rgid}/rules/1/evaluate", headers=staff)
            assert r.status_code == 400  # only ACTIVE versions evaluate

            # needs_review list filter surfaces groups awaiting governance.
            r = await client.get("/groups?needs_review=true&page_size=100", headers=staff)
            assert r.status_code == 200
            assert "B1Rej" not in [g["name"] for g in r.json()["items"]]
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_filtered_handoff_matches_full_people_population():
    """B2/B1 integration: preview/materialize with M1 criteria + filter tree
    must equal the POST /constituents/search population for the same query."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        ids = await _make_people()
        # Alumni rows + ancient freshness so the stale combo can include fixtures.
        from datetime import datetime, timezone

        from app.db.session import async_session_factory
        from app.models import AlumniProfile, Constituent

        async with async_session_factory() as session:
            from sqlalchemy import select

            for tag, roll in [("B1ALPHA", "B1HAND001"), ("B1BETA", "B1HAND002")]:
                session.add(AlumniProfile(constituent_id=uuid.UUID(ids[tag]), roll_no=roll))
            await session.flush()
            result = await session.execute(
                select(Constituent).where(
                    Constituent.normalised_display_name.like("b1test%")
                )
            )
            for c in result.scalars().all():
                c.last_substantive_profile_update_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
            await session.commit()
        try:
            it = _industry_it()

            async def people_total(body: dict) -> tuple[int, set]:
                r = await client.post("/constituents/search", json=body, headers=staff)
                assert r.status_code == 200, r.text
                return r.json()["total"], {i["id"] for i in r.json()["items"]}

            r = await client.post("/groups", json={"name": "B1Handoff", "type": "MANUAL"}, headers=staff)
            assert r.status_code == 201
            gid = r.json()["id"]

            async def preview(body: dict) -> dict:
                r = await client.post(f"/groups/{gid}/members/preview", json=body, headers=staff)
                assert r.status_code == 200, r.text
                return r.json()

            # 1. Name search + structured filter.
            total, who = await people_total({"q": "B1Test", "filter": it, "page_size": 100})
            assert {ids["B1ALPHA"]} <= who and ids["B1BETA"] not in who
            p = await preview({"q": "B1Test", "filter": it})
            assert p["matched"] == total

            # 2. Roll Number + structured filter narrows to one.
            total, who = await people_total({"roll_no": "B1HAND001", "filter": it, "page_size": 100})
            assert (total, who) == (1, {ids["B1ALPHA"]})
            p = await preview({"roll_no": "B1HAND001", "filter": it})
            assert p["matched"] == 1

            # 3. Organisation substring + structured filter.
            total, who = await people_total(
                {"organisation_q": "B1Corp", "filter": it, "page_size": 100}
            )
            assert who == {ids["B1ALPHA"]}
            p = await preview({"organisation_q": "B1Corp", "filter": it})
            assert p["matched"] == total == 1

            # 4. Stale filter + structured filter agrees with People.
            total, who = await people_total(
                {"stale_threshold_days": 365, "filter": it, "page_size": 100}
            )
            assert ids["B1ALPHA"] in who
            p = await preview({"stale_threshold_days": 365, "filter": it})
            assert p["matched"] == total

            # 5. Materialize applies exactly the People population.
            r = await client.post(
                f"/groups/{gid}/members/materialize",
                json={"organisation_q": "B1Corp", "filter": it},
                headers=staff,
            )
            assert r.status_code == 200
            assert r.json()["matched"] == 1 and r.json()["added"] == [ids["B1ALPHA"]]
            r = await client.get(f"/groups/{gid}/members?page_size=100", headers=staff)
            assert [m["constituent_id"] for m in r.json()["items"]] == [ids["B1ALPHA"]]

            # 6. Invalid combinations fail identically on both surfaces.
            bad = {"q": "B1Test", "filter": {"op": "and", "conditions": [{"field": "groups", "operator": "is_any_of", "values": ["x"]}]}}
            r = await client.post("/constituents/search", json=bad, headers=staff)
            assert r.status_code == 400
            r = await client.post(f"/groups/{gid}/members/preview", json=bad, headers=staff)
            assert r.status_code == 400
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_group_audit_trail_uses_central_events():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        ids = await _make_people()
        try:
            r = await client.post("/groups", json={"name": "B1Audit", "type": "MANUAL"}, headers=staff)
            gid = r.json()["id"]
            await client.post(
                f"/groups/{gid}/members", json={"constituent_ids": [ids["B1ALPHA"]]}, headers=staff
            )
            await client.post(f"/groups/{gid}/deactivate", headers=staff)
            r = await client.get(
                "/admin/audit-events?entity_type=group&page_size=100", headers=admin
            )
            assert r.status_code == 200
            actions = {e["action"] for e in r.json()["items"]}
            assert {"GROUP_CREATE", "GROUP_MEMBER_ADD", "GROUP_DEACTIVATE"} <= actions
            # Audit carries metadata, never member row dumps.
            creates = [e for e in r.json()["items"] if e["action"] == "GROUP_CREATE"]
            assert creates and creates[0]["entity_id"] == gid
        finally:
            await _drop_fixtures()
