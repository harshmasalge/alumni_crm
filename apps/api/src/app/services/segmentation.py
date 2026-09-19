"""M1.1 Phase A — reusable people-segmentation query engine.

The frontend builds a filter tree; this module validates and compiles it to
server-side SQLAlchemy predicates. Nothing is evaluated in the browser.

Design notes (see ADR-005):
- Every history-backed leaf compiles to a correlated EXISTS subquery, so a
  person with N affiliations still matches once and history is never
  flattened into the constituent row.
- Derived tenures (years_in_current_company, years_in_current_position,
  years_of_experience) come from affiliation start_dates at query time and
  are never persisted. Cutoffs use 365.25 days/year — an approximation the
  source data's month-level precision already dominates.
- NULL/missing values never match value comparisons; use is_empty /
  is_not_empty to query absence explicitly.
"""

from datetime import date, timedelta
from typing import Any, Union

from sqlalchemy import String, cast, exists, func, or_, select

from app.models import (
    Address,
    AddressType,
    Affiliation,
    AlumniProfile,
    Constituent,
    ConstituentKind,
    ConstituentStatus,
    EducationRecord,
    Organisation,
    Person,
)
from app.schemas import (
    FILTER_FIELD_REGISTRY,
    RESERVED_PHASE_B_FIELDS,
    FilterCondition,
    FilterGroup,
)

MAX_FILTER_DEPTH = 3
MAX_FILTER_CONDITIONS = 50

FilterNode = Union[FilterCondition, FilterGroup]


class PhaseBReservedError(ValueError):
    """A filter field reserved for a later phase (Groups in Phase B)."""


SINGLE_VALUE_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "starts_with",
    "gt",
    "gte",
    "lt",
    "lte",
}
LIST_VALUE_OPERATORS = {"is_any_of", "is_none_of", "is_all_of", "between"}
NO_VALUE_OPERATORS = {"is_empty", "is_not_empty"}


def validate_filter_tree(node: FilterNode, depth: int = 0, _count: list | None = None) -> int:
    """Validate structure, field/operator support, and value shapes.

    Returns the leaf-condition count. Raises ValueError with a UI-safe
    message on any invalid definition; the router maps it to 422 (or 400
    for the Phase B reserved field).
    """
    if _count is None:
        _count = [0]
    if isinstance(node, FilterGroup):
        if node.op not in ("and", "or"):
            raise ValueError(f"Invalid group operator: {node.op!r}. Must be 'and' or 'or'.")
        if depth >= MAX_FILTER_DEPTH:
            raise ValueError(f"Filter nesting exceeds {MAX_FILTER_DEPTH} levels.")
        if not node.conditions:
            raise ValueError("Filter group must contain at least one condition.")
        for child in node.conditions:
            validate_filter_tree(child, depth + 1, _count)
    else:
        _count[0] += 1
        if _count[0] > MAX_FILTER_CONDITIONS:
            raise ValueError(f"Filter exceeds {MAX_FILTER_CONDITIONS} conditions.")
        _validate_condition(node)
    return _count[0]


