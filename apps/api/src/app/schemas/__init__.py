from datetime import date, datetime
from typing import Literal, Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, computed_field

from app.services.freshness import days_since


class ConstituentBase(BaseModel):
    kind: str = Field(..., description="PERSON or ORGANISATION")
    status: str = Field(default="ACTIVE", description="ACTIVE, DECEASED, LOST_CONTACT, OPTED_OUT, ARCHIVED")
    display_name: str
    notes: Optional[str] = None


class ConstituentCreate(ConstituentBase):
    pass


class ConstituentUpdate(BaseModel):
    status: Optional[str] = None
    display_name: Optional[str] = None
    notes: Optional[str] = None


class ConstituentResponse(ConstituentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    normalised_display_name: str
    profile_completeness_percent: int
    last_substantive_profile_update_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def days_since_profile_update(self) -> Optional[int]:
        """Days since last substantive update; None when never updated.

        Calculated on read per the data dictionary — never persisted.
        """
        return days_since(self.last_substantive_profile_update_at)


class PersonBase(BaseModel):
    first_name: str
    full_name: str
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None
    spouse_name: Optional[str] = None
    profile_photo_file_id: Optional[UUID] = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    full_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    blood_group: Optional[str] = None
    spouse_name: Optional[str] = None
    profile_photo_file_id: Optional[UUID] = None


class PersonResponse(PersonBase):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID


class OrganisationBase(BaseModel):
    legal_name: str
    normalised_name: str
    sector: Optional[str] = None
    website_url: Optional[str] = None
    company_type: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    hq_country: Optional[str] = None


class OrganisationCreate(OrganisationBase):
    pass


class OrganisationUpdate(BaseModel):
    legal_name: Optional[str] = None
    normalised_name: Optional[str] = None
    sector: Optional[str] = None
    website_url: Optional[str] = None
    company_type: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    hq_country: Optional[str] = None


class OrganisationResponse(OrganisationBase):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID


class AlumniProfileBase(BaseModel):
    roll_no: str
    iitgn_email: Optional[EmailStr] = None
    programme_id: Optional[UUID] = None
    discipline_id: Optional[UUID] = None
    year_of_graduation: Optional[int] = None
    final_cpi: Optional[float] = None
    thesis_title: Optional[str] = None
    thesis_defence_date: Optional[date] = None
    thesis_supervisor_id: Optional[UUID] = None
    thesis_co_supervisor_id: Optional[UUID] = None
    jee_air: Optional[int] = None
    gate_air: Optional[int] = None
    jam_air: Optional[int] = None
    csir_net_rank: Optional[int] = None


class AlumniProfileCreate(AlumniProfileBase):
    pass


class AlumniProfileUpdate(BaseModel):
    iitgn_email: Optional[EmailStr] = None
    programme_id: Optional[UUID] = None
    discipline_id: Optional[UUID] = None
    year_of_graduation: Optional[int] = None
    final_cpi: Optional[float] = None
    thesis_title: Optional[str] = None
    thesis_defence_date: Optional[date] = None
    thesis_supervisor_id: Optional[UUID] = None
    thesis_co_supervisor_id: Optional[UUID] = None
    jee_air: Optional[int] = None
    gate_air: Optional[int] = None
    jam_air: Optional[int] = None
    csir_net_rank: Optional[int] = None


class AlumniProfileResponse(AlumniProfileBase):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class DonorProfileBase(BaseModel):
    donor_id: str
    pan_encrypted: Optional[str] = None
    pan_last_four: Optional[str] = None
    aadhaar_encrypted: Optional[str] = None


class DonorProfileCreate(DonorProfileBase):
    pass


class DonorProfileUpdate(BaseModel):
    pan_encrypted: Optional[str] = None
    pan_last_four: Optional[str] = None
    aadhaar_encrypted: Optional[str] = None


class DonorProfileResponse(DonorProfileBase):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class EducationRecordBase(BaseModel):
    education_stage: str = Field(..., description="PRE_IITGN, IITGN, POST_IITGN")
    qualification: str
    institution_name: str
    board_or_university: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    completion_year: Optional[int] = None
    grade_or_cgpa: Optional[str] = None
    remarks: Optional[str] = None
    is_verified: bool = False


class EducationRecordCreate(EducationRecordBase):
    constituent_id: UUID


class EducationRecordUpdate(BaseModel):
    education_stage: Optional[str] = None
    qualification: Optional[str] = None
    institution_name: Optional[str] = None
    board_or_university: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    completion_year: Optional[int] = None
    grade_or_cgpa: Optional[str] = None
    remarks: Optional[str] = None
    is_verified: Optional[bool] = None


class EducationRecordResponse(EducationRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class AffiliationBase(BaseModel):
    organisation_id: Optional[UUID] = None
    organisation_name_raw: Optional[str] = None
    affiliation_type: Optional[str] = None
    sector: Optional[str] = None
    designation: Optional[str] = None
    function: Optional[str] = None
    seniority_level: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    date_precision: str = "UNKNOWN"
    source: str = "STAFF"
    verified_at: Optional[datetime] = None


class AffiliationCreate(AffiliationBase):
    constituent_id: UUID


class AffiliationUpdate(BaseModel):
    organisation_id: Optional[UUID] = None
    organisation_name_raw: Optional[str] = None
    affiliation_type: Optional[str] = None
    sector: Optional[str] = None
    designation: Optional[str] = None
    function: Optional[str] = None
    seniority_level: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    date_precision: Optional[str] = None
    source: Optional[str] = None
    verified_at: Optional[datetime] = None


class AffiliationResponse(AffiliationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class ContactMethodBase(BaseModel):
    contact_type: str
    value: str
    normalised_value: str
    is_primary: bool = False
    is_verified: bool = False
    whatsapp_linked: bool = False
    is_active: bool = True


class ContactMethodCreate(ContactMethodBase):
    constituent_id: UUID


class ContactMethodUpdate(BaseModel):
    is_primary: Optional[bool] = None
    is_verified: Optional[bool] = None
    whatsapp_linked: Optional[bool] = None
    is_active: Optional[bool] = None


class ContactMethodResponse(ContactMethodBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class AddressBase(BaseModel):
    address_type: str
    line1: str
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: bool = True


class AddressCreate(AddressBase):
    constituent_id: UUID


class AddressUpdate(BaseModel):
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: Optional[bool] = None


class AddressResponse(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime
    updated_at: datetime


class CommunicationPreferencesBase(BaseModel):
    email_opt_in: bool = True
    whatsapp_opt_in: bool = True
    sms_opt_in: bool = True
    global_dnc: bool = False
    consent_source: Optional[str] = None
    consent_time: Optional[datetime] = None


class CommunicationPreferencesCreate(CommunicationPreferencesBase):
    constituent_id: UUID


class CommunicationPreferencesUpdate(BaseModel):
    email_opt_in: Optional[bool] = None
    whatsapp_opt_in: Optional[bool] = None
    sms_opt_in: Optional[bool] = None
    global_dnc: Optional[bool] = None
    consent_source: Optional[str] = None
    consent_time: Optional[datetime] = None


class CommunicationPreferencesResponse(CommunicationPreferencesBase):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID
    updated_at: datetime


class FileRecordBase(BaseModel):
    storage_key: str
    original_name: str
    mime_type: str
    size_bytes: int
    scan_status: str = "pending"
    classification: Optional[str] = None
    uploaded_by: Optional[UUID] = None


class FileRecordCreate(FileRecordBase):
    constituent_id: UUID


class FileRecordResponse(FileRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: Optional[UUID]
    actor_id: Optional[UUID]
    actor_type: str
    ip_address: Optional[str]
    request_id: Optional[str]
    entity_type: str
    entity_id: UUID
    action: str
    before_state: Optional[str]
    after_state: Optional[str]
    created_at: datetime


class ConstituentSearchParams(BaseModel):
    q: Optional[str] = Field(None, description="Search query for name")
    roll_no: Optional[str] = Field(None, description="Exact roll number match")
    kind: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class _ChildRecordBase(BaseModel):
    """Shared shape for T-table child rows: owner + audit timestamp."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    created_at: datetime


class HostelHistoryResponse(_ChildRecordBase):
    hostel_name: str
    room_number: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None


class AcademicCourseResponse(_ChildRecordBase):
    programme_level: str
    course_code: str
    course_name: Optional[str] = None
    credits: Optional[float] = None
    year: Optional[int] = None
    semester: Optional[str] = None
    instructor: Optional[str] = None
    grade: Optional[str] = None


class SemesterPerformanceResponse(_ChildRecordBase):
    programme_level: str
    year: Optional[int] = None
    semester: Optional[str] = None
    spi: Optional[float] = None
    cpi: Optional[float] = None


class GpsAssignmentResponse(_ChildRecordBase):
    year: Optional[int] = None
    semester: Optional[str] = None
    coordinator_name: Optional[str] = None


class AwardRecognitionResponse(_ChildRecordBase):
    award_type: str
    award_date: Optional[date] = None
    agency: Optional[str] = None
    details: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None


class ScholarshipFinancialAidResponse(_ChildRecordBase):
    aid_type: Optional[str] = None
    name: str
    year: Optional[int] = None
    amount: Optional[float] = None
    remarks: Optional[str] = None


class InternshipResponse(_ChildRecordBase):
    scope: Optional[str] = None
    format: Optional[str] = None
    duration_text: Optional[str] = None
    organisation: Optional[str] = None
    year: Optional[int] = None
    funding_source: Optional[str] = None
    funding_amount: Optional[float] = None


class PlacementResponse(_ChildRecordBase):
    scope: Optional[str] = None
    company: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    ctc: Optional[float] = None
    date_of_joining: Optional[date] = None


class StartupResponse(_ChildRecordBase):
    startup_name: str
    startup_type: Optional[str] = None
    incubator: Optional[str] = None
    founders: Optional[str] = None
    year: Optional[int] = None
    team_size: Optional[int] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class SsacRecordResponse(_ChildRecordBase):
    incident_details: Optional[str] = None
    sanction_letter_date: Optional[date] = None
    attachment_storage_key: Optional[str] = None


class PositionOfResponsibilityResponse(_ChildRecordBase):
    title: str
    domain: Optional[str] = None
    academic_year: Optional[str] = None


class PublicationResponse(_ChildRecordBase):
    title: str
    doi: Optional[str] = None
    pub_date: Optional[date] = None
    attachment_storage_key: Optional[str] = None


class OverseasExposureResponse(_ChildRecordBase):
    organisation: Optional[str] = None
    year: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    funding_details: Optional[str] = None
    funding_amount: Optional[float] = None


class FamilyMemberResponse(_ChildRecordBase):
    name: str
    relation: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None


class ProfilePhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    constituent_id: UUID
    original_name: str
    mime_type: str
    size_bytes: int
    position: int
    is_primary: bool
    created_at: datetime


class ProfilePhotoUpdate(BaseModel):
    is_primary: Optional[bool] = None


class ContactMethodCreateIn(BaseModel):
    contact_type: str
    value: str
    is_primary: bool = False
    is_verified: bool = False
    whatsapp_linked: bool = False
    is_active: bool = True


class HostelHistoryCreate(BaseModel):
    hostel_name: str
    room_number: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None


class AcademicCourseCreate(BaseModel):
    programme_level: Literal["UG", "PG", "PHD"]
    course_code: str
    course_name: Optional[str] = None
    credits: Optional[float] = None
    year: Optional[int] = None
    semester: Optional[str] = None
    instructor: Optional[str] = None
    grade: Optional[str] = None


class SemesterPerformanceCreate(BaseModel):
    programme_level: Literal["UG", "PG", "PHD"]
    year: Optional[int] = None
    semester: Optional[str] = None
    spi: Optional[float] = None
    cpi: Optional[float] = None


class GpsAssignmentCreate(BaseModel):
    year: Optional[int] = None
    semester: Optional[str] = None
    coordinator_name: Optional[str] = None


class AwardRecognitionCreate(BaseModel):
    award_type: str
    award_date: Optional[date] = None
    agency: Optional[str] = None
    details: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None


class ScholarshipFinancialAidCreate(BaseModel):
    aid_type: Optional[str] = None
    name: str
    year: Optional[int] = None
    amount: Optional[float] = None
    remarks: Optional[str] = None


class InternshipCreate(BaseModel):
    scope: Optional[str] = None
    format: Optional[str] = None
    duration_text: Optional[str] = None
    organisation: Optional[str] = None
    year: Optional[int] = None
    funding_source: Optional[str] = None
    funding_amount: Optional[float] = None


class PlacementCreate(BaseModel):
    scope: Optional[str] = None
    company: Optional[str] = None
    sector: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    ctc: Optional[float] = None
    date_of_joining: Optional[date] = None


class StartupCreate(BaseModel):
    startup_name: str
    startup_type: Optional[str] = None
    incubator: Optional[str] = None
    founders: Optional[str] = None
    year: Optional[int] = None
    team_size: Optional[int] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class SsacRecordCreate(BaseModel):
    incident_details: Optional[str] = None
    sanction_letter_date: Optional[date] = None
    attachment_storage_key: Optional[str] = None


class PositionOfResponsibilityCreate(BaseModel):
    title: str
    domain: Optional[str] = None
    academic_year: Optional[str] = None


class PublicationCreate(BaseModel):
    title: str
    doi: Optional[str] = None
    pub_date: Optional[date] = None
    attachment_storage_key: Optional[str] = None


class OverseasExposureCreate(BaseModel):
    organisation: Optional[str] = None
    year: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    funding_details: Optional[str] = None
    funding_amount: Optional[float] = None


class FamilyMemberCreate(BaseModel):
    name: str
    relation: Optional[str] = None
    contact_number: Optional[str] = None
    email: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: List[ConstituentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class Profile360Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    constituent: ConstituentResponse
    person: Optional[PersonResponse] = None
    organisation: Optional[OrganisationResponse] = None
    alumni_profile: Optional[AlumniProfileResponse] = None
    donor_profile: Optional[DonorProfileResponse] = None
    contact_methods: List[ContactMethodResponse] = []
    addresses: List[AddressResponse] = []
    communication_preferences: Optional[CommunicationPreferencesResponse] = None
    education_records: List[EducationRecordResponse] = []
    affiliations: List[AffiliationResponse] = []
    files: List[FileRecordResponse] = []
    audit_events: List[AuditEventResponse] = []
    hostel_history: List[HostelHistoryResponse] = []
    academic_courses: List[AcademicCourseResponse] = []
    semester_performance: List[SemesterPerformanceResponse] = []
    gps_assignments: List[GpsAssignmentResponse] = []
    awards_recognition: List[AwardRecognitionResponse] = []
    scholarships_financial_aid: List[ScholarshipFinancialAidResponse] = []
    internships: List[InternshipResponse] = []
    placements: List[PlacementResponse] = []
    startups: List[StartupResponse] = []
    ssac_records: List[SsacRecordResponse] = []
    positions_of_responsibility: List[PositionOfResponsibilityResponse] = []
    publications: List[PublicationResponse] = []
    overseas_exposure: List[OverseasExposureResponse] = []
    family_members: List[FamilyMemberResponse] = []
    profile_photos: List[ProfilePhotoResponse] = []


class StaleProfileCountResponse(BaseModel):
    count: int
    threshold_days: int = 365


class OrganisationSearchParams(BaseModel):
    q: str = Field(..., description="Organisation name to search")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class OrganisationSearchResult(BaseModel):
    constituent_id: UUID
    display_name: str
    roll_no: Optional[str] = None
    affiliation_status: str = Field(..., description="Current, Past, or Current and past")
    organisation_name: str
    designation: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class OrganisationSearchResponse(BaseModel):
    items: List[OrganisationSearchResult]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminUserResponse(BaseModel):
    """Staff user. Never serializes any credential material."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    roles: List[str] = []
    created_at: datetime
    updated_at: datetime


class AdminUserCreate(BaseModel):
    # Email-allowlist entry (ADR-003): no password is stored, ever.
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role_ids: List[UUID] = []
    is_superuser: bool = False


class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class AdminUserRolesUpdate(BaseModel):
    role_ids: List[UUID]


class AdminUserListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    created_at: datetime


class AdminRoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class AdminRolePermissionsUpdate(BaseModel):
    permission_ids: List[UUID]


class AdminPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    module: str
    action: str


class AdminAuditListResponse(BaseModel):
    items: List[AuditEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# M1.1 Phase A — people segmentation: generic filter DSL + staff taxonomies.
#
# The frontend is presentation only: it builds this filter tree, the backend
# validates and evaluates it. Field/operator support is whitelisted in
# FILTER_FIELD_REGISTRY (single source of truth, also served to the UI via
# GET /constituents/search/fields). Saved-search persistence and Groups
# arrive in Phase B; the tree shape is already reusable for both.
# ---------------------------------------------------------------------------

TEXT_OPERATORS = (
    "equals",
    "not_equals",
    "contains",
    "starts_with",
    "is_any_of",
    "is_none_of",
    "is_empty",
    "is_not_empty",
)

NUMERIC_OPERATORS = (
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "is_empty",
    "is_not_empty",
)

MULTI_OPERATORS = (
    "is_any_of",
    "is_all_of",
    "is_none_of",
    "is_empty",
    "is_not_empty",
)

# field -> query semantics. "scope" documents which records a match is
# evaluated against; every leaf compiles to an EXISTS subquery (or a direct
# predicate for person-level fields) so history is never flattened.
FILTER_FIELD_REGISTRY: dict[str, dict] = {
    "current_company": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "current affiliations: resolved legal name or raw employer text",
        "group": "Company",
    },
    "past_company": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "past affiliations: resolved legal name or raw employer text",
        "group": "Company",
    },
    "company_type": {
        "kind": "multi",
        "operators": list(MULTI_OPERATORS),
        "scope": "any affiliation: affiliation_type or resolved organisation company_type",
        "group": "Company",
    },
    "company_hq": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "any affiliation city/state/country or resolved organisation HQ location",
        "group": "Company",
    },
    "function": {
        "kind": "multi",
        "operators": list(MULTI_OPERATORS),
        "scope": "any affiliation function (staff-maintained vocabulary)",
        "group": "Role",
    },
    "current_job_title": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "current affiliation designation",
        "group": "Role",
    },
    "seniority_level": {
        "kind": "multi",
        "operators": list(MULTI_OPERATORS),
        "scope": "any affiliation seniority_level (staff-maintained vocabulary)",
        "group": "Role",
    },
    "past_job_title": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "past affiliation designations",
        "group": "Role",
    },
    "years_in_current_company": {
        "kind": "numeric",
        "operators": list(NUMERIC_OPERATORS),
        "scope": "years since current affiliation start_date (NULL start dates never match)",
        "group": "Role",
    },
    "years_in_current_position": {
        "kind": "numeric",
        "operators": list(NUMERIC_OPERATORS),
        "scope": "years since current affiliation start_date; equals company tenure until a position-history model lands (ADR-005)",
        "group": "Role",
    },
    "geography": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "current affiliation city/state/country or current address city/state/country",
        "group": "Personal",
    },
    "industry": {
        "kind": "multi",
        "operators": list(MULTI_OPERATORS),
        "scope": "any affiliation sector (staff-maintained industry vocabulary)",
        "group": "Personal",
    },
    "first_name": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "person first_name",
        "group": "Personal",
    },
    "last_name": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "person last_name",
        "group": "Personal",
    },
    "years_of_experience": {
        "kind": "numeric",
        "operators": list(NUMERIC_OPERATORS),
        "scope": "years since earliest affiliation start_date (derived, never stored)",
        "group": "Personal",
    },
    "school": {
        "kind": "text",
        "operators": list(TEXT_OPERATORS),
        "scope": "education_records institution_name across all stages",
        "group": "Personal",
    },
}

