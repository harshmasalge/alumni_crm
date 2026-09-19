"""M1.1 Phase A — people segmentation, filter DSL, taxonomies.

Unit tests run without a database. Integration tests use httpx.ASGITransport
against real PostgreSQL (like the M1 suite) with dedicated SegTest fixtures
that are removed afterwards so seeded data stays pristine.

Profile-photo tests are out of scope and live in test_api_integration.py;
this module never touches them.
"""

import uuid
from datetime import date

import httpx
import pytest

from app.main import app
from app.schemas import AdvancedSearchRequest, FILTER_FIELD_REGISTRY
from app.services.segmentation import (
    PhaseBReservedError,
    compile_filter,
    validate_filter_tree,
)


# ---------------------------------------------------------------------------
# Unit: filter DSL validation (no database required)
# ---------------------------------------------------------------------------


def test_registry_covers_m11_company_role_personal_fields():
    required = {
        "current_company",
        "past_company",
        "company_type",
        "company_hq",
        "function",
        "current_job_title",
        "seniority_level",
        "past_job_title",
        "years_in_current_company",
        "years_in_current_position",
        "geography",
        "industry",
        "first_name",
        "last_name",
        "years_of_experience",
        "school",
    }
    assert required <= set(FILTER_FIELD_REGISTRY)
    # Groups is Phase B: known to the contract, never in the Phase A registry.
    assert "groups" not in FILTER_FIELD_REGISTRY


def test_validate_accepts_prompt_example_nested_tree():
    req = AdvancedSearchRequest(
        **{
            "filter": {
                "op": "and",
                "conditions": [
                    {"field": "current_company", "operator": "equals", "value": "Google"},
                    {"field": "geography", "operator": "equals", "value": "India"},
                    {
                        "op": "or",
                        "conditions": [
                            {
                                "field": "seniority_level",
                                "operator": "is_any_of",
                                "values": ["Director"],
                            },
                            {
                                "field": "seniority_level",
                                "operator": "is_any_of",
                                "values": ["VP", "C-Level"],
                            },
                        ],
                    },
                ],
            }
        }
    )
    assert validate_filter_tree(req.filter) == 4
    compile_filter(req.filter)  # must not raise


def test_validate_rejects_unknown_field():
    req = AdvancedSearchRequest(
        filter={"op": "and", "conditions": [{"field": "nope", "operator": "equals", "value": "x"}]}  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="Unknown filter field"):
        validate_filter_tree(req.filter)


def test_validate_rejects_nonsensical_operator():
    req = AdvancedSearchRequest(
        filter={
            "op": "and",
            "conditions": [{"field": "years_of_experience", "operator": "contains", "value": "x"}],
        }  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="not supported"):
        validate_filter_tree(req.filter)


def test_validate_rejects_bad_value_shapes():
    cases = [
        {"field": "current_company", "operator": "equals"},  # missing value
        {"field": "industry", "operator": "is_any_of", "values": []},  # empty list
        {"field": "years_of_experience", "operator": "between", "values": [2]},  # arity
        {"field": "years_of_experience", "operator": "gte", "value": "many"},  # non-numeric
        {"field": "school", "operator": "is_empty", "value": "x"},  # value forbidden
    ]
    for cond in cases:
        req = AdvancedSearchRequest(filter={"op": "and", "conditions": [cond]})  # type: ignore[list-item]
        with pytest.raises(ValueError):
            validate_filter_tree(req.filter)


def test_validate_rejects_deep_nesting_and_floods():
    deep: dict = {"field": "school", "operator": "contains", "value": "x"}
    for _ in range(5):
        deep = {"op": "and", "conditions": [deep]}
    req = AdvancedSearchRequest(filter=deep)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="nesting"):
        validate_filter_tree(req.filter)

    many = [{"field": "school", "operator": "contains", "value": f"s{i}"} for i in range(60)]
    req = AdvancedSearchRequest(filter={"op": "and", "conditions": many})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="exceeds"):
        validate_filter_tree(req.filter)


def test_validate_groups_field_is_phase_b_reserved():
    req = AdvancedSearchRequest(
        filter={"op": "and", "conditions": [{"field": "groups", "operator": "is_any_of", "values": ["x"]}]}  # type: ignore[list-item]
    )
    with pytest.raises(PhaseBReservedError, match="Phase B"):
        validate_filter_tree(req.filter)


