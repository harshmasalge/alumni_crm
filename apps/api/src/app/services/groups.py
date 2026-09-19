"""M1.1 Phase B1 — rule evaluation and proposal explanation.

Evaluation reuses the Phase A segmentation engine (`compile_filter`) so
People search and rule-based groups share one filter language. Reasons are
snapshotted onto each proposal at evaluation time: reviewers never depend
on mutable current data to understand a change.

Scale note: per-leaf explanation queries are one EXISTS each; fine for
on-demand evaluation at current scale (hundreds–thousands of rows). If
evaluation ever moves to a background worker, batch the snapshots there —
the reason schema is already worker-compatible.
"""

import json
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select

from app.models import (
    Address,
    AddressType,
    Affiliation,
    Constituent,
    ConstituentKind,
    EducationRecord,
    Group,
    GroupMembership,
    GroupMembershipProposal,
    GroupRuleVersion,
    Organisation,
    Person,
    ProposalAction,
    ProposalStatus,
    RuleVersionStatus,
)
from app.schemas import FilterCondition, FilterGroup
from app.services.segmentation import (
    compile_filter,
    validate_filter_tree,
)


async def single_leaf_matches(db: Any, constituent_id: UUID, cond: FilterCondition) -> bool:
    """Evaluate one leaf condition against one constituent."""
    expr = compile_filter(FilterGroup(op="and", conditions=[cond]))
    query = select(Constituent.id).where(
        Constituent.id == constituent_id, Constituent.kind == ConstituentKind.PERSON
    ).where(expr)
    result = await db.execute(query)
    return result.scalars().first() is not None


async def matched_constituent_ids(db: Any, tree: FilterGroup) -> set[UUID]:
    validate_filter_tree(tree)
    query = select(Constituent.id).where(Constituent.kind == ConstituentKind.PERSON).where(
        compile_filter(tree)
    )
    result = await db.execute(query)
    return {row for row in result.scalars().all()}


async def matched_population_ids(
    db: Any,
    *,
    q: str | None = None,
    roll_no: str | None = None,
    organisation_q: str | None = None,
    stale_threshold_days: int | None = None,
    filter: FilterGroup | None = None,
) -> set[UUID]:
    """Full People-query population: M1 criteria + filter tree as one
    server-side intersection (POST /constituents/search semantics)."""
    from app.services.segmentation import apply_m1_search_filters

    query = select(Constituent.id)
    query = apply_m1_search_filters(
        query,
        q=q,
        roll_no=roll_no,
        kind=None,
        status=None,
        organisation_q=organisation_q,
        stale_threshold_days=stale_threshold_days,
    )
    if filter is not None:
        validate_filter_tree(filter)
        query = query.where(compile_filter(filter))
    result = await db.execute(query)
    return {row for row in result.scalars().all()}


async def current_member_ids(db: Any, group_id: UUID) -> set[UUID]:
    result = await db.execute(
        select(GroupMembership.constituent_id).where(GroupMembership.group_id == group_id)
    )
    return set(result.scalars().all())


