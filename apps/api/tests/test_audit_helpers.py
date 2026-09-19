from uuid import UUID

from starlette.requests import Request

from app.core.audit_middleware import (
    extract_actor_id,
    extract_entity_id,
    get_audit_action,
    get_entity_type,
)
from app.core.security import create_access_token


def test_audit_action_mapping():
    assert get_audit_action("GET", "/api/v1/constituents") == "LIST"
    assert get_audit_action("GET", "/api/v1/constituents/stale-profiles-count") == "STALE_COUNT"
    assert get_audit_action("GET", "/api/v1/constituents/stale-profiles") == "LIST_STALE"
    assert get_audit_action("GET", "/api/v1/constituents/organisations/search") == "SEARCH_ORG"
    cid = "12345678-1234-5678-1234-567812345678"
    assert get_audit_action("GET", f"/api/v1/constituents/{cid}/profile") == "READ_PROFILE"
    assert get_audit_action("POST", "/api/v1/constituents") == "WRITE"
    assert get_audit_action("GET", "/api/v1/health") is None
    assert get_audit_action("GET", "/api/v1/auth/me") is None


def test_entity_type_and_id():
    cid = "12345678-1234-5678-1234-567812345678"
    assert get_entity_type(f"/api/v1/constituents/{cid}/profile") == "constituent"
    assert get_entity_type("/api/v1/health") is None
    assert extract_entity_id(f"/api/v1/constituents/{cid}/profile") == UUID(cid)
    assert extract_entity_id("/api/v1/constituents/stale-profiles") is None
    assert extract_entity_id("/api/v1/constituents/organisations/search") is None


def _request_with_auth(header_value: str | None) -> Request:
    headers = []
    if header_value is not None:
        headers.append((b"authorization", header_value.encode()))
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


def test_extract_actor_id():
    token = create_access_token(
        subject=UUID("12345678-1234-5678-1234-567812345678"),
        roles=[],
        permissions=[],
    )
    assert extract_actor_id(_request_with_auth(f"Bearer {token}")) == UUID(
        "12345678-1234-5678-1234-567812345678"
    )
    assert extract_actor_id(_request_with_auth(None)) is None
    assert extract_actor_id(_request_with_auth("Bearer garbage")) is None
    assert extract_actor_id(_request_with_auth("Basic abc")) is None
