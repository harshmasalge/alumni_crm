"""Profile write workflows: full edit coverage for the 360° profile.

Identity, alumni, contact, and address blocks are edited in place (with
validation); history blocks (education, affiliations, T-tables) are
append-only — new rows never overwrite prior rows. Adding a new current
affiliation closes the previous current one (preserved as past history)
and every write refreshes `last_substantive_profile_update_at`.
Roll Number is immutable and has no write path by design. All endpoints
enforce server-side permissions; the audit middleware records each write
with the actor.
"""

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    check_constituents_read,
    check_constituents_write,
    check_family_write,
    check_ssac_write,
)
from app.db.session import get_db
from app.services.storage import get_storage_backend
from app.models import (
    AcademicCourse,
    Address,
    Affiliation,
    AlumniProfile,
    AwardRecognition,
    CommunicationPreferences,
    Constituent,
    ConstituentKind,
    ConstituentStatus,
    ContactMethod,
    EducationRecord,
    FamilyMember,
    Gender,
    GpsAssignment,
    HostelHistory,
    Internship,
    OverseasExposure,
    Person,
    Placement,
    PositionOfResponsibility,
    ProfilePhoto,
    Publication,
    ScholarshipFinancialAid,
    SemesterPerformance,
    SsacRecord,
    Startup,
    User,
)
from app.schemas import (
    AcademicCourseCreate,
    AcademicCourseResponse,
    AddressBase,
    AddressResponse,
    AffiliationBase,
    AffiliationResponse,
    AlumniProfileResponse,
    AlumniProfileUpdate,
    AwardRecognitionCreate,
    AwardRecognitionResponse,
    CommunicationPreferencesBase,
    CommunicationPreferencesResponse,
    ConstituentResponse,
    ConstituentUpdate,
    ContactMethodCreateIn,
    ContactMethodResponse,
    EducationRecordBase,
    EducationRecordResponse,
    FamilyMemberCreate,
    FamilyMemberResponse,
    GpsAssignmentCreate,
    GpsAssignmentResponse,
    HostelHistoryCreate,
    HostelHistoryResponse,
    InternshipCreate,
    InternshipResponse,
    OverseasExposureCreate,
    OverseasExposureResponse,
    PersonResponse,
    PersonUpdate,
    ProfilePhotoResponse,
    ProfilePhotoUpdate,
    PlacementCreate,
    PlacementResponse,
    PositionOfResponsibilityCreate,
    PositionOfResponsibilityResponse,
    PublicationCreate,
    PublicationResponse,
    ScholarshipFinancialAidCreate,
    ScholarshipFinancialAidResponse,
    SemesterPerformanceCreate,
    SemesterPerformanceResponse,
    SsacRecordCreate,
    SsacRecordResponse,
    StartupCreate,
    StartupResponse,
)

router = APIRouter()


async def _get_person_constituent(db: AsyncSession, constituent_id: UUID) -> Constituent:
    result = await db.execute(select(Constituent).where(Constituent.id == constituent_id))
    constituent = result.scalars().first()
    if not constituent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Constituent with id {constituent_id} not found",
        )
    if constituent.kind != ConstituentKind.PERSON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Education and affiliation history applies to person constituents only",
        )
    return constituent


def _touch(constituent: Constituent) -> None:
    constituent.last_substantive_profile_update_at = datetime.now(timezone.utc)


