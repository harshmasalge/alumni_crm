import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ConstituentKind(str, enum.Enum):
    PERSON = "PERSON"
    ORGANISATION = "ORGANISATION"


class ConstituentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DECEASED = "DECEASED"
    LOST_CONTACT = "LOST_CONTACT"
    OPTED_OUT = "OPTED_OUT"
    ARCHIVED = "ARCHIVED"


class MemberType(str, enum.Enum):
    ALUMNUS = "ALUMNUS"
    DONOR = "DONOR"
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    STAFF = "STAFF"
    FRIEND = "FRIEND"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class EducationStage(str, enum.Enum):
    PRE_IITGN = "PRE_IITGN"
    IITGN = "IITGN"
    POST_IITGN = "POST_IITGN"


class AffiliationType(str, enum.Enum):
    PRIVATE = "PRIVATE"
    GOVERNMENT = "GOVERNMENT"
    ACADEMIC = "ACADEMIC"
    STARTUP = "STARTUP"
    OTHER = "OTHER"


class DatePrecision(str, enum.Enum):
    DAY = "DAY"
    MONTH = "MONTH"
    YEAR = "YEAR"
    UNKNOWN = "UNKNOWN"


class AffiliationSource(str, enum.Enum):
    STAFF = "STAFF"
    PORTAL = "PORTAL"
    IMPORT = "IMPORT"
    VERIFIED_SOURCE = "VERIFIED_SOURCE"


class ContactType(str, enum.Enum):
    EMAIL_IITGN = "EMAIL_IITGN"
    EMAIL_PERSONAL = "EMAIL_PERSONAL"
    EMAIL_WORK = "EMAIL_WORK"
    PHONE_PRIMARY = "PHONE_PRIMARY"
    PHONE_SECONDARY = "PHONE_SECONDARY"
    LINKEDIN = "LINKEDIN"
    INSTAGRAM = "INSTAGRAM"
    WHATSAPP = "WHATSAPP"


class AddressType(str, enum.Enum):
    CURRENT = "CURRENT"
    PERMANENT = "PERMANENT"


class ConsentSource(str, enum.Enum):
    PORTAL = "PORTAL"
    FORM = "FORM"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    IMPORT = "IMPORT"


