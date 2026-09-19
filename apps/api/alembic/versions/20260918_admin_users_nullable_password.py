"""admin users: hashed_password nullable (ADR-003)

Revision ID: 7f3a9c2e41b8
Revises: d31cd5af3c76
Create Date: 2026-09-18

Production uses Sign in with Google (email allowlist, no stored
credentials), so new users are created without a password hash.
Existing dev seed rows keep their hashes; the column simply stops
being mandatory.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3a9c2e41b8'
down_revision: Union[str, None] = 'd31cd5af3c76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(length=255),
                    nullable=True)


def downgrade() -> None:
    op.execute("UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL")
    op.alter_column('users', 'hashed_password',
                    existing_type=sa.String(length=255),
                    nullable=False)
