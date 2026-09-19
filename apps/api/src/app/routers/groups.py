"""M1.1 Phase B1 — groups domain API (backend foundation, no UI).

Two population semantics, never mixed: explicit constituent-ID lists vs
server-side filter definitions re-evaluated at execution time. Membership
is current-state + UNIQUE(group, constituent) so every add path is
idempotent. Rule approval and membership approval are separate endpoints
with separate permission checks; self-approval is rejected (no bypass).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.auth import (
    check_groups_approve,
    check_groups_create,
    check_groups_deactivate,
    check_groups_manage_members,
    check_groups_manage_rules,
    check_groups_read,
    check_groups_update,
)
from app.core.field_permissions import FieldPermissionChecker
from app.db.session import get_db
from app.models import (
    Constituent,
    ConstituentKind,
    Group,
    GroupMembership,
    GroupMembershipProposal,
    GroupRuleVersion,
    GroupStatus,
    GroupType,
    ProposalAction,
    ProposalStatus,
    RuleVersionStatus,
    User,
)
from app.schemas import (
    EvaluationSummary,
    GroupCreate,
    GroupListResponse,
    GroupMemberListResponse,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
    MaterializeResponse,
    MemberAddRequest,
    MemberAddResponse,
    PopulationPreviewRequest,
    PopulationPreviewResponse,
    ProposalDecisionRequest,
    ProposalDecisionResponse,
    ProposalListResponse,
    ProposalResponse,
    RuleApprovalResponse,
    RuleProposeRequest,
    RuleVersionResponse,
)
from app.services.groups import (
    active_rule_version,
    current_member_ids,
    evaluate_rule,
    group_counts,
    matched_constituent_ids,
    matched_population_ids,
    pending_rule_version,
    resolve_ids,
)
from app.services.segmentation import PhaseBReservedError, validate_filter_tree

router = APIRouter(tags=["groups"])


# -- helpers ---------------------------------------------------------------

async def _get_group_or_404(db: AsyncSession, group_id: UUID) -> Group:
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalars().first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id {group_id} not found",
        )
    return group


def _require_active(group: Group) -> None:
    if group.status != GroupStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group '{group.name}' is {group.status.value}; reactivate it first.",
        )


def _require_rule_based(group: Group) -> None:
    if group.type != GroupType.RULE_BASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group '{group.name}' is Manual; rules apply to rule-based groups only.",
        )


def _require_manual(group: Group) -> None:
    if group.type != GroupType.MANUAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Group '{group.name}' is rule-based: membership changes only via "
                "approved-rule proposals, never direct edits."
            ),
        )


async def _reload_group(db: AsyncSession, group_id: UUID) -> Group:
    db.expunge_all()
    return await _get_group_or_404(db, group_id)


async def _shape(db: AsyncSession, group: Group) -> GroupResponse:
    counts = await group_counts(db, group.id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        type=group.type.value,
        status=group.status.value,
        created_by=group.created_by,
        created_at=group.created_at,
        updated_at=group.updated_at,
        **counts,
    )


async def _rule_or_404(db: AsyncSession, group_id: UUID, version: int) -> GroupRuleVersion:
    result = await db.execute(
        select(GroupRuleVersion).where(
            GroupRuleVersion.group_id == group_id,
            GroupRuleVersion.version_number == version,
        )
    )
    row = result.scalars().first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule v{version} not found for this group",
        )
    return row


def _check_not_self(actor_id: UUID, other_id: Optional[UUID], action: str) -> None:
    if other_id is not None and actor_id == other_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Self-approval is not allowed: {action}. A different reviewer must approve.",
        )


async def _audit(
    db: AsyncSession,
    actor: Optional[User],
    group_id: UUID,
    action: str,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    await log_audit(
        db,
        actor=actor,
        entity_type="group",
        entity_id=group_id,
        action=action,
        before=before,
        after=after,
        request=request,
    )


# -- groups ----------------------------------------------------------------

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_create),
) -> GroupResponse:
    try:
        group_type = GroupType(payload.type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="type must be MANUAL or RULE_BASED.",
        )
    name = payload.name.strip()
    if group_type == GroupType.MANUAL and payload.initial_rule is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Manual groups take no rule; members are managed explicitly.",
        )
    if payload.initial_rule is not None:
        try:
            validate_filter_tree(payload.initial_rule)
        except PhaseBReservedError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    group = Group(
        name=name,
        description=payload.description.strip() if payload.description else None,
        type=group_type,
        status=GroupStatus.ACTIVE,
        created_by=current_user.id,
    )
    db.add(group)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A group named '{name}' already exists.",
        )
    group = await _reload_group(db, group.id)
    after: dict = {"name": group.name, "type": group.type.value}
    if payload.initial_rule is not None:
        version = GroupRuleVersion(
            group_id=group.id,
            version_number=1,
            filter_tree=payload.initial_rule.model_dump(),
            status=RuleVersionStatus.PENDING,
            proposed_by=current_user.id,
        )
        db.add(version)
        await db.commit()
        after["pending_rule_version"] = 1
    await _audit(db, current_user, group.id, "GROUP_CREATE", after=after, request=request)
    await db.commit()
    return await _shape(db, group)


@router.get("", response_model=GroupListResponse)
async def list_groups(
    type: Optional[str] = Query(None, description="MANUAL | RULE_BASED"),
    status: Optional[str] = Query(None, description="ACTIVE | DEACTIVATED"),
    needs_review: Optional[bool] = Query(None, description="Pending rule or pending proposals"),
    q: Optional[str] = Query(None, description="Partial name match"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_read),
) -> GroupListResponse:
    query = select(Group)
    if type:
        try:
            query = query.where(Group.type == GroupType(type.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid type filter.")
    if status:
        try:
            query = query.where(Group.status == GroupStatus(status.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter.")
    if q:
        query = query.where(Group.name.ilike(f"%{q.strip()}%"))
    if needs_review is True:
        query = query.where(
            or_(
                exists(
                    select(GroupRuleVersion.id).where(
                        GroupRuleVersion.group_id == Group.id,
                        GroupRuleVersion.status == RuleVersionStatus.PENDING,
                    )
                ),
                exists(
                    select(GroupMembershipProposal.id).where(
                        GroupMembershipProposal.group_id == Group.id,
                        GroupMembershipProposal.status == ProposalStatus.PENDING,
                    )
                ),
            )
        )
    elif needs_review is False:
        query = query.where(
            ~exists(
                select(GroupRuleVersion.id).where(
                    GroupRuleVersion.group_id == Group.id,
                    GroupRuleVersion.status == RuleVersionStatus.PENDING,
                )
            ),
            ~exists(
                select(GroupMembershipProposal.id).where(
                    GroupMembershipProposal.group_id == Group.id,
                    GroupMembershipProposal.status == ProposalStatus.PENDING,
                )
            ),
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Group.name).offset((page - 1) * page_size).limit(page_size)
    groups = (await db.execute(query)).scalars().all()

    items = [await _shape(db, g) for g in groups]
    return GroupListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_read),
) -> GroupResponse:
    return await _shape(db, await _get_group_or_404(db, group_id))


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    payload: GroupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_update),
) -> GroupResponse:
    group = await _get_group_or_404(db, group_id)
    before = {"name": group.name, "description": group.description}
    if payload.name is not None:
        group.name = payload.name.strip()
    if payload.description is not None:
        group.description = payload.description.strip() or None
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A group named '{payload.name}' already exists.",
        )
    group = await _reload_group(db, group.id)
    await _audit(
        db, current_user, group.id, "GROUP_UPDATE",
        before=before,
        after={"name": group.name, "description": group.description},
        request=request,
    )
    await db.commit()
    return await _shape(db, group)


@router.post("/{group_id}/deactivate", response_model=GroupResponse)
async def deactivate_group(
    group_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_deactivate),
) -> GroupResponse:
    group = await _get_group_or_404(db, group_id)
    group.status = GroupStatus.DEACTIVATED
    await db.commit()
    group = await _reload_group(db, group.id)
    await _audit(db, current_user, group.id, "GROUP_DEACTIVATE", request=request)
    await db.commit()
    return await _shape(db, group)


@router.post("/{group_id}/reactivate", response_model=GroupResponse)
async def reactivate_group(
    group_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_deactivate),
) -> GroupResponse:
    group = await _get_group_or_404(db, group_id)
    group.status = GroupStatus.ACTIVE
    await db.commit()
    group = await _reload_group(db, group.id)
    await _audit(db, current_user, group.id, "GROUP_REACTIVATE", request=request)
    await db.commit()
    return await _shape(db, group)


# -- membership (manual groups; server-authoritative, idempotent) -----------

@router.get("/{group_id}/members", response_model=GroupMemberListResponse)
async def list_members(
    group_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_read),
) -> GroupMemberListResponse:
    group = await _get_group_or_404(db, group_id)
    checker = FieldPermissionChecker(db)
    base = (
        select(GroupMembership, Constituent)
        .join(Constituent, GroupMembership.constituent_id == Constituent.id)
        .where(GroupMembership.group_id == group.id)
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            base.order_by(Constituent.display_name).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    user_perms = await checker.get_user_permissions(current_user.id)
    items = []
    for membership, constituent in rows:
        shaped = checker.filter_dict(
            "constituent",
            {"display_name": constituent.display_name, "notes": constituent.notes},
            user_perms,
            current_user.is_superuser,
        )
        items.append(
            GroupMemberResponse(
                constituent_id=constituent.id,
                display_name=shaped.get("display_name") or constituent.display_name,
                added_at=membership.added_at,
                notes=shaped.get("notes"),
            )
        )
    return GroupMemberListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/{group_id}/members", response_model=MemberAddResponse)
async def add_members(
    group_id: UUID,
    payload: MemberAddRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_members),
) -> MemberAddResponse:
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_manual(group)
    valid, invalid = await resolve_ids(db, payload.constituent_ids)
    existing = await current_member_ids(db, group.id)
    to_add = [c for c in valid if c not in existing]
    already = [c for c in valid if c in existing]
    for cid in to_add:
        db.add(GroupMembership(group_id=group.id, constituent_id=cid, added_by=current_user.id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Concurrent add raced us; re-read authoritative state instead of failing.
        existing = await current_member_ids(db, group.id)
        valid, invalid = await resolve_ids(db, payload.constituent_ids)
        to_add = []
        already = [c for c in valid if c in existing]
    if to_add or already:
        await _audit(
            db, current_user, group.id, "GROUP_MEMBER_ADD",
            after={"added": [str(c) for c in to_add], "already_members": [str(c) for c in already]},
            request=request,
        )
        await db.commit()
    return MemberAddResponse(added=to_add, already_members=already, invalid=invalid)


@router.delete("/{group_id}/members/{constituent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: UUID,
    constituent_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_members),
) -> None:
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_manual(group)
    result = await db.execute(
        select(GroupMembership).where(
            GroupMembership.group_id == group.id,
            GroupMembership.constituent_id == constituent_id,
        )
    )
    row = result.scalars().first()
    if row is None:
        return None  # idempotent: repeated removals succeed silently
    before = {"constituent_id": str(constituent_id)}
    await db.delete(row)
    await _audit(db, current_user, group.id, "GROUP_MEMBER_REMOVE", before=before, request=request)
    await db.commit()
    return None


@router.post("/{group_id}/members/preview", response_model=PopulationPreviewResponse)
async def preview_population(
    group_id: UUID,
    payload: PopulationPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_members),
) -> PopulationPreviewResponse:
    """Dry-run for a future add: never mutates. Exactly one of ids/filter."""
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_manual(group)
    has_ids = payload.constituent_ids is not None
    has_filter = payload.filter is not None
    if has_ids == has_filter:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide exactly one of constituent_ids or filter.",
        )
    if has_ids:
        assert payload.constituent_ids is not None
        valid, invalid = await resolve_ids(db, payload.constituent_ids)
        matched = valid
    else:
        assert payload.filter is not None
        try:
            matched = sorted(
                await matched_population_ids(
                    db,
                    q=payload.q,
                    roll_no=payload.roll_no,
                    organisation_q=payload.organisation_q,
                    stale_threshold_days=payload.stale_threshold_days,
                    filter=payload.filter,
                ),
                key=str,
            )
        except PhaseBReservedError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        invalid = []
    members = await current_member_ids(db, group.id)
    already = [c for c in matched if c in members]
    return PopulationPreviewResponse(
        matched=len(matched),
        already_members=len(already),
        would_add=len(matched) - len(already),
        invalid=invalid,
    )


@router.post("/{group_id}/members/materialize", response_model=MaterializeResponse)
async def materialize_filtered_population(
    group_id: UUID,
    payload: PopulationPreviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_members),
) -> MaterializeResponse:
    """Add everyone currently matching a filter (re-evaluated now, never the
    browser's stale count). Manual groups only; already-members are skipped."""
    from app.schemas import FilterGroup as _FG

    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_manual(group)
    if payload.filter is None or payload.constituent_ids is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Materialize requires a filter definition (re-evaluated server-side).",
        )
    try:
        matched = sorted(
            await matched_population_ids(
                db,
                q=payload.q,
                roll_no=payload.roll_no,
                organisation_q=payload.organisation_q,
                stale_threshold_days=payload.stale_threshold_days,
                filter=payload.filter,
            ),
            key=str,
        )
    except PhaseBReservedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    members = await current_member_ids(db, group.id)
    to_add = [c for c in matched if c not in members]
    for cid in to_add:
        db.add(GroupMembership(group_id=group.id, constituent_id=cid, added_by=current_user.id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        members = await current_member_ids(db, group.id)
        to_add = [c for c in matched if c not in members]
        for cid in to_add:
            db.add(GroupMembership(group_id=group.id, constituent_id=cid, added_by=current_user.id))
        await db.commit()
    await _audit(
        db, current_user, group.id, "GROUP_MEMBER_MATERIALIZE",
        after={
            "matched": len(matched),
            "added": [str(c) for c in to_add],
            "filter": payload.filter.model_dump(),
            "q": payload.q,
            "roll_no": payload.roll_no,
            "organisation_q": payload.organisation_q,
            "stale_threshold_days": payload.stale_threshold_days,
        },
        request=request,
    )
    await db.commit()
    return MaterializeResponse(
        matched=len(matched), added=to_add, already_members=len(matched) - len(to_add), invalid=[]
    )


# -- rules (rule-based groups; propose ≠ approve) ----------------------------

@router.post("/{group_id}/rules", response_model=RuleVersionResponse, status_code=status.HTTP_201_CREATED)
async def propose_rule(
    group_id: UUID,
    payload: RuleProposeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_rules),
) -> RuleVersionResponse:
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    if await pending_rule_version(db, group.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending rule version already awaits review; approve or reject it first.",
        )
    try:
        validate_filter_tree(payload.filter)
    except PhaseBReservedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    max_v = (
        await db.execute(
            select(func.max(GroupRuleVersion.version_number)).where(
                GroupRuleVersion.group_id == group.id
            )
        )
    ).scalar() or 0
    version = GroupRuleVersion(
        group_id=group.id,
        version_number=max_v + 1,
        filter_tree=payload.filter.model_dump(),
        status=RuleVersionStatus.PENDING,
        proposed_by=current_user.id,
    )
    db.add(version)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending rule version already awaits review; approve or reject it first.",
        )
    db.expunge_all()
    version = await _rule_or_404(db, group.id, max_v + 1)
    await _audit(
        db, current_user, group.id, "GROUP_RULE_PROPOSE",
        after={"version": version.version_number, "filter": version.filter_tree},
        request=request,
    )
    await db.commit()
    return RuleVersionResponse.model_validate(version)


