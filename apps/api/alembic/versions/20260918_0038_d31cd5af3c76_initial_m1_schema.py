"""initial_m1_schema

Revision ID: d31cd5af3c76
Revises:
Create Date: 2026-09-18 00:38:28.422372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd31cd5af3c76'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # constituents
    op.create_table(
        'constituents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Enum('PERSON', 'ORGANISATION', name='constituentkind'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'DECEASED', 'LOST_CONTACT', 'OPTED_OUT', 'ARCHIVED', name='constituentstatus'), nullable=False, server_default='ACTIVE'),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('normalised_display_name', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('profile_completeness_percent', sa.SmallInteger(), nullable=False, server_default='0'),
        sa.Column('last_substantive_profile_update_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_constituents_kind_status', 'constituents', ['kind', 'status'])
    op.create_index('ix_constituents_normalised_display_name', 'constituents', ['normalised_display_name'])

    # people
    op.create_table(
        'people',
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('gender', sa.Enum('MALE', 'FEMALE', 'OTHER', 'PREFER_NOT_TO_SAY', name='gender'), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('spouse_name', sa.String(length=255), nullable=True),
        sa.Column('profile_photo_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('constituent_id')
    )

    # organisations
    op.create_table(
        'organisations',
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('normalised_name', sa.String(length=255), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('constituent_id')
    )
    op.create_index('ix_organisations_normalised_name', 'organisations', ['normalised_name'])

    # alumni_profiles
    op.create_table(
        'alumni_profiles',
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('roll_no', sa.String(length=50), nullable=False),
        sa.Column('iitgn_email', sa.String(length=255), nullable=True),
        sa.Column('programme_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('discipline_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('year_of_graduation', sa.SmallInteger(), nullable=True),
        sa.Column('final_cpi', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('thesis_title', sa.Text(), nullable=True),
        sa.Column('thesis_defence_date', sa.Date(), nullable=True),
        sa.Column('thesis_supervisor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('thesis_co_supervisor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('jee_air', sa.Integer(), nullable=True),
        sa.Column('gate_air', sa.Integer(), nullable=True),
        sa.Column('jam_air', sa.Integer(), nullable=True),
        sa.Column('csir_net_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('constituent_id')
    )
    op.create_index('ix_alumni_profiles_roll_no', 'alumni_profiles', ['roll_no'], unique=True)
    op.create_index('ix_alumni_profiles_iitgn_email', 'alumni_profiles', ['iitgn_email'], unique=True)
    op.create_index('ix_alumni_profiles_year_of_graduation', 'alumni_profiles', ['year_of_graduation'])

    # donor_profiles
    op.create_table(
        'donor_profiles',
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('donor_id', sa.String(length=50), nullable=False),
        sa.Column('pan_encrypted', sa.Text(), nullable=True),
        sa.Column('pan_last_four', sa.String(length=4), nullable=True),
        sa.Column('aadhaar_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('constituent_id')
    )
    op.create_index('ix_donor_profiles_donor_id', 'donor_profiles', ['donor_id'], unique=True)

    # education_records
    op.create_table(
        'education_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('education_stage', sa.Enum('PRE_IITGN', 'IITGN', 'POST_IITGN', name='educationstage'), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=False),
        sa.Column('institution_name', sa.String(length=255), nullable=False),
        sa.Column('board_or_university', sa.String(length=255), nullable=True),
        sa.Column('field_of_study', sa.String(length=255), nullable=True),
        sa.Column('start_year', sa.SmallInteger(), nullable=True),
        sa.Column('completion_year', sa.SmallInteger(), nullable=True),
        sa.Column('grade_or_cgpa', sa.String(length=50), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_education_records_constituent_stage', 'education_records', ['constituent_id', 'education_stage'])
    op.create_index('ix_education_records_institution', 'education_records', ['institution_name'])

    # affiliations
    op.create_table(
        'affiliations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('organisation_name_raw', sa.String(length=255), nullable=True),
        sa.Column('affiliation_type', sa.Enum('PRIVATE', 'GOVERNMENT', 'ACADEMIC', 'STARTUP', 'OTHER', name='affiliationtype'), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('designation', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('date_precision', sa.Enum('DAY', 'MONTH', 'YEAR', 'UNKNOWN', name='dateprecision'), nullable=False, server_default='UNKNOWN'),
        sa.Column('source', sa.Enum('STAFF', 'PORTAL', 'IMPORT', 'VERIFIED_SOURCE', name='affiliationsource'), nullable=False, server_default='STAFF'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organisation_id'], ['organisations.constituent_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_affiliations_constituent_current', 'affiliations', ['constituent_id', 'is_current'])
    op.create_index('ix_affiliations_organisation', 'affiliations', ['organisation_id'])
    op.create_index('ix_affiliations_org_name_raw', 'affiliations', ['organisation_name_raw'])

    # contact_methods
    op.create_table(
        'contact_methods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_type', sa.Enum('EMAIL_IITGN', 'EMAIL_PERSONAL', 'EMAIL_WORK', 'PHONE_PRIMARY', 'PHONE_SECONDARY', 'LINKEDIN', 'INSTAGRAM', 'WHATSAPP', name='contacttype'), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('normalised_value', sa.String(length=255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('whatsapp_linked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contact_methods_constituent_type', 'contact_methods', ['constituent_id', 'contact_type'])
    op.create_index('ix_contact_methods_normalised_value', 'contact_methods', ['normalised_value'])
    op.create_unique_constraint('uq_contact_method_constituent_type_value', 'contact_methods', ['constituent_id', 'contact_type', 'value'])

    # addresses
    op.create_table(
        'addresses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('address_type', sa.Enum('CURRENT', 'PERMANENT', name='addresstype'), nullable=False),
        sa.Column('line1', sa.String(length=255), nullable=False),
        sa.Column('line2', sa.String(length=255), nullable=True),
        sa.Column('line3', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_addresses_constituent_type', 'addresses', ['constituent_id', 'address_type'])
    op.create_index('ix_addresses_city_country', 'addresses', ['city', 'country'])

    # communication_preferences
    op.create_table(
        'communication_preferences',
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_opt_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('whatsapp_opt_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_opt_in', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('global_dnc', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('consent_source', sa.Enum('PORTAL', 'FORM', 'EMAIL', 'PHONE', 'IMPORT', name='consentsource'), nullable=True),
        sa.Column('consent_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('constituent_id')
    )

    # files
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('original_name', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('scan_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('classification', sa.String(length=50), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_files_constituent', 'files', ['constituent_id'])

    # audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('constituent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('before_state', sa.Text(), nullable=True),
        sa.Column('after_state', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['constituent_id'], ['constituents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_events_constituent', 'audit_events', ['constituent_id'])
    op.create_index('ix_audit_events_entity', 'audit_events', ['entity_type', 'entity_id'])
    op.create_index('ix_audit_events_actor', 'audit_events', ['actor_id'])
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'])

    # users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # roles
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # permissions
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # user_roles
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id')
    )

    # role_permissions
    op.create_table(
        'role_permissions',
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.drop_index('ix_audit_events_created_at', table_name='audit_events')
    op.drop_index('ix_audit_events_actor', table_name='audit_events')
    op.drop_index('ix_audit_events_entity', table_name='audit_events')
    op.drop_index('ix_audit_events_constituent', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index('ix_files_constituent', table_name='files')
    op.drop_table('files')
    op.drop_table('communication_preferences')
    op.drop_index('ix_addresses_city_country', table_name='addresses')
    op.drop_index('ix_addresses_constituent_type', table_name='addresses')
    op.drop_table('addresses')
    op.drop_constraint('uq_contact_method_constituent_type_value', 'contact_methods', type_='unique')
    op.drop_index('ix_contact_methods_normalised_value', table_name='contact_methods')
    op.drop_index('ix_contact_methods_constituent_type', table_name='contact_methods')
    op.drop_table('contact_methods')
    op.drop_index('ix_affiliations_org_name_raw', table_name='affiliations')
    op.drop_index('ix_affiliations_organisation', table_name='affiliations')
    op.drop_index('ix_affiliations_constituent_current', table_name='affiliations')
    op.drop_table('affiliations')
    op.drop_index('ix_education_records_institution', table_name='education_records')
    op.drop_index('ix_education_records_constituent_stage', table_name='education_records')
    op.drop_table('education_records')
    op.drop_index('ix_donor_profiles_donor_id', table_name='donor_profiles')
    op.drop_table('donor_profiles')
    op.drop_index('ix_alumni_profiles_year_of_graduation', table_name='alumni_profiles')
    op.drop_index('ix_alumni_profiles_iitgn_email', table_name='alumni_profiles')
    op.drop_index('ix_alumni_profiles_roll_no', table_name='alumni_profiles')
    op.drop_table('alumni_profiles')
    op.drop_index('ix_organisations_normalised_name', table_name='organisations')
    op.drop_table('organisations')
    op.drop_table('people')
    op.drop_index('ix_constituents_normalised_display_name', table_name='constituents')
    op.drop_index('ix_constituents_kind_status', table_name='constituents')
    op.drop_table('constituents')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS role_permissions_granted_by CASCADE')
    op.execute('DROP TYPE IF EXISTS user_roles_assigned_by CASCADE')
    op.execute('DROP TYPE IF EXISTS constituentkind CASCADE')
    op.execute('DROP TYPE IF EXISTS constituentstatus CASCADE')
    op.execute('DROP TYPE IF EXISTS gender CASCADE')
    op.execute('DROP TYPE IF EXISTS educationstage CASCADE')
    op.execute('DROP TYPE IF EXISTS affiliationtype CASCADE')
    op.execute('DROP TYPE IF EXISTS dateprecision CASCADE')
    op.execute('DROP TYPE IF EXISTS affiliationsource CASCADE')
    op.execute('DROP TYPE IF EXISTS contacttype CASCADE')
    op.execute('DROP TYPE IF EXISTS addresstype CASCADE')
    op.execute('DROP TYPE IF EXISTS consentsource CASCADE')