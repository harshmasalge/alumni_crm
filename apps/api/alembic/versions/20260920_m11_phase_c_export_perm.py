"""M1.1 Phase C — bulk-export permission (no schema change; exports stateless).

Revision ID: c1a91c4d88e2
Revises: b1a91c4d77e2
Create Date: 2026-09-20

Adds `constituents.export` (bulk XLSX generation). Grants: admin + staff.
Viewer/finance intentionally excluded: bulk PII extraction is riskier than
single-profile reads, and finance coverage arrives with the M2 ledger if
needed. Field-level restrictions still apply inside exports via the
unchanged FieldPermissionChecker. See ADR-007.
Idempotent: safe to re-run.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c1a91c4d88e2'
down_revision: Union[str, None] = 'b1a91c4d77e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO permissions (id, name, description, module, action) "
        "VALUES (gen_random_uuid(), 'constituents.export', "
        "'Generate bulk XLSX exports of people populations', 'constituents', 'export') "
        "ON CONFLICT (name) DO NOTHING"
    )
    for role in ('admin', 'staff'):
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = '%s' AND p.name = 'constituents.export' "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = p.id)" % role
        )


def downgrade() -> None:
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE name = 'constituents.export')"
    )
    op.execute("DELETE FROM permissions WHERE name = 'constituents.export'")
