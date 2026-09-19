"""M1.1 Phase A — organisation master-data read/write surface.

Resolved organisation records (company_type, sector, HQ location) back the
company-type and headquarters filters alongside raw affiliation text. Reads
ride the existing organisation search/360 paths; this router adds the
smallest manageable surface: fetch one master record and patch its
descriptive fields. Creation/matching of resolved records against raw
affiliation text belongs to the M3 import workbench, not Phase A.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.auth import check_constituents_read, check_constituents_write
from app.db.session import get_db
from app.models import Organisation, User
from app.schemas import OrganisationResponse, OrganisationUpdate

router = APIRouter(tags=["organisations"])


async def _get_or_404(db: AsyncSession, organisation_id: UUID) -> Organisation:
    result = await db.execute(
        select(Organisation).where(Organisation.constituent_id == organisation_id)
    )
    org = result.scalars().first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organisation with id {organisation_id} not found",
        )
    return org


@router.get("/{organisation_id}", response_model=OrganisationResponse)
async def get_organisation(
    organisation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_read),
) -> OrganisationResponse:
    return OrganisationResponse.model_validate(await _get_or_404(db, organisation_id))


@router.patch("/{organisation_id}", response_model=OrganisationResponse)
async def update_organisation(
    organisation_id: UUID,
    payload: OrganisationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_write),
) -> OrganisationResponse:
    org = await _get_or_404(db, organisation_id)
    before = {
        "company_type": org.company_type,
        "sector": org.sector,
        "website_url": org.website_url,
        "hq_city": org.hq_city,
        "hq_state": org.hq_state,
        "hq_country": org.hq_country,
    }
    for field in ("company_type", "sector", "website_url", "hq_city", "hq_state", "hq_country"):
        value = getattr(payload, field)
        if value is not None:
            setattr(org, field, value.strip() if isinstance(value, str) else value)
    await db.commit()
    db.expunge_all()
    org = await _get_or_404(db, organisation_id)
    await log_audit(
        db,
        actor=current_user,
        entity_type="organisation",
        entity_id=org.constituent_id,
        action="ORG_MASTER_UPDATE",
        before=before,
        after={
            "company_type": org.company_type,
            "sector": org.sector,
            "website_url": org.website_url,
            "hq_city": org.hq_city,
            "hq_state": org.hq_state,
            "hq_country": org.hq_country,
        },
        request=request,
    )
    await db.commit()
    return OrganisationResponse.model_validate(org)
