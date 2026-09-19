"""M1.1 Phase C — permission-aware people export (synchronous XLSX first).

Populations are re-evaluated server-side from the same contracts as People
search and Groups (explicit IDs | M1 + filter tree | group members) — the
frontend never supplies the population. Requested fields are intersected
with the caller's field permissions through the unchanged
FieldPermissionChecker (optional restricted fields dropped, required ones
masked as [restricted], exactly like profile reads).

Sync-first is deliberate at current scale (see ADR-007): the request shape
(population + fields → file) is already compatible with a future
request → job → worker → download evolution; row cap keeps single requests
bounded meanwhile.
"""

import io
from datetime import date
from typing import Any, Optional
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.field_permissions import RESTRICTED_FIELDS, FieldPermissionChecker
from app.models import (
    Address,
    AddressType,
    Affiliation,
    Constituent,
    ConstituentKind,
    ContactMethod,
    ContactType,
    Group,
    User,
)
from app.schemas import FilterGroup
from app.services.groups import current_member_ids, matched_population_ids, resolve_ids

MAX_EXPORT_ROWS = 5000
JOINED_VALUE_CAP = 1000

# Sections of the 360° profile that never export (not tabular profile data).
SKIP_SECTIONS = {"files", "audit_events", "profile_photos"}

# Whole-section gates mirroring the profile route (beyond field checks).
SECTION_GATES: dict[str, list[str]] = {
    "ssac_records": ["ssac.read_restricted"],
    "family_members": ["people.read_family"],
}

# Never exported: Aadhaar (disabled without approved requirement), encrypted
# blobs, and technical identifiers/timestamps/search internals.
EXCLUDED_FIELDS = {"id", "aadhaar_encrypted", "pan_encrypted", "profile_photo_file_id"}


def _keep_field(name: str) -> bool:
    if name in EXCLUDED_FIELDS:
        return False
    if name.startswith("normalised_"):
        return False
    if name.endswith(("_id", "_by", "_at")):
        return False
    if "storage_key" in name or name in {"scan_status", "classification"}:
        return False
    return True


def _checker_entity(section: str) -> str:
    return {"contact_methods": "contact_method", "addresses": "address"}.get(section, section)


def _title(text: str) -> str:
    return text.replace("_", " ").title()


# Curated legacy columns (stable keys/labels). entity/field route through
# FieldPermissionChecker; sensitive-by-design data (notes, PAN ciphertext,
# SSAC, family) is excluded from the registry entirely, not merely gated.
LEGACY_EXPORTABLE_FIELDS: list[dict[str, Any]] = [
    {"key": "display_name", "label": "Name", "entity": "constituent", "field": "display_name"},
    {"key": "status", "label": "Status", "entity": "constituent", "field": "status"},
    {"key": "first_name", "label": "First name", "entity": "person", "field": "first_name"},
    {"key": "last_name", "label": "Last name", "entity": "person", "field": "last_name"},
    {"key": "gender", "label": "Gender", "entity": "person", "field": "gender"},
    {"key": "date_of_birth", "label": "Date of birth", "entity": "person", "field": "date_of_birth"},
    {"key": "blood_group", "label": "Blood group", "entity": "person", "field": "blood_group"},
    {"key": "roll_no", "label": "Roll Number", "entity": "alumni_profile", "field": "roll_no"},
    {"key": "iitgn_email", "label": "IITGN email", "entity": "contact_method", "field": "value"},
    {"key": "year_of_graduation", "label": "Year of graduation", "entity": "alumni_profile", "field": "year_of_graduation"},
    {"key": "final_cpi", "label": "Final CPI", "entity": "alumni_profile", "field": "final_cpi"},
    {"key": "current_company", "label": "Current company", "entity": "affiliation", "field": "organisation_name_raw"},
    {"key": "current_job_title", "label": "Current job title", "entity": "affiliation", "field": "designation"},
    {"key": "function", "label": "Function", "entity": "affiliation", "field": "function"},
    {"key": "seniority_level", "label": "Seniority level", "entity": "affiliation", "field": "seniority_level"},
    {"key": "industry", "label": "Industry", "entity": "affiliation", "field": "sector"},
    {"key": "work_city", "label": "Work city", "entity": "affiliation", "field": "city"},
    {"key": "work_country", "label": "Work country", "entity": "affiliation", "field": "country"},
    {"key": "years_in_current_company", "label": "Years in current company", "entity": "affiliation", "field": "start_date"},
    {"key": "primary_email", "label": "Primary email", "entity": "contact_method", "field": "value"},
    {"key": "primary_phone", "label": "Primary phone", "entity": "contact_method", "field": "value"},
    {"key": "current_city", "label": "Current city (address)", "entity": "address", "field": "city"},
    {"key": "current_country", "label": "Current country (address)", "entity": "address", "field": "country"},
    {"key": "school", "label": "School (latest education)", "entity": "education_record", "field": "institution_name"},
]


