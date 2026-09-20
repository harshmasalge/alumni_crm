"""First-boot demo bootstrap for staging/demo deployments (e.g. Render).

When `DEMO_SEED=true`, the API lifespan calls `run_demo_bootstrap()` once per
boot. It brings an empty database to the same state a local deployment has
after running the dev seed scripts:

- access catalog (permissions, roles, grants) — idempotent upsert by name,
- four demo accounts (admin/staff/viewer/finance) with `DEMO_PASSWORD`,
- ~`DEMO_ALUMNI_COUNT` fictional alumni with education, career history
  (current + past), contacts, addresses, and a realistic fresh/stale spread
  so the profile-freshness dashboard shows meaningful numbers,
- one manual demo group with members.

Rules that keep this safe:

- ALL demo people are fictional (Faker, fixed seed — every boot that seeds
  produces the same dataset). Never real alumni, donor, or financial data.
- Refuses to run when `environment == "production"`. Production uses Sign in
  with Google (ADR-003) and IITGN-controlled break-glass admins — this module
  is not the production recovery model.
- Secrets travel via env vars only. Passwords are hashed with bcrypt before
  storage and never logged.
- Alumni seeding runs only when the constituents table is empty, so data
  created during a demo survives container restarts. Demo users are
  declarative: missing accounts are recreated and passwords reset to
  `DEMO_PASSWORD` on every boot, so leadership always knows the logins.
- Direct inserts (no HTTP actor), so no audit rows are written for the seed
  itself — same convention as the local seed scripts.
"""

import logging
import random
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.access_catalog import DEMO_USERS, PERMISSIONS, ROLE_PERMS, ROLES
from app.db.session import async_session_factory
from app.models import (
    Address,
    AddressType,
    Affiliation,
    AffiliationSource,
    AffiliationType,
    AlumniProfile,
    CommunicationPreferences,
    Constituent,
    ConstituentKind,
    ConstituentStatus,
    ContactMethod,
    ContactType,
    DatePrecision,
    EducationRecord,
    EducationStage,
    Gender,
    Group,
    GroupMembership,
    GroupStatus,
    GroupType,
    Permission,
    Person,
    Role,
    RolePermission,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

# Fixed seed: every database seeded by this module holds the same dataset,
# so the leadership demo is reproducible across deploys.
FAKER_SEED = 20260920
DEMO_GROUP_NAME = "Demo — Batch of 2019"

_DISCIPLINES = [
    "Computer Science and Engineering",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
    "Materials Engineering",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Cognitive and Brain Sciences",
    "Society and Culture",
]

_PROGRAMMES = ["BTech", "BTech", "BTech", "MTech", "MSc", "MA", "PhD"]

_CURRENT_ORGS = [
    ("Google", "Software Engineer", "Technology"),
    ("Microsoft", "Product Manager", "Technology"),
    ("Amazon", "Data Scientist", "Technology"),
    ("Goldman Sachs", "Analyst", "Finance"),
    ("Tata Motors", "Design Engineer", "Manufacturing"),
    ("ISRO", "Scientist", "Research"),
    ("IIT Gandhinagar", "Research Associate", "Academia"),
    ("Flipkart", "Business Analyst", "E-commerce"),
    ("Infosys", "Systems Engineer", "Technology"),
    ("McKinsey & Company", "Associate", "Consulting"),
]

_PAST_ORGS = [
    ("Google", "Software Engineering Intern", "Technology"),
    ("Infosys", "Systems Engineer", "Technology"),
    ("TCS", "Assistant Consultant", "Technology"),
    ("L&T", "Graduate Trainee", "Manufacturing"),
]

_CITIES = [
    ("Bengaluru", "Karnataka", "India"),
    ("Mumbai", "Maharashtra", "India"),
    ("Gandhinagar", "Gujarat", "India"),
    ("Ahmedabad", "Gujarat", "India"),
    ("Hyderabad", "Telangana", "India"),
    ("Chennai", "Tamil Nadu", "India"),
    ("Pune", "Maharashtra", "India"),
    ("New Delhi", "Delhi", "India"),
    ("Singapore", "Singapore", "Singapore"),
    ("London", "England", "United Kingdom"),
]

_BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]


def stale_plan(index: int) -> int:
    """Deterministic days-since-update for demo person ``index``.

    Spreads ~0–700 days so roughly half the demo alumni are stale (>365
    days) and the freshness dashboard drill-down has something to show.
    Pure function — unit tested without a database.
    """
    return (index * 37) % 700


def _wants_demo() -> bool:
    return settings.demo_seed