# Phase B reserved: accepted by the registry contract but rejected with a
# clear 400 until governed Groups land. Never silently ignored.
RESERVED_PHASE_B_FIELDS = ("groups",)


class FilterCondition(BaseModel):
    field: str
    operator: str
    value: Optional[str | float | int] = None
    values: Optional[List[str | float | int]] = None


class FilterGroup(BaseModel):
    op: str = Field(default="and", description="and | or")
    conditions: List["FilterNode"] = Field(default_factory=list)


FilterNode = FilterCondition | FilterGroup
FilterGroup.model_rebuild()


class AdvancedSearchRequest(BaseModel):
    q: Optional[str] = Field(None, description="Partial-name search (M1 semantics preserved)")
    roll_no: Optional[str] = Field(None, description="Exact Roll Number (M1 semantics preserved)")
    kind: Optional[str] = None
    status: Optional[str] = None
    organisation_q: Optional[str] = Field(
        None, description="Organisation substring across current+past affiliations (M1 semantics preserved)"
    )
    stale_threshold_days: Optional[int] = Field(
        None, ge=1, description="When set, intersect with the M1 stale-profile definition"
    )
    filter: Optional[FilterGroup] = Field(None, description="Nested AND/OR filter tree")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="display_name", description="display_name | year_of_graduation")
    sort_dir: str = Field(default="asc", description="asc | desc")


