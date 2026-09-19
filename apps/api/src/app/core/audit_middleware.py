import json
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import get_token_subject
from app.db.session import async_session_factory
from app.models import AuditEvent


NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")


def get_audit_action(method: str, path: str) -> Optional[str]:
    """Map read endpoints to audit actions. Exact matches first, then patterns."""
    if method == "GET" and path == "/api/v1/constituents":
        return "LIST"
    if method == "GET" and path == "/api/v1/constituents/stale-profiles-count":
        return "STALE_COUNT"
    if method == "GET" and path == "/api/v1/constituents/stale-profiles":
        return "LIST_STALE"
    if method == "GET" and path == "/api/v1/constituents/organisations/search":
        return "SEARCH_ORG"
    if method == "GET" and path.startswith("/api/v1/constituents/") and path.endswith("/profile"):
        return "READ_PROFILE"
    if method in ("POST", "PATCH", "PUT", "DELETE") and path.startswith("/api/v1/constituents"):
        return "WRITE"
    return None


def get_entity_type(path: str) -> Optional[str]:
    if path.startswith("/api/v1/constituents"):
        return "constituent"
    return None


def extract_entity_id(path: str) -> Optional[UUID]:
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "constituents" and i + 1 < len(parts):
            try:
                return UUID(parts[i + 1])
            except ValueError:
                continue
    return None


def extract_actor_id(request: Request) -> Optional[UUID]:
    """Attribute the actor from the Bearer token without touching the DB.

    Auth dependencies enforce access; the middleware only records who acted.
    Never consume the request body here so downstream handlers still see it.
    """
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return get_token_subject(token.strip())


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        action = get_audit_action(method, path)
        entity_type = get_entity_type(path)
        if not action or not entity_type:
            return await call_next(request)

        entity_id = extract_entity_id(path)
        actor_id = extract_actor_id(request)

        ip_address = request.client.host if request.client else None
        request_id = request.headers.get("x-request-id")

        response = await call_next(request)

        if response.status_code >= 400:
            return response

        async with async_session_factory() as db:
            try:
                audit = AuditEvent(
                    constituent_id=entity_id if entity_type == "constituent" else None,
                    actor_id=actor_id,
                    actor_type="user" if actor_id else "anonymous",
                    ip_address=ip_address,
                    request_id=request_id,
                    entity_type=entity_type,
                    entity_id=entity_id or NIL_UUID,
                    action=action,
                    before_state=json.dumps({"method": method, "path": path}),
                    after_state=None,
                )
                db.add(audit)
                await db.commit()
            except Exception:
                pass

        return response
