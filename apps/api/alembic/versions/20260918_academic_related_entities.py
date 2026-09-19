"""related entity tables T4-T25 (M1-extension slice)

Revision ID: 9c4e1a7f2d63
Revises: 7f3a9c2e41b8
Create Date: 2026-09-18

Fourteen child tables of the alumni profile (constituent_id FK, append-only).
Attachments are object-storage keys, never byte columns. SSAC rows are
permission-gated at the API layer (ssac.read_restricted).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9c4e1a7f2d63'
down_revision: Union[str, None] = '7f3a9c2e41b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _base_columns():
    return [
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    ]


def upgrade() -> None:
    op.execute("CREATE TYPE programmelevel AS ENUM ('UG', 'PG', 'PHD')")

    op.create_table(
        'hostel_history',
        *_base_columns(),
        sa.Column('hostel_name', sa.String(length=255), nullable=False),
        sa.Column('room_number', sa.String(length=50), nullable=True),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.Column('semester', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_hostel_history_constituent', 'hostel_history', ['constituent_id'])

    op.create_table(
        'academic_courses',
        *_base_columns(),
        sa.Column('programme_level', postgresql.ENUM('UG', 'PG', 'PHD', name='programmelevel', create_type=False), nullable=False),
        sa.Column('course_code', sa.String(length=50), nullable=False),
        sa.Column('course_name', sa.String(length=255), nullable=True),
        sa.Column('credits', sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('semester', sa.String(length=20), nullable=True),
        sa.Column('instructor', sa.String(length=255), nullable=True),
        sa.Column('grade', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_academic_courses_constituent', 'academic_courses', ['constituent_id'])
    op.create_index('ix_academic_courses_code', 'academic_courses', ['course_code'])

    op.create_table(
        'semester_performance',
        *_base_columns(),
        sa.Column('programme_level', postgresql.ENUM('UG', 'PG', 'PHD', name='programmelevel', create_type=False), nullable=False),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('semester', sa.String(length=20), nullable=True),
        sa.Column('spi', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('cpi', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_semester_performance_constituent', 'semester_performance', ['constituent_id'])

    op.create_table(
        'gps_assignments',
        *_base_columns(),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('semester', sa.String(length=20), nullable=True),
        sa.Column('coordinator_name', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_gps_assignments_constituent', 'gps_assignments', ['constituent_id'])

    op.create_table(
        'awards_recognition',
        *_base_columns(),
        sa.Column('award_type', sa.String(length=100), nullable=False),
        sa.Column('award_date', sa.Date(), nullable=True),
        sa.Column('agency', sa.String(length=255), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.Column('semester', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_awards_recognition_constituent', 'awards_recognition', ['constituent_id'])

    op.create_table(
        'scholarships_financial_aid',
        *_base_columns(),
        sa.Column('aid_type', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_scholarships_constituent', 'scholarships_financial_aid', ['constituent_id'])

    op.create_table(
        'internships',
        *_base_columns(),
        sa.Column('scope', sa.String(length=50), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=True),
        sa.Column('duration_text', sa.String(length=100), nullable=True),
        sa.Column('organisation', sa.String(length=255), nullable=True),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('funding_source', sa.String(length=255), nullable=True),
        sa.Column('funding_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_internships_constituent', 'internships', ['constituent_id'])

    op.create_table(
        'placements',
        *_base_columns(),
        sa.Column('scope', sa.String(length=50), nullable=True),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('ctc', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('date_of_joining', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_placements_constituent', 'placements', ['constituent_id'])

    op.create_table(
        'startups',
        *_base_columns(),
        sa.Column('startup_name', sa.String(length=255), nullable=False),
        sa.Column('startup_type', sa.String(length=100), nullable=True),
        sa.Column('incubator', sa.String(length=255), nullable=True),
        sa.Column('founders', sa.Text(), nullable=True),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('team_size', sa.Integer(), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_startups_constituent', 'startups', ['constituent_id'])

    op.create_table(
        'ssac_records',
        *_base_columns(),
        sa.Column('incident_details', sa.Text(), nullable=True),
        sa.Column('sanction_letter_date', sa.Date(), nullable=True),
        sa.Column('attachment_storage_key', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ssac_records_constituent', 'ssac_records', ['constituent_id'])

    op.create_table(
        'positions_of_responsibility',
        *_base_columns(),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=100), nullable=True),
        sa.Column('academic_year', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_por_constituent', 'positions_of_responsibility', ['constituent_id'])

    op.create_table(
        'publications',
        *_base_columns(),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('doi', sa.String(length=255), nullable=True),
        sa.Column('pub_date', sa.Date(), nullable=True),
        sa.Column('attachment_storage_key', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_publications_constituent', 'publications', ['constituent_id'])

    op.create_table(
        'overseas_exposure',
        *_base_columns(),
        sa.Column('organisation', sa.String(length=255), nullable=True),
        sa.Column('year', sa.SmallInteger(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('funding_details', sa.Text(), nullable=True),
        sa.Column('funding_amount', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_overseas_exposure_constituent', 'overseas_exposure', ['constituent_id'])

    op.create_table(
        'family_members',
        *_base_columns(),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('relationship', sa.String(length=100), nullable=True),
        sa.Column('contact_number', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_family_members_constituent', 'family_members', ['constituent_id'])

    # Seed the SSAC restricted permission (admin role grant follows in seed data).
    op.execute(
        "INSERT INTO permissions (id, name, description, module, action) "
        "SELECT gen_random_uuid(), 'ssac.read_restricted', "
        "'Read student conduct records (restricted)', 'ssac', 'read_restricted' "
        "WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE name = 'ssac.read_restricted')"
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) "
        "SELECT r.id, p.id FROM roles r, permissions p "
        "WHERE r.name = 'admin' AND p.name = 'ssac.read_restricted' "
        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
        "WHERE rp.role_id = r.id AND rp.permission_id = p.id)"
    )


def downgrade() -> None:
    for table in (
        'family_members',
        'overseas_exposure',
        'publications',
        'positions_of_responsibility',
        'ssac_records',
        'startups',
        'placements',
        'internships',
        'scholarships_financial_aid',
        'awards_recognition',
        'gps_assignments',
        'semester_performance',
        'academic_courses',
        'hostel_history',
    ):
        op.drop_table(table)
    op.execute(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE name = 'ssac.read_restricted')"
    )
    op.execute("DELETE FROM permissions WHERE name = 'ssac.read_restricted'")
    op.execute("DROP TYPE programmelevel")
