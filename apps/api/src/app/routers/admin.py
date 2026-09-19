"""Administration API (M1 completion, not M7).

Admin-gated management of the email-allowlist users, roles, permissions,
and the audit log. Per ADR-003, creating a user only registers their email
plus roles — no password is ever stored. Every write is explicitly audited.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_audit
from app.core.auth import (
    check_admin_audit,
    check_admin_roles,
    check_admin_users,
)
from app.db.session import get_db
from app.models import (
    AuditEvent,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.schemas import (
    AdminAuditListResponse,
    AdminPermissionResponse,
    AdminRoleCreate,
    AdminRolePermissionsUpdate,
    AdminRoleResponse,
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserRolesUpdate,
    AdminUserUpdate,
    AuditEventResponse,
)

router = APIRouter(tags=["admin"])


def _user_to_response(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=sorted(r.name for r in user.roles),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _role_to_response(role: Role) -> AdminRoleResponse:
    return AdminRoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=sorted(p.name for p in role.permissions),
        created_at=role.created_at,
    )


async def _active_superuser_count(db: AsyncSession, exclude_user_id: Optional[UUID] = None) -> int:
    query = select(func.count(User.id)).where(
        User.is_active.is_(True), User.is_superuser.is_(True)
    )
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def _get_user_or_404(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return user


async def _reload_user(db: AsyncSession, user_id: UUID) -> User:
    """Re-fetch after commit so response building never touches expired
    attributes outside the async greenlet context."""
    db.expunge_all()
    return await _get_user_or_404(db, user_id)


async def _reload_role(db: AsyncSession, role_id: UUID) -> Role:
    db.expunge_all()
    return await _get_role_or_404(db, role_id)


async def _get_role_or_404(db: AsyncSession, role_id: UUID) -> Role:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    )
    role = result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id {role_id} not found",
        )
    return role


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Partial email or name match"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_users),
) -> AdminUserListResponse:
    query = select(User).options(selectinload(User.roles))
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.where(
            (User.email.ilike(term)) | (User.full_name.ilike(term))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(User.email).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(query)).scalars().all()

    return AdminUserListResponse(
        items=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_users),
) -> AdminUserResponse:
    email = payload.email.strip().lower()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {email} already exists",
        )

    roles = []
    if payload.role_ids:
        result = await db.execute(select(Role).where(Role.id.in_(payload.role_ids)))
        roles = list(result.scalars().all())
        if len(roles) != len(set(payload.role_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more role_ids do not exist",
            )

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=None,
        is_active=True,
        is_superuser=payload.is_superuser,
    )
    db.add(user)
    await db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id, assigned_by=current_user.id))
    await log_audit(
        db,
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        action="CREATE",
        after={"email": email, "roles": [r.name for r in roles]},
        request=request,
    )
    await db.commit()
    user = await _reload_user(db, user.id)
    return _user_to_response(user)


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_users),
) -> AdminUserResponse:
    return _user_to_response(await _get_user_or_404(db, user_id))


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_users),
) -> AdminUserResponse:
    user = await _get_user_or_404(db, user_id)
    before = {"full_name": user.full_name, "is_active": user.is_active,
              "is_superuser": user.is_superuser}

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.is_active is False and user.is_superuser:
        if await _active_superuser_count(db, exclude_user_id=user.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active superuser",
            )
        user.is_active = False
    elif payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_superuser is False and user.is_superuser:
        if await _active_superuser_count(db, exclude_user_id=user.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove superuser from the last active superuser",
            )
        user.is_superuser = False
    elif payload.is_superuser is not None:
        user.is_superuser = payload.is_superuser

    await log_audit(
        db,
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        action="UPDATE",
        before=before,
        after={"full_name": user.full_name, "is_active": user.is_active,
               "is_superuser": user.is_superuser},
        request=request,
    )
    await db.commit()
    user = await _reload_user(db, user.id)
    return _user_to_response(user)


@router.put("/users/{user_id}/roles", response_model=AdminUserResponse)
async def set_user_roles(
    user_id: UUID,
    payload: AdminUserRolesUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_users),
) -> AdminUserResponse:
    user = await _get_user_or_404(db, user_id)
    before = sorted(r.name for r in user.roles)

    result = await db.execute(select(Role).where(Role.id.in_(payload.role_ids)))
    roles = list(result.scalars().all())
    if len(roles) != len(set(payload.role_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more role_ids do not exist",
        )

    for existing in list(user.roles):
        user.roles.remove(existing)
    for role in roles:
        user.roles.append(role)

    await log_audit(
        db,
        actor=current_user,
        entity_type="user",
        entity_id=user.id,
        action="ROLES",
        before={"roles": before},
        after={"roles": sorted(r.name for r in roles)},
        request=request,
    )
    await db.commit()
    user = await _reload_user(db, user.id)
    return _user_to_response(user)


@router.get("/roles", response_model=list[AdminRoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_roles),
) -> list[AdminRoleResponse]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
    )
    return [_role_to_response(r) for r in result.scalars().all()]


@router.post("/roles", response_model=AdminRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: AdminRoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_roles),
) -> AdminRoleResponse:
    name = payload.name.strip().lower()
    existing = await db.execute(select(Role).where(Role.name == name))
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Role {name} already exists",
        )
    role = Role(name=name, description=(payload.description or None))
    db.add(role)
    await db.flush()
    await log_audit(
        db,
        actor=current_user,
        entity_type="role",
        entity_id=role.id,
        action="CREATE",
        after={"name": name},
        request=request,
    )
    await db.commit()
    role = await _reload_role(db, role.id)
    return _role_to_response(role)


@router.put("/roles/{role_id}/permissions", response_model=AdminRoleResponse)
async def set_role_permissions(
    role_id: UUID,
    payload: AdminRolePermissionsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_roles),
) -> AdminRoleResponse:
    role = await _get_role_or_404(db, role_id)
    before = sorted(p.name for p in role.permissions)

    result = await db.execute(select(Permission).where(Permission.id.in_(payload.permission_ids)))
    permissions = list(result.scalars().all())
    if len(permissions) != len(set(payload.permission_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more permission_ids do not exist",
        )

    for existing in list(role.permissions):
        role.permissions.remove(existing)
    for perm in permissions:
        role.permissions.append(perm)

    await log_audit(
        db,
        actor=current_user,
        entity_type="role",
        entity_id=role.id,
        action="PERMISSIONS",
        before={"permissions": before},
        after={"permissions": sorted(p.name for p in permissions)},
        request=request,
    )
    await db.commit()
    role = await _reload_role(db, role.id)
    return _role_to_response(role)


@router.get("/permissions", response_model=list[AdminPermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_roles),
) -> list[AdminPermissionResponse]:
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.name))
    return [AdminPermissionResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/audit-events", response_model=AdminAuditListResponse)
async def list_audit_events(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    actor_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_audit),
) -> AdminAuditListResponse:
    query = select(AuditEvent)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if action:
        query = query.where(AuditEvent.action == action)
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(AuditEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    events = (await db.execute(query)).scalars().all()

    return AdminAuditListResponse(
        items=[AuditEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