async def _snapshot(db: Any, constituent_id: UUID) -> dict[str, Any]:
    """Small read model of a constituent for explanations (never persisted)."""
    affs = (
        await db.execute(
            select(Affiliation).where(Affiliation.constituent_id == constituent_id)
        )
    ).scalars().all()
    org_ids = [a.organisation_id for a in affs if a.organisation_id]
    orgs: dict = {}
    if org_ids:
        rows = (
            await db.execute(
                select(Organisation).where(Organisation.constituent_id.in_(org_ids))
            )
        ).scalars().all()
        orgs = {o.constituent_id: o for o in rows}
    person = (
        await db.execute(select(Person).where(Person.constituent_id == constituent_id))
    ).scalars().first()
    schools = (
        await db.execute(
            select(EducationRecord.institution_name).where(
                EducationRecord.constituent_id == constituent_id,
                EducationRecord.institution_name.is_not(None),
            )
        )
    ).scalars().all()

    def org_name(a: Affiliation) -> str | None:
        if a.organisation_id and a.organisation_id in orgs:
            return orgs[a.organisation_id].legal_name
        return a.organisation_name_raw

    current = [a for a in affs if a.is_current]
    past = [a for a in affs if not a.is_current]
    return {
        "current_company": sorted({n for a in current if (n := org_name(a))}),
        "past_company": sorted({n for a in past if (n := org_name(a))}),
        "company_type": sorted(
            {
                v
                for a in affs
                for v in (
                    [str(a.affiliation_type.value) if a.affiliation_type else None]
                    + (
                        [orgs[a.organisation_id].company_type]
                        if a.organisation_id in orgs and orgs[a.organisation_id].company_type
                        else []
                    )
                )
                if v
            }
        ),
        "company_hq": sorted(
            {
                v
                for a in affs
                for v in (
                    [a.city, a.state, a.country]
                    + (
                        [
                            orgs[a.organisation_id].hq_city,
                            orgs[a.organisation_id].hq_state,
                            orgs[a.organisation_id].hq_country,
                        ]
                        if a.organisation_id in orgs
                        else []
                    )
                )
                if v
            }
        ),
        "function": sorted({a.function for a in affs if a.function}),
        "current_job_title": sorted({a.designation for a in current if a.designation}),
        "seniority_level": sorted({a.seniority_level for a in affs if a.seniority_level}),
        "past_job_title": sorted({a.designation for a in past if a.designation}),
        "geography": sorted(
            {v for a in current for v in (a.city, a.state, a.country) if v}
        ),
        "industry": sorted({a.sector for a in affs if a.sector}),
        "first_name": person.first_name if person else None,
        "last_name": person.last_name if person else None,
        "school": sorted(set(schools)),
        "earliest_start": min(
            (a.start_date for a in affs if a.start_date), default=None
        ),
        "current_start": next(
            (a.start_date for a in current if a.start_date), None
        ),
    }


def _expected_text(cond: FilterCondition) -> str:
    if cond.values:
        return ", ".join(str(v) for v in cond.values)
    return "" if cond.value is None else str(cond.value)


def _actual_text(field: str, snap: dict[str, Any]) -> str:
    value = snap.get(field)
    if value is None:
        return "unknown"
    if isinstance(value, list):
        return ", ".join(value) if value else "none recorded"
    if isinstance(value, date):
        years = (date.today() - value).days / 365.25
        return f"{years:.1f} years (since {value.isoformat()})"
    return str(value)


def _iter_leaves(node: Any) -> list[FilterCondition]:
    out: list[FilterCondition] = []

    def walk(n: Any) -> None:
        if isinstance(n, FilterGroup):
            for c in n.conditions:
                walk(c)
        else:
            out.append(n)

    walk(node)
    return out


async def explain_membership(
    db: Any, constituent_id: UUID, tree: FilterGroup, action: str, version_number: int
) -> tuple[str, str]:
    """Build (summary, detail-JSON) reason snapshot for one proposal."""
    snap = await _snapshot(db, constituent_id)
    leaves = _iter_leaves(tree)
    entries = []
    for cond in leaves:
        matched = await single_leaf_matches(db, constituent_id, cond)
        entries.append(
            {
                "field": cond.field,
                "operator": cond.operator,
                "expected": _expected_text(cond),
                "actual": _actual_text(cond.field, snap),
                "matched": matched,
            }
        )
    if action == "ADD":
        summary = f"Matches approved rule v{version_number}: " + "; ".join(
            f"{e['field']} = {e['actual']}" for e in entries if e["matched"]
        )
    else:
        failed = [e for e in entries if not e["matched"]]
        shown = failed if failed else entries
        summary = f"No longer matches approved rule v{version_number}: " + "; ".join(
            f"{e['field']} requires {e['expected']} (current: {e['actual']})" for e in shown
        )
    detail = json.dumps(
        {"version": version_number, "action": action, "leaves": entries}, default=str
    )
    return summary, detail