@router.get("/{group_id}/rules", response_model=list[RuleVersionResponse])
async def list_rules(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_read),
) -> list[RuleVersionResponse]:
    await _get_group_or_404(db, group_id)
    rows = (
        await db.execute(
            select(GroupRuleVersion)
            .where(GroupRuleVersion.group_id == group_id)
            .order_by(GroupRuleVersion.version_number)
        )
    ).scalars().all()
    return [RuleVersionResponse.model_validate(r) for r in rows]


@router.post("/{group_id}/rules/{version}/approve", response_model=RuleApprovalResponse)
async def approve_rule(
    group_id: UUID,
    version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_approve),
) -> RuleApprovalResponse:
    from datetime import datetime, timezone

    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    row = await _rule_or_404(db, group_id, version)
    if row.status != RuleVersionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule v{version} is {row.status.value}, not pending review.",
        )
    _check_not_self(current_user.id, row.proposed_by, "rule approval")
    previous = await active_rule_version(db, group.id)
    now = datetime.now(timezone.utc)
    if previous is not None:
        # Flush the supersede first: the partial unique index permits only
        # one ACTIVE version per group at any instant.
        previous.status = RuleVersionStatus.SUPERSEDED
        await db.flush()
    row.status = RuleVersionStatus.ACTIVE
    row.reviewed_by = current_user.id
    row.decided_at = now
    await db.commit()
    # Stage 1 ends here. Evaluation only *proposes* membership deltas —
    # application requires the separate Stage-2 approval below.
    summary = await evaluate_rule(db, group, row, current_user.id)
    await db.commit()
    await _audit(
        db, current_user, group.id, "GROUP_RULE_APPROVE",
        after={
            "version": row.version_number,
            "superseded": previous.version_number if previous else None,
            "evaluation": summary,
        },
        request=request,
    )
    await db.commit()
    db.expunge_all()
    row = await _rule_or_404(db, group_id, version)
    return RuleApprovalResponse(
        rule=RuleVersionResponse.model_validate(row),
        evaluation=summary,  # type: ignore[arg-type]
    )


