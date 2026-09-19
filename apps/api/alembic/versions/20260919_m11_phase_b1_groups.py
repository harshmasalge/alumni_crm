"""M1.1 Phase B1 — groups domain foundation (backend only, no UI).

Revision ID: b1a91c4d77e2
Revises: f3a91c4d55e2
Create Date: 2026-09-19

Tables (see ADR-006):
- groups: managed populations (MANUAL / RULE_BASED, ACTIVE / DEACTIVATED).
  Name is unique. No hard delete — lifecycle is deactivation.
- group_memberships: current-state rows; UNIQUE(group_id, constituent_id)
  makes adds idempotent. Removals delete the row (audited); history lives
  in audit_events, not here.
- group_rule_versions: append-only filter-tree snapshots (JSON). Statuses
  PENDING / ACTIVE / SUPERSEDED / REJECTED. Partial unique indexes enforce
  at most one ACTIVE and at most one PENDING version per group; the
  application treats any violation as 409/500-safe conflicts.
- group_membership_proposals: governed deltas bound to the evaluated rule
  version, with stored reason snapshots, proposer/evaluator/approver
  identities, and applied_at. Approval is valid only while the bound
  version is still the group's ACTIVE version (optimistic check, no locks).

Permissions (existing seed + migration-grant convention):
- groups.read/create/update/manage_members/manage_rules/approve/deactivate.
- Grants: admin ← all; staff ← all (four-eyes still enforced per-actor:
  proposer ≠ approver, no bypass in B1); viewer ← read-only.
Idempotent: safe to re-run.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1a91c4d77e2'
down_revision: Union[str, None] = 'f3a91c4d55e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GROUP_PERMISSIONS = (
    ('groups.read', 'groups', 'read', 'Read groups and memberships'),
    ('groups.create', 'groups', 'create', 'Create groups'),
    ('groups.update', 'groups', 'update', 'Edit group name/description'),
    ('groups.manage_members', 'groups', 'manage_members', 'Add/remove manual-group members'),
    ('groups.manage_rules', 'groups', 'manage_rules', 'Propose rule changes'),
    ('groups.approve', 'groups', 'approve', 'Approve rules and membership proposals'),
    ('groups.deactivate', 'groups', 'deactivate', 'Deactivate/reactivate groups'),
)

STAFF_GROUP_GRANTS = (
    'groups.read',
    'groups.create',
    'groups.update',
    'groups.manage_members',
    'groups.manage_rules',
    'groups.approve',
    'groups.deactivate',
)


def upgrade() -> None:
    group_type = sa.Enum('MANUAL', 'RULE_BASED', name='grouptype')
    group_status = sa.Enum('ACTIVE', 'DEACTIVATED', name='groupstatus')
    rule_status = sa.Enum('PENDING', 'ACTIVE', 'SUPERSEDED', 'REJECTED', name='ruleversionstatus')
    proposal_action = sa.Enum('ADD', 'REMOVE', name='proposalaction')
    proposal_status = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='proposalstatus')

    op.create_table(
        'groups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', group_type, nullable=False),
        sa.Column('status', group_status, nullable=False, server_default='ACTIVE'),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_groups_name'),
    )
    op.create_index('ix_groups_type_status', 'groups', ['type', 'status'])

    op.create_table(
        'group_memberships',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('constituent_id', sa.Uuid(), nullable=False),
        sa.Column('added_by', sa.Uuid(), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'constituent_id', name='uq_group_membership'),
    )
    op.create_index('ix_group_memberships_group', 'group_memberships', ['group_id'])
    op.create_index('ix_group_memberships_constituent', 'group_memberships', ['constituent_id'])

    op.create_table(
        'group_rule_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('filter_tree', sa.JSON(), nullable=False),
        sa.Column('status', rule_status, nullable=False, server_default='PENDING'),
        sa.Column('proposed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'version_number', name='uq_group_rule_version'),
    )
    op.create_index('ix_group_rule_versions_group', 'group_rule_versions', ['group_id'])
    # At most one ACTIVE and at most one PENDING version per group.
    op.execute(
        "CREATE UNIQUE INDEX uq_group_rule_active "
        "ON group_rule_versions (group_id) WHERE status = 'ACTIVE'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_group_rule_pending "
        "ON group_rule_versions (group_id) WHERE status = 'PENDING'"
    )

    op.create_table(
        'group_membership_proposals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('group_id', sa.Uuid(), nullable=False),
        sa.Column('rule_version_id', sa.Uuid(), nullable=False),
        sa.Column('constituent_id', sa.Uuid(), nullable=False),
        sa.Column('action', proposal_action, nullable=False),
        sa.Column('reason_summary', sa.Text(), nullable=False),
        sa.Column('reason_detail', sa.Text(), nullable=True),
        sa.Column('status', proposal_status, nullable=False, server_default='PENDING'),
        sa.Column('evaluated_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_version_id'], ['group_rule_versions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_group_proposals_group_status', 'group_membership_proposals', ['group_id', 'status'])
    op.create_index('ix_group_proposals_version', 'group_membership_proposals', ['rule_version_id'])

    for name, module, action, description in GROUP_PERMISSIONS:
        op.execute(
            "INSERT INTO permissions (id, name, description, module, action) "
            "VALUES (gen_random_uuid(), '%s', '%s', '%s', '%s') "
            "ON CONFLICT (name) DO NOTHING" % (name, description, module, action)
        )
    for perm in STAFF_GROUP_GRANTS:
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = 'staff' AND p.name = '%s' "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = p.id)" % perm
        )
    for perm in STAFF_GROUP_GRANTS:
        op.execute(
            "INSERT INTO role_permissions (role_id, permission_id) "
            "SELECT r.id, p.id FROM roles r, permissions p "
            "WHERE r.name = 'admin' AND p.name = '%s' "
            "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = p.id)" % perm
        )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'viewer' AND p.name = 'groups.read' "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
        "WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
    )


def _drop_enums() -> None:
    for name in ('proposalstatus', 'proposalaction', 'ruleversionstatus', 'groupstatus', 'grouptype'):
        op.execute(f"DROP TYPE IF EXISTS {name}")


def downgrade() -> None:
    op.drop_index('ix_group_proposals_version', table_name='group_membership_proposals')
    op.drop_index('ix_group_proposals_group_status', table_name='group_membership_proposals')
    op.drop_table('group_membership_proposals')
    op.execute("DROP INDEX IF EXISTS uq_group_rule_pending")
    op.execute("DROP INDEX IF EXISTS uq_group_rule_active")
    op.drop_index('ix_group_rule_versions_group', table_name='group_rule_versions')
    op.drop_table('group_rule_versions')
    op.drop_index('ix_group_memberships_constituent', table_name='group_memberships')
    op.drop_index('ix_group_memberships_group', table_name='group_memberships')
    op.drop_table('group_memberships')
    op.drop_index('ix_groups_type_status', table_name='groups')
    op.drop_table('groups')
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE name LIKE 'groups.%%')"
    )
    op.execute("DELETE FROM permissions WHERE name LIKE 'groups.%%'")
    _drop_enums()
