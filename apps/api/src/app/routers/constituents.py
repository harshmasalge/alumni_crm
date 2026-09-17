from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models import (
    Address,
    Affiliation,
    AlumniProfile,
    AuditEvent,
    CommunicationPreferences,
    Constituent,
    ContactMethod,
    ConstituentKind,
    ConstituentStatus,
    DonorProfile,
    EducationRecord,
    FileRecord,
    Organisation,
    Person,
)
from app.schemas import (
    AddressResponse,
    AffiliationResponse,
    AlumniProfileResponse,
    AuditEventResponse,
    CommunicationPreferencesResponse,
    ConstituentResponse,
    ConstituentSearchParams,
    ContactMethodResponse,
    DonorProfileResponse,
    EducationRecordResponse,
    FileRecordResponse,
    OrganisationResponse,
    OrganisationSearchParams,
    OrganisationSearchResponse,
    OrganisationSearchResult,
    PaginatedResponse,
    PersonResponse,
    Profile360Response,
    StaleProfileCountResponse,
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
) -> PaginatedResponse:
    """
    Search constituents by name (partial match) or exact roll number.
    """
    # Build base query
    query = select(Constituent)

    # Apply filters
    conditions = []

    if roll_no:
        # Exact roll number match - join with alumni_profiles
        subquery = select(AlumniProfile.constituent_id).where(
            AlumniProfile.roll_no == roll_no.strip().upper()
        )
        conditions.append(Constituent.id.in_(subquery))
    elif q:
        # Partial name search on normalised_display_name
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

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.order_by(Constituent.display_name).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    constituents = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[ConstituentResponse.model_validate(c) for c in constituents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stale-profiles-count", response_model=StaleProfileCountResponse)
async def get_stale_profiles_count(
    threshold_days: int = Query(365, ge=1),
    db: AsyncSession = Depends(get_db),
) -> StaleProfileCountResponse:
    """
    Get count of alumni with no substantive profile update for more than threshold_days.
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
) -> PaginatedResponse:
    """
    Get paginated list of alumni with no substantive profile update for more than threshold_days.
    """
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

    return PaginatedResponse(
        items=[ConstituentResponse.model_validate(c) for c in constituents],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{constituent_id}/profile", response_model=Profile360Response)
async def get_profile_360(
    constituent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Profile360Response:
    """
    Get complete 360° profile for a constituent.
    Includes all related data: person/organisation details, alumni/donor profile,
    contact methods, addresses, education records, affiliations, files, and audit events.
    """
    # Load constituent with all relationships
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

    # Build response manually to ensure all nested data is loaded
    return Profile360Response(
        constituent=ConstituentResponse.model_validate(constituent),
        person=PersonResponse.model_validate(constituent.person) if constituent.person else None,
        organisation=OrganisationResponse.model_validate(constituent.organisation) if constituent.organisation else None,
        alumni_profile=AlumniProfileResponse.model_validate(constituent.alumni_profile) if constituent.alumni_profile else None,
        donor_profile=DonorProfileResponse.model_validate(constituent.donor_profile) if constituent.donor_profile else None,
        contact_methods=[ContactMethodResponse.model_validate(cm) for cm in constituent.contact_methods],
        addresses=[AddressResponse.model_validate(a) for a in constituent.addresses],
        communication_preferences=CommunicationPreferencesResponse.model_validate(constituent.communication_preferences) if constituent.communication_preferences else None,
        education_records=[EducationRecordResponse.model_validate(er) for er in constituent.education_records],
        affiliations=[AffiliationResponse.model_validate(a) for a in constituent.affiliations],
        files=[FileRecordResponse.model_validate(f) for f in constituent.files],
        audit_events=[AuditEventResponse.model_validate(ae) for ae in constituent.audit_events],
    )


@router.get("/organisations/search", response_model=OrganisationSearchResponse)
async def search_organisations(
    q: str = Query(..., description="Organisation name to search"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> OrganisationSearchResponse:
    """
    Search organisations across all affiliations (current and past).
    Returns each alumnus once with computed affiliation status.
    """
    search_term = f"%{q.strip().lower()}%"

    # Query affiliations matching the organisation name (normalised or raw)
    # Join with organisations table and constituents
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

    # Group by constituent to compute affiliation status
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

        # Use the first matching affiliation for display
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