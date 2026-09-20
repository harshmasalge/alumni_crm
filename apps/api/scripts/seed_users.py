#!/usr/bin/env python
"""
Seed script to create test users with roles and permissions.
Run after migrations: python scripts/seed_users.py

DEV ONLY (see ADR-003): seeded password accounts are for local
development. Production uses Sign in with Google; never create
password accounts there.

Permission/role definitions live in app.db.access_catalog (shared with
the demo bootstrap); this script only applies them to a local database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.access_catalog import DEMO_USERS, PERMISSIONS, ROLE_PERMS, ROLES
from app.db.session import async_session_factory
from app.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


async def seed(passwords: dict[str, str] | None = None):
    passwords = passwords or {
        "admin@iitgn.ac.in": "admin123",
        "staff@iitgn.ac.in": "staff123",
        "viewer@iitgn.ac.in": "viewer123",
        "finance@iitgn.ac.in": "finance123",
    }
    async with async_session_factory() as session:
        for name, module, action, description in PERMISSIONS:
            session.add(
                Permission(
                    name=name, module=module, action=action, description=description
                )
            )
        await session.flush()

        roles: dict[str, Role] = {}
        for name, description in ROLES:
            role = Role(name=name, description=description)
            session.add(role)
            roles[name] = role
        await session.flush()

        perm_rows = (await session.execute(select(Permission))).scalars().all()
        perm_by_name = {p.name: p for p in perm_rows}
        for role_name, perm_names in ROLE_PERMS.items():
            granted = (
                list(perm_by_name.values())
                if perm_names == ["*"]
                else [perm_by_name[n] for n in perm_names]
            )
            for perm in granted:
                session.add(
                    RolePermission(
                        role_id=roles[role_name].id, permission_id=perm.id
                    )
                )
        await session.flush()

        users: dict[str, User] = {}
        for email, full_name, _role, is_superuser in DEMO_USERS:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=get_password_hash(passwords[email]),
                is_active=True,
                is_superuser=is_superuser,
            )
            session.add(user)
            users[email] = user
        await session.flush()

        for email, _full_name, role_name, _super in DEMO_USERS:
            session.add(
                UserRole(user_id=users[email].id, role_id=roles[role_name].id)
            )

        await session.commit()
        print("Seeded test users, roles, and permissions")


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed())
