"""M1.1 Phase A — people segmentation foundations.

Revision ID: f3a91c4d55e2
Revises: c42d8f1e5a77
Create Date: 2026-09-19

Schema (no duplicate sources of truth; employment history stays historical):
- people.last_name (nullable; Excel carries a Last Name column the M1 seed
  ignored — new seeds populate it, existing rows stay NULL).
- affiliations.function / affiliations.seniority_level (nullable free text;
  the taxonomies table below is the staff-managed vocabulary, advisory not
  FK-constrained, so existing rows are never invalidated).
- organisations.company_type / hq_city / hq_state / hq_country (nullable;
  master data for the company-type and headquarters filters).
- taxonomies (staff-managed categorical values: category + value, active
  flag for soft-deactivation instead of destructive deletion).

Data (grounded in the real Excel profiling of 2026-09-19, 4,101 rows):
- industry values: distinct affiliation sectors observed in the data,
  de-duplicated case-insensitively ('it'/'IT', 'retail'/'Retail' merged)
  with the junk literal 'Sector' dropped.
- company_type values: the established AffiliationType vocabulary
  (PRIVATE/GOVERNMENT/ACADEMIC/STARTUP/OTHER) reused at org level.
- function / seniority_level: intentionally NOT seeded — the source data
  has no structured function/seniority (only 658 free-text designations),
  so staff populate these vocabularies through the CRM. See ADR-005.

Idempotent taxonomy inserts: safe to re-run.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3a91c4d55e2'
down_revision: Union[str, None] = 'c42d8f1e5a77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Distinct Sector values observed in Alumni Database.xlsx (4,101 rows),
# de-duplicated case-insensitively; junk literal 'Sector' excluded.
INDUSTRY_SEED = (
    'Agriculture & Food Science',
    'Arts & Entertainment',
    'Aviation',
    'Banking',
    'Biotechnology',
    'Business',
    'Chemicals',
    'Construction',
    'Consulting',
    'Corporate security',
    'Cost Analytics',
    'Defence',
    'Design',
    'Education',
    'Energy',
    'Engineering',
    'Engineering Service',
    'Environmental Services',
    'Fashion&Lifestyle',
    'Finance',
    'Healthcare',
    'Hospitality & Tourism',
    'IT',
    'Insurance',
    'Investment',
    'Journalism',
    'Manufacturing',
    'Marketing',
    'Marketing&Management',
    'Mining',
    'Nonprofit Sector',
    'Professional service',
    'Public Sector',
    'R & D',
    'Real Estate',
    'Research',
    'Research services',
    'Retail',
    'Security services',
    'Software',
    'Space Sector',
    'Sports & Recreation',
    'Telecommunications',
    'Transportation & Logistics',
)

COMPANY_TYPE_SEED = (
    'PRIVATE',
    'GOVERNMENT',
    'ACADEMIC',
    'STARTUP',
    'OTHER',
)


def upgrade() -> None:
    op.add_column('people', sa.Column('last_name', sa.String(100), nullable=True))
    op.create_index('ix_people_last_name', 'people', ['last_name'])

    op.add_column('affiliations', sa.Column('function', sa.String(100), nullable=True))
    op.add_column('affiliations', sa.Column('seniority_level', sa.String(100), nullable=True))
    op.create_index('ix_affiliations_function', 'affiliations', ['function'])
    op.create_index('ix_affiliations_seniority', 'affiliations', ['seniority_level'])

    op.add_column('organisations', sa.Column('company_type', sa.String(100), nullable=True))
    op.add_column('organisations', sa.Column('hq_city', sa.String(100), nullable=True))
    op.add_column('organisations', sa.Column('hq_state', sa.String(100), nullable=True))
    op.add_column('organisations', sa.Column('hq_country', sa.String(100), nullable=True))
    op.create_index('ix_organisations_company_type', 'organisations', ['company_type'])

    op.create_table(
        'taxonomies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('normalised_value', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'normalised_value', name='uq_taxonomy_category_value'),
    )
    op.create_index('ix_taxonomies_category', 'taxonomies', ['category'])
    op.create_index('ix_taxonomies_category_active', 'taxonomies', ['category', 'is_active'])

    for value in INDUSTRY_SEED:
        _seed_taxonomy('industry', value)
    for value in COMPANY_TYPE_SEED:
        _seed_taxonomy('company_type', value)


def _seed_taxonomy(category: str, value: str) -> None:
    normalised = value.strip().lower()
    op.execute(
        "INSERT INTO taxonomies (id, category, value, normalised_value, is_active) "
        "VALUES (gen_random_uuid(), '%s', '%s', '%s', TRUE) "
        "ON CONFLICT (category, normalised_value) DO NOTHING"
        % (category, value.replace("'", "''"), normalised.replace("'", "''"))
    )


def downgrade() -> None:
    op.drop_index('ix_taxonomies_category_active', table_name='taxonomies')
    op.drop_index('ix_taxonomies_category', table_name='taxonomies')
    op.drop_table('taxonomies')
    op.drop_index('ix_organisations_company_type', table_name='organisations')
    op.drop_column('organisations', 'hq_country')
    op.drop_column('organisations', 'hq_state')
    op.drop_column('organisations', 'hq_city')
    op.drop_column('organisations', 'company_type')
    op.drop_index('ix_affiliations_seniority', table_name='affiliations')
    op.drop_index('ix_affiliations_function', table_name='affiliations')
    op.drop_column('affiliations', 'seniority_level')
    op.drop_column('affiliations', 'function')
    op.drop_index('ix_people_last_name', table_name='people')
    op.drop_column('people', 'last_name')