def _discover_dynamic_fields() -> list[dict[str, Any]]:
    """Derive exportable columns from the 360° profile response models, so a
    newly added profile field is automatically exportable (subject to the
    same permission checks). Runs once at import."""
    from app import schemas as S

    profile_fields: dict[str, Any] = S.Profile360Response.model_fields
    taken = {e["key"] for e in LEGACY_EXPORTABLE_FIELDS}
    dynamic: list[dict[str, Any]] = []
    for section, field_info in profile_fields.items():
        if section in SKIP_SECTIONS:
            continue
        annotation = getattr(field_info, "annotation", None)
        item_model = None
        is_list = False
        if getattr(annotation, "__origin__", None) is list:
            # Bare list[X] (Profile360Response collections).
            is_list = True
            inner = (getattr(annotation, "__args__", []) or [None])[0]
            if hasattr(inner, "model_fields"):
                item_model = inner
        else:
            args = list(getattr(annotation, "__args__", []) or [])
            for arg in args:
                origin = getattr(arg, "__origin__", None)
                if origin is list:
                    is_list = True
                    inner = (getattr(arg, "__args__", []) or [None])[0]
                    if hasattr(inner, "model_fields"):
                        item_model = inner
                elif hasattr(arg, "model_fields"):
                    item_model = arg
            if item_model is None and hasattr(annotation, "model_fields"):
                item_model = annotation
        if item_model is None:
            continue
        entity = _checker_entity(section)
        if is_list:
            dynamic.append({
                "key": f"{section}_count",
                "label": f"{_title(section)} Count",
                "entity": entity,
                "field": "__count__",
                "section": section,
            })
            for fname in item_model.model_fields:
                if not _keep_field(fname) or f"{section}.{fname}" in taken:
                    continue
                taken.add(f"{section}.{fname}")
                dynamic.append({
                    "key": f"{section}.{fname}",
                    "label": f"{_title(fname)} ({_title(section)})",
                    "entity": entity,
                    "field": fname,
                    "section": section,
                })
        else:
            for fname in item_model.model_fields:
                if not _keep_field(fname) or fname in taken:
                    continue
                taken.add(fname)
                dynamic.append({
                    "key": fname,
                    "label": _title(fname),
                    "entity": entity,
                    "field": fname,
                    "section": section,
                })
    return dynamic


EXPORTABLE_FIELDS: list[dict[str, Any]] = LEGACY_EXPORTABLE_FIELDS + _discover_dynamic_fields()
EXPORT_FIELDS_BY_KEY = {e["key"]: e for e in EXPORTABLE_FIELDS}


def required_permissions(entity: str, field: str, section: Optional[str] = None) -> Optional[list[str]]:
    if section in SECTION_GATES:
        return SECTION_GATES[section]
    return RESTRICTED_FIELDS.get(entity, {}).get(field)


def _section_allowed(section: Optional[str], user_permissions: set[str], is_superuser: bool) -> bool:
    if is_superuser:
        return True
    gate = SECTION_GATES.get(section or "")
    if not gate:
        return True
    return any(p in user_permissions for p in gate)