def _validate_condition(cond: FilterCondition) -> None:
    if cond.field in RESERVED_PHASE_B_FIELDS:
        raise PhaseBReservedError(
            f"Filter field '{cond.field}' arrives with governed Groups in Phase B "
            "and cannot be used yet."
        )
    spec = FILTER_FIELD_REGISTRY.get(cond.field)
    if spec is None:
        raise ValueError(f"Unknown filter field: {cond.field!r}.")
    if cond.operator not in spec["operators"]:
        raise ValueError(
            f"Operator '{cond.operator}' is not supported for field '{cond.field}'. "
            f"Supported: {', '.join(spec['operators'])}."
        )
    if cond.operator in SINGLE_VALUE_OPERATORS and cond.value is None:
        raise ValueError(f"Operator '{cond.operator}' requires a single 'value'.")
    if cond.operator in LIST_VALUE_OPERATORS and not cond.values:
        raise ValueError(f"Operator '{cond.operator}' requires a non-empty 'values' list.")
    if cond.operator == "between":
        assert cond.values is not None
        if len(cond.values) != 2:
            raise ValueError("Operator 'between' requires exactly two values [low, high].")
        if cond.values[0] is None or cond.values[1] is None:
            raise ValueError("Operator 'between' values must not be null.")
    if cond.operator in NO_VALUE_OPERATORS and (cond.value is not None or cond.values):
        raise ValueError(f"Operator '{cond.operator}' takes no value.")
    kind = spec["kind"]
    if kind == "numeric" and cond.operator not in NO_VALUE_OPERATORS:
        raw = [cond.value] if cond.value is not None else list(cond.values or [])
        for v in raw:
            try:
                float(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                raise ValueError(f"Field '{cond.field}' requires numeric values.") from None


def compile_filter(node: FilterNode) -> Any:
    """Compile a validated tree to a SQLAlchemy boolean expression."""
    if isinstance(node, FilterGroup):
        parts = [compile_filter(child) for child in node.conditions]
        if len(parts) == 1:
            return parts[0]
        if node.op == "or":
            return or_(*parts)
        return _and_all(parts)
    return _compile_condition(node)


def _and_all(parts: list) -> Any:
    expr = parts[0]
    for part in parts[1:]:
        expr = expr & part
    return expr


# -- text matching -----------------------------------------------------------

def _text_predicate(column: Any, operator: str, value: Any, values: list | None) -> Any:
    if operator == "equals":
        return func.lower(column) == str(value).strip().lower()
    if operator == "not_equals":
        return or_(column.is_(None), func.lower(column) != str(value).strip().lower())
    if operator == "contains":
        return column.ilike(f"%{str(value).strip()}%")
    if operator == "starts_with":
        return column.ilike(f"{str(value).strip()}%")
    if operator == "is_any_of":
        return or_(*[func.lower(column) == str(v).strip().lower() for v in (values or [])])
    if operator == "is_none_of":
        return _and_all(
            [or_(column.is_(None), func.lower(column) != str(v).strip().lower()) for v in (values or [])]
        )
    if operator == "is_empty":
        return or_(column.is_(None), column == "")
    if operator == "is_not_empty":
        return column.is_not(None) & (column != "")
    raise ValueError(f"Unsupported text operator: {operator}")  # pragma: no cover


def _aff_exists(*criteria: Any, current: bool | None = None) -> Any:
    sub = select(Affiliation.id).where(Affiliation.constituent_id == Constituent.id)
    if current is True:
        sub = sub.where(Affiliation.is_current.is_(True))
    elif current is False:
        sub = sub.where(Affiliation.is_current.is_(False))
    if criteria:
        sub = sub.where(*criteria)
    return exists(sub)


def _aff_org_exists(*criteria: Any, current: bool | None = None) -> Any:
    """Affiliation EXISTS with the resolved organisation joined, so filters
    can match master-data columns (legal_name, company_type, HQ) alongside
    raw affiliation text."""
    sub = (
        select(Affiliation.id)
        .select_from(Affiliation)
        .outerjoin(Organisation, Affiliation.organisation_id == Organisation.constituent_id)
        .where(Affiliation.constituent_id == Constituent.id)
    )
    if current is True:
        sub = sub.where(Affiliation.is_current.is_(True))
    elif current is False:
        sub = sub.where(Affiliation.is_current.is_(False))
    if criteria:
        sub = sub.where(*criteria)
    return exists(sub)


def _company_name_predicate(operator: str, value: Any, values: list | None, current: bool) -> Any:
    def one(col: Any) -> Any:
        return _text_predicate(col, operator, value, values)

    if operator in ("is_empty", "is_not_empty"):
        pred = or_(
            one(Affiliation.organisation_name_raw),
            one(Organisation.legal_name),
        )
        # is_empty must also cover constituents with no affiliations at all.
        if operator == "is_empty":
            return or_(~_aff_exists(current=current), _aff_org_exists(pred, current=current))
        return _aff_org_exists(pred, current=current)
    pred = or_(
        one(Affiliation.organisation_name_raw),
        one(Organisation.legal_name),
    )
    if operator in ("not_equals", "is_none_of"):
        # NULL names must not silently satisfy a negation: require a named
        # affiliation that fails the match.
        named = or_(
            Affiliation.organisation_name_raw.is_not(None),
            Organisation.legal_name.is_not(None),
        )
        return _aff_org_exists(named & pred, current=current)
    return _aff_org_exists(pred, current=current)


def _hq_predicate(operator: str, value: Any, values: list | None) -> Any:
    cols = [
        Affiliation.city,
        Affiliation.state,
        Affiliation.country,
        Organisation.hq_city,
        Organisation.hq_state,
        Organisation.hq_country,
    ]

    def one(col: Any) -> Any:
        return _text_predicate(col, operator, value, values)

    if operator in ("is_empty", "is_not_empty"):
        pred = or_(*[one(c) for c in cols])
        if operator == "is_empty":
            return or_(~_aff_exists(), _aff_org_exists(pred))
        return _aff_org_exists(pred)
    pred = or_(*[one(c) for c in cols])
    if operator in ("not_equals", "is_none_of"):
        named = or_(*[c.is_not(None) for c in cols])
        return _aff_org_exists(named & pred)
    return _aff_org_exists(pred)


def _company_type_predicate(operator: str, values: list | None) -> Any:
    wanted = [str(v).strip().upper() for v in (values or [])]
    # affiliation_type is a PG enum: cast to text before upper().
    aff_type_text = func.upper(cast(Affiliation.affiliation_type, String))

    def match_aff_type() -> Any:
        col = aff_type_text
        if operator == "is_any_of":
            return or_(*[col == w for w in wanted])
        if operator == "is_none_of":
            return _and_all([or_(Affiliation.affiliation_type.is_(None), col != w) for w in wanted])
        # is_all_of
        return None  # handled below

    def match_org_type() -> Any:
        col = func.lower(Organisation.company_type)
        lowered = [w.lower() for w in wanted]
        if operator == "is_any_of":
            return or_(*[col == w for w in lowered])
        if operator == "is_none_of":
            return _and_all(
                [or_(Organisation.company_type.is_(None), col != w) for w in lowered]
            )
        return None  # handled below

    if operator == "is_all_of":
        parts = []
        for w in wanted:
            parts.append(
                _aff_org_exists(
                    or_(
                        aff_type_text == w,
                        func.lower(Organisation.company_type) == w.lower(),
                    )
                )
            )
        return _and_all(parts)
    if operator == "is_empty":
        return or_(
            ~_aff_exists(),
            _aff_org_exists(
                Affiliation.affiliation_type.is_(None) & Organisation.company_type.is_(None)
            ),
        )
    if operator == "is_not_empty":
        return _aff_org_exists(
            or_(
                Affiliation.affiliation_type.is_not(None),
                Organisation.company_type.is_not(None),
            )
        )
    pred = or_(match_aff_type(), match_org_type())
    if operator == "is_none_of":
        named = or_(
            Affiliation.affiliation_type.is_not(None),
            Organisation.company_type.is_not(None),
        )
        return _aff_org_exists(named & pred)
    return _aff_org_exists(pred)


def _aff_text_field_predicate(
    column: Any, operator: str, value: Any, values: list | None, current: bool | None = None
) -> Any:
    pred = _text_predicate(column, operator, value, values)
    if operator in ("is_empty",):
        return or_(~_aff_exists(current=current), _aff_exists(pred, current=current))
    if operator in ("not_equals", "is_none_of"):
        return _aff_exists(column.is_not(None) & pred, current=current)
    return _aff_exists(pred, current=current)


def _multi_aff_predicate(
    column: Any, operator: str, values: list | None, current: bool | None = None
) -> Any:
    wanted = [str(v).strip().lower() for v in (values or [])]
    col = func.lower(column)
    if operator == "is_any_of":
        return _aff_exists(or_(*[col == w for w in wanted]), current=current)
    if operator == "is_none_of":
        pred = _and_all([or_(column.is_(None), col != w) for w in wanted])
        return _aff_exists(column.is_not(None) & pred, current=current)
    if operator == "is_all_of":
        return _and_all([_aff_exists(col == w, current=current) for w in wanted])
    if operator == "is_empty":
        return or_(~_aff_exists(current=current), _aff_exists(or_(column.is_(None), column == ""), current=current))
    # is_not_empty
    return _aff_exists(column.is_not(None) & (column != ""), current=current)


def _geography_predicate(operator: str, value: Any, values: list | None) -> Any:
    aff_cols = [Affiliation.city, Affiliation.state, Affiliation.country]

    def one(col: Any) -> Any:
        return _text_predicate(col, operator, value, values)

    aff_pred = or_(*[one(c) for c in aff_cols])
    addr_sub = (
        select(Address.id)
        .where(Address.constituent_id == Constituent.id)
        .where(Address.address_type == AddressType.CURRENT)
        .where(Address.is_active.is_(True))
    )
    addr_cols = [Address.city, Address.state, Address.country]
    addr_pred = or_(*[_text_predicate(c, operator, value, values) for c in addr_cols])
    addr_exists = exists(addr_sub.where(addr_pred))
    if operator == "is_empty":
        return or_(
            ~_aff_exists(current=True) & ~exists(addr_sub),
            _aff_org_exists(aff_pred, current=True) | addr_exists,
        )
    if operator in ("not_equals", "is_none_of"):
        named_aff = or_(*[c.is_not(None) for c in aff_cols])
        return _aff_org_exists(named_aff & aff_pred, current=True) | addr_exists
    return _aff_org_exists(aff_pred, current=True) | addr_exists


def _school_predicate(operator: str, value: Any, values: list | None) -> Any:
    pred = _text_predicate(EducationRecord.institution_name, operator, value, values)
    sub = select(EducationRecord.id).where(EducationRecord.constituent_id == Constituent.id)
    if operator == "is_empty":
        return or_(~exists(sub), exists(sub.where(pred)))
    if operator in ("not_equals", "is_none_of"):
        return exists(
            sub.where(EducationRecord.institution_name.is_not(None)).where(pred)
        )
    return exists(sub.where(pred))


def _person_predicate(column: Any, operator: str, value: Any, values: list | None) -> Any:
    pred = _text_predicate(column, operator, value, values)
    sub = select(Person.constituent_id).where(Person.constituent_id == Constituent.id)
    if operator == "is_empty":
        return or_(~exists(sub), exists(sub.where(pred)))
    if operator in ("not_equals", "is_none_of"):
        return exists(sub.where(column.is_not(None)).where(pred))
    return exists(sub.where(pred))


# -- derived tenures ----------------------------------------------------------

def _years_ago_cutoff(years: float) -> date:
    return date.today() - timedelta(days=int(float(years) * 365.25))


def _tenure_predicate(operator: str, value: Any, values: list | None, scope: str) -> Any:
    """scope: 'current' (company/position tenure) or 'experience' (earliest start)."""
    dated = Affiliation.start_date.is_not(None)
    if scope == "current":
        def current_dated() -> Any:
            return _aff_exists(dated, current=True)

        def current_old(cutoff: date, strict: bool) -> Any:
            cmp = Affiliation.start_date < cutoff if strict else Affiliation.start_date <= cutoff
            return _aff_exists(dated & cmp, current=True)

        if operator == "is_empty":
            return ~current_dated()
        if operator == "is_not_empty":
            return current_dated()
        if operator in ("gte", "gt"):
            return current_old(_years_ago_cutoff(float(value)), strict=operator == "gt")  # type: ignore[arg-type]
        if operator in ("lte", "lt"):
            cutoff = _years_ago_cutoff(float(value))  # type: ignore[arg-type]
            cmp = Affiliation.start_date > cutoff if operator == "lt" else Affiliation.start_date >= cutoff
            return _aff_exists(dated & cmp, current=True)
        # between [lo, hi]
        assert values is not None and len(values) == 2
        lo, hi = float(values[0]), float(values[1])  # type: ignore[arg-type]
        if lo > hi:
            lo, hi = hi, lo
        recent, older = _years_ago_cutoff(lo), _years_ago_cutoff(hi)
        return _aff_exists(dated & (Affiliation.start_date <= recent) & (Affiliation.start_date >= older), current=True)
    # experience: earliest start across all affiliations
    if operator == "is_empty":
        return ~_aff_exists(dated)
    if operator == "is_not_empty":
        return _aff_exists(dated)
    if operator in ("gte", "gt"):
        cutoff = _years_ago_cutoff(float(value))  # type: ignore[arg-type]
        cmp = Affiliation.start_date < cutoff if operator == "gt" else Affiliation.start_date <= cutoff
        return _aff_exists(dated & cmp)
    if operator in ("lte", "lt"):
        cutoff = _years_ago_cutoff(float(value))  # type: ignore[arg-type]
        # Earliest start must be on/after (lte) or after (lt) the cutoff,
        # and at least one dated affiliation must exist.
        older = Affiliation.start_date < cutoff if operator == "lte" else Affiliation.start_date <= cutoff
        return _aff_exists(dated) & ~_aff_exists(dated & older)
    assert values is not None and len(values) == 2
    lo, hi = float(values[0]), float(values[1])  # type: ignore[arg-type]
    if lo > hi:
        lo, hi = hi, lo
    recent, older = _years_ago_cutoff(lo), _years_ago_cutoff(hi)
    return _aff_exists(dated & (Affiliation.start_date <= recent)) & ~_aff_exists(
        dated & (Affiliation.start_date < older)
    )


def _compile_condition(cond: FilterCondition) -> Any:
    f, op = cond.field, cond.operator
    v, vs = cond.value, cond.values
    if f == "current_company":
        return _company_name_predicate(op, v, vs, current=True)
    if f == "past_company":
        return _company_name_predicate(op, v, vs, current=False)
    if f == "company_type":
        return _company_type_predicate(op, vs)
    if f == "company_hq":
        return _hq_predicate(op, v, vs)
    if f == "function":
        return _multi_aff_predicate(Affiliation.function, op, vs)
    if f == "current_job_title":
        return _aff_text_field_predicate(Affiliation.designation, op, v, vs, current=True)
    if f == "seniority_level":
        return _multi_aff_predicate(Affiliation.seniority_level, op, vs)
    if f == "past_job_title":
        return _aff_text_field_predicate(Affiliation.designation, op, v, vs, current=False)
    if f == "years_in_current_company":
        return _tenure_predicate(op, v, vs, "current")
    if f == "years_in_current_position":
        return _tenure_predicate(op, v, vs, "current")
    if f == "geography":
        return _geography_predicate(op, v, vs)
    if f == "industry":
        return _multi_aff_predicate(Affiliation.sector, op, vs)
    if f == "first_name":
        return _person_predicate(Person.first_name, op, v, vs)
    if f == "last_name":
        return _person_predicate(Person.last_name, op, v, vs)
    if f == "years_of_experience":
        return _tenure_predicate(op, v, vs, "experience")
    if f == "school":
        return _school_predicate(op, v, vs)
    raise ValueError(f"Unknown filter field: {f!r}")  # validated earlier; guard only


# -- shared M1 search fragments (intersection semantics) ----------------------

def apply_m1_search_filters(
    query: Any,
    *,
    q: str | None,
    roll_no: str | None,
    kind: str | None,
    status: str | None,
    organisation_q: str | None,
    stale_threshold_days: int | None,
) -> Any:
    """Apply the preserved M1 search semantics (GET parity) to a base query."""
    from datetime import datetime, timezone

    if roll_no:
        sub = select(AlumniProfile.constituent_id).where(
            AlumniProfile.roll_no == roll_no.strip().upper()
        )
        query = query.where(Constituent.id.in_(sub))
    elif q:
        query = query.where(Constituent.normalised_display_name.ilike(f"%{q.strip().lower()}%"))
    if kind:
        try:
            query = query.where(Constituent.kind == ConstituentKind(kind.upper()))
        except ValueError:
            raise ValueError(f"Invalid kind: {kind}. Must be PERSON or ORGANISATION.")
    if status:
        try:
            query = query.where(Constituent.status == ConstituentStatus(status.upper()))
        except ValueError:
            raise ValueError(f"Invalid status: {status}.")
    if organisation_q:
        term = f"%{organisation_q.strip().lower()}%"
        query = query.where(
            exists(
                select(Affiliation.id)
                .select_from(Affiliation)
                .outerjoin(
                    Organisation,
                    Affiliation.organisation_id == Organisation.constituent_id,
                )
                .where(Affiliation.constituent_id == Constituent.id)
                .where(
                    or_(
                        Organisation.normalised_name.ilike(term),
                        Affiliation.organisation_name_raw.ilike(term),
                    )
                )
            )
        )
    if stale_threshold_days is not None:
        from datetime import timedelta as _td

        cutoff = datetime.now(timezone.utc) - _td(days=stale_threshold_days)
        query = query.where(
            Constituent.kind == ConstituentKind.PERSON,
            Constituent.status.notin_([ConstituentStatus.DECEASED, ConstituentStatus.ARCHIVED]),
            or_(
                Constituent.last_substantive_profile_update_at.is_(None),
                Constituent.last_substantive_profile_update_at < cutoff,
            ),
            exists(
                select(AlumniProfile.constituent_id).where(
                    AlumniProfile.constituent_id == Constituent.id
                )
            ),
        )
    return query
