"""M1 integration tests against the real PostgreSQL database.

Requires seeded dev data (scripts/seed_alumni.py, scripts/seed_users.py).
Skips cleanly when the database is unreachable so unit tests still run in CI.
"""

import uuid
from datetime import date, datetime

import httpx
import pytest

from app.core.config import settings

from app.db.session import async_session_factory
from app.main import app


async def _db_reachable() -> bool:
    # Each test runs on its own event loop, so drop pooled connections tied
    # to a previous loop before probing; otherwise the checkout fails even
    # though PostgreSQL itself is healthy.
    from sqlalchemy import text

    from app.db.session import engine

    try:
        await engine.dispose()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.mark.asyncio
async def test_m1_flows_with_real_db():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        # 1. Unauthenticated requests are rejected server-side.
        r = await client.get("/constituents?q=test")
        assert r.status_code == 401

        # 2. Staff login works (requires seeded users).
        r = await client.post(
            "/auth/login",
            data={"username": "staff@iitgn.ac.in", "password": "staff123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 401:
            pytest.skip("seed users missing; run scripts/seed_users.py first")
        assert r.status_code == 200
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "X-Request-ID": f"test-{uuid.uuid4()}"}

        # 3. Name search (partial) works.
        r = await client.get("/constituents", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert body["page"] == 1
        first = body["items"][0]

        # 4. 360 profile opens from search result.
        r = await client.get(f"/constituents/{first['id']}/profile", headers=headers)
        assert r.status_code == 200
        profile = r.json()
        assert profile["constituent"]["id"] == first["id"]
        assert "education_records" in profile
        assert "affiliations" in profile
        assert "audit_events" in profile

        # 5. Stale count + paginated stale list share the same filter.
        r = await client.get("/constituents/stale-profiles-count", headers=headers)
        assert r.status_code == 200
        stale_total = r.json()["count"]
        assert stale_total >= 0

        r = await client.get(
            "/constituents/stale-profiles?page=1&page_size=5", headers=headers
        )
        assert r.status_code == 200
        stale = r.json()
        assert stale["page"] == 1
        assert stale["page_size"] == 5
        assert stale["total"] == stale_total

        r = await client.get(
            "/constituents/stale-profiles?page=2&page_size=5", headers=headers
        )
        assert r.status_code == 200
        assert r.json()["page"] == 2

        # 6. Organisation search labels current/past status.
        r = await client.get(
            "/constituents/organisations/search?q=University", headers=headers
        )
        assert r.status_code == 200
        org = r.json()
        assert org["total"] >= 1
        for item in org["items"]:
            assert item["affiliation_status"] in ("Current", "Past", "Current and past")

        # 7. Viewer (no demographics permission) gets masked/filtered fields.
        r = await client.post(
            "/auth/login",
            data={"username": "viewer@iitgn.ac.in", "password": "viewer123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        viewer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await client.get(f"/constituents/{first['id']}/profile", headers=viewer_headers)
        assert r.status_code == 200
        viewer_profile = r.json()
        # Optional restricted fields are withheld; required ones are masked.
        if viewer_profile.get("person"):
            assert viewer_profile["person"].get("gender") is None
            assert viewer_profile["person"].get("date_of_birth") is None
        for cm in viewer_profile.get("contact_methods", []):
            assert cm["value"] == "[restricted]"


@pytest.mark.asyncio
async def test_m1_append_workflows_preserve_history():
    """Education and career history are append-only; new current job closes the old one."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://localhost:8000/api/v1", timeout=30.0
    ) as client:
        r = await client.post(
            "/auth/login",
            data={"username": "staff@iitgn.ac.in", "password": "staff123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 401:
            pytest.skip("seed users missing; run scripts/seed_users.py first")
        staff_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await client.get("/constituents?page_size=1", headers=staff_headers)
        cid = r.json()["items"][0]["id"]

        r = await client.get(f"/constituents/{cid}/profile", headers=staff_headers)
        before = r.json()
        edu_before = len(before["education_records"])
        current_before = [a for a in before["affiliations"] if a["is_current"]]
        prev_state = {a["id"]: (a["is_current"], a["end_date"]) for a in before["affiliations"]}
        freshness_before = before["constituent"]["last_substantive_profile_update_at"]

        # 1. Append a post-IITGN qualification; earlier records are preserved.
        r = await client.post(
            f"/constituents/{cid}/education",
            json={
                "education_stage": "POST_IITGN",
                "qualification": "MTech Test",
                "institution_name": "Test Institute",
                "completion_year": 2024,
            },
            headers=staff_headers,
        )
        assert r.status_code == 201
        assert r.json()["qualification"] == "MTech Test"

        # 2. Invalid year ordering is rejected, nothing appended.
        r = await client.post(
            f"/constituents/{cid}/education",
            json={
                "education_stage": "POST_IITGN",
                "qualification": "Bad Record",
                "institution_name": "Test Institute",
                "start_year": 2024,
                "completion_year": 2020,
            },
            headers=staff_headers,
        )
        assert r.status_code == 400

        # 3. New current job closes the previous current affiliation.
        r = await client.post(
            f"/constituents/{cid}/affiliations",
            json={
                "organisation_name_raw": "Test Org",
                "designation": "Engineer",
                "is_current": True,
                "start_date": "2024-06-01",
            },
            headers=staff_headers,
        )
        assert r.status_code == 201
        assert r.json()["is_current"] is True

        # 4. End-before-start is rejected.
        r = await client.post(
            f"/constituents/{cid}/affiliations",
            json={
                "organisation_name_raw": "Bad Org",
                "start_date": "2024-06-01",
                "end_date": "2023-01-01",
            },
            headers=staff_headers,
        )
        assert r.status_code == 400

        r = await client.get(f"/constituents/{cid}/profile", headers=staff_headers)
        after = r.json()
        assert len(after["education_records"]) == edu_before + 1
        assert any(e["qualification"] == "MTech Test" for e in after["education_records"])
        current_after = [a for a in after["affiliations"] if a["is_current"]]
        assert len(current_after) == 1
        assert current_after[0]["organisation_name_raw"] == "Test Org"
        for prev_id in [a["id"] for a in current_before]:
            prev = next(a for a in after["affiliations"] if a["id"] == prev_id)
            assert prev["is_current"] is False
        # 5. A substantive write refreshes freshness.
        assert after["constituent"]["last_substantive_profile_update_at"] is not None
        assert after["constituent"]["days_since_profile_update"] == 0

        # 6. Viewer role cannot write (server-side enforcement, not UI hiding).
        r = await client.post(
            "/auth/login",
            data={"username": "viewer@iitgn.ac.in", "password": "viewer123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        viewer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await client.post(
            f"/constituents/{cid}/education",
            json={
                "education_stage": "POST_IITGN",
                "qualification": "Sneaky Record",
                "institution_name": "Test Institute",
            },
            headers=viewer_headers,
        )
        assert r.status_code == 403

        # Cleanup test fixtures so seeded data stays pristine.
        from app.db.session import async_session_factory
        from app.models import Affiliation, Constituent, EducationRecord
        from sqlalchemy import delete, select

        async with async_session_factory() as session:
            await session.execute(
                delete(EducationRecord).where(
                    EducationRecord.constituent_id == cid,
                    EducationRecord.qualification == "MTech Test",
                )
            )
            await session.execute(
                delete(Affiliation).where(
                    Affiliation.constituent_id == cid,
                    Affiliation.organisation_name_raw == "Test Org",
                )
            )
            result = await session.execute(
                select(Affiliation).where(Affiliation.constituent_id == cid)
            )
            for aff in result.scalars().all():
                if str(aff.id) in prev_state:
                    was_current, old_end = prev_state[str(aff.id)]
                    aff.is_current = was_current
                    aff.end_date = date.fromisoformat(old_end) if old_end else None
            result = await session.execute(
                select(Constituent).where(Constituent.id == cid)
            )
            constituent = result.scalars().first()
            if constituent is not None:
                constituent.last_substantive_profile_update_at = (
                    datetime.fromisoformat(freshness_before) if freshness_before else None
                )
            await session.commit()


@pytest.mark.asyncio
async def test_related_entities_in_profile_and_restricted_gating():
    """T-table slice: all 14 child collections ride the 360° profile;
    SSAC and family rows are withheld without the respective permission."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        async def login(email, password):
            r = await client.post(
                "/auth/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.status_code == 401:
                pytest.skip("seed users missing; run scripts/seed_users.py first")
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        staff_headers = await login("staff@iitgn.ac.in", "staff123")
        admin_headers = await login("admin@iitgn.ac.in", "admin123")

        child_keys = [
            "hostel_history", "academic_courses", "semester_performance",
            "gps_assignments", "awards_recognition", "scholarships_financial_aid",
            "internships", "placements", "startups", "ssac_records",
            "positions_of_responsibility", "publications", "overseas_exposure",
            "family_members",
        ]

        r = await client.get("/constituents?page_size=100", headers=staff_headers)
        assert r.status_code == 200
        fixture_cid = None
        for item in r.json()["items"]:
            p = await client.get(f"/constituents/{item['id']}/profile", headers=staff_headers)
            assert p.status_code == 200
            profile = p.json()
            for key in child_keys:
                assert key in profile, f"missing child collection {key}"
            if profile["hostel_history"]:
                fixture_cid = item["id"]
                staff_profile = profile
                break
        if fixture_cid is None:
            pytest.skip("academic fixtures missing; run scripts/seed_academic.py first")

        # Staff: academic rows visible; SSAC withheld (admin-only), while
        # family is visible (staff holds people.read_family).
        assert len(staff_profile["academic_courses"]) >= 2
        assert len(staff_profile["semester_performance"]) >= 1
        assert staff_profile["ssac_records"] == []
        assert len(staff_profile["family_members"]) == 1

        # Admin (superuser): restricted rows visible.
        r = await client.get(f"/constituents/{fixture_cid}/profile", headers=admin_headers)
        assert r.status_code == 200
        admin_profile = r.json()
        assert len(admin_profile["ssac_records"]) == 1
        assert len(admin_profile["family_members"]) == 1


@pytest.mark.asyncio
async def test_profile_blocks_are_editable():
    """Every 360° profile block (except immutable Roll Number) has a write
    path: PATCH constituent/person/alumni/comms, POST contacts/addresses,
    and the generic T-table POST factory."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        r = await client.post(
            "/auth/login",
            data={"username": "staff@iitgn.ac.in", "password": "staff123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 401:
            pytest.skip("seed users missing; run scripts/seed_users.py first")
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = await client.get("/constituents?page_size=1", headers=h)
        cid = r.json()["items"][0]["id"]
        r = await client.get(f"/constituents/{cid}/profile", headers=h)
        before = r.json()
        orig_roll = (before["alumni_profile"] or {}).get("roll_no")
        orig_notes = before["constituent"]["notes"]

        # PATCH constituent block.
        r = await client.patch(
            f"/constituents/{cid}", json={"notes": "Test note"}, headers=h
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Test note"
        r = await client.patch(
            f"/constituents/{cid}", json={"status": "BOGUS"}, headers=h
        )
        assert r.status_code == 400
        r = await client.patch(
            "/constituents/00000000-0000-0000-0000-000000000000",
            json={"notes": "x"}, headers=h,
        )
        assert r.status_code == 404

        # PATCH person + alumni blocks; Roll Number has no write path.
        r = await client.patch(
            f"/constituents/{cid}/person",
            json={"spouse_name": "Test Spouse", "gender": "OTHER"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["spouse_name"] == "Test Spouse"
        r = await client.patch(
            f"/constituents/{cid}/person", json={"gender": "BOGUS"}, headers=h
        )
        assert r.status_code == 400
        r = await client.patch(
            f"/constituents/{cid}/alumni-profile",
            json={"thesis_title": "Test Thesis"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["thesis_title"] == "Test Thesis"
        assert r.json()["roll_no"] == orig_roll

        # POST contacts + addresses; PUT comms preferences.
        r = await client.post(
            f"/constituents/{cid}/contact-methods",
            json={"contact_type": "EMAIL_PERSONAL", "value": "Test@Example.com"},
            headers=h,
        )
        assert r.status_code == 201
        assert r.json()["normalised_value"] == "test@example.com"
        contact_id = r.json()["id"]
        r = await client.post(
            f"/constituents/{cid}/addresses",
            json={"address_type": "CURRENT", "line1": "Test Street 1",
                  "city": "Test City", "country": "India"},
            headers=h,
        )
        assert r.status_code == 201
        address_id = r.json()["id"]
        r = await client.put(
            f"/constituents/{cid}/communication-preferences",
            json={"email_opt_in": True, "whatsapp_opt_in": False,
                  "sms_opt_in": False, "global_dnc": True},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["global_dnc"] is True

        # Generic T-table factory: create, invalid enum rejected.
        r = await client.post(
            f"/constituents/{cid}/hostel-history",
            json={"hostel_name": "Test Hall", "room_number": "T-1"},
            headers=h,
        )
        assert r.status_code == 201
        hostel_id = r.json()["id"]
        r = await client.post(
            f"/constituents/{cid}/academic-courses",
            json={"programme_level": "UG", "course_code": "TS101"},
            headers=h,
        )
        assert r.status_code == 201
        course_id = r.json()["id"]
        r = await client.post(
            f"/constituents/{cid}/academic-courses",
            json={"programme_level": "SCHOOL", "course_code": "TS102"},
            headers=h,
        )
        assert r.status_code == 422

        # Restricted tables: staff (no ssac perm) refused; family allowed.
        r = await client.post(
            f"/constituents/{cid}/ssac-records",
            json={"incident_details": "Test"},
            headers=h,
        )
        assert r.status_code == 403
        r = await client.post(
            f"/constituents/{cid}/family-members",
            json={"name": "Test Kin", "relation": "Sibling"},
            headers=h,
        )
        assert r.status_code == 201
        family_id = r.json()["id"]

        # Writes refresh freshness and appear in the profile.
        r = await client.get(f"/constituents/{cid}/profile", headers=h)
        after = r.json()
        assert after["constituent"]["days_since_profile_update"] == 0
        assert any(e["id"] == hostel_id for e in after["hostel_history"])
        assert any(e["id"] == course_id for e in after["academic_courses"])
        assert any(e["id"] == family_id for e in after["family_members"])
        assert after["constituent"]["notes"] == "Test note"

        # Cleanup: restore notes/spouse/thesis/comms, delete created rows.
        from app.db.session import async_session_factory
        from app.models import (
            AcademicCourse,
            Address,
            AlumniProfile,
            CommunicationPreferences,
            ContactMethod,
            Constituent,
            FamilyMember,
            HostelHistory,
            Person,
        )
        from sqlalchemy import delete, select

        async with async_session_factory() as session:
            for model, rid in (
                (HostelHistory, hostel_id), (AcademicCourse, course_id),
                (ContactMethod, contact_id), (Address, address_id),
                (FamilyMember, family_id),
            ):
                await session.execute(delete(model).where(model.id == rid))
            result = await session.execute(
                select(Constituent).where(Constituent.id == cid)
            )
            constituent = result.scalars().first()
            constituent.notes = orig_notes
            result = await session.execute(
                select(Person).where(Person.constituent_id == cid)
            )
            person = result.scalars().first()
            person.spouse_name = None
            result = await session.execute(
                select(AlumniProfile).where(AlumniProfile.constituent_id == cid)
            )
            alumni = result.scalars().first()
            alumni.thesis_title = None
            result = await session.execute(
                select(CommunicationPreferences).where(
                    CommunicationPreferences.constituent_id == cid
                )
            )
            prefs = result.scalars().first()
            if prefs is not None:
                prefs.global_dnc = False
            await session.commit()


@pytest.mark.asyncio
async def test_profile_photos_lifecycle():
    """Multiple photos per profile: upload, ordered listing with primary
    first, byte serving gated by read permission, primary switch, delete
    with promotion, MIME/size validation, and write gating."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x00\x01\x00\x18\xfb\x03\x0b\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        async def login(email, password):
            r = await client.post(
                "/auth/login",
                data={"username": email, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.status_code == 401:
                pytest.skip("seed users missing; run scripts/seed_users.py first")
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        staff_headers = await login("staff@iitgn.ac.in", "staff123")
        r = await client.get("/constituents?page_size=1", headers=staff_headers)
        cid = r.json()["items"][0]["id"]

        # Upload two photos; first becomes primary.
        r = await client.post(
            f"/constituents/{cid}/photos",
            files=[
                ("files", ("one.png", png, "image/png")),
                ("files", ("two.png", png, "image/png")),
            ],
            headers=staff_headers,
        )
        assert r.status_code == 201
        assert len(r.json()) == 2
        first_id, second_id = r.json()[0]["id"], r.json()[1]["id"]
        assert r.json()[0]["is_primary"] is True

        # Profile lists both, primary first.
        r = await client.get(f"/constituents/{cid}/profile", headers=staff_headers)
        photos = r.json()["profile_photos"]
        assert [p["id"] for p in photos[:2]] == [first_id, second_id]

        # Byte serving requires auth and returns the stored bytes.
        r = await client.get(f"/constituents/{cid}/photos/{first_id}/content")
        assert r.status_code == 401
        r = await client.get(
            f"/constituents/{cid}/photos/{first_id}/content", headers=staff_headers
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/png"
        assert r.content == png

        # Switch primary, then delete it: the survivor is promoted.
        r = await client.patch(
            f"/constituents/{cid}/photos/{second_id}",
            json={"is_primary": True}, headers=staff_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_primary"] is True
        r = await client.delete(
            f"/constituents/{cid}/photos/{second_id}", headers=staff_headers
        )
        assert r.status_code == 204
        r = await client.get(f"/constituents/{cid}/profile", headers=staff_headers)
        remaining = r.json()["profile_photos"]
        assert [p["id"] for p in remaining] == [first_id]
        assert remaining[0]["is_primary"] is True

        # Validation: SVG and oversize rejected; viewer cannot upload.
        r = await client.post(
            f"/constituents/{cid}/photos",
            files=[("files", ("evil.svg", b"<svg/>", "image/svg+xml"))],
            headers=staff_headers,
        )
        assert r.status_code == 400
        r = await client.post(
            f"/constituents/{cid}/photos",
            files=[("files", ("big.png", b"x" * (5 * 1024 * 1024 + 1), "image/png"))],
            headers=staff_headers,
        )
        assert r.status_code == 413
        viewer_headers = await login("viewer@iitgn.ac.in", "viewer123")
        r = await client.post(
            f"/constituents/{cid}/photos",
            files=[("files", ("v.png", png, "image/png"))],
            headers=viewer_headers,
        )
        assert r.status_code == 403

        # Cleanup both photos.
        r = await client.delete(
            f"/constituents/{cid}/photos/{first_id}", headers=staff_headers
        )
        assert r.status_code == 204
        r = await client.delete(
            f"/constituents/{cid}/photos/{second_id}", headers=staff_headers
        )
        assert r.status_code == 204


@pytest.mark.asyncio
async def test_google_login_allowlists_email(monkeypatch):
    """Google sign-in mints a working session for allowlisted emails and
    refuses unknown emails — verified with a stubbed Google verifier."""
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")

    def fake_verify(id_token, request, audience=None):
        if id_token == "good-token":
            return {
                "email": "staff@iitgn.ac.in",
                "email_verified": True,
                "name": "CRM Staff User",
                "sub": "google-sub-1",
            }
        if id_token == "stranger-token":
            return {
                "email": "stranger@example.com",
                "email_verified": True,
                "name": "Stranger",
                "sub": "google-sub-2",
            }
        raise ValueError("bad token")

    import google.oauth2.id_token as google_id_token

    monkeypatch.setattr(google_id_token, "verify_oauth2_token", fake_verify)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        # Allowlisted email → session token that authorizes API access.
        r = await client.post("/auth/google", json={"id_token": "good-token"})
        if r.status_code == 401:
            pytest.skip("seed users missing; run scripts/seed_users.py first")
        assert r.status_code == 200
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        r = await client.get("/constituents?page_size=1", headers=headers)
        assert r.status_code == 200

        # Unknown email → 403, no session minted.
        r = await client.post("/auth/google", json={"id_token": "stranger-token"})
        assert r.status_code == 403

        # Forged token → rejected.
        r = await client.post("/auth/google", json={"id_token": "forged"})
        assert r.status_code == 401