class AdvancedSearchResponse(BaseModel):
    items: List[ConstituentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TaxonomyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    value: str
    normalised_value: str
    is_active: bool
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime


class TaxonomyCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=50)
    value: str = Field(..., min_length=1, max_length=255)


class TaxonomyUpdate(BaseModel):
    value: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class TaxonomyListResponse(BaseModel):
    items: List[TaxonomyResponse]
    total: int


# ---------------------------------------------------------------------------
# M1.1 Phase B1 — groups domain contracts.
#
# Two population semantics (never mixed): explicit constituent-ID lists vs
# server-side filter definitions re-evaluated at execution time. "Select all
# on page" is just explicit IDs; there is no page-population type.
# ---------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: str = Field(..., description="MANUAL | RULE_BASED")
    initial_rule: Optional[FilterGroup] = Field(
        None, description="Rule-based only: stored as PENDING v1, never active on creation"
    )


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    type: str
    status: str
    member_count: int = 0
    pending_proposal_count: int = 0
    has_pending_rule: bool = False
    active_rule_version: Optional[int] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class GroupListResponse(BaseModel):
    items: List[GroupResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MemberAddRequest(BaseModel):
    constituent_ids: List[UUID] = Field(..., min_length=1, max_length=500)


class MemberAddResponse(BaseModel):
    added: List[UUID] = []
    already_members: List[UUID] = []
    invalid: List[UUID] = []


class GroupMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    constituent_id: UUID
    display_name: str
    added_at: datetime
    # Restricted constituent fields are withheld/masked via
    # FieldPermissionChecker; membership never leaks them.
    notes: Optional[str] = None


class GroupMemberListResponse(BaseModel):
    items: List[GroupMemberResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PopulationPreviewRequest(BaseModel):
    constituent_ids: Optional[List[UUID]] = Field(None, max_length=2000)
    filter: Optional[FilterGroup] = None
    # M1 People-search criteria: combined server-side with the filter tree as
    # one intersection (same semantics as POST /constituents/search), so a
    # transferred population always equals the visible People population.
    q: Optional[str] = None
    roll_no: Optional[str] = None
    organisation_q: Optional[str] = None
    stale_threshold_days: Optional[int] = Field(None, ge=1)


class PopulationPreviewResponse(BaseModel):
    matched: int
    already_members: int
    would_add: int
    invalid: List[UUID] = []


class MaterializeResponse(BaseModel):
    matched: int
    added: List[UUID] = []
    already_members: int = 0
    invalid: List[UUID] = []


class RuleProposeRequest(BaseModel):
    filter: FilterGroup


class RuleVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    version_number: int
    filter_tree: dict
    status: str
    proposed_by: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    created_at: datetime


class RuleApprovalResponse(BaseModel):
    rule: RuleVersionResponse
    evaluation: Optional["EvaluationSummary"] = None


class EvaluationSummary(BaseModel):
    version_number: int
    matched: int
    additions: int
    removals: int
    skipped_existing_pending: int = 0


class ProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    rule_version_id: UUID
    rule_version_number: int = 0
    constituent_id: UUID
    display_name: str = ""
    action: str
    reason_summary: str
    reason_detail: Optional[str] = None
    status: str
    evaluated_by: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    decided_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: datetime


class ProposalListResponse(BaseModel):
    items: List[ProposalResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProposalDecisionRequest(BaseModel):
    proposal_ids: List[UUID] = Field(..., min_length=1, max_length=500)


class ProposalDecisionResponse(BaseModel):
    approved_or_rejected: List[UUID] = []
    stale: List[UUID] = []
    already_decided: List[UUID] = []


# ---------------------------------------------------------------------------
# M1.1 Phase C — permission-aware export contracts.
#
# Populations mirror the Groups handoff semantics: explicit IDs | M1 search
# criteria + filter tree (re-evaluated) | group members. The frontend never
# supplies row data or the population itself.
# ---------------------------------------------------------------------------

class ExportPeopleRequest(BaseModel):
    constituent_ids: Optional[List[UUID]] = Field(None, max_length=5000)
    filter: Optional[FilterGroup] = None
    q: Optional[str] = None
    roll_no: Optional[str] = None
    organisation_q: Optional[str] = None
    stale_threshold_days: Optional[int] = Field(None, ge=1)
    group_id: Optional[UUID] = None
    fields: Optional[List[str]] = Field(
        None, description="Export column keys; omitted means all columns the caller may see"
    )


class ExportFieldInfo(BaseModel):
    key: str
    label: str
    allowed: bool
    requires: Optional[List[str]] = None


class ExportFieldCatalogResponse(BaseModel):
    items: List[ExportFieldInfo]


RuleApprovalResponse.model_rebuild()