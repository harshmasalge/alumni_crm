"""M1.1 Phase C — permission-aware people export (synchronous XLSX).

The backend re-evaluates the population (explicit IDs are validated,
filters re-run, group members read server-side) and intersects requested
columns with the caller's field permissions. Frontend field lists are
advisory only: direct API calls cannot widen the population or the columns.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.auth import check_constituents_export
from app.core.field_permissions import FieldPermissionChecker
from app.db.session import get_db
from app.models import User
from app.schemas import (
    ExportFieldCatalogResponse,
    ExportFieldInfo,
    ExportPeopleRequest,
)
from app.services.exports import (
    EXPORTABLE_FIELDS,
    SECTION_GATES,
    build_row_snapshots,
    load_export_rows,
    render_xlsx,
    required_permissions,
    resolve_export_fields,
    resolve_export_population,
)
from app.services.segmentation import PhaseBReservedError

router = APIRouter(tags=["exports"])


@router.get("/people/fields", response_model=ExportFieldCatalogResponse)
async def export_field_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_export),
) -> ExportFieldCatalogResponse:
    checker = FieldPermissionChecker(db)
    perms = await checker.get_user_permissions(current_user.id)
    return ExportFieldCatalogResponse(
        items=[
            ExportFieldInfo(
                key=e["key"],
                label=e["label"],
                allowed=checker.can_access_field(
                    e["entity"], e["field"], perms, current_user.is_superuser
                ) and (
                    e.get("section") not in SECTION_GATES
                    or current_user.is_superuser
                    or any(p in perms for p in SECTION_GATES[e["section"]])
                ),
                requires=required_permissions(e["entity"], e["field"], e.get("section")),
            )
            for e in EXPORTABLE_FIELDS
        ]
    )


@router.post("/people")
async def export_people(
    payload: ExportPeopleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_constituents_export),
) -> Response:
    checker = FieldPermissionChecker(db)
    perms = await checker.get_user_permissions(current_user.id)
    try:
        allowed, dropped = resolve_export_fields(
            checker, payload.fields, perms, current_user.is_superuser
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    try:
        ids, summary, invalid = await resolve_export_population(
            db,
            actor=current_user,
            constituent_ids=payload.constituent_ids,
            q=payload.q,
            roll_no=payload.roll_no,
            organisation_q=payload.organisation_q,
            stale_threshold_days=payload.stale_threshold_days,
            filter=payload.filter,
            group_id=payload.group_id,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PhaseBReservedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except OverflowError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    constituents = await load_export_rows(db, ids)
    rows = build_row_snapshots(constituents, checker, perms, current_user.is_superuser)
    content = render_xlsx(allowed, rows)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    await log_audit(
        db,
        actor=current_user,
        entity_type="export",
        entity_id=current_user.id,
        action="EXPORT_PEOPLE",
        after={
            "population": summary,
            "fields_requested": payload.fields,
            "fields_allowed": [e["key"] for e in allowed],
            "fields_dropped": dropped,
            "row_count": len(rows),
            "invalid_ids": len(invalid),
        },
        request=request,
    )
    await db.commit()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="people-export-{stamp}.xlsx"'},
    )