async def evaluate_rule(
    db: Any,
    group: Group,
    version: GroupRuleVersion,
    actor_id: UUID | None,
) -> dict[str, Any]:
    """Diff rule matches vs current members; create proposals for new deltas.

    Idempotent: existing PENDING proposals for the same (version,
    constituent, action) are never duplicated. Never mutates membership.
    """
    tree = FilterGroup.model_validate(version.filter_tree)
    matched = await matched_constituent_ids(db, tree)
    members = await current_member_ids(db, group.id)

    adds = matched - members
    removes = members - matched

    existing = (
        await db.execute(
            select(
                GroupMembershipProposal.constituent_id,
                GroupMembershipProposal.action,
            ).where(
                GroupMembershipProposal.group_id == group.id,
                GroupMembershipProposal.rule_version_id == version.id,
                GroupMembershipProposal.status == ProposalStatus.PENDING,
            )
        )
    ).all()
    pending_keys = {(c, a) for c, a in existing}

    created_adds = 0
    created_removes = 0
    skipped = 0
    for cid in sorted(adds, key=str):
        if (cid, ProposalAction.ADD) in pending_keys:
            skipped += 1
            continue
        summary, detail = await explain_membership(db, cid, tree, "ADD", version.version_number)
        db.add(
            GroupMembershipProposal(
                group_id=group.id,
                rule_version_id=version.id,
                constituent_id=cid,
                action=ProposalAction.ADD,
                reason_summary=summary,
                reason_detail=detail,
                status=ProposalStatus.PENDING,
                evaluated_by=actor_id,
            )
        )
        created_adds += 1
    for cid in sorted(removes, key=str):
        if (cid, ProposalAction.REMOVE) in pending_keys:
            skipped += 1
            continue
        summary, detail = await explain_membership(
            db, cid, tree, "REMOVE", version.version_number
        )
        db.add(
            GroupMembershipProposal(
                group_id=group.id,
                rule_version_id=version.id,
                constituent_id=cid,
                action=ProposalAction.REMOVE,
                reason_summary=summary,
                reason_detail=detail,
                status=ProposalStatus.PENDING,
                evaluated_by=actor_id,
            )
        )
        created_removes += 1
    return {
        "version_number": version.version_number,
        "matched": len(matched),
        "additions": created_adds,
        "removals": created_removes,
        "skipped_existing_pending": skipped,
    }


async def resolve_ids(
    db: Any, constituent_ids: list[UUID]
) -> tuple[list[UUID], list[UUID]]:
    """Split IDs into (valid PERSON constituents, invalid). Deduplicated."""
    seen: list[UUID] = []
    for cid in constituent_ids:
        if cid not in seen:
            seen.append(cid)
    if not seen:
        return [], []
    rows = (
        await db.execute(
            select(Constituent.id).where(
                Constituent.id.in_(seen),
                Constituent.kind == ConstituentKind.PERSON,
            )
        )
    ).scalars().all()
    valid = set(rows)
    return [c for c in seen if c in valid], [c for c in seen if c not in valid]


async def active_rule_version(db: Any, group_id: UUID) -> GroupRuleVersion | None:
    result = await db.execute(
        select(GroupRuleVersion).where(
            GroupRuleVersion.group_id == group_id,
            GroupRuleVersion.status == RuleVersionStatus.ACTIVE,
        )
    )
    return result.scalars().first()


async def pending_rule_version(db: Any, group_id: UUID) -> GroupRuleVersion | None:
    result = await db.execute(
        select(GroupRuleVersion).where(
            GroupRuleVersion.group_id == group_id,
            GroupRuleVersion.status == RuleVersionStatus.PENDING,
        )
    )
    return result.scalars().first()


async def group_counts(db: Any, group_id: UUID) -> dict[str, Any]:
    members = await current_member_ids(db, group_id)
    pending_props = (
        await db.execute(
            select(func.count()).select_from(GroupMembershipProposal).where(
                GroupMembershipProposal.group_id == group_id,
                GroupMembershipProposal.status == ProposalStatus.PENDING,
            )
        )
    ).scalar() or 0
    active = await active_rule_version(db, group_id)
    pending = await pending_rule_version(db, group_id)
    return {
        "member_count": len(members),
        "pending_proposal_count": pending_props,
        "has_pending_rule": pending is not None,
        "active_rule_version": active.version_number if active else None,
    }