@router.post(
    "/{constituent_id}/education",
    response_model=EducationRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_education_record(
    constituent_id: UUID,
    payload: EducationRecordBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> EducationRecordResponse:
    constituent = await _get_person_constituent(db, constituent_id)

    if (
        payload.start_year is not None
        and payload.completion_year is not None
        and payload.completion_year < payload.start_year
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="completion_year cannot precede start_year",
        )

    record = EducationRecord(constituent_id=constituent.id, **payload.model_dump())
    _touch(constituent)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return EducationRecordResponse.model_validate(record)


@router.post(
    "/{constituent_id}/affiliations",
    response_model=AffiliationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_affiliation(
    constituent_id: UUID,
    payload: AffiliationBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> AffiliationResponse:
    constituent = await _get_person_constituent(db, constituent_id)

    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot precede start_date",
        )

    if payload.is_current:
        result = await db.execute(
            select(Affiliation).where(
                Affiliation.constituent_id == constituent.id,
                Affiliation.is_current.is_(True),
            )
        )
        for previous in result.scalars().all():
            previous.is_current = False
            if previous.end_date is None:
                previous.end_date = payload.start_date or date.today()

    record = Affiliation(constituent_id=constituent.id, **payload.model_dump())
    _touch(constituent)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return AffiliationResponse.model_validate(record)


async def _reload(model, db: AsyncSession, record_id: UUID):
    """Re-fetch after commit (see admin router: avoids expired-attribute
    access outside the async greenlet context)."""
    db.expunge_all()
    result = await db.execute(select(model).where(model.id == record_id))
    return result.scalars().first()


async def _reload_by_constituent(model, db: AsyncSession, constituent_id: UUID):
    """Same as _reload for tables keyed by constituent_id
    (person, alumni profile, communication preferences)."""
    db.expunge_all()
    result = await db.execute(select(model).where(model.constituent_id == constituent_id))
    return result.scalars().first()


@router.patch(
    "/{constituent_id}",
    response_model=ConstituentResponse,
)
async def update_constituent(
    constituent_id: UUID,
    payload: ConstituentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> ConstituentResponse:
    result = await db.execute(select(Constituent).where(Constituent.id == constituent_id))
    constituent = result.scalars().first()
    if not constituent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Constituent with id {constituent_id} not found",
        )
    if payload.status is not None:
        try:
            constituent.status = ConstituentStatus(payload.status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {payload.status}",
            )
    if payload.display_name is not None:
        constituent.display_name = payload.display_name.strip()
        constituent.normalised_display_name = payload.display_name.strip().lower()
    if payload.notes is not None:
        constituent.notes = payload.notes
    _touch(constituent)
    await db.commit()
    constituent = await _reload(Constituent, db, constituent.id)
    return ConstituentResponse.model_validate(constituent)


@router.patch(
    "/{constituent_id}/person",
    response_model=PersonResponse,
)
async def update_person(
    constituent_id: UUID,
    payload: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> PersonResponse:
    constituent = await _get_person_constituent(db, constituent_id)
    if payload.gender is not None:
        try:
            Gender(payload.gender.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid gender: {payload.gender}",
            )
        payload = payload.model_copy(update={"gender": payload.gender.upper()})

    result = await db.execute(select(Person).where(Person.constituent_id == constituent.id))
    person = result.scalars().first()
    if person is None:
        if not payload.full_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full_name is required to create the person record",
            )
        person = Person(
            constituent_id=constituent.id,
            first_name=payload.first_name or payload.full_name.split()[0],
            full_name=payload.full_name,
        )
        db.add(person)
    for field in ("first_name", "full_name", "gender", "date_of_birth",
                  "blood_group", "spouse_name", "profile_photo_file_id"):
        value = getattr(payload, field)
        if value is not None:
            setattr(person, field, value)
    _touch(constituent)
    await db.commit()
    person = await _reload_by_constituent(Person, db, person.constituent_id)
    return PersonResponse.model_validate(person)


@router.patch(
    "/{constituent_id}/alumni-profile",
    response_model=AlumniProfileResponse,
)
async def update_alumni_profile(
    constituent_id: UUID,
    payload: AlumniProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> AlumniProfileResponse:
    """All alumni fields except Roll Number, which is immutable by design."""
    constituent = await _get_person_constituent(db, constituent_id)
    result = await db.execute(
        select(AlumniProfile).where(AlumniProfile.constituent_id == constituent.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No alumni profile for this constituent",
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    _touch(constituent)
    await db.commit()
    profile = await _reload_by_constituent(AlumniProfile, db, profile.constituent_id)
    return AlumniProfileResponse.model_validate(profile)


@router.post(
    "/{constituent_id}/contact-methods",
    response_model=ContactMethodResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact_method(
    constituent_id: UUID,
    payload: ContactMethodCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> ContactMethodResponse:
    constituent = await _get_person_constituent(db, constituent_id)
    record = ContactMethod(
        constituent_id=constituent.id,
        contact_type=payload.contact_type,
        value=payload.value.strip(),
        normalised_value=payload.value.strip().lower(),
        is_primary=payload.is_primary,
        is_verified=payload.is_verified,
        whatsapp_linked=payload.whatsapp_linked,
        is_active=payload.is_active,
    )
    _touch(constituent)
    db.add(record)
    await db.commit()
    record = await _reload(ContactMethod, db, record.id)
    return ContactMethodResponse.model_validate(record)


@router.post(
    "/{constituent_id}/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_address(
    constituent_id: UUID,
    payload: AddressBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> AddressResponse:
    constituent = await _get_person_constituent(db, constituent_id)
    record = Address(constituent_id=constituent.id, **payload.model_dump())
    _touch(constituent)
    db.add(record)
    await db.commit()
    record = await _reload(Address, db, record.id)
    return AddressResponse.model_validate(record)


@router.put(
    "/{constituent_id}/communication-preferences",
    response_model=CommunicationPreferencesResponse,
)
async def set_communication_preferences(
    constituent_id: UUID,
    payload: CommunicationPreferencesBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> CommunicationPreferencesResponse:
    constituent = await _get_person_constituent(db, constituent_id)
    result = await db.execute(
        select(CommunicationPreferences).where(
            CommunicationPreferences.constituent_id == constituent.id
        )
    )
    prefs = result.scalars().first()
    if prefs is None:
        prefs = CommunicationPreferences(constituent_id=constituent.id, **payload.model_dump())
        db.add(prefs)
    else:
        for field, value in payload.model_dump().items():
            setattr(prefs, field, value)
    _touch(constituent)
    await db.commit()
    prefs = await _reload_by_constituent(CommunicationPreferences, db, prefs.constituent_id)
    return CommunicationPreferencesResponse.model_validate(prefs)


def _register_child_create(
    slug: str,
    model,
    create_schema: type[BaseModel],
    response_schema: type[BaseModel],
    permission_checker=None,
    extra_validate=None,
):
    """Register POST /{constituent_id}/<slug> for a T-table child entity.

    Records are appended with the path constituent as owner; each write
    refreshes profile freshness. Restricted tables pass their own
    permission checker (SSAC, family); the rest use constituents.write.
    """
    checker = permission_checker or check_constituents_write

    async def create_child(
        constituent_id: UUID,
        payload: create_schema,  # type: ignore[valid-type]
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(checker),
    ):
        constituent = await _get_person_constituent(db, constituent_id)
        if extra_validate is not None:
            extra_validate(payload)
        record = model(constituent_id=constituent.id, **payload.model_dump())
        _touch(constituent)
        db.add(record)
        await db.commit()
        record = await _reload(model, db, record.id)
        return response_schema.model_validate(record)

    create_child.__name__ = f"create_{model.__tablename__}"
    router.post(
        "/{constituent_id}/" + slug,
        response_model=response_schema,
        status_code=status.HTTP_201_CREATED,
    )(create_child)


def _validate_overseas(payload) -> None:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot precede start_date",
        )


for _slug, _model, _create, _response, _checker, _validate in [
    ("hostel-history", HostelHistory, HostelHistoryCreate, HostelHistoryResponse, None, None),
    ("academic-courses", AcademicCourse, AcademicCourseCreate, AcademicCourseResponse, None, None),
    ("semester-performance", SemesterPerformance, SemesterPerformanceCreate, SemesterPerformanceResponse, None, None),
    ("gps-assignments", GpsAssignment, GpsAssignmentCreate, GpsAssignmentResponse, None, None),
    ("awards", AwardRecognition, AwardRecognitionCreate, AwardRecognitionResponse, None, None),
    ("scholarships", ScholarshipFinancialAid, ScholarshipFinancialAidCreate, ScholarshipFinancialAidResponse, None, None),
    ("internships", Internship, InternshipCreate, InternshipResponse, None, None),
    ("placements", Placement, PlacementCreate, PlacementResponse, None, None),
    ("startups", Startup, StartupCreate, StartupResponse, None, None),
    ("ssac-records", SsacRecord, SsacRecordCreate, SsacRecordResponse, check_ssac_write, None),
    ("responsibilities", PositionOfResponsibility, PositionOfResponsibilityCreate, PositionOfResponsibilityResponse, None, None),
    ("publications", Publication, PublicationCreate, PublicationResponse, None, None),
    ("overseas-exposure", OverseasExposure, OverseasExposureCreate, OverseasExposureResponse, None, _validate_overseas),
    ("family-members", FamilyMember, FamilyMemberCreate, FamilyMemberResponse, check_family_write, None),
]:
    _register_child_create(_slug, _model, _create, _response, _checker, _validate)
del _slug, _model, _create, _response, _checker, _validate


MAX_PHOTO_BYTES = 5 * 1024 * 1024
ALLOWED_PHOTO_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post(
    "/{constituent_id}/photos",
    response_model=list[ProfilePhotoResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_profile_photos(
    constituent_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> list[ProfilePhotoResponse]:
    """Upload one or more profile photos. Raster images only (SVG rejected:
    served bytes could execute script in the browser origin)."""
    constituent = await _get_person_constituent(db, constituent_id)
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded",
        )

    backend = get_storage_backend()
    result = await db.execute(
        select(func.max(ProfilePhoto.position)).where(
            ProfilePhoto.constituent_id == constituent.id
        )
    )
    position = (result.scalar() or -1) + 1

    created: list[ProfilePhoto] = []
    existing_count_result = await db.execute(
        select(func.count(ProfilePhoto.id)).where(
            ProfilePhoto.constituent_id == constituent.id
        )
    )
    first_is_primary = (existing_count_result.scalar() or 0) == 0
    for index, upload in enumerate(files):
        data = await upload.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"{upload.filename or 'file'} exceeds the 5 MB limit",
            )
        mime = (upload.content_type or "").split(";")[0].strip().lower()
        if mime not in ALLOWED_PHOTO_MIME:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{upload.filename or 'file'} is not an accepted image (JPEG/PNG/WebP/GIF)",
            )
        key = backend.save(data, upload.filename or "photo")
        created.append(
            ProfilePhoto(
                constituent_id=constituent.id,
                storage_key=key,
                original_name=upload.filename or "photo",
                mime_type=mime,
                size_bytes=len(data),
                position=position + index,
                is_primary=first_is_primary and index == 0,
                uploaded_by=current_user.id,
            )
        )
    _touch(constituent)
    db.add_all(created)
    await db.commit()
    out = []
    for record in created:
        record = await _reload(ProfilePhoto, db, record.id)
        out.append(ProfilePhotoResponse.model_validate(record))
    return out


@router.get("/{constituent_id}/photos/{photo_id}/content")
async def serve_profile_photo(
    constituent_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> Response:
    result = await db.execute(
        select(ProfilePhoto).where(
            ProfilePhoto.id == photo_id,
            ProfilePhoto.constituent_id == constituent_id,
        )
    )
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )
    try:
        data = get_storage_backend().load(photo.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo bytes missing from storage",
        )
    return Response(content=data, media_type=photo.mime_type)


@router.patch(
    "/{constituent_id}/photos/{photo_id}",
    response_model=ProfilePhotoResponse,
)
async def update_profile_photo(
    constituent_id: UUID,
    photo_id: UUID,
    payload: ProfilePhotoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> ProfilePhotoResponse:
    result = await db.execute(
        select(ProfilePhoto).where(
            ProfilePhoto.id == photo_id,
            ProfilePhoto.constituent_id == constituent_id,
        )
    )
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )
    if payload.is_primary is True:
        others = await db.execute(
            select(ProfilePhoto).where(
                ProfilePhoto.constituent_id == constituent_id,
                ProfilePhoto.id != photo_id,
            )
        )
        for other in others.scalars().all():
            other.is_primary = False
        photo.is_primary = True
    elif payload.is_primary is False:
        photo.is_primary = False
    constituent = await _get_person_constituent(db, constituent_id)
    _touch(constituent)
    await db.commit()
    photo = await _reload(ProfilePhoto, db, photo.id)
    return ProfilePhotoResponse.model_validate(photo)


@router.delete(
    "/{constituent_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_profile_photo(
    constituent_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> None:
    result = await db.execute(
        select(ProfilePhoto).where(
            ProfilePhoto.id == photo_id,
            ProfilePhoto.constituent_id == constituent_id,
        )
    )
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )
    key = photo.storage_key
    was_primary = photo.is_primary
    await db.delete(photo)
    constituent = await _get_person_constituent(db, constituent_id)
    if was_primary:
        remaining = await db.execute(
            select(ProfilePhoto)
            .where(ProfilePhoto.constituent_id == constituent_id)
            .order_by(ProfilePhoto.position, ProfilePhoto.created_at)
            .limit(1)
        )
        promoted = remaining.scalars().first()
        if promoted is not None:
            promoted.is_primary = True
    _touch(constituent)
    await db.commit()
    get_storage_backend().delete(key)
    return None