async def ensure_access_catalog(session: AsyncSession) -> None:
    """Idempotent upsert of permissions, roles, and role grants by name."""
    existing_perms = (await session.execute(select(Permission))).scalars().all()
    perm_by_name = {p.name: p for p in existing_perms}
    for name, module, action, description in PERMISSIONS:
        row = perm_by_name.get(name)
        if row is None:
            row = Permission(
                name=name, module=module, action=action, description=description
            )
            session.add(row)
            perm_by_name[name] = row
        else:
            row.module, row.action, row.description = module, action, description
    await session.flush()

    existing_roles = (await session.execute(select(Role))).scalars().all()
    role_by_name = {r.name: r for r in existing_roles}
    for name, description in ROLES:
        if name not in role_by_name:
            role = Role(name=name, description=description)
            session.add(role)
            role_by_name[name] = role
    await session.flush()

    grants = (await session.execute(select(RolePermission))).scalars().all()
    have = {(g.role_id, g.permission_id) for g in grants}
    for role_name, perm_names in ROLE_PERMS.items():
        wanted = (
            list(perm_by_name.values())
            if perm_names == ["*"]
            else [perm_by_name[n] for n in perm_names]
        )
        role_id = role_by_name[role_name].id
        for perm in wanted:
            if (role_id, perm.id) not in have:
                session.add(
                    RolePermission(role_id=role_id, permission_id=perm.id)
                )
                have.add((role_id, perm.id))
    await session.flush()


async def ensure_demo_users(session: AsyncSession, password: str) -> list[User]:
    """Declarative demo accounts: recreate missing, reset passwords/roles."""
    hashed = get_password_hash(password)
    roles = {
        r.name: r
        for r in (await session.execute(select(Role))).scalars().all()
    }
    users: list[User] = []
    for email, full_name, role_name, is_superuser in DEMO_USERS:
        user = (
            await session.execute(select(User).where(User.email == email))
        ).scalars().first()
        if user is None:
            user = User(email=email, full_name=full_name)
            session.add(user)
        user.full_name = full_name
        user.hashed_password = hashed
        user.is_active = True
        user.is_superuser = is_superuser
        await session.flush()
        grant = (
            await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == roles[role_name].id,
                )
            )
        ).scalars().first()
        if grant is None:
            session.add(
                UserRole(user_id=user.id, role_id=roles[role_name].id)
            )
        users.append(user)
    await session.flush()
    return users


async def count_constituents(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(Constituent.id)))
    return int(result.scalar() or 0)


async def seed_demo_constituents(
    session: AsyncSession, count: int
) -> list[Constituent]:
    """Insert ``count`` fictional alumni. Caller guarantees an empty table."""
    Faker.seed(FAKER_SEED)
    rng = random.Random(FAKER_SEED)
    fake = Faker("en_IN")
    now = datetime.now(UTC)
    made: list[Constituent] = []

    for i in range(count):
        first = fake.first_name()
        last = fake.last_name()
        full = f"{first} {last}"
        roll = f"19{i:06d}"
        grad_year = 2012 + (i * 13) % 13
        programme = rng.choice(_PROGRAMMES)
        discipline = rng.choice(_DISCIPLINES)
        days_ago = stale_plan(i)

        constituent = Constituent(
            kind=ConstituentKind.PERSON,
            status=ConstituentStatus.ACTIVE,
            display_name=full,
            normalised_display_name=full.lower(),
            profile_completeness_percent=50,
            last_substantive_profile_update_at=now - timedelta(days=days_ago),
        )
        session.add(constituent)
        await session.flush()

        session.add(
            Person(
                constituent_id=constituent.id,
                first_name=first,
                full_name=full,
                last_name=last,
                gender=rng.choice([Gender.MALE, Gender.FEMALE]),
                date_of_birth=date(1990 + (i % 10), (i % 12) + 1, (i % 27) + 1),
                blood_group=_BLOOD_GROUPS[i % len(_BLOOD_GROUPS)],
            )
        )
        session.add(
            AlumniProfile(
                constituent_id=constituent.id,
                roll_no=roll,
                iitgn_email=f"{roll.lower()}@iitgn.ac.in",
                year_of_graduation=grad_year,
                final_cpi=round(6.0 + ((i * 37) % 400) / 100, 2)
                if i % 10 < 7
                else None,
                jee_air=1000 + ((i * 101) % 9000) if programme == "BTech" else None,
            )
        )
        session.add(
            EducationRecord(
                constituent_id=constituent.id,
                education_stage=EducationStage.IITGN,
                qualification=programme,
                institution_name="IIT Gandhinagar",
                field_of_study=discipline,
                completion_year=grad_year,
                is_verified=True,
            )
        )
        if i % 5 == 0:  # some alumni went on to further study
            session.add(
                EducationRecord(
                    constituent_id=constituent.id,
                    education_stage=EducationStage.POST_IITGN,
                    qualification="MS",
                    institution_name="Carnegie Mellon University",
                    field_of_study=discipline,
                    start_year=grad_year,
                    completion_year=grad_year + 2,
                    is_verified=False,
                )
            )

        org, designation, sector = _CURRENT_ORGS[i % len(_CURRENT_ORGS)]
        if i % 10 == 0:  # anchor org-search demo: several current Googlers
            org, designation, sector = ("Google", "Software Engineer", "Technology")
        city, state, country = _CITIES[i % len(_CITIES)]
        start = date(grad_year + (i % 3), (i % 12) + 1, 1)
        session.add(
            Affiliation(
                constituent_id=constituent.id,
                organisation_name_raw=org,
                affiliation_type=AffiliationType.PRIVATE,
                designation=designation,
                sector=sector,
                city=city,
                state=state,
                country=country,
                start_date=start,
                is_current=True,
                date_precision=DatePrecision.MONTH,
                source=AffiliationSource.IMPORT,
            )
        )
        if i % 10 == 1:  # org-search demo: Google as a *past* affiliation
            session.add(
                Affiliation(
                    constituent_id=constituent.id,
                    organisation_name_raw="Google",
                    affiliation_type=AffiliationType.PRIVATE,
                    designation="Software Engineering Intern",
                    sector="Technology",
                    city=city,
                    state=state,
                    country=country,
                    start_date=date(grad_year, 6, 1),
                    end_date=date(grad_year + 1, 5, 31),
                    is_current=False,
                    date_precision=DatePrecision.MONTH,
                    source=AffiliationSource.IMPORT,
                )
            )
        elif i % 4 == 0:
            # Skip _PAST_ORGS[0] (Google) here — Google past affiliations
            # come only from the i % 10 == 1 anchors above, keeping the
            # demo's Google footprint realistic.
            past_org, past_role, past_sector = _PAST_ORGS[
                (i % (len(_PAST_ORGS) - 1)) + 1
            ]
            session.add(
                Affiliation(
                    constituent_id=constituent.id,
                    organisation_name_raw=past_org,
                    affiliation_type=AffiliationType.PRIVATE,
                    designation=past_role,
                    sector=past_sector,
                    city=city,
                    state=state,
                    country=country,
                    start_date=date(grad_year, 7, 1),
                    end_date=date(grad_year + 1, 6, 30),
                    is_current=False,
                    date_precision=DatePrecision.MONTH,
                    source=AffiliationSource.IMPORT,
                )
            )

        personal = f"{first}.{last}{i}@example.com".lower()
        for value, ctype, primary in (
            (f"{roll.lower()}@iitgn.ac.in", ContactType.EMAIL_IITGN, True),
            (personal, ContactType.EMAIL_PERSONAL, False),
            (f"+91 9{(i * 7919) % 1_000_000_000:09d}", ContactType.PHONE_PRIMARY, False),
        ):
            session.add(
                ContactMethod(
                    constituent_id=constituent.id,
                    contact_type=ctype,
                    value=value,
                    normalised_value=value.lower(),
                    is_primary=primary,
                    is_verified=False,
                    is_active=True,
                )
            )
        session.add(
            Address(
                constituent_id=constituent.id,
                address_type=AddressType.CURRENT,
                line1=fake.street_address(),
                city=city,
                state=state,
                country=country,
                is_active=True,
            )
        )
        session.add(
            CommunicationPreferences(
                constituent_id=constituent.id,
                email_opt_in=True,
                whatsapp_opt_in=False,
                sms_opt_in=False,
                global_dnc=False,
            )
        )
        made.append(constituent)

    await session.flush()
    return made


