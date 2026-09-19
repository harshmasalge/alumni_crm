#!/usr/bin/env python
"""
Seed script to create test users with roles and permissions.
Run after migrations: python scripts/seed_users.py

DEV ONLY (see ADR-003): seeded password accounts are for local
development. Production uses Sign in with Google; never create
password accounts there.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.models import (
    Constituent, ConstituentKind, ConstituentStatus,
    User, Role, Permission, UserRole, RolePermission,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def seed():
    async with async_session_factory() as session:
        # Create permissions
        permissions = [
            # Constituent permissions
            Permission(name="constituents.read", module="constituents", action="read", description="Read constituents"),
            Permission(name="constituents.write", module="constituents", action="write", description="Create/update constituents"),
            Permission(name="constituents.delete", module="constituents", action="delete", description="Delete constituents"),
            Permission(name="constituents.read_internal", module="constituents", action="read_internal", description="Read internal notes"),
            # People permissions
            Permission(name="people.read", module="people", action="read", description="Read people"),
            Permission(name="people.write", module="people", action="write", description="Create/update people"),
            Permission(name="people.read_demographics", module="people", action="read_demographics", description="Read demographics"),
            Permission(name="people.read_health", module="people", action="read_health", description="Read health info"),
            Permission(name="people.read_family", module="people", action="read_family", description="Read family info"),
            # Alumni permissions
            Permission(name="alumni.read", module="alumni", action="read", description="Read alumni profiles"),
            Permission(name="alumni.write", module="alumni", action="write", description="Create/update alumni profiles"),
            Permission(name="alumni.read_academic", module="alumni", action="read_academic", description="Read academic records"),
            # Donor permissions
            Permission(name="donors.read", module="donors", action="read", description="Read donor profiles"),
            Permission(name="donors.write", module="donors", action="write", description="Create/update donor profiles"),
            Permission(name="donors.read_finance", module="donors", action="read_finance", description="Read financial info"),
            # Contact permissions
            Permission(name="contacts.read", module="contacts", action="read", description="Read contact methods"),
            Permission(name="contacts.write", module="contacts", action="write", description="Create/update contact methods"),
            Permission(name="contacts.read_pii", module="contacts", action="read_pii", description="Read PII in contacts"),
            # Address permissions
            Permission(name="addresses.read", module="addresses", action="read", description="Read addresses"),
            Permission(name="addresses.write", module="addresses", action="write", description="Create/update addresses"),
            Permission(name="addresses.read_pii", module="addresses", action="read_pii", description="Read PII in addresses"),
            # Education permissions
            Permission(name="education.read", module="education", action="read", description="Read education records"),
            Permission(name="education.write", module="education", action="write", description="Create/update education records"),
            # Affiliation permissions
            Permission(name="affiliations.read", module="affiliations", action="read", description="Read affiliations"),
            Permission(name="affiliations.write", module="affiliations", action="write", description="Create/update affiliations"),
            # Files permissions
            Permission(name="files.read", module="files", action="read", description="Read files"),
            Permission(name="files.write", module="files", action="write", description="Upload files"),
            # Admin permissions
            Permission(name="admin.users", module="admin", action="users", description="Manage users"),
            Permission(name="admin.roles", module="admin", action="roles", description="Manage roles"),
            Permission(name="admin.audit", module="admin", action="audit", description="View audit logs"),
            # Restricted records (admin role only via the admin-gets-all grant below)
            Permission(name="ssac.read_restricted", module="ssac", action="read_restricted", description="Read student conduct records (restricted)"),
        ]

        for perm in permissions:
            session.add(perm)
        await session.flush()

        # Create roles
        admin_role = Role(name="admin", description="Full administrative access")
        staff_role = Role(name="staff", description="CRM staff with read/write access")
        viewer_role = Role(name="viewer", description="Read-only access to non-sensitive data")
        finance_role = Role(name="finance", description="Finance team with donor finance access")

        session.add_all([admin_role, staff_role, viewer_role, finance_role])
        await session.flush()

        # Assign permissions to roles
        # Admin gets all permissions
        all_perms = {p.name: p for p in permissions}
        for perm in permissions:
            session.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

        # Staff gets full read/write on everything except user/role
        # administration (admin.users, admin.roles stay admin-only).
        # admin.audit (read-only log viewing) is intentionally included.
        staff_perms = [
            "constituents.read", "constituents.write", "constituents.delete",
            "constituents.read_internal",
            "people.read", "people.write", "people.read_demographics",
            "people.read_health", "people.read_family",
            "alumni.read", "alumni.write", "alumni.read_academic",
            "donors.read", "donors.write", "donors.read_finance",
            "contacts.read", "contacts.write", "contacts.read_pii",
            "addresses.read", "addresses.write", "addresses.read_pii",
            "education.read", "education.write",
            "affiliations.read", "affiliations.write",
            "files.read", "files.write",
            "admin.audit",
        ]
        for perm_name in staff_perms:
            session.add(RolePermission(role_id=staff_role.id, permission_id=all_perms[perm_name].id))

        # Viewer gets read-only
        viewer_perms = [
            "constituents.read",
            "people.read",
            "alumni.read",
            "donors.read",
            "contacts.read",
            "addresses.read",
            "education.read",
            "affiliations.read",
            "files.read",
        ]
        for perm_name in viewer_perms:
            session.add(RolePermission(role_id=viewer_role.id, permission_id=all_perms[perm_name].id))

        # Finance gets donor finance access
        finance_perms = [
            "constituents.read",
            "donors.read", "donors.write", "donors.read_finance",
            "contacts.read",
            "addresses.read",
            "admin.audit",
        ]
        for perm_name in finance_perms:
            session.add(RolePermission(role_id=finance_role.id, permission_id=all_perms[perm_name].id))

        await session.flush()

        # Create test users
        admin_user = User(
            email="admin@iitgn.ac.in",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_superuser=True,
        )
        staff_user = User(
            email="staff@iitgn.ac.in",
            full_name="CRM Staff User",
            hashed_password=get_password_hash("staff123"),
            is_active=True,
            is_superuser=False,
        )
        viewer_user = User(
            email="viewer@iitgn.ac.in",
            full_name="Read-only Viewer",
            hashed_password=get_password_hash("viewer123"),
            is_active=True,
            is_superuser=False,
        )
        finance_user = User(
            email="finance@iitgn.ac.in",
            full_name="Finance Team Member",
            hashed_password=get_password_hash("finance123"),
            is_active=True,
            is_superuser=False,
        )

        session.add_all([admin_user, staff_user, viewer_user, finance_user])
        await session.flush()

        # Assign roles
        session.add_all([
            UserRole(user_id=admin_user.id, role_id=admin_role.id),
            UserRole(user_id=staff_user.id, role_id=staff_role.id),
            UserRole(user_id=viewer_user.id, role_id=viewer_role.id),
            UserRole(user_id=finance_user.id, role_id=finance_role.id),
        ])

        await session.commit()
        print("Seeded test users, roles, and permissions")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())