"""M1.1 Phase A — staff-managed segmentation vocabularies.

One generic table serves every controlled list (industry, company_type,
function, seniority_level, ...). Values are advisory, never FK-enforced, so
taxonomy edits cannot invalidate existing constituent rows.

Authorization reuses the existing gates (ADR-005): read requires
constituents.read, writes require constituents.write — no new permissions in
Phase A. Every write is explicitly audited with before/after states.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.auth import check_constituents_read, check_constituents_write
from app.db.session import get_db
from app.models import Affiliation, Organisation, Taxonomy, User
from app.schemas import (
    TaxonomyCreate,
    TaxonomyListResponse,
    TaxonomyResponse,
    TaxonomyUpdate,
)

router = APIRouter(tags=["taxonomies"])

# Where each category is referenced (case-insensitive). Unknown categories
# have no references and are always safe to delete.
REFERENCE_COLUMNS = {
    "industry": Affiliation.sector,
    "company_type": Organisation.company_type,
    "function": Affiliation.function,
    "seniority_level": Affiliation.seniority_level,
}

CATEGORY_PATTERN = r"^[a-z][a-z0-9_]{1,49}$"


async def _usage_count(db: AsyncSession, category: str, normalised_value: str) -> int:
    column = REFERENCE_COLUMNS.get(category)
    if column is None:
        return 0
    result = await db.execute(
        select(func.count()).where(func.lower(column) == normalised_value)
    )
    return result.scalar() or 0


async def _usage_map(db: AsyncSession, rows: list[Taxonomy]) -> dict[tuple[str, str], int]:
    """Batch usage counts per (category, normalised_value) with one aggregate
    query per referenced table shape."""
    usage: dict[tuple[str, str], int] = {}
    by_model: dict[str, list[str]] = {}
    for row in rows:
        if row.category in REFERENCE_COLUMNS:
            by_model.setdefault(row.category, []).append(row.normalised_value)
    for category, values in by_model.items():
        column = REFERENCE_COLUMNS[category]
        result = await db.execute(
            select(func.lower(column), func.count()).where(
                func.lower(column).in_(values)
            ).group_by(func.lower(column))
        )
        for normalised, count in result.all():
            usage[(category, normalised)] = count
    return usage


def _to_response(row: Taxonomy, usage: int = 0) -> TaxonomyResponse:
    response = TaxonomyResponse.model_validate(row)
    response.usage_count = usage
    return response


async def _get_or_404(db: AsyncSession, taxonomy_id: UUID) -> Taxonomy:
    result = await db.execute(select(Taxonomy).where(Taxonomy.id == taxonomy_id))
    row = result.scalars().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taxonomy value with id {taxonomy_id} not found",
        )
    return row


async def _reload(db: AsyncSession, taxonomy_id: UUID) -> Taxonomy:
    """Re-fetch after commit (project convention: avoids expired-attribute
    access outside the async greenlet context)."""
    db.expunge_all()
    return await _get_or_404(db, taxonomy_id)


@router.get("", response_model=TaxonomyListResponse)
async def list_taxonomies(
    category: Optional[str] = Query(None, description="Filter by category slug"),
    include_inactive: bool = Query(False, description="Include deactivated values"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> TaxonomyListResponse:
    query = select(Taxonomy).order_by(Taxonomy.category, Taxonomy.value)
    if category:
        query = query.where(Taxonomy.category == category.strip().lower())
    if not include_inactive:
        query = query.where(Taxonomy.is_active.is_(True))
    result = await db.execute(query)
    rows = list(result.scalars().all())
    usage = await _usage_map(db, rows)
    return TaxonomyListResponse(
        items=[
            _to_response(r, usage.get((r.category, r.normalised_value), 0)) for r in rows
        ],
        total=len(rows),
    )


@router.get("/{taxonomy_id}", response_model=TaxonomyResponse)
async def get_taxonomy(
    taxonomy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> TaxonomyResponse:
    row = await _get_or_404(db, taxonomy_id)
    return _to_response(
        row, await _usage_count(db, row.category, row.normalised_value)
    )


@router.post("", response_model=TaxonomyResponse, status_code=status.HTTP_201_CREATED)
async def create_taxonomy(
    payload: TaxonomyCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> TaxonomyResponse:
    import re

    category = payload.category.strip().lower()
    if not re.match(CATEGORY_PATTERN, category):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="category must be a lowercase slug (letters, digits, underscores).",
        )
    value = payload.value.strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="value must not be blank.",
        )
    existing = await db.execute(
        select(Taxonomy).where(
            Taxonomy.category == category,
            Taxonomy.normalised_value == value.lower(),
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Value '{value}' already exists in category '{category}'.",
        )
    row = Taxonomy(category=category, value=value, normalised_value=value.lower())
    db.add(row)
    await db.commit()
    row = await _reload(db, row.id)
    await log_audit(
        db,
        actor=current_user,
        entity_type="taxonomy",
        entity_id=row.id,
        action="TAXONOMY_CREATE",
        after={"category": row.category, "value": row.value},
        request=request,
    )
    await db.commit()
    return _to_response(row, 0)


@router.patch("/{taxonomy_id}", response_model=TaxonomyResponse)
async def update_taxonomy(
    taxonomy_id: UUID,
    payload: TaxonomyUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> TaxonomyResponse:
    row = await _get_or_404(db, taxonomy_id)
    before = {"value": row.value, "is_active": row.is_active}
    if payload.value is not None:
        value = payload.value.strip()
        if not value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="value must not be blank.",
            )
        conflict = await db.execute(
            select(Taxonomy).where(
                Taxonomy.category == row.category,
                Taxonomy.normalised_value == value.lower(),
                Taxonomy.id != row.id,
            )
        )
        if conflict.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Value '{value}' already exists in category '{row.category}'.",
            )
        # Renaming a referenced value does not rewrite constituent rows
        # (advisory vocabulary): the usage count travels to the new value
        # only for future matches. Recorded in the audit trail.
        row.value = value
        row.normalised_value = value.lower()
    if payload.is_active is not None:
        # Soft-deactivation is always allowed — it is the preferred path
        # for referenced values. Existing rows keep their stored text and
        # keep matching; the value just stops being suggested for new data.
        row.is_active = payload.is_active
    await db.commit()
    row = await _reload(db, row.id)
    await log_audit(
        db,
        actor=current_user,
        entity_type="taxonomy",
        entity_id=row.id,
        action="TAXONOMY_UPDATE",
        before=before,
        after={"value": row.value, "is_active": row.is_active},
        request=request,
    )
    await db.commit()
    return _to_response(
        row, await _usage_count(db, row.category, row.normalised_value)
    )


@router.delete("/{taxonomy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_taxonomy(
    taxonomy_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> None:
    row = await _get_or_404(db, taxonomy_id)
    in_use = await _usage_count(db, row.category, row.normalised_value)
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Value '{row.value}' is referenced by {in_use} record(s) and cannot "
                "be deleted. Deactivate it instead once records are re-pointed."
            ),
        )
    before = {"category": row.category, "value": row.value}
    entity_id = row.id
    await db.delete(row)
    await log_audit(
        db,
        actor=current_user,
        entity_type="taxonomy",
        entity_id=entity_id,
        action="TAXONOMY_DELETE",
        before=before,
        request=request,
    )
    await db.commit()
    return None
