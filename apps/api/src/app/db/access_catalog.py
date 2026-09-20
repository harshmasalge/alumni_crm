"""Canonical access catalog: permissions, roles, and role grants.

Single source of truth shared by the local dev seed (`scripts/seed_users.py`)
and the demo bootstrap (`app.db.demo_bootstrap`). Add a new permission here
once and both paths stay in sync; the bootstrap upserts by name so deploys
pick up additions automatically.
"""

PERMISSIONS: list[tuple[str, str, str, str]] = [
    # Layout per entry below: name, module, action, description.
    ("constituents.read", "constituents", "read", "Read constituents"),
    (
        "constituents.export",
        "constituents",
        "export",
        "Generate bulk XLSX exports of people populations",
    ),
    ("constituents.write", "constituents", "write", "Create/update constituents"),
    ("constituents.delete", "constituents", "delete", "Delete constituents"),
    (
        "constituents.read_internal",
        "constituents",
        "read_internal",
        "Read internal notes",
    ),
    ("people.read", "people", "read", "Read people"),
    ("people.write", "people", "write", "Create/update people"),
    (
        "people.read_demographics",
        "people",
        "read_demographics",
        "Read demographics",
    ),
    ("people.read_health", "people", "read_health", "Read health info"),
    ("people.read_family", "people", "read_family", "Read family info"),
    ("alumni.read", "alumni", "read", "Read alumni profiles"),
    ("alumni.write", "alumni", "write", "Create/update alumni profiles"),
    (
        "alumni.read_academic",
        "alumni",
        "read_academic",
        "Read academic records",
    ),
    ("donors.read", "donors", "read", "Read donor profiles"),
    ("donors.write", "donors", "write", "Create/update donor profiles"),
    (
        "donors.read_finance",
        "donors",
        "read_finance",
        "Read financial info",
    ),
    ("contacts.read", "contacts", "read", "Read contact methods"),
    (
        "contacts.write",
        "contacts",
        "write",
        "Create/update contact methods",
    ),
    (
        "contacts.read_pii",
        "contacts",
        "read_pii",
        "Read PII in contacts",
    ),
    ("addresses.read", "addresses", "read", "Read addresses"),
    (
        "addresses.write",
        "addresses",
        "write",
        "Create/update addresses",
    ),
    (
        "addresses.read_pii",
        "addresses",
        "read_pii",
        "Read PII in addresses",
    ),
    ("education.read", "education", "read", "Read education records"),
    (
        "education.write",
        "education",
        "write",
        "Create/update education records",
    ),
    ("affiliations.read", "affiliations", "read", "Read affiliations"),
    (
        "affiliations.write",
        "affiliations",
        "write",
        "Create/update affiliations",
    ),
    ("files.read", "files", "read", "Read files"),
    ("files.write", "files", "write", "Upload files"),
    ("admin.users", "admin", "users", "Manage users"),
    ("admin.roles", "admin", "roles", "Manage roles"),
    ("admin.audit", "admin", "audit", "View audit logs"),
    (
        "ssac.read_restricted",
        "ssac",
        "read_restricted",
        "Read student conduct records (restricted)",
    ),
    ("groups.read", "groups", "read", "Read groups and memberships"),
    ("groups.create", "groups", "create", "Create groups"),
    ("groups.update", "groups", "update", "Edit group name/description"),
    (
        "groups.manage_members",
        "groups",
        "manage_members",
        "Add/remove manual-group members",
    ),
    (
        "groups.manage_rules",
        "groups",
        "manage_rules",
        "Propose rule changes",
    ),
    (
        "groups.approve",
        "groups",
        "approve",
        "Approve rules and membership proposals",
    ),
    (
        "groups.deactivate",
        "groups",
        "deactivate",
        "Deactivate/reactivate groups",
    ),
]

ROLES: list[tuple[str, str]] = [
    ("admin", "Full administrative access"),
    ("staff", "CRM staff with read/write access"),
    ("viewer", "Read-only access to non-sensitive data"),
    ("finance", "Finance team with donor finance access"),
]

# Staff gets full read/write on everything except user/role administration
# (admin.users, admin.roles stay admin-only). admin.audit (read-only log
# viewing) is intentionally included.
STAFF_PERMS: list[str] = [
    "constituents.read",
    "constituents.export",
    "constituents.write",
    "constituents.delete",
    "constituents.read_internal",
    "people.read",
    "people.write",
    "people.read_demographics",
    "people.read_health",
    "people.read_family",
    "alumni.read",
    "alumni.write",
    "alumni.read_academic",
    "donors.read",
    "donors.write",
    "donors.read_finance",
    "contacts.read",
    "contacts.write",
    "contacts.read_pii",
    "addresses.read",
    "addresses.write",
    "addresses.read_pii",
    "education.read",
    "education.write",
    "affiliations.read",
    "affiliations.write",
    "files.read",
    "files.write",
    "admin.audit",
    "groups.read",
    "groups.create",
    "groups.update",
    "groups.manage_members",
    "groups.manage_rules",
    "groups.approve",
    "groups.deactivate",
]

VIEWER_PERMS: list[str] = [
    "constituents.read",
    "people.read",
    "alumni.read",
    "donors.read",
    "contacts.read",
    "addresses.read",
    "education.read",
    "affiliations.read",
    "files.read",
    "groups.read",
]

FINANCE_PERMS: list[str] = [
    "constituents.read",
    "donors.read",
    "donors.write",
    "donors.read_finance",
    "contacts.read",
    "addresses.read",
    "admin.audit",
]

# Admin holds every permission ("*" = all of PERMISSIONS). Other roles map to
# their explicit grant lists above.
ROLE_PERMS: dict[str, list[str]] = {
    "admin": ["*"],
    "staff": STAFF_PERMS,
    "viewer": VIEWER_PERMS,
    "finance": FINANCE_PERMS,
}

# Demo accounts (fictional people). Passwords are never stored here — the
# demo bootstrap hashes settings.demo_password at boot time.
DEMO_USERS: list[tuple[str, str, str, bool]] = [
    # Layout per entry below: email, full_name, role, is_superuser.
    ("admin@iitgn.ac.in", "System Administrator", "admin", True),
    ("staff@iitgn.ac.in", "CRM Staff User", "staff", False),
    ("viewer@iitgn.ac.in", "Read-only Viewer", "viewer", False),
    ("finance@iitgn.ac.in", "Finance Team Member", "finance", False),
]
