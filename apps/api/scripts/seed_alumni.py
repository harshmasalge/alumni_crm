#!/usr/bin/env python
"""
Seed script to populate database with ~100 alumni from Excel file.
Run after migrations: python scripts/seed_alumni.py
"""
import sys
import uuid
from datetime import datetime, date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.db.session import engine, async_session_factory, Base
from app.models import (
    Constituent, ConstituentKind, ConstituentStatus,
    Person, Gender,
    AlumniProfile,
    EducationRecord, EducationStage,
    Affiliation, AffiliationType, DatePrecision, AffiliationSource,
    ContactMethod, ContactType,
    Address, AddressType,
    CommunicationPreferences,
)
from sqlalchemy.ext.asyncio import AsyncSession


EXCEL_PATH = Path(__file__).resolve().parents[3] / "Alumni Database.xlsx"
SAMPLE_SIZE = 100


def parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, date)):
        return val
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def parse_year(val):
    if pd.isna(val):
        return None
    try:
        return int(val)
    except Exception:
        return None


def parse_float(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except Exception:
        return None


def parse_int(val):
    if pd.isna(val):
        return None
    try:
        return int(val)
    except Exception:
        return None


def clean_str(val):
    if pd.isna(val) or not str(val).strip():
        return None
    return str(val).strip()


async def seed():
    df = pd.read_excel(EXCEL_PATH)
    df = df.head(SAMPLE_SIZE)

    async with async_session_factory() as session:
        for _, row in df.iterrows():
            roll_no = clean_str(row.get("Roll No"))
            if not roll_no:
                continue

            full_name = clean_str(row.get(" Full Name")) or clean_str(row.get("First Name")) or roll_no
            first_name = clean_str(row.get("First Name")) or full_name.split()[0]
            last_name = clean_str(row.get("Last Name"))
            display_name = full_name

            # Create constituent
            constituent = Constituent(
                kind=ConstituentKind.PERSON,
                status=ConstituentStatus.ACTIVE,
                display_name=display_name,
                normalised_display_name=display_name.lower(),
                profile_completeness_percent=50,
            )
            session.add(constituent)
            await session.flush()

            # Person
            gender_map = {"Male": Gender.MALE, "Female": Gender.FEMALE}
            gender = gender_map.get(clean_str(row.get("Gender")))

            birthday = parse_date(row.get("Birthday"))
            # Excel stores dates as serial numbers (e.g., 34612.0 = 1994-11-15 approx)
            if birthday and birthday.year > 2000:  # likely serial number
                try:
                    birthday = date(1899, 12, 30) + pd.Timedelta(days=int(birthday.toordinal() - date(1899, 12, 30).toordinal()))
                except Exception:
                    birthday = None

            person = Person(
                constituent_id=constituent.id,
                first_name=first_name,
                full_name=full_name,
                last_name=last_name,
                gender=gender,
                date_of_birth=birthday,
                blood_group=clean_str(row.get("Blood Group")),
            )
            session.add(person)

            # Alumni Profile
            alumni = AlumniProfile(
                constituent_id=constituent.id,
                roll_no=roll_no.strip().upper(),
                iitgn_email=clean_str(row.get("IITGn Email")),
                year_of_graduation=parse_year(row.get("Year of Graduation")),
                final_cpi=parse_float(row.get("CPI")),
                jee_air=parse_int(row.get("JEE AIR")),
                gate_air=parse_int(row.get("GATE AIR")),
            )
            session.add(alumni)

            # Education Record (IITGN)
            programme = clean_str(row.get("Programme"))
            discipline = clean_str(row.get("Discipline"))
            if programme or discipline:
                edu = EducationRecord(
                    constituent_id=constituent.id,
                    education_stage=EducationStage.IITGN,
                    qualification=programme or "BTech",
                    institution_name="IIT Gandhinagar",
                    field_of_study=discipline,
                    completion_year=parse_year(row.get("Year of Graduation")),
                    is_verified=True,
                )
                session.add(edu)

            # Affiliation (current job)
            org_name = clean_str(row.get("Organization/Institute/University"))
            designation = clean_str(row.get("Designation"))
            sector = clean_str(row.get("Sector"))
            city = clean_str(row.get("City"))
            state = clean_str(row.get("State/ Province"))
            country = clean_str(row.get("Country"))
            join_date = parse_date(row.get("Month and Year of Joining"))

            if org_name or designation:
                aff = Affiliation(
                    constituent_id=constituent.id,
                    organisation_name_raw=org_name,
                    designation=designation,
                    sector=sector,
                    city=city,
                    state=state,
                    country=country,
                    start_date=join_date,
                    is_current=bool(org_name or designation),
                    date_precision=DatePrecision.MONTH if join_date else DatePrecision.UNKNOWN,
                    source=AffiliationSource.IMPORT,
                )
                session.add(aff)

            # Contact Methods
            contacts = [
                ("IITGn Email", ContactType.EMAIL_IITGN),
                ("Personal Email ID", ContactType.EMAIL_PERSONAL),
                ("Work Email ID", ContactType.EMAIL_WORK),
                ("Phone1", ContactType.PHONE_PRIMARY),
                ("Phone2", ContactType.PHONE_SECONDARY),
            ]
            for col, ctype in contacts:
                val = clean_str(row.get(col))
                if val:
                    cm = ContactMethod(
                        constituent_id=constituent.id,
                        contact_type=ctype,
                        value=val,
                        normalised_value=val.lower(),
                        is_primary=(ctype == ContactType.EMAIL_IITGN),
                        is_verified=False,
                        is_active=True,
                    )
                    session.add(cm)

            # Address
            if city or country:
                addr = Address(
                    constituent_id=constituent.id,
                    address_type=AddressType.CURRENT,
                    line1=city or "—",
                    city=city,
                    state=state,
                    country=country,
                    is_active=True,
                )
                session.add(addr)

            # Communication Preferences
            prefs = CommunicationPreferences(
                constituent_id=constituent.id,
                email_opt_in=True,
                whatsapp_opt_in=False,
                sms_opt_in=False,
                global_dnc=False,
            )
            session.add(prefs)

        await session.commit()
        print(f"Seeded {SAMPLE_SIZE} alumni records.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())