@router.post("/{group_id}/rules/{version}/reject", response_model=RuleVersionResponse)
async def reject_rule(
    group_id: UUID,
    version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_approve),
) -> RuleVersionResponse:
    from datetime import datetime, timezone

    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    row = await _rule_or_404(db, group_id, version)
    if row.status != RuleVersionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule v{version} is {row.status.value}, not pending review.",
        )
    _check_not_self(current_user.id, row.proposed_by, "rule rejection")
    row.status = RuleVersionStatus.REJECTED
    row.reviewed_by = current_user.id
    row.decided_at = datetime.now(timezone.utc)
    await db.commit()
    db.expunge_all()
    row = await _rule_or_404(db, group_id, version)
    await _audit(
        db, current_user, group.id, "GROUP_RULE_REJECT",
        after={"version": row.version_number},
        request=request,
    )
    await db.commit()
    return RuleVersionResponse.model_validate(row)


@router.post("/{group_id}/rules/{version}/evaluate", response_model=EvaluationSummary)
async def evaluate_active_rule(
    group_id: UUID,
    version: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_manage_rules),
) -> EvaluationSummary:
    """Re-evaluate the ACTIVE rule (e.g. constituent data changed). Only
    creates new pending deltas; never applies membership."""
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    row = await _rule_or_404(db, group_id, version)
    if row.status != RuleVersionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only the active rule version can be evaluated; pending-rule impact "
            "can be previewed via POST /constituents/search instead.",
        )
    summary = await evaluate_rule(db, group, row, current_user.id)
    await db.commit()
    await _audit(
        db, current_user, group.id, "GROUP_RULE_EVALUATE",
        after=summary,
        request=request,
    )
    await db.commit()
    return EvaluationSummary(**summary)