class Constituent(Base):
    __tablename__ = "constituents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[ConstituentKind] = mapped_column(Enum(ConstituentKind), nullable=False)
    status: Mapped[ConstituentStatus] = mapped_column(Enum(ConstituentStatus), nullable=False, default=ConstituentStatus.ACTIVE)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalised_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_completeness_percent: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    last_substantive_profile_update_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    person: Mapped[Optional["Person"]] = relationship(back_populates="constituent", uselist=False, cascade="all, delete-orphan")
    organisation: Mapped[Optional["Organisation"]] = relationship(back_populates="constituent", uselist=False, cascade="all, delete-orphan")
    alumni_profile: Mapped[Optional["AlumniProfile"]] = relationship(back_populates="constituent", uselist=False, cascade="all, delete-orphan")
    donor_profile: Mapped[Optional["DonorProfile"]] = relationship(back_populates="constituent", uselist=False, cascade="all, delete-orphan")
    contact_methods: Mapped[list["ContactMethod"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    addresses: Mapped[list["Address"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    communication_preferences: Mapped[Optional["CommunicationPreferences"]] = relationship(back_populates="constituent", uselist=False, cascade="all, delete-orphan")
    education_records: Mapped[list["EducationRecord"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    affiliations: Mapped[list["Affiliation"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    files: Mapped[list["FileRecord"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_constituents_kind_status", "kind", "status"),
        Index("ix_constituents_normalised_display_name", "normalised_display_name"),
    )


class Person(Base):
    __tablename__ = "people"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    spouse_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    profile_photo_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    constituent: Mapped["Constituent"] = relationship(back_populates="person")


class Organisation(Base):
    __tablename__ = "organisations"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalised_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    constituent: Mapped["Constituent"] = relationship(back_populates="organisation")

    __table_args__ = (
        Index("ix_organisations_normalised_name", "normalised_name"),
    )


class AlumniProfile(Base):
    __tablename__ = "alumni_profiles"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    roll_no: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    iitgn_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    programme_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    discipline_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    year_of_graduation: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    final_cpi: Mapped[Optional[float]] = mapped_column(nullable=True)
    thesis_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thesis_defence_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    thesis_supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    thesis_co_supervisor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    jee_air: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gate_air: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    jam_air: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    csir_net_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="alumni_profile")

    __table_args__ = (
        Index("ix_alumni_profiles_roll_no", "roll_no"),
        Index("ix_alumni_profiles_iitgn_email", "iitgn_email"),
        Index("ix_alumni_profiles_year_of_graduation", "year_of_graduation"),
    )


class DonorProfile(Base):
    __tablename__ = "donor_profiles"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    donor_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    pan_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pan_last_four: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    aadhaar_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="donor_profile")

    __table_args__ = (
        Index("ix_donor_profiles_donor_id", "donor_id"),
    )


class EducationRecord(Base):
    __tablename__ = "education_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    education_stage: Mapped[EducationStage] = mapped_column(Enum(EducationStage), nullable=False)
    qualification: Mapped[str] = mapped_column(String(255), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)
    board_or_university: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    completion_year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    grade_or_cgpa: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="education_records")

    __table_args__ = (
        Index("ix_education_records_constituent_stage", "constituent_id", "education_stage"),
        Index("ix_education_records_institution", "institution_name"),
    )


class Affiliation(Base):
    __tablename__ = "affiliations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    organisation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("organisations.constituent_id", ondelete="SET NULL"), nullable=True)
    organisation_name_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    affiliation_type: Mapped[Optional[AffiliationType]] = mapped_column(Enum(AffiliationType), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    date_precision: Mapped[DatePrecision] = mapped_column(Enum(DatePrecision), nullable=False, default=DatePrecision.UNKNOWN)
    source: Mapped[AffiliationSource] = mapped_column(Enum(AffiliationSource), nullable=False, default=AffiliationSource.STAFF)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="affiliations")
    organisation: Mapped[Optional["Organisation"]] = relationship()

    __table_args__ = (
        Index("ix_affiliations_constituent_current", "constituent_id", "is_current"),
        Index("ix_affiliations_organisation", "organisation_id"),
        Index("ix_affiliations_org_name_raw", "organisation_name_raw"),
    )


class ContactMethod(Base):
    __tablename__ = "contact_methods"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    contact_type: Mapped[ContactType] = mapped_column(Enum(ContactType), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalised_value: Mapped[str] = mapped_column(String(255), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_linked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="contact_methods")

    __table_args__ = (
        Index("ix_contact_methods_constituent_type", "constituent_id", "contact_type"),
        Index("ix_contact_methods_normalised_value", "normalised_value"),
        UniqueConstraint("constituent_id", "contact_type", "value", name="uq_contact_method_constituent_type_value"),
    )


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    address_type: Mapped[AddressType] = mapped_column(Enum(AddressType), nullable=False)
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    line3: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="addresses")

    __table_args__ = (
        Index("ix_addresses_constituent_type", "constituent_id", "address_type"),
        Index("ix_addresses_city_country", "city", "country"),
    )


class CommunicationPreferences(Base):
    __tablename__ = "communication_preferences"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    email_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    global_dnc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_source: Mapped[Optional[ConsentSource]] = mapped_column(Enum(ConsentSource), nullable=True)
    consent_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="communication_preferences")


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    scan_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    classification: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="files")

    __table_args__ = (
        Index("ix_files_constituent", "constituent_id"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="SET NULL"), nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped[Optional["Constituent"]] = relationship(back_populates="audit_events")

    __table_args__ = (
        Index("ix_audit_events_constituent", "constituent_id"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_actor", "actor_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")

    __table_args__ = (
        Index("ix_users_email", "email"),
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users: Mapped[list["User"]] = relationship(secondary="user_roles", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    roles: Mapped[list["Role"]] = relationship(secondary="role_permissions", back_populates="permissions")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)