# ---------------------------------------------------------------------------
# Integration: server-side filtering, taxonomies, org master data
# ---------------------------------------------------------------------------


async def _db_reachable() -> bool:
    from sqlalchemy import text

    from app.db.session import async_session_factory, engine

    try:
        await engine.dispose()
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _login(client: httpx.AsyncClient, email: str, password: str) -> dict:
    r = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code == 401:
        pytest.skip("seed users missing; run scripts/seed_users.py first")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _make_fixtures() -> dict:
    """Two controlled constituents + one resolved organisation for filters."""
    await _drop_fixtures()  # rerun-safe: clear leftovers from a crashed run
    from app.db.session import async_session_factory
    from app.models import (
        Address,
        AddressType,
        Affiliation,
        AffiliationSource,
        AlumniProfile,
        Constituent,
        ConstituentKind,
        ConstituentStatus,
        DatePrecision,
        EducationRecord,
        EducationStage,
        Organisation,
        Person,
    )

    async with async_session_factory() as session:
        org_constituent = Constituent(
            kind=ConstituentKind.ORGANISATION,
            status=ConstituentStatus.ACTIVE,
            display_name="SegTestOrgMaster",
            normalised_display_name="segtestorgmaster",
        )
        session.add(org_constituent)
        await session.flush()
        org = Organisation(
            constituent_id=org_constituent.id,
            legal_name="SegTestCorp",
            normalised_name="segtestcorp",
            sector="IT",
            company_type="STARTUP",
            hq_city="Bengaluru",
            hq_country="India",
        )
        session.add(org)

        people = {}
        for tag, first, last, roll, year in [
            ("ALPHA", "SegAlphaFirst", "SegAlphaLast", "SEGTEST001", 2018),
            ("BETA", "SegBetaFirst", "SegBetaLast", "SEGTEST002", 2021),
        ]:
            c = Constituent(
                kind=ConstituentKind.PERSON,
                status=ConstituentStatus.ACTIVE,
                display_name=f"SegTest {tag} Person",
                normalised_display_name=f"segtest {tag.lower()} person",
                notes="SegSecret",
            )
            session.add(c)
            await session.flush()
            session.add(
                Person(
                    constituent_id=c.id,
                    first_name=first,
                    full_name=f"{first} {last}",
                    last_name=last,
                )
            )
            session.add(
                AlumniProfile(
                    constituent_id=c.id, roll_no=roll, year_of_graduation=year
                )
            )
            people[tag] = c.id

        alpha = people["ALPHA"]
        session.add(
            Affiliation(
                constituent_id=alpha,
                organisation_id=org_constituent.id,
                organisation_name_raw="SegTestCorp",
                designation="Senior Engineer",
                function="Engineering",
                seniority_level="Senior",
                sector="IT",
                city="Bengaluru",
                country="India",
                start_date=date(2020, 1, 15),
                is_current=True,
                date_precision=DatePrecision.DAY,
                source=AffiliationSource.STAFF,
            )
        )
        session.add(
            Affiliation(
                constituent_id=alpha,
                organisation_name_raw="OldCorp",
                designation="Intern",
                sector="Education",
                start_date=date(2018, 6, 1),
                end_date=date(2019, 12, 31),
                is_current=False,
                date_precision=DatePrecision.DAY,
                source=AffiliationSource.STAFF,
            )
        )
        session.add(
            EducationRecord(
                constituent_id=alpha,
                education_stage=EducationStage.POST_IITGN,
                qualification="MTech",
                institution_name="SegTest School of Tech",
                completion_year=2020,
            )
        )
        session.add(
            Address(
                constituent_id=alpha,
                address_type=AddressType.CURRENT,
                line1="221 Seg Street",
                city="Bengaluru",
                country="India",
            )
        )

        beta = people["BETA"]
        session.add(
            Affiliation(
                constituent_id=beta,
                organisation_name_raw="OtherCorp",
                designation="Director of Finance",
                function="Finance",
                seniority_level="Director",
                sector="Finance",
                city="New York",
                country="United States",
                start_date=date(2022, 3, 1),
                is_current=True,
                date_precision=DatePrecision.DAY,
                source=AffiliationSource.STAFF,
            )
        )
        await session.commit()
        return {
            "alpha": str(alpha),
            "beta": str(beta),
            "org": str(org_constituent.id),
        }