# -- proposals (stage 2; bound to the evaluated version) ---------------------

def _proposal_to_response(
    proposal: GroupMembershipProposal, display_name: str, version_number: int
) -> ProposalResponse:
    return ProposalResponse(
        id=proposal.id,
        group_id=proposal.group_id,
        rule_version_id=proposal.rule_version_id,
        rule_version_number=version_number,
        constituent_id=proposal.constituent_id,
        display_name=display_name,
        action=proposal.action.value,
        reason_summary=proposal.reason_summary,
        reason_detail=proposal.reason_detail,
        status=proposal.status.value,
        evaluated_by=proposal.evaluated_by,
        reviewed_by=proposal.reviewed_by,
        decided_at=proposal.decided_at,
        applied_at=proposal.applied_at,
        created_at=proposal.created_at,
    )


@router.get("/{group_id}/proposals", response_model=ProposalListResponse)
async def list_proposals(
    group_id: UUID,
    status: Optional[str] = Query(None, description="PENDING | APPROVED | REJECTED"),
    action: Optional[str] = Query(None, description="ADD | REMOVE"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_read),
) -> ProposalListResponse:
    await _get_group_or_404(db, group_id)
    query = (
        select(GroupMembershipProposal, Constituent.display_name, GroupRuleVersion.version_number)
        .join(Constituent, GroupMembershipProposal.constituent_id == Constituent.id)
        .join(GroupRuleVersion, GroupMembershipProposal.rule_version_id == GroupRuleVersion.id)
        .where(GroupMembershipProposal.group_id == group_id)
    )
    if status:
        try:
            query = query.where(GroupMembershipProposal.status == ProposalStatus(status.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter.")
    if action:
        try:
            query = query.where(GroupMembershipProposal.action == ProposalAction(action.upper()))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action filter.")
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (
        await db.execute(
            query.order_by(GroupMembershipProposal.created_at).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return ProposalListResponse(
        items=[_proposal_to_response(p, name, ver) for p, name, ver in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


async def _decide_proposals(
    db: AsyncSession,
    group: Group,
    proposal_ids: list[UUID],
    approve: bool,
    current_user: User,
    request: Optional[Request],
) -> ProposalDecisionResponse:
    from datetime import datetime, timezone

    rows = (
        await db.execute(
            select(GroupMembershipProposal).where(
                GroupMembershipProposal.group_id == group.id,
                GroupMembershipProposal.id.in_(proposal_ids),
            )
        )
    ).scalars().all()
    found = {p.id for p in rows}
    missing = [pid for pid in proposal_ids if pid not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposals not found in this group: {[str(m) for m in missing]}",
        )
    decided: list[UUID] = []
    stale: list[UUID] = []
    already: list[UUID] = []
    active = await active_rule_version(db, group.id)
    active_id = active.id if active else None
    now = datetime.now(timezone.utc)
    for p in rows:
        if p.status != ProposalStatus.PENDING:
            already.append(p.id)
            continue
        if p.rule_version_id != active_id:
            stale.append(p.id)  # rule moved on; never apply under the wrong version
            continue
        if approve:
            # Four-eyes per stage: the membership approver must differ from
            # the actor who produced this stage's input (the evaluator).
            # Rule-stage separation (approver != proposer) is enforced at
            # rule approval; requiring both here deadlocks two-reviewer
            # teams, so the evaluator check is the binding one. See ADR-006.
            _check_not_self(current_user.id, p.evaluated_by, "membership approval")
            if p.action == ProposalAction.ADD:
                # Race-safe idempotent insert: a concurrent add path results
                # in ON CONFLICT DO NOTHING rather than an error.
                from sqlalchemy.dialects.postgresql import insert as pg_insert

                await db.execute(
                    pg_insert(GroupMembership)
                    .values(
                        group_id=group.id,
                        constituent_id=p.constituent_id,
                        added_by=current_user.id,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["group_id", "constituent_id"]
                    )
                )
            else:
                existing = await db.execute(
                    select(GroupMembership).where(
                        GroupMembership.group_id == group.id,
                        GroupMembership.constituent_id == p.constituent_id,
                    )
                )
                old = existing.scalars().first()
                if old is not None:
                    await db.delete(old)
            p.status = ProposalStatus.APPROVED
            p.reviewed_by = current_user.id
            p.decided_at = now
            p.applied_at = now
            decided.append(p.id)
        else:
            p.status = ProposalStatus.REJECTED
            p.reviewed_by = current_user.id
            p.decided_at = now
            decided.append(p.id)
    await db.commit()
    await _audit(
        db, current_user, group.id,
        "GROUP_PROPOSAL_APPROVE" if approve else "GROUP_PROPOSAL_REJECT",
        after={"decided": [str(d) for d in decided], "stale": [str(s) for s in stale]},
        request=request,
    )
    await db.commit()
    return ProposalDecisionResponse(
        approved_or_rejected=decided, stale=stale, already_decided=already
    )


@router.post("/{group_id}/proposals/approve", response_model=ProposalDecisionResponse)
async def approve_proposals(
    group_id: UUID,
    payload: ProposalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_approve),
) -> ProposalDecisionResponse:
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    return await _decide_proposals(db, group, payload.proposal_ids, True, current_user, request)


@router.post("/{group_id}/proposals/reject", response_model=ProposalDecisionResponse)
async def reject_proposals(
    group_id: UUID,
    payload: ProposalDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_groups_approve),
) -> ProposalDecisionResponse:
    group = await _get_group_or_404(db, group_id)
    _require_active(group)
    _require_rule_based(group)
    return await _decide_proposals(db, group, payload.proposal_ids, False, current_user, request)
