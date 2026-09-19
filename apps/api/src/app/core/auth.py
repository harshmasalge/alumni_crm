from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_token_subject
from app.db.session import get_db
from app.models import Permission, Role, RolePermission, User, UserRole


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = get_token_subject(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_user_roles(db: AsyncSession, user_id: UUID) -> list[str]:
    result = await db.execute(
        select(Role.name)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_user_permissions(db: AsyncSession, user_id: UUID) -> list[str]:
    result = await db.execute(
        select(Permission.name)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .join(UserRole, RolePermission.role_id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def check_constituents_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    permissions = await get_user_permissions(db, current_user.id)
    if "constituents.read" not in permissions and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: constituents.read required",
        )
    return current_user


async def check_constituents_write(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    permissions = await get_user_permissions(db, current_user.id)
    if "constituents.write" not in permissions and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: constituents.write required",
        )
    return current_user


async def _require_named_permission(
    db: AsyncSession, current_user: User, permission: str
) -> User:
    permissions = await get_user_permissions(db, current_user.id)
    if permission not in permissions and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission} required",
        )
    return current_user


async def check_groups_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.read")


async def check_groups_create(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.create")


async def check_groups_update(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.update")


async def check_groups_manage_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.manage_members")


async def check_groups_manage_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.manage_rules")


async def check_groups_approve(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.approve")


async def check_constituents_export(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "constituents.export")


async def check_groups_deactivate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "groups.deactivate")


async def check_admin_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "admin.users")


async def check_admin_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "admin.roles")


async def check_admin_audit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _require_named_permission(db, current_user, "admin.audit")


async def check_ssac_write(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    permissions = await get_user_permissions(db, current_user.id)
    if "ssac.read_restricted" not in permissions and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: ssac.read_restricted required",
        )
    return current_user


async def check_family_write(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    permissions = await get_user_permissions(db, current_user.id)
    if "people.read_family" not in permissions and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: people.read_family required",
        )
    return current_user


async def check_admin_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if current_user.is_superuser:
        return current_user
    roles = await get_user_roles(db, current_user.id)
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role denied: admin required",
        )
    return current_user


async def check_staff_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if current_user.is_superuser:
        return current_user
    roles = await get_user_roles(db, current_user.id)
    if not any(r in ("admin", "staff") for r in roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role denied: staff or admin required",
        )
    return current_user