async def _drop_fixtures() -> None:
    from sqlalchemy import delete

    from app.db.session import async_session_factory
    from app.models import Constituent

    async with async_session_factory() as session:
        await session.execute(
            delete(Constituent).where(
                Constituent.normalised_display_name.like("segtest%")
            )
        )
        await session.commit()


def _cond(field: str, operator: str, value=None, values=None) -> dict:
    cond = {"field": field, "operator": operator}
    if value is not None:
        cond["value"] = value
    if values is not None:
        cond["values"] = values
    return cond


@pytest.mark.asyncio
async def test_advanced_search_auth_and_field_security():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        # Unauthenticated search is rejected server-side.
        r = await client.post("/constituents/search", json={})
        assert r.status_code == 401

        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")

        # Viewer holds constituents.read: filtering is allowed (read path)...
        r = await client.post("/constituents/search", json={}, headers=viewer)
        assert r.status_code == 200

        # ...but restricted constituent fields stay withheld server-side.
        r = await client.post(
            "/constituents/search", json={"q": "SegTest", "page_size": 100}, headers=viewer
        )
        assert r.status_code == 200

        # Registry endpoint needs auth too.
        r = await client.get("/constituents/search/fields")
        assert r.status_code == 401
        r = await client.get("/constituents/search/fields", headers=staff)
        assert r.status_code == 200
        assert "current_company" in r.json()["fields"]
        assert "groups" not in r.json()["fields"]


@pytest.mark.asyncio
async def test_advanced_search_filters_pagination_and_m1_combination():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")
        ids = await _make_fixtures()
        try:

            async def run(body: dict, headers: dict | None = None):
                # Membership assertions need the whole population: seed data
                # can match the same filters, so default to a full page.
                body = {"page_size": 100, **body}
                r = await client.post(
                    "/constituents/search", json=body, headers=headers or staff
                )
                assert r.status_code == 200, r.text
                return r.json()

            def matched(body_result: dict) -> set:
                return {i["id"] for i in body_result["items"]}

            alpha, beta = ids["alpha"], ids["beta"]

            # No filters: fixtures present among results with a sane count.
            body = await run({"q": "SegTest", "page_size": 100})
            assert {alpha, beta} <= matched(body)
            assert body["total"] >= 2

            # M1 parity: exact Roll Number still resolves one record.
            body = await run({"roll_no": "SEGTEST001"})
            assert matched(body) == {alpha}

            # Company filters backed by employment history (not flat columns).
            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("current_company", "equals", "SegTestCorp")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("past_company", "equals", "OldCorp")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("company_type", "is_any_of", values=["STARTUP"])]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("company_hq", "equals", "Bengaluru")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            # Role filters incl. structured employment attributes. Membership
            # assertions (not exact sets): seeded dev data also contains
            # engineers/interns, which must legitimately match.
            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("current_job_title", "contains", "Engineer")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("past_job_title", "equals", "Intern")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("function", "is_any_of", values=["Engineering"])]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {
                    "filter": {
                        "op": "and",
                        "conditions": [
                            _cond("seniority_level", "is_any_of", values=["Director", "VP"])
                        ],
                    }
                }
            )
            assert beta in matched(body) and alpha not in matched(body)

            # Derived tenures: alpha started 2020, beta 2022.
            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("years_in_current_company", "gte", 5)]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {
                    "filter": {
                        "op": "and",
                        "conditions": [_cond("years_of_experience", "between", values=[5, 15])],
                    }
                }
            )
            assert alpha in matched(body) and beta not in matched(body)

            # Personal filters.
            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("geography", "equals", "India")]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("industry", "is_any_of", values=["IT"])]}}
            )
            assert alpha in matched(body) and beta not in matched(body)

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("first_name", "equals", "SegBetaFirst")]}}
            )
            assert matched(body) == {beta}

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("last_name", "equals", "SegAlphaLast")]}}
            )
            assert matched(body) == {alpha}

            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("school", "contains", "SegTest School")]}}
            )
            assert matched(body) == {alpha}

            # Prompt's nested AND/OR example end to end.
            body = await run(
                {
                    "q": "SegTest",
                    "filter": {
                        "op": "and",
                        "conditions": [
                            _cond("geography", "equals", "India"),
                            {
                                "op": "or",
                                "conditions": [
                                    _cond("seniority_level", "is_any_of", values=["Director"]),
                                    _cond("seniority_level", "is_any_of", values=["Senior"]),
                                ],
                            },
                        ],
                    },
                }
            )
            assert alpha in matched(body) and beta not in matched(body)

            # Organisation substring + structured filter intersect (M1 + M1.1).
            body = await run(
                {
                    "organisation_q": "SegTestCorp",
                    "filter": {
                        "op": "and",
                        "conditions": [_cond("industry", "is_any_of", values=["IT"])],
                    },
                }
            )
            assert alpha in matched(body) and beta not in matched(body)

            # Zero matches, invalid definitions, reserved field.
            body = await run(
                {"filter": {"op": "and", "conditions": [_cond("current_company", "equals", "NoSuchCorpZZZ")]}}
            )
            assert body["total"] == 0 and body["items"] == []

            r = await client.post(
                "/constituents/search",
                json={"filter": {"op": "and", "conditions": [_cond("industry", "contains", "IT")]}},
                headers=staff,
            )
            assert r.status_code == 422

            r = await client.post(
                "/constituents/search",
                json={"filter": {"op": "and", "conditions": [_cond("groups", "is_any_of", values=["x"])]}},
                headers=staff,
            )
            assert r.status_code == 400

            # Pagination is server-side.
            page1 = await run({"q": "SegTest", "page": 1, "page_size": 1})
            page2 = await run({"q": "SegTest", "page": 2, "page_size": 1})
            assert page1["total"] >= 2
            assert page1["items"][0]["id"] != page2["items"][0]["id"]

            # Sorting by graduation year separates the fixtures deterministically.
            body = await run(
                {"q": "SegTest", "page_size": 100, "sort_by": "year_of_graduation", "sort_dir": "desc"}
            )
            order = [i["id"] for i in body["items"]]
            assert order.index(beta) < order.index(alpha)

            # Field-level security on list results: viewer never sees notes.
            staff_body = await run({"q": "SegTest", "page_size": 100})
            viewer_body = await run({"q": "SegTest", "page_size": 100}, viewer)
            staff_alpha = next(i for i in staff_body["items"] if i["id"] == alpha)
            viewer_alpha = next(i for i in viewer_body["items"] if i["id"] == alpha)
            assert staff_alpha.get("notes") == "SegSecret"
            assert viewer_alpha.get("notes") is None
        finally:
            await _drop_fixtures()


