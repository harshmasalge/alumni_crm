"""profile photos: multiple images per alumni profile (T-field Photo).

Revision ID: c42d8f1e5a77
Revises: b81f5d3a90c2
Create Date: 2026-09-18

Bytes live in object storage (local uploads/ dir in dev); the table holds
metadata, ordering, and the primary flag only.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c42d8f1e5a77'
down_revision: Union[str, None] = 'b81f5d3a90c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profile_photos',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_profile_photos_constituent', 'profile_photos', ['constituent_id'])


def downgrade() -> None:
    op.drop_index('ix_profile_photos_constituent', table_name='profile_photos')
    op.drop_table('profile_photos')
