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
    JSON,
    Numeric,
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


class ProgrammeLevel(str, enum.Enum):
    UG = "UG"
    PG = "PG"
    PHD = "PHD"


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
    hostel_history: Mapped[list["HostelHistory"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    academic_courses: Mapped[list["AcademicCourse"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    semester_performance: Mapped[list["SemesterPerformance"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    gps_assignments: Mapped[list["GpsAssignment"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    awards_recognition: Mapped[list["AwardRecognition"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    scholarships_financial_aid: Mapped[list["ScholarshipFinancialAid"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    internships: Mapped[list["Internship"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    placements: Mapped[list["Placement"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    startups: Mapped[list["Startup"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    ssac_records: Mapped[list["SsacRecord"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    positions_of_responsibility: Mapped[list["PositionOfResponsibility"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    publications: Mapped[list["Publication"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    overseas_exposure: Mapped[list["OverseasExposure"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    family_members: Mapped[list["FamilyMember"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")
    profile_photos: Mapped[list["ProfilePhoto"]] = relationship(back_populates="constituent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_constituents_kind_status", "kind", "status"),
        Index("ix_constituents_normalised_display_name", "normalised_display_name"),
    )


class Person(Base):
    __tablename__ = "people"

    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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
    company_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hq_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hq_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hq_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

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
    function: Mapped[Optional[str]] = mapped_column("function", String(100), nullable=True)
    seniority_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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
    # Nullable per ADR-003: production users authenticate via Google and
    # have no stored credential; dev seed rows may carry a local hash.
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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


# ---------------------------------------------------------------------------
# Related entity tables T4–T25 (M1-extension slice).
#
# Every table is a child of the alumni profile via constituent_id UUID with
# ON DELETE CASCADE. Rows are append-only; nothing here overwrites history.
# File attachments (T17/T21) are object-storage keys, never byte columns.
# ---------------------------------------------------------------------------

class HostelHistory(Base):
    """T4 — complete on-campus residential history."""

    __tablename__ = "hostel_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    hostel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="hostel_history")

    __table_args__ = (
        Index("ix_hostel_history_constituent", "constituent_id"),
    )


class AcademicCourse(Base):
    """T5/T8/T10 — complete academic transcript; programme_level distinguishes UG/PG/PhD."""

    __tablename__ = "academic_courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    programme_level: Mapped[ProgrammeLevel] = mapped_column(Enum(ProgrammeLevel), nullable=False)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    course_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credits: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    instructor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="academic_courses")

    __table_args__ = (
        Index("ix_academic_courses_constituent", "constituent_id"),
        Index("ix_academic_courses_code", "course_code"),
    )


class SemesterPerformance(Base):
    """T6/T9/T11 — semester-wise SPI and CPI per programme level."""

    __tablename__ = "semester_performance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    programme_level: Mapped[ProgrammeLevel] = mapped_column(Enum(ProgrammeLevel), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    spi: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    cpi: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="semester_performance")

    __table_args__ = (
        Index("ix_semester_performance_constituent", "constituent_id"),
    )


class GpsAssignment(Base):
    """T7 — Graduate Program Seminar assignments with coordinator name."""

    __tablename__ = "gps_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    coordinator_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="gps_assignments")

    __table_args__ = (
        Index("ix_gps_assignments_constituent", "constituent_id"),
    )


class AwardRecognition(Base):
    """T12 — Dean's List / medals / awards / recognition."""

    __tablename__ = "awards_recognition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    award_type: Mapped[str] = mapped_column(String(100), nullable=False)
    award_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    agency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    semester: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="awards_recognition")

    __table_args__ = (
        Index("ix_awards_recognition_constituent", "constituent_id"),
    )


class ScholarshipFinancialAid(Base):
    """T13 — all forms of financial support received."""

    __tablename__ = "scholarships_financial_aid"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    aid_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="scholarships_financial_aid")

    __table_args__ = (
        Index("ix_scholarships_constituent", "constituent_id"),
    )


class Internship(Base):
    """T14 — domestic/international, online/offline internships with funding."""

    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    organisation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    funding_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    funding_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="internships")

    __table_args__ = (
        Index("ix_internships_constituent", "constituent_id"),
    )


class Placement(Base):
    """T15 — placement record with CTC and joining date."""

    __tablename__ = "placements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    scope: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ctc: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    date_of_joining: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="placements")

    __table_args__ = (
        Index("ix_placements_constituent", "constituent_id"),
    )


class Startup(Base):
    """T16 — startup and entrepreneurship record."""

    __tablename__ = "startups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    startup_name: Mapped[str] = mapped_column(String(255), nullable=False)
    startup_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    incubator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    founders: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    team_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="startups")

    __table_args__ = (
        Index("ix_startups_constituent", "constituent_id"),
    )


class SsacRecord(Base):
    """T17 — student conduct records. Restricted: separate policy/approval
    required; readable only with the ssac.read_restricted permission."""

    __tablename__ = "ssac_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    incident_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sanction_letter_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    attachment_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="ssac_records")

    __table_args__ = (
        Index("ix_ssac_records_constituent", "constituent_id"),
    )


class PositionOfResponsibility(Base):
    """T18 — leadership history (council / club / event)."""

    __tablename__ = "positions_of_responsibility"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="positions_of_responsibility")

    __table_args__ = (
        Index("ix_por_constituent", "constituent_id"),
    )


class Publication(Base):
    """T21 — research output tracking; PDF lives in object storage."""

    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doi: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pub_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    attachment_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="publications")

    __table_args__ = (
        Index("ix_publications_constituent", "constituent_id"),
    )


class OverseasExposure(Base):
    """T23 — exchange programmes and visiting positions with funding."""

    __tablename__ = "overseas_exposure"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    organisation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    funding_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funding_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="overseas_exposure")

    __table_args__ = (
        Index("ix_overseas_exposure_constituent", "constituent_id"),
    )


class FamilyMember(Base):
    """T25 — emergency contacts and spouse/children information.

    Third-party PII: readable only with the people.read_family permission;
    never in list/search/export responses.
    """

    __tablename__ = "family_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relation: Mapped[Optional[str]] = mapped_column("relationship", String(100), nullable=True)
    contact_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="family_members")

    __table_args__ = (
        Index("ix_family_members_constituent", "constituent_id"),
    )


class GroupType(str, enum.Enum):
    MANUAL = "MANUAL"
    RULE_BASED = "RULE_BASED"


class GroupStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DEACTIVATED = "DEACTIVATED"


class RuleVersionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ProposalAction(str, enum.Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"


class ProposalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Group(Base):
    """M1.1 Phase B1 — managed CRM population.

    Lifecycle is activation/deactivation only (no hard delete). Attention
    states (pending rule, pending proposals) are derived from child rows,
    not stored here. See ADR-006.
    """

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)
    status: Mapped[GroupStatus] = mapped_column(Enum(GroupStatus), nullable=False, default=GroupStatus.ACTIVE)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    memberships: Mapped[list["GroupMembership"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    rule_versions: Mapped[list["GroupRuleVersion"]] = relationship(back_populates="group", cascade="all, delete-orphan")
    proposals: Mapped[list["GroupMembershipProposal"]] = relationship(back_populates="group", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_groups_type_status", "type", "status"),
    )


class GroupMembership(Base):
    """Current-state membership. One row = member; removal deletes the row
    (audited). UNIQUE(group_id, constituent_id) makes adds idempotent."""

    __tablename__ = "group_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    group: Mapped["Group"] = relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("group_id", "constituent_id", name="uq_group_membership"),
        Index("ix_group_memberships_group", "group_id"),
        Index("ix_group_memberships_constituent", "constituent_id"),
    )


class GroupRuleVersion(Base):
    """Append-only rule snapshots. Never mutated after decision — approval
    flips statuses and appends, preserving history for later evaluation."""

    __tablename__ = "group_rule_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    filter_tree: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[RuleVersionStatus] = mapped_column(Enum(RuleVersionStatus), nullable=False, default=RuleVersionStatus.PENDING)
    proposed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    group: Mapped["Group"] = relationship(back_populates="rule_versions")

    __table_args__ = (
        UniqueConstraint("group_id", "version_number", name="uq_group_rule_version"),
        Index("ix_group_rule_versions_group", "group_id"),
    )


class GroupMembershipProposal(Base):
    """Governed delta bound to the evaluated rule version, with stored
    reason snapshots so reviewers never depend on mutable current data.
    Approval is valid only while the bound version is still ACTIVE."""

    __tablename__ = "group_membership_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    rule_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("group_rule_versions.id", ondelete="CASCADE"), nullable=False)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[ProposalAction] = mapped_column(Enum(ProposalAction), nullable=False)
    reason_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), nullable=False, default=ProposalStatus.PENDING)
    evaluated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    group: Mapped["Group"] = relationship(back_populates="proposals")

    __table_args__ = (
        Index("ix_group_proposals_group_status", "group_id", "status"),
        Index("ix_group_proposals_version", "rule_version_id"),
    )


class Taxonomy(Base):
    """M1.1 — staff-managed categorical vocabulary for segmentation.

    One generic table serves every controlled list (industry, company_type,
    function, seniority_level, ...). Values are advisory, never FK-enforced,
    so taxonomy edits cannot invalidate existing constituent rows.
    Destructive deletion is blocked while a value is referenced; staff
    deactivate (is_active=False) instead. See ADR-005.
    """

    __tablename__ = "taxonomies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalised_value: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("category", "normalised_value", name="uq_taxonomy_category_value"),
        Index("ix_taxonomies_category", "category"),
        Index("ix_taxonomies_category_active", "category", "is_active"),
    )


class ProfilePhoto(Base):
    """Alumni profile photos (multiple per profile, ordered).

    Binary bytes live in object storage (local dir in dev); only metadata
    lives here. `person.profile_photo_file_id` is the legacy single-photo
    pointer and is no longer written by new code.
    """

    __tablename__ = "profile_photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    constituent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("constituents.id", ondelete="CASCADE"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    constituent: Mapped["Constituent"] = relationship(back_populates="profile_photos")

    __table_args__ = (
        Index("ix_profile_photos_constituent", "constituent_id"),
    )