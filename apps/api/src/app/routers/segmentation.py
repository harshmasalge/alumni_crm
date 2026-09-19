"""M1.1 Phase A — advanced people search over the generic filter DSL.

GET /constituents (M1) is preserved verbatim. Complex nested filtering uses
POST /constituents/search with a JSON filter tree; the backend validates the
tree, compiles it to EXISTS-based SQL (see app/services/segmentation.py),
and enforces the same RBAC + field-level permissions as every M1 read.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import check_constituents_read
from app.db.session import get_db
from app.models import AlumniProfile, Constituent, User
from app.core.field_permissions import FieldPermissionChecker
from app.schemas import (
    AdvancedSearchRequest,
    AdvancedSearchResponse,
    ConstituentResponse,
    FILTER_FIELD_REGISTRY,
)
from app.services.segmentation import (
    PhaseBReservedError,
    apply_m1_search_filters,
    compile_filter,
    validate_filter_tree,
)

router = APIRouter()


@router.get("/search/fields")
async def get_filter_field_registry(
    current_user: User = Depends(check_constituents_read),
) -> dict:
    """Single source of truth for filter UI: supported fields, operators, scopes."""
    return {"fields": FILTER_FIELD_REGISTRY}


@router.post("/search", response_model=AdvancedSearchResponse)
async def advanced_search(
    payload: AdvancedSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> AdvancedSearchResponse:
    field_checker = FieldPermissionChecker(db)
    query = select(Constituent)
    try:
        query = apply_m1_search_filters(
            query,
            q=payload.q,
            roll_no=payload.roll_no,
            kind=payload.kind,
            status=payload.status,
            organisation_q=payload.organisation_q,
            stale_threshold_days=payload.stale_threshold_days,
        )
        if payload.filter is not None:
            validate_filter_tree(payload.filter)
            query = query.where(compile_filter(payload.filter))
    except PhaseBReservedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if payload.sort_by not in ("display_name", "year_of_graduation"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort_by must be 'display_name' or 'year_of_graduation'.",
        )
    if payload.sort_dir not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort_dir must be 'asc' or 'desc'.",
        )

    if payload.sort_by == "year_of_graduation":
        query = query.outerjoin(AlumniProfile, AlumniProfile.constituent_id == Constituent.id)
        order_col = AlumniProfile.year_of_graduation
    else:
        order_col = Constituent.display_name
    query = query.order_by(order_col.asc() if payload.sort_dir == "asc" else order_col.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((payload.page - 1) * payload.page_size).limit(payload.page_size)
    result = await db.execute(query)
    constituents = result.scalars().all()

    total_pages = (total + payload.page_size - 1) // payload.page_size

    items = [ConstituentResponse.model_validate(c) for c in constituents]
    user_perms = await field_checker.get_user_permissions(current_user.id)
    items = field_checker.filter_list(
        "constituent", [i.model_dump() for i in items], user_perms, current_user.is_superuser
    )

    return AdvancedSearchResponse(
        items=[ConstituentResponse(**i) for i in items],
        total=total,
        page=payload.page,
        page_size=payload.page_size,
        total_pages=total_pages,
    )