async def seed_demo_group(
    session: AsyncSession,
    created_by_id: UUID | None,
    members: list[Constituent],
) -> Group:
    """One manual demo group (idempotent by name, tops up membership)."""
    group = (
        await session.execute(select(Group).where(Group.name == DEMO_GROUP_NAME))
    ).scalars().first()
    if group is None:
        group = Group(
            name=DEMO_GROUP_NAME,
            description="Fictional demo cohort for leadership walkthroughs.",
            type=GroupType.MANUAL,
            status=GroupStatus.ACTIVE,
            created_by=created_by_id,
        )
        session.add(group)
        await session.flush()
    have = {
        m.constituent_id
        for m in (
            await session.execute(
                select(GroupMembership).where(GroupMembership.group_id == group.id)
            )
        )
        .scalars()
        .all()
    }
    for person in members[:12]:
        if person.id not in have:
            session.add(
                GroupMembership(
                    group_id=group.id,
                    constituent_id=person.id,
                    added_by=created_by_id,
                )
            )
            have.add(person.id)
    await session.flush()
    return group


async def run_demo_bootstrap() -> None:
    """Entry point: seed demo state when enabled. Safe to run every boot."""
    if not _wants_demo():
        return
    if settings.environment == "production":
        raise RuntimeError(
            "DEMO_SEED is enabled while ENVIRONMENT=production. Demo seeding "
            "is for staging/demo environments only — refusing to run."
        )
    if not settings.demo_password:
        raise RuntimeError(
            "DEMO_SEED is enabled but DEMO_PASSWORD is empty. Set DEMO_PASSWORD "
            "to provision the demo accounts."
        )

    async with async_session_factory() as session:
        await ensure_access_catalog(session)
        users = await ensure_demo_users(session, settings.demo_password)
        admin_id = next(u.id for u in users if u.is_superuser)

        seeded = 0
        if await count_constituents(session) == 0:
            people = await seed_demo_constituents(
                session, settings.demo_alumni_count
            )
            await seed_demo_group(session, admin_id, people)
            seeded = len(people)

        await session.commit()

    logger.info(
        "Demo bootstrap complete: %d demo users ensured, %d demo alumni "
        "seeded (0 means data already present).",
        len(users),
        seeded,
    )
