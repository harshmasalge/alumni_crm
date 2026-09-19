#!/usr/bin/env python
"""
Seed clearly-fictional fixtures for the T-table M1-extension slice.

Attaches hostel, transcript, performance, awards, internship, placement,
POR, publication, and overseas rows to the first alumni in the database,
plus one SSAC row and family rows on the very first profile so the
restricted-gating tests have data. Idempotent: skips constituents that
already have fixtures (marked by a 'DEMO-FIXTURE' hostel row).
Run after migrations: python scripts/seed_academic.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.db.session import async_session_factory
from app.models import (
    AcademicCourse,
    AlumniProfile,
    AwardRecognition,
    Constituent,
    ConstituentKind,
    FamilyMember,
    GpsAssignment,
    HostelHistory,
    Internship,
    OverseasExposure,
    Placement,
    PositionOfResponsibility,
    ProgrammeLevel,
    Publication,
    SemesterPerformance,
    SsacRecord,
)
from sqlalchemy import select


SAMPLE_LIMIT = 20


async def seed():
    async with async_session_factory() as session:
        result = await session.execute(
            select(Constituent.id)
            .join(AlumniProfile, Constituent.id == AlumniProfile.constituent_id)
            .where(Constituent.kind == ConstituentKind.PERSON)
            .order_by(Constituent.display_name)
            .limit(SAMPLE_LIMIT)
        )
        ids = list(result.scalars().all())
        if not ids:
            print("No alumni found; run scripts/seed_alumni.py first.")
            return

        # Idempotency marker.
        existing = await session.execute(
            select(HostelHistory.constituent_id).where(
                HostelHistory.hostel_name == "DEMO-FIXTURE"
            )
        )
        done = set(existing.scalars().all())
        fresh = [i for i in ids if i not in done]
        if not fresh:
            print("Academic fixtures already seeded.")
            return

        hostels = ["Vikram Sarabhai Hall", "C. V. Raman Hall", "Homi Bhabha Hall"]
        for n, cid in enumerate(fresh):
            yog = 2015 + (n % 8)
            session.add(HostelHistory(
                constituent_id=cid, hostel_name=hostels[n % 3],
                room_number=f"{100 + n}", academic_year=f"{yog - 4}-{yog}", semester="Even",
            ))
            session.add(HostelHistory(
                constituent_id=cid, hostel_name="DEMO-FIXTURE",
                academic_year=f"{yog - 4}-{yog}", semester="Even",
            ))
            session.add(AcademicCourse(
                constituent_id=cid, programme_level=ProgrammeLevel.UG,
                course_code="CS101", course_name="Introduction to Computing",
                credits=4.0, year=yog - 3, semester="Odd",
                instructor="Demo Faculty", grade="AA",
            ))
            session.add(AcademicCourse(
                constituent_id=cid, programme_level=ProgrammeLevel.UG,
                course_code="MA201", course_name="Linear Algebra",
                credits=4.0, year=yog - 3, semester="Even",
                instructor="Demo Faculty", grade="AB",
            ))
            session.add(SemesterPerformance(
                constituent_id=cid, programme_level=ProgrammeLevel.UG,
                year=yog - 3, semester="Even", spi=8.5, cpi=8.4,
            ))
            session.add(GpsAssignment(
                constituent_id=cid, year=yog - 2, semester="Odd",
                coordinator_name="Demo Coordinator",
            ))
            session.add(AwardRecognition(
                constituent_id=cid, award_type="Dean's List",
                award_date=date(yog - 2, 5, 15), agency="IIT Gandhinagar",
                details="Demo fixture award", academic_year=str(yog - 2), semester="Even",
            ))
            session.add(Internship(
                constituent_id=cid, scope="Domestic", format="Offline",
                duration_text="8 weeks", organisation="Demo Labs",
                year=yog - 1, funding_source="Institute stipend", funding_amount=20000,
            ))
            session.add(Placement(
                constituent_id=cid, scope="Domestic", company="Demo Corp",
                sector="IT", city="Bengaluru", state="Karnataka", country="India",
                ctc=1200000, date_of_joining=date(yog, 7, 1),
            ))
            session.add(PositionOfResponsibility(
                constituent_id=cid, title="Demo Club Coordinator",
                domain="Club", academic_year=str(yog - 1),
            ))
            session.add(Publication(
                constituent_id=cid, title="Demo Research Paper",
                doi="10.0000/demo.fixture", pub_date=date(yog, 3, 10),
            ))
            session.add(OverseasExposure(
                constituent_id=cid, organisation="Demo Exchange University",
                year=yog - 1, start_date=date(yog - 1, 1, 10), end_date=date(yog - 1, 5, 20),
                funding_details="Demo scholarship", funding_amount=150000,
            ))

        # Restricted fixtures on the first profile only.
        first = fresh[0]
        session.add(SsacRecord(
            constituent_id=first, incident_details="Demo fixture incident (fictional)",
            sanction_letter_date=date(2019, 9, 1),
        ))
        session.add(FamilyMember(
            constituent_id=first, name="Demo Guardian", relation="Parent",
            contact_number="+91-0000000000", email="guardian@example.invalid",
        ))

        await session.commit()
        print(f"Seeded academic fixtures for {len(fresh)} alumni.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
