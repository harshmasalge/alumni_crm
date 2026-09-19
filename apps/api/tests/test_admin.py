"""Admin API tests against the real PostgreSQL database.

Covers server-side gating (non-admins get 403, never filtered client-side),
the email-allowlist user lifecycle (no passwords, ADR-003), duplicate and
unknown-reference handling, the last-superuser guard, and audit logging of
admin writes. Requires seeded dev data; skips cleanly otherwise.
"""

import uuid

import httpx
import pytest

from app.db.session import async_session_factory
from app.main import app


async def _db_reachable() -> bool:
    from sqlalchemy import text

    from app.db.session import engine

    try:
        await engine.dispose()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _login(client, email, password):
    r = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return r


@pytest.mark.asyncio
async def test_admin_endpoints():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        # Unauthenticated admin access is rejected.
        r = await client.get("/admin/users")
        assert r.status_code == 401

        r = await _login(client, "staff@iitgn.ac.in", "staff123")
        if r.status_code == 401:
            pytest.skip("seed users missing; run scripts/seed_users.py first")
        staff_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Staff lacks admin.users/admin.roles but holds admin.audit (seeded).
        r = await client.get("/admin/users", headers=staff_headers)
        assert r.status_code == 403
        r = await client.get("/admin/roles", headers=staff_headers)
        assert r.status_code == 403
        r = await client.get("/admin/audit-events?page_size=1", headers=staff_headers)
        assert r.status_code == 200

        r = await _login(client, "admin@iitgn.ac.in", "admin123")
        admin_headers = {
            "Authorization": f"Bearer {r.json()['access_token']}",
            "X-Request-ID": f"test-admin-{uuid.uuid4()}",
        }

        # Permission catalog + roles are readable.
        r = await client.get("/admin/permissions", headers=admin_headers)
        assert r.status_code == 200
        assert any(p["name"] == "constituents.read" for p in r.json())
        r = await client.get("/admin/roles", headers=admin_headers)
        assert r.status_code == 200
        roles = {x["name"]: x for x in r.json()}
        assert {"admin", "staff", "viewer", "finance"} <= set(roles)
        viewer_role_id = roles["viewer"]["id"]

        # Create an allowlist user (no password stored, ever).
        new_email = f"test.allow.{uuid.uuid4().hex[:8]}@iitgn.ac.in"
        r = await client.post(
            "/admin/users",
            json={"email": new_email, "full_name": "Test Allow", "role_ids": [viewer_role_id]},
            headers=admin_headers,
        )
        assert r.status_code == 201
        created = r.json()
        assert created["email"] == new_email
        assert created["roles"] == ["viewer"]
        assert "hashed_password" not in created
        new_id = created["id"]

        # Duplicate email is rejected.
        r = await client.post(
            "/admin/users",
            json={"email": new_email, "full_name": "Dupe"},
            headers=admin_headers,
        )
        assert r.status_code == 409

        # Unknown role ids are rejected.
        r = await client.post(
            "/admin/users",
            json={"email": f"bad.{uuid.uuid4().hex[:8]}@iitgn.ac.in", "full_name": "Bad",
                    "role_ids": ["00000000-0000-0000-0000-000000000000"]},
            headers=admin_headers,
        )
        assert r.status_code == 400

        # Deactivate + reactivate round-trip.
        r = await client.patch(
            f"/admin/users/{new_id}", json={"is_active": False}, headers=admin_headers
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        r = await client.patch(
            f"/admin/users/{new_id}", json={"is_active": True}, headers=admin_headers
        )
        assert r.json()["is_active"] is True

        # Last-superuser guard: find the seeded admin and try to demote it
        # only if it is the sole active superuser.
        r = await client.get("/admin/users?q=admin@iitgn.ac.in", headers=admin_headers)
        admins = [u for u in r.json()["items"] if u["is_superuser"] and u["is_active"]]
        if len(admins) == 1:
            r = await client.patch(
                f"/admin/users/{admins[0]['id']}", json={"is_superuser": False},
                headers=admin_headers,
            )
            assert r.status_code == 400
            r = await client.patch(
                f"/admin/users/{admins[0]['id']}", json={"is_active": False},
                headers=admin_headers,
            )
            assert r.status_code == 400

        # Role permission assignment round-trips and audits.
        staff_role_id = roles["staff"]["id"]
        staff_perms_before = sorted(roles["staff"]["permissions"])
        r = await client.get("/admin/permissions", headers=admin_headers)
        perm_by_name = {p["name"]: p["id"] for p in r.json()}
        subset = [perm_by_name["constituents.read"], perm_by_name["people.read"]]
        r = await client.put(
            f"/admin/roles/{staff_role_id}/permissions",
            json={"permission_ids": subset},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert sorted(r.json()["permissions"]) == ["constituents.read", "people.read"]
        # Restore.
        all_staff = [perm_by_name[n] for n in staff_perms_before]
        r = await client.put(
            f"/admin/roles/{staff_role_id}/permissions",
            json={"permission_ids": all_staff},
            headers=admin_headers,
        )
        assert r.status_code == 200
        # Unknown permission ids are rejected.
        r = await client.put(
            f"/admin/roles/{staff_role_id}/permissions",
            json={"permission_ids": ["00000000-0000-0000-0000-000000000000"]},
            headers=admin_headers,
        )
        assert r.status_code == 400

        # Audit log shows the admin writes from this run.
        r = await client.get(
            "/admin/audit-events?entity_type=user&page_size=50", headers=admin_headers
        )
        assert r.status_code == 200
        actions = {(e["entity_id"], e["action"]) for e in r.json()["items"]}
        assert (new_id, "CREATE") in actions
        assert (new_id, "UPDATE") in actions

        # Cleanup: deactivate the fixture user (rows stay for audit trail).
        r = await client.patch(
            f"/admin/users/{new_id}", json={"is_active": False}, headers=admin_headers
        )
        assert r.status_code == 200
