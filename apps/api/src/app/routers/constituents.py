from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import check_constituents_read
from app.core.field_permissions import FieldPermissionChecker
from app.db.session import get_db
from app.models import (
    Affiliation,
    AlumniProfile,
    Constituent,
    ConstituentKind,
    ConstituentStatus,
    Organisation,
    User,
)
from app.schemas import (
    AcademicCourseResponse,
    AddressResponse,
    AffiliationResponse,
    AlumniProfileResponse,
    AuditEventResponse,
    AwardRecognitionResponse,
    CommunicationPreferencesResponse,
    ConstituentResponse,
    ContactMethodResponse,
    DonorProfileResponse,
    EducationRecordResponse,
    FamilyMemberResponse,
    FileRecordResponse,
    GpsAssignmentResponse,
    HostelHistoryResponse,
    InternshipResponse,
    OrganisationResponse,
    OrganisationSearchResponse,
    OrganisationSearchResult,
    OverseasExposureResponse,
    PaginatedResponse,
    PersonResponse,
    PlacementResponse,
    PositionOfResponsibilityResponse,
    Profile360Response,
    ProfilePhotoResponse,
    PublicationResponse,
    ScholarshipFinancialAidResponse,
    SemesterPerformanceResponse,
    SsacRecordResponse,
    StaleProfileCountResponse,
    StartupResponse,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def search_constituents(
    q: Optional[str] = Query(None, description="Search query for name"),
    roll_no: Optional[str] = Query(None, description="Exact roll number match"),
    kind: Optional[str] = Query(None, description="Filter by kind: PERSON or ORGANISATION"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> PaginatedResponse:
    """
    Search constituents by name (partial match) or exact roll number.
    Requires constituents.read permission.
    """
    field_checker = FieldPermissionChecker(db)
    query = select(Constituent)

    conditions = []

    if roll_no:
        subquery = select(AlumniProfile.constituent_id).where(
            AlumniProfile.roll_no == roll_no.strip().upper()
        )
        conditions.append(Constituent.id.in_(subquery))
    elif q:
        search_term = f"%{q.strip().lower()}%"
        conditions.append(Constituent.normalised_display_name.ilike(search_term))

    if kind:
        try:
            kind_enum = ConstituentKind(kind.upper())
            conditions.append(Constituent.kind == kind_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid kind: {kind}. Must be PERSON or ORGANISATION",
            )

    if status:
        try:
            status_enum = ConstituentStatus(status.upper())
            conditions.append(Constituent.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )

    if conditions:
        query = query.where(*conditions)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Constituent.display_name).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    constituents = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    items = [ConstituentResponse.model_validate(c) for c in constituents]
    items = field_checker.filter_list("constituent", [i.model_dump() for i in items], await field_checker.get_user_permissions(current_user.id), current_user.is_superuser)

    return PaginatedResponse(
        items=[ConstituentResponse(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stale-profiles-count", response_model=StaleProfileCountResponse)
async def get_stale_profiles_count(
    threshold_days: int = Query(365, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> StaleProfileCountResponse:
    """
    Get count of alumni with no substantive profile update for more than threshold_days.
    Requires constituents.read permission.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)

    query = (
        select(func.count(Constituent.id))
        .join(AlumniProfile, Constituent.id == AlumniProfile.constituent_id)
        .where(
            Constituent.kind == ConstituentKind.PERSON,
            Constituent.status.notin_([ConstituentStatus.DECEASED, ConstituentStatus.ARCHIVED]),
            or_(
                Constituent.last_substantive_profile_update_at.is_(None),
                Constituent.last_substantive_profile_update_at < cutoff_date,
            ),
        )
    )

    result = await db.execute(query)
    count = result.scalar() or 0

    return StaleProfileCountResponse(count=count, threshold_days=threshold_days)


@router.get("/stale-profiles", response_model=PaginatedResponse)
async def get_stale_profiles(
    threshold_days: int = Query(365, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
    ) -> PaginatedResponse:
    """
    Get paginated list of alumni with no substantive profile update for more than threshold_days.
    Requires constituents.read permission.
    """
    field_checker = FieldPermissionChecker(db)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=threshold_days)

    query = (
        select(Constituent)
        .join(AlumniProfile, Constituent.id == AlumniProfile.constituent_id)
        .where(
            Constituent.kind == ConstituentKind.PERSON,
            Constituent.status.notin_([ConstituentStatus.DECEASED, ConstituentStatus.ARCHIVED]),
            or_(
                Constituent.last_substantive_profile_update_at.is_(None),
                Constituent.last_substantive_profile_update_at < cutoff_date,
            ),
        )
        .order_by(Constituent.display_name)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    constituents = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    items = [ConstituentResponse.model_validate(c) for c in constituents]
    items = field_checker.filter_list("constituent", [i.model_dump() for i in items], await field_checker.get_user_permissions(current_user.id), current_user.is_superuser)

    return PaginatedResponse(
        items=[ConstituentResponse(**i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{constituent_id}/profile", response_model=Profile360Response)
async def get_profile_360(
    constituent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> Profile360Response:
    """
    Get complete 360° profile for a constituent.
    Includes all related data with field-level permissions applied.
    Requires constituents.read permission.
    """
    field_checker = FieldPermissionChecker(db)
    query = (
        select(Constituent)
        .options(
            selectinload(Constituent.person),
            selectinload(Constituent.organisation),
            selectinload(Constituent.alumni_profile),
            selectinload(Constituent.donor_profile),
            selectinload(Constituent.contact_methods),
            selectinload(Constituent.addresses),
            selectinload(Constituent.communication_preferences),
            selectinload(Constituent.education_records),
            selectinload(Constituent.affiliations).selectinload(Affiliation.organisation),
            selectinload(Constituent.files),
            selectinload(Constituent.audit_events),
            selectinload(Constituent.hostel_history),
            selectinload(Constituent.academic_courses),
            selectinload(Constituent.semester_performance),
            selectinload(Constituent.gps_assignments),
            selectinload(Constituent.awards_recognition),
            selectinload(Constituent.scholarships_financial_aid),
            selectinload(Constituent.internships),
            selectinload(Constituent.placements),
            selectinload(Constituent.startups),
            selectinload(Constituent.ssac_records),
            selectinload(Constituent.positions_of_responsibility),
            selectinload(Constituent.publications),
            selectinload(Constituent.overseas_exposure),
            selectinload(Constituent.family_members),
            selectinload(Constituent.profile_photos),
        )
        .where(Constituent.id == constituent_id)
    )

    result = await db.execute(query)
    constituent = result.scalars().first()

    if not constituent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Constituent with id {constituent_id} not found",
        )

    user_perms = await field_checker.get_user_permissions(current_user.id)
    is_super = current_user.is_superuser

    def filter_entity(entity_type: str, data):
        if not data:
            return None
        d = data.model_dump() if hasattr(data, 'model_dump') else data
        return field_checker.filter_dict(entity_type, d, user_perms, is_super)

    def filter_list_entities(entity_type: str, data_list):
        return [filter_entity(entity_type, d) for d in data_list]

    # Restricted whole-record gating: SSAC conduct records and third-party
    # family data are withheld entirely without the respective permission.
    can_ssac = is_super or "ssac.read_restricted" in user_perms
    can_family = is_super or "people.read_family" in user_perms

    return Profile360Response(
        constituent=filter_entity("constituent", ConstituentResponse.model_validate(constituent)),
        person=filter_entity("person", PersonResponse.model_validate(constituent.person)) if constituent.person else None,
        organisation=filter_entity("organisation", OrganisationResponse.model_validate(constituent.organisation)) if constituent.organisation else None,
        alumni_profile=filter_entity("alumni_profile", AlumniProfileResponse.model_validate(constituent.alumni_profile)) if constituent.alumni_profile else None,
        donor_profile=filter_entity("donor_profile", DonorProfileResponse.model_validate(constituent.donor_profile)) if constituent.donor_profile else None,
        contact_methods=filter_list_entities("contact_method", [ContactMethodResponse.model_validate(cm) for cm in constituent.contact_methods]),
        addresses=filter_list_entities("address", [AddressResponse.model_validate(a) for a in constituent.addresses]),
        communication_preferences=filter_entity("communication_preferences", CommunicationPreferencesResponse.model_validate(constituent.communication_preferences)) if constituent.communication_preferences else None,
        education_records=filter_list_entities("education_record", [EducationRecordResponse.model_validate(er) for er in constituent.education_records]),
        affiliations=filter_list_entities("affiliation", [AffiliationResponse.model_validate(a) for a in constituent.affiliations]),
        files=filter_list_entities("file", [FileRecordResponse.model_validate(f) for f in constituent.files]),
        audit_events=[AuditEventResponse.model_validate(ae) for ae in constituent.audit_events],
        hostel_history=[HostelHistoryResponse.model_validate(h) for h in constituent.hostel_history],
        academic_courses=[AcademicCourseResponse.model_validate(c) for c in constituent.academic_courses],
        semester_performance=[SemesterPerformanceResponse.model_validate(s) for s in constituent.semester_performance],
        gps_assignments=[GpsAssignmentResponse.model_validate(g) for g in constituent.gps_assignments],
        awards_recognition=[AwardRecognitionResponse.model_validate(a) for a in constituent.awards_recognition],
        scholarships_financial_aid=[ScholarshipFinancialAidResponse.model_validate(s) for s in constituent.scholarships_financial_aid],
        internships=[InternshipResponse.model_validate(i) for i in constituent.internships],
        placements=[PlacementResponse.model_validate(p) for p in constituent.placements],
        startups=[StartupResponse.model_validate(s) for s in constituent.startups],
        ssac_records=[SsacRecordResponse.model_validate(s) for s in constituent.ssac_records] if can_ssac else [],
        positions_of_responsibility=[PositionOfResponsibilityResponse.model_validate(p) for p in constituent.positions_of_responsibility],
        publications=[PublicationResponse.model_validate(p) for p in constituent.publications],
        overseas_exposure=[OverseasExposureResponse.model_validate(o) for o in constituent.overseas_exposure],
        family_members=[FamilyMemberResponse.model_validate(f) for f in constituent.family_members] if can_family else [],
        profile_photos=sorted(
            (ProfilePhotoResponse.model_validate(p) for p in constituent.profile_photos),
            key=lambda p: (not p.is_primary, p.position, p.created_at),
        ),
    )


@router.get("/organisations/search", response_model=OrganisationSearchResponse)
async def search_organisations(
    q: str = Query(..., description="Organisation name to search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> OrganisationSearchResponse:
    """
    Search organisations across all affiliations (current and past).
    Returns each alumnus once with computed affiliation status.
    Requires constituents.read permission.
    """
    search_term = f"%{q.strip().lower()}%"

    query = (
        select(
            Constituent.id.label("constituent_id"),
            Constituent.display_name,
            AlumniProfile.roll_no,
            Affiliation.organisation_id,
            Organisation.legal_name,
            Organisation.normalised_name,
            Affiliation.organisation_name_raw,
            Affiliation.designation,
            Affiliation.start_date,
            Affiliation.end_date,
            Affiliation.is_current,
        )
        .select_from(Constituent)
        .join(AlumniProfile, Constituent.id == AlumniProfile.constituent_id)
        .join(Affiliation, Constituent.id == Affiliation.constituent_id)
        .outerjoin(Organisation, Affiliation.organisation_id == Organisation.constituent_id)
        .where(
            Constituent.kind == ConstituentKind.PERSON,
            or_(
                Organisation.normalised_name.ilike(search_term),
                Affiliation.organisation_name_raw.ilike(search_term),
            ),
        )
        .order_by(Constituent.display_name)
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    grouped = defaultdict(list)
    for row in rows:
        grouped[row.constituent_id].append(row)

    items = []
    for constituent_id, affiliations in grouped.items():
        has_current = any(a.is_current for a in affiliations)
        has_past = any(not a.is_current for a in affiliations)

        if has_current and has_past:
            status_label = "Current and past"
        elif has_current:
            status_label = "Current"
        else:
            status_label = "Past"

        first_aff = affiliations[0]
        org_name = first_aff.legal_name or first_aff.normalised_name or first_aff.organisation_name_raw or "Unknown"

        items.append(
            OrganisationSearchResult(
                constituent_id=constituent_id,
                display_name=first_aff.display_name,
                roll_no=first_aff.roll_no,
                affiliation_status=status_label,
                organisation_name=org_name,
                designation=first_aff.designation,
                start_date=first_aff.start_date,
                end_date=first_aff.end_date,
            )
        )

    total_pages = (total + page_size - 1) // page_size

    return OrganisationSearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
