"""staff role: full read/write except user/role administration.

Revision ID: b81f5d3a90c2
Revises: 9c4e1a7f2d63
Create Date: 2026-09-18

Grants people.read_health, people.read_family, donors.read_finance, and
constituents.delete to the staff role. admin.users / admin.roles stay
admin-only; admin.audit (read-only) remains granted to staff.
Idempotent: safe to re-run.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b81f5d3a90c2'
down_revision: Union[str, None] = '9c4e1a7f2d63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STAFF_GRANTS = (
    'people.read_health',
    'people.read_family',
    'donors.read_finance',
    'constituents.delete',
)


def upgrade() -> None:
    for perm in STAFF_GRANTS:
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = 'staff' AND p.name = '%s' "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = p.id)" % perm
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE role_id IN "
        "(SELECT id FROM roles WHERE name = 'staff') AND permission_id IN "
        "(SELECT id FROM permissions WHERE name IN "
        "('people.read_health', 'people.read_family', "
        "'donors.read_finance', 'constituents.delete'))"
    )