@pytest.mark.asyncio
async def test_taxonomy_management_auth_validation_and_referential_safety():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")
        admin = await _login(client, "admin@iitgn.ac.in", "admin123")
        await _make_fixtures()
        try:
            await _taxonomy_flow(client, staff, viewer, admin)
        finally:
            await _drop_fixtures()


async def _drop_test_taxonomies() -> None:
    from sqlalchemy import delete

    from app.db.session import async_session_factory
    from app.models import Taxonomy

    async with async_session_factory() as session:
        await session.execute(
            delete(Taxonomy).where(
                Taxonomy.category == "seniority_level",
                Taxonomy.normalised_value.in_(
                    ["segfellow", "segfellowrenamed", "segother"]
                ),
            )
        )
        await session.commit()


async def _taxonomy_flow(client, staff, viewer, admin):
        await _drop_test_taxonomies()  # rerun-safe: clear leftovers first
        try:
            await _taxonomy_steps(client, staff, viewer, admin)
        finally:
            await _drop_test_taxonomies()


async def _taxonomy_steps(client, staff, viewer, admin):
        # Seeded industry vocabulary from real sector profiling is listed.
        r = await client.get("/taxonomies?category=industry", headers=staff)
        assert r.status_code == 200
        seeded = {i["value"] for i in r.json()["items"]}
        assert {"IT", "Education", "Finance"} <= seeded

        # Unauthenticated + viewer writes are rejected server-side.
        r = await client.post("/taxonomies", json={"category": "function", "value": "X"})
        assert r.status_code == 401
        r = await client.post(
            "/taxonomies", json={"category": "function", "value": "X"}, headers=viewer
        )
        assert r.status_code == 403

        # Staff create + duplicate protection (case-insensitive).
        r = await client.post(
            "/taxonomies",
            json={"category": "seniority_level", "value": "SegFellow"},
            headers=staff,
        )
        assert r.status_code == 201, r.text
        created_id = r.json()["id"]
        assert r.json()["usage_count"] == 0
        r = await client.post(
            "/taxonomies",
            json={"category": "seniority_level", "value": "segfellow"},
            headers=staff,
        )
        assert r.status_code == 409

        # Rename works; rename conflict is rejected. Values stay unreferenced
        # (fixtures use 'Senior'/'Director' affiliations, so those names are
        # avoided here to keep the delete path deterministic).
        r = await client.patch(
            f"/taxonomies/{created_id}", json={"value": "SegFellowRenamed"}, headers=staff
        )
        assert r.status_code == 200
        assert r.json()["value"] == "SegFellowRenamed"
        other_id = (
            await client.post(
                "/taxonomies",
                json={"category": "seniority_level", "value": "SegOther"},
                headers=staff,
            )
        ).json()["id"]
        r = await client.patch(
            f"/taxonomies/{other_id}", json={"value": "SegFellowRenamed"}, headers=staff
        )
        assert r.status_code == 409

        # Referenced values cannot be destructively deleted...
        industry_rows = (
            await client.get("/taxonomies?category=industry", headers=staff)
        ).json()["items"]
        it_row = next(i for i in industry_rows if i["value"] == "IT")
        assert it_row["usage_count"] >= 1
        r = await client.delete(f"/taxonomies/{it_row['id']}", headers=staff)
        assert r.status_code == 409

        # ...but soft-deactivation is always allowed for referenced values.
        r = await client.patch(
            f"/taxonomies/{it_row['id']}", json={"is_active": False}, headers=staff
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        r = await client.get("/taxonomies?category=industry", headers=staff)
        assert "IT" not in {i["value"] for i in r.json()["items"]}
        r = await client.get(
            "/taxonomies?category=industry&include_inactive=true", headers=staff
        )
        assert "IT" in {i["value"] for i in r.json()["items"]}
        # Restore for other tests / developers.
        r = await client.patch(
            f"/taxonomies/{it_row['id']}", json={"is_active": True}, headers=staff
        )
        assert r.status_code == 200

        # Unreferenced values delete cleanly; audit trail records the writes.
        r = await client.delete(f"/taxonomies/{created_id}", headers=staff)
        assert r.status_code == 204
        r = await client.delete(f"/taxonomies/{other_id}", headers=staff)
        assert r.status_code == 204

        r = await client.get(
            "/admin/audit-events?entity_type=taxonomy&page_size=50", headers=admin
        )
        assert r.status_code == 200
        actions = {e["action"] for e in r.json()["items"]}
        assert {"TAXONOMY_CREATE", "TAXONOMY_UPDATE", "TAXONOMY_DELETE"} <= actions


@pytest.mark.asyncio
async def test_organisation_master_data_and_filtered_search_audit():
    if not await _db_reachable():
        pytest.skip("PostgreSQL unreachable; run docker-compose up -d postgres redis first")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test/api/v1", timeout=30.0
    ) as client:
        staff = await _login(client, "staff@iitgn.ac.in", "staff123")
        viewer = await _login(client, "viewer@iitgn.ac.in", "viewer123")
        ids = await _make_fixtures()
        try:
            r = await client.get(f"/organisations/{ids['org']}")
            assert r.status_code == 401
            r = await client.get(f"/organisations/{ids['org']}", headers=viewer)
            assert r.status_code == 200
            assert r.json()["company_type"] == "STARTUP"

            # Viewer cannot edit master data (server-side, not UI hiding).
            r = await client.patch(
                f"/organisations/{ids['org']}",
                json={"hq_country": "Atlantis"},
                headers=viewer,
            )
            assert r.status_code == 403

            r = await client.patch(
                f"/organisations/{ids['org']}",
                json={"hq_country": "India", "company_type": "STARTUP"},
                headers=staff,
            )
            assert r.status_code == 200
            assert r.json()["hq_country"] == "India"

            # Filtered search generates a centralized audit event (metadata
            # only — never exported row data; exports arrive in Phase C).
            request_id = f"segtest-{uuid.uuid4()}"
            r = await client.post(
                "/constituents/search",
                json={"filter": {"op": "and", "conditions": [_cond("industry", "is_any_of", values=["IT"])]}},
                headers={**staff, "X-Request-ID": request_id},
            )
            assert r.status_code == 200
            r = await client.get(
                "/admin/audit-events?action=SEARCH_FILTERED&page_size=5", headers=staff
            )
            assert r.status_code == 200
            assert any(e["action"] == "SEARCH_FILTERED" for e in r.json()["items"])
        finally:
            await _drop_fixtures()
