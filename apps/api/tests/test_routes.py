from app.main import app


def test_expected_paths_registered_once():
    spec = app.openapi()
    paths = sorted(spec["paths"].keys())
    expected = sorted(
        [
            "/api/v1/auth/login",
            "/api/v1/auth/google",
            "/api/v1/auth/me",
            "/api/v1/admin/users",
            "/api/v1/admin/users/{user_id}",
            "/api/v1/admin/users/{user_id}/roles",
            "/api/v1/admin/roles",
            "/api/v1/admin/roles/{role_id}/permissions",
            "/api/v1/admin/permissions",
            "/api/v1/admin/audit-events",
            "/api/v1/constituents",
            "/api/v1/constituents/organisations/search",
            "/api/v1/constituents/stale-profiles",
            "/api/v1/constituents/stale-profiles-count",
            "/api/v1/constituents/{constituent_id}/affiliations",
            "/api/v1/constituents/{constituent_id}/education",
            "/api/v1/constituents/{constituent_id}/profile",
            "/api/v1/health",
            "/api/v1/health/ready",
        ]
    )
    for p in expected:
        assert p in paths, f"missing route {p}"
    # No double-prefix regressions from router composition.
    assert "/api/v1/auth/auth/login" not in paths
    assert "/api/v1/constituents/constituents" not in paths
