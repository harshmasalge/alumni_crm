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


class OrganisationCreate(OrganisationBase):
    pass


class OrganisationUpdate(BaseModel):
    legal_name: Optional[str] = None
    normalised_name: Optional[str] = None
    sector: Optional[str] = None
    website_url: Optional[str] = None


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