def resolve_export_fields(
    checker: FieldPermissionChecker,
    requested: Optional[list[str]],
    user_permissions: set[str],
    is_superuser: bool,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Intersect requested (or default-all) columns with field permissions.

    Unknown keys fail closed (ValueError → 422). Returns (allowed, dropped).
    """
    if requested is None or len(requested) == 0:
        candidates = list(EXPORTABLE_FIELDS)
    else:
        candidates = []
        for key in requested:
            entry = EXPORT_FIELDS_BY_KEY.get(key)
            if entry is None:
                raise ValueError(f"Unknown export field: {key!r}.")
            candidates.append(entry)
    allowed: list[dict[str, Any]] = []
    dropped: list[str] = []
    for entry in candidates:
        if _section_allowed(entry.get("section"), user_permissions, is_superuser) and checker.can_access_field(
            entry["entity"], entry["field"], user_permissions, is_superuser
        ):
            allowed.append(entry)
        else:
            dropped.append(entry["key"])
    return allowed, dropped


async def resolve_export_population(
    db: Any,
    *,
    actor: User,
    constituent_ids: Optional[list[UUID]] = None,
    q: Optional[str] = None,
    roll_no: Optional[str] = None,
    organisation_q: Optional[str] = None,
    stale_threshold_days: Optional[int] = None,
    filter: Optional[FilterGroup] = None,
    group_id: Optional[UUID] = None,
) -> tuple[list[UUID], dict[str, Any], list[UUID]]:
    """Re-evaluate the export population server-side.

    Returns (ordered IDs, summary, invalid IDs). Raises LookupError for an
    unknown group, PermissionError for group populations without
    groups.read, ValueError for bad definitions, and OverflowError past
    MAX_EXPORT_ROWS.
    """
    from app.core.auth import get_user_permissions

    modes = [
        constituent_ids is not None,
        group_id is not None,
        any(v is not None for v in (q, roll_no, organisation_q, stale_threshold_days, filter)),
    ]
    if sum(modes) > 1:
        raise ValueError("Provide only one population: constituent_ids, group_id, or search criteria.")
    invalid: list[UUID] = []
    summary: dict[str, Any] = {}
    if group_id is not None:
        result = await db.execute(select(Group).where(Group.id == group_id))
        group = result.scalars().first()
        if group is None:
            raise LookupError(f"Group with id {group_id} not found")
        perms = set(await get_user_permissions(db, actor.id))
        if "groups.read" not in perms and not actor.is_superuser:
            raise PermissionError("Permission denied: groups.read required for group exports")
        ids = sorted(await current_member_ids(db, group.id), key=str)
        summary = {"mode": "group", "group_id": str(group_id), "group_name": group.name}
    elif constituent_ids is not None:
        valid, invalid = await resolve_ids(db, constituent_ids)
        ids = sorted(valid, key=str)
        summary = {"mode": "ids", "requested": len(constituent_ids)}
    elif any(v is not None for v in (q, roll_no, organisation_q, stale_threshold_days, filter)):
        matched = await matched_population_ids(
            db, q=q, roll_no=roll_no, organisation_q=organisation_q,
            stale_threshold_days=stale_threshold_days, filter=filter,
        )
        ids = sorted(matched, key=str)
        summary = {
            "mode": "filtered",
            "q": q, "roll_no": roll_no, "organisation_q": organisation_q,
            "stale_threshold_days": stale_threshold_days,
            "filter": filter.model_dump() if filter else None,
        }
    else:
        result = await db.execute(
            select(Constituent.id)
            .where(Constituent.kind == ConstituentKind.PERSON)
            .order_by(Constituent.display_name)
        )
        ids = list(result.scalars().all())
        summary = {"mode": "all"}
    if len(ids) > MAX_EXPORT_ROWS:
        raise OverflowError(
            f"Export population ({len(ids)}) exceeds the {MAX_EXPORT_ROWS}-row single-request "
            "limit; narrow it with filters."
        )
    summary["matched"] = len(ids)
    summary["invalid"] = len(invalid)
    return ids, summary, invalid


async def load_export_rows(db: Any, ids: list[UUID]) -> list[Constituent]:
    if not ids:
        return []
    result = await db.execute(
        select(Constituent)
        .options(
            selectinload(Constituent.person),
            selectinload(Constituent.organisation),
            selectinload(Constituent.alumni_profile),
            selectinload(Constituent.donor_profile),
            selectinload(Constituent.affiliations).selectinload(Affiliation.organisation),
            selectinload(Constituent.contact_methods),
            selectinload(Constituent.addresses),
            selectinload(Constituent.communication_preferences),
            selectinload(Constituent.education_records),
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
        )
        .where(Constituent.id.in_(ids))
        .order_by(Constituent.display_name)
    )
    return list(result.scalars().all())


def _preferred_contact(c: Constituent, types: list[ContactType]) -> Optional[str]:
    active = [m for m in c.contact_methods if m.is_active and m.contact_type in types]
    if not active:
        return None
    active.sort(key=lambda m: (not m.is_primary,))
    return active[0].value


EMAIL_TYPES = [ContactType.EMAIL_PERSONAL, ContactType.EMAIL_IITGN, ContactType.EMAIL_WORK]
PHONE_TYPES = [ContactType.PHONE_PRIMARY, ContactType.PHONE_SECONDARY, ContactType.WHATSAPP]


def _fmt(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (date,)):
        return value.isoformat()
    if value.__class__.__name__ in ("datetime",):
        return value.isoformat()
    if hasattr(value, "value") and value.__class__.__name__ not in ("str",):
        try:
            return value.value
        except Exception:
            return str(value)
    return value


def _attrs(obj: Any, fields: list[str]) -> dict[str, Any]:
    if obj is None:
        return {}
    return {f: _fmt(getattr(obj, f, None)) for f in fields}


def _section_source(c: Constituent, section: str) -> tuple[Any, bool]:
    """Raw ORM source + is-list flag for a 360° section."""
    mapping: dict[str, Any] = {
        "constituent": c,
        "person": c.person,
        "organisation": c.organisation,
        "alumni_profile": c.alumni_profile,
        "donor_profile": c.donor_profile,
        "communication_preferences": c.communication_preferences,
        "contact_methods": c.contact_methods,
        "addresses": c.addresses,
        "education_records": c.education_records,
        "affiliations": c.affiliations,
        "hostel_history": c.hostel_history,
        "academic_courses": c.academic_courses,
        "semester_performance": c.semester_performance,
        "gps_assignments": c.gps_assignments,
        "awards_recognition": c.awards_recognition,
        "scholarships_financial_aid": c.scholarships_financial_aid,
        "internships": c.internships,
        "placements": c.placements,
        "startups": c.startups,
        "ssac_records": c.ssac_records,
        "positions_of_responsibility": c.positions_of_responsibility,
        "publications": c.publications,
        "overseas_exposure": c.overseas_exposure,
        "family_members": c.family_members,
    }
    value = mapping.get(section)
    return value, isinstance(value, list)


def build_row_snapshots(
    constituents: list[Constituent],
    checker: FieldPermissionChecker,
    user_permissions: set[str],
    is_superuser: bool,
) -> list[dict[str, Any]]:
    """Per-row values with field permissions applied (drop/mask semantics).

    Legacy curated columns keep their exact extractors; every other
    registry column resolves generically from its 360° section.
    """
    rows: list[dict[str, Any]] = []
    for c in constituents:
        person = checker.filter_dict(
            "person",
            {
                "first_name": c.person.first_name if c.person else None,
                "last_name": c.person.last_name if c.person else None,
                "gender": c.person.gender.value if c.person and c.person.gender else None,
                "date_of_birth": c.person.date_of_birth.isoformat() if c.person and c.person.date_of_birth else None,
                "blood_group": c.person.blood_group if c.person else None,
            },
            user_permissions, is_superuser,
        )
        alumni = checker.filter_dict(
            "alumni_profile",
            {
                "roll_no": c.alumni_profile.roll_no if c.alumni_profile else None,
                "iitgn_email": c.alumni_profile.iitgn_email if c.alumni_profile else None,
                "year_of_graduation": c.alumni_profile.year_of_graduation if c.alumni_profile else None,
                "final_cpi": c.alumni_profile.final_cpi if c.alumni_profile else None,
            },
            user_permissions, is_superuser,
        )
        current = next((a for a in c.affiliations if a.is_current), None)

        def org_name(a: Optional[Affiliation]) -> Optional[str]:
            if a is None:
                return None
            if a.organisation is not None:
                return a.organisation.legal_name
            return a.organisation_name_raw

        contact_email = checker.filter_dict(
            "contact_method", {"value": _preferred_contact(c, EMAIL_TYPES)},
            user_permissions, is_superuser,
        )["value"]
        contact_phone = checker.filter_dict(
            "contact_method", {"value": _preferred_contact(c, PHONE_TYPES)},
            user_permissions, is_superuser,
        )["value"]
        address = next(
            (x for x in c.addresses if x.address_type == AddressType.CURRENT and x.is_active), None
        )
        addr = checker.filter_dict(
            "address",
            {"city": address.city if address else None, "country": address.country if address else None},
            user_permissions, is_superuser,
        )
        schools = sorted({e.institution_name for e in c.education_records if e.institution_name})
        years_here: Optional[float] = None
        if current and current.start_date:
            years_here = round((date.today() - current.start_date).days / 365.25, 1)
        row = {
            "display_name": c.display_name,
            "status": c.status.value,
            "first_name": person.get("first_name"),
            "last_name": person.get("last_name"),
            "gender": person.get("gender"),
            "date_of_birth": person.get("date_of_birth"),
            "blood_group": person.get("blood_group"),
            "roll_no": alumni.get("roll_no"),
            "iitgn_email": contact_email if contact_email else alumni.get("iitgn_email"),
            "year_of_graduation": alumni.get("year_of_graduation"),
            "final_cpi": alumni.get("final_cpi"),
            "current_company": org_name(current),
            "current_job_title": current.designation if current else None,
            "function": current.function if current else None,
            "seniority_level": current.seniority_level if current else None,
            "industry": current.sector if current else None,
            "work_city": current.city if current else None,
            "work_country": current.country if current else None,
            "years_in_current_company": years_here,
            "primary_email": contact_email,
            "primary_phone": contact_phone,
            "current_city": addr.get("city"),
            "current_country": addr.get("country"),
            "school": schools[-1] if schools else None,
        }
        # Dynamic remainder: every other registry column resolves from its
        # 360° section with the same drop/mask permission semantics.
        for entry in EXPORTABLE_FIELDS:
            key = entry["key"]
            if key in row:
                continue
            section = entry.get("section")
            if not section:
                row[key] = None
                continue
            if not _section_allowed(section, user_permissions, is_superuser):
                row[key] = 0 if entry["field"] == "__count__" else None
                continue
            source, is_list = _section_source(c, section)
            entity = entry["entity"]
            if is_list:
                items = source or []
                if entry["field"] == "__count__":
                    row[key] = len(items)
                    continue
                values = []
                for item in items:
                    shaped = checker.filter_dict(
                        entity, {entry["field"]: _fmt(getattr(item, entry["field"], None))},
                        user_permissions, is_superuser,
                    )
                    if shaped.get(entry["field"]) not in (None, ""):
                        values.append(str(shaped[entry["field"]]))
                joined = " | ".join(values)
                row[key] = joined[:JOINED_VALUE_CAP] + ("…" if len(joined) > JOINED_VALUE_CAP else "") if joined else None
            else:
                shaped = checker.filter_dict(
                    entity, {entry["field"]: _fmt(getattr(source, entry["field"], None)) if source is not None else None},
                    user_permissions, is_superuser,
                )
                row[key] = shaped.get(entry["field"])
        rows.append(row)
    return rows


def render_xlsx(columns: list[dict[str, Any]], rows: list[dict[str, Any]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "People"
    header_font = Font(bold=True)
    for col, entry in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col, value=entry["label"])
        cell.font = header_font
    for r, row in enumerate(rows, start=2):
        for col, entry in enumerate(columns, start=1):
            value = row.get(entry["key"])
            ws.cell(row=r, column=col, value="" if value is None else value)
    ws.freeze_panes = "A2"
    for col, entry in enumerate(columns, start=1):
        width = len(entry["label"])
        for row in rows:
            value = row.get(entry["key"])
            if value is not None:
                width = max(width, min(len(str(value)), 60))
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = min(width + 2, 62)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()
