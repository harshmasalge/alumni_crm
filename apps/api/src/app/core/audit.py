"""Explicit audit logging for write endpoints.

The audit middleware covers constituent reads automatically; admin writes
(users, roles) call log_audit() directly so the actor, entity, and
before/after states are recorded even though those paths bypass the
constituent-focused middleware mapping.
"""

import json
from typing import Any, Optional
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, User


def _request_meta(request: Optional[Request]) -> tuple[Optional[str], Optional[str]]:
    if request is None:
        return None, None
    ip = request.client.host if request.client else None
    return ip, request.headers.get("x-request-id")


async def log_audit(
    db: AsyncSession,
    *,
    actor: Optional[User],
    entity_type: str,
    entity_id: UUID,
    action: str,
    before: Optional[Any] = None,
    after: Optional[Any] = None,
    constituent_id: Optional[UUID] = None,
    request: Optional[Request] = None,
) -> None:
    ip_address, request_id = _request_meta(request)
    db.add(
        AuditEvent(
            constituent_id=constituent_id,
            actor_id=actor.id if actor else None,
            actor_type="user" if actor else "system",
            ip_address=ip_address,
            request_id=request_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before_state=json.dumps(before, default=str) if before is not None else None,
            after_state=json.dumps(after, default=str) if after is not None else None,
        )
    )
