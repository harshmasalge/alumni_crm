# IITGN Alumni & Donor CRM — Final Open-Source System Design

## 1. Design principles

This design is based on the IITGN RFP, but with one additional hard constraint from you:

> **All software used in the core system must be free/open-source.**

This does **not** mean pretending that production infrastructure is free. Servers, domain, managed databases, institutional SSO configuration, WhatsApp Business API, SMS, payment gateways, backups, monitoring, etc. may have real infrastructure/provider costs.

The architecture therefore separates:

1. **Free/open-source application software** — what we develop/use.
2. **Paid/externally dependent infrastructure and services** — integrated later when IITGN provides them.

The RFP itself expects cloud deployment, 99.9% uptime, backups, DR, Indian data residency, 50 concurrent users and scalability to 200,000 records. Those are production-infrastructure requirements and cannot honestly be promised at ₹0.  

---

# 2. Final architecture

```text
                         ┌─────────────────────────┐
                         │      IITGN USERS         │
                         └────────────┬────────────┘
                                      │
                         IITGN Google Workspace
                              Authentication
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      Access Gateway     │
                         │                         │
                         │ HTTPS / Rate Limit      │
                         │ IITGN Network Allowlist │
                         │ Authentication          │
                         └────────────┬────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │                                 │
                     ▼                                 ▼
          ┌────────────────────┐             ┌────────────────────┐
          │ Internal CRM       │             │ Alumni Portal      │
          │ React + TypeScript │             │ React + TypeScript │
          └──────────┬─────────┘             └──────────┬─────────┘
                     │                                  │
                     └────────────────┬─────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       FastAPI           │
                         │   Modular Monolith      │
                         │                         │
                         │ Auth / RBAC              │
                         │ Constituents             │
                         │ Alumni                    │
                         │ Academics                 │
                         │ Career                    │
                         │ Donations                 │
                         │ Engagement                │
                         │ Communication             │
                         │ Search                    │
                         │ Reports                   │
                         │ Imports                   │
                         │ Portal                    │
                         │ Audit                     │
                         └────────────┬────────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │ PostgreSQL      │      │ Redis            │      │ Object Storage  │
    │                 │      │                  │      │                 │
    │ System of Truth │      │ Cache            │      │ Photos          │
    │ CRM data        │      │ Job queue        │      │ PDFs            │
    │ Transactions    │      │ Rate limiting    │      │ Documents       │
    │ Audit metadata  │      │ Temporary state  │      │ Attachments     │
    └─────────────────┘      └─────────────────┘      └─────────────────┘
             │
             ▼
    ┌─────────────────────┐
    │ Reporting Layer     │
    │ SQL Views /         │
    │ Materialized Views  │
    └──────────┬──────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
   CRM Dashboards    Power BI
   / Metabase        Integration
```

### Core stack

| Layer             | Technology                                      | Why                  |
| ----------------- | ----------------------------------------------- | -------------------- |
| CRM frontend      | React + TypeScript + Vite                       | Free, mature         |
| Alumni portal     | React + TypeScript                              | Same codebase/domain |
| UI                | Tailwind CSS                                    | Free                 |
| Backend           | FastAPI                                         | Free/open-source     |
| ORM               | SQLAlchemy                                      | Free/open-source     |
| Validation        | Pydantic                                        | Free/open-source     |
| Database          | PostgreSQL                                      | Free/open-source     |
| Migrations        | Alembic                                         | Free/open-source     |
| Cache/queue       | Redis                                           | Free/open-source     |
| Background jobs   | ARQ/Celery                                      | Free/open-source     |
| File storage      | S3-compatible storage / MinIO where self-hosted | Free software        |
| Reverse proxy     | Nginx                                           | Free/open-source     |
| Containers        | Docker                                          | Free                 |
| Local AI          | Ollama + suitable local model                   | Free software        |
| Charts            | Recharts                                        | Free                 |
| Reporting         | Metabase or custom React dashboards             | Free/open-source     |
| API documentation | FastAPI/OpenAPI                                 | Free                 |
| PDF generation    | ReportLab                                       | Free/open-source     |

---

# 3. Important: "IITGN SSO Wi-Fi" has two separate security controls

Your requirement:

> **The system should only work on IITGN SSO Wi-Fi.**

should **not** be implemented merely by checking whether someone has an `@iitgn.ac.in` email.

These are two different controls.

## Layer 1 — Network restriction

```text
Internet
   │
   ├──────X──────> CRM
   │
IITGN network
   │
   ▼
 CRM
```

At the production gateway/firewall/reverse proxy:

```text
Allowed:
IITGN approved network/IP ranges

Blocked:
Everything else
```

The exact IP ranges must come from IITGN IT/network administrators.

### Important consequence

If IITGN's Wi-Fi uses dynamic/NATed IPs, the network architecture must be confirmed with IITGN IT.

Do **not** hard-code guessed IP ranges.

---

# 4. Layer 2 — IITGN Google authentication

The application uses:

```text
Google OAuth 2.0
      │
      ▼
IITGN Google Workspace
      │
      ▼
@iitgn.ac.in
```

We should enforce:

```text
email_verified = true
domain = iitgn.ac.in
```

and maintain an application-level user/role table.

This is separate from the RFP's alumni portal requirement, which specifies IITGN email / Google OAuth / LinkedIn OAuth. 

For the **internal CRM**, I would initially allow only IITGN Google Workspace accounts.

---

# 5. Master Admin

Your proposed idea works, but I would implement it carefully.

## One Master Admin

There is one specially designated:

```text
MASTER_ADMIN
```

whose email is configured outside the normal UI:

```text
MASTER_ADMIN_EMAIL=someone@iitgn.ac.in
```

Only that exact verified IITGN account can become Master Admin.

### Master Admin can:

```text
Users
 ├── Add user
 ├── Disable user
 ├── Reactivate user
 ├── Assign role
 ├── Remove role
 └── View access history
```

and:

```text
Roles
 ├── CRM Manager
 ├── Database Manager
 ├── Donation Manager
 ├── Event Manager
 └── Report Viewer
```

---

# 6. Don't make access control just "section access"

We need **RBAC + module permissions + field permissions**.

Example:

```text
                     MASTER ADMIN
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
       CRM Manager   Database Manager  Finance
             │             │             │
       All CRM        Alumni data      Donations
       Reports        Academics        Finance reports
       Automation     Career
                      Imports
```

Then at the field level:

```text
Donation Manager:

Name                    ✓
Roll No                 ✓
Donation amount         ✓
Donation date           ✓
Receipt                 ✓

Personal email          ✓
Phone                   ✓

PAN                     masked / restricted
Aadhaar                 ✗
Detailed academic data  ✗
SSAC                    ✗
Family details          ✗
```

This directly reflects the RFP's role definitions and field-level security requirements. 

---

# 7. Recommended permission model

Instead of hard-coding:

```python
if user.role == "admin":
```

use:

```text
User
  ↓
Role
  ↓
Permissions
  ↓
Resource
  ↓
Action
```

Example:

```text
DONATION_VIEW
DONATION_CREATE
DONATION_EDIT
DONATION_DELETE
DONATION_EXPORT

ALUMNI_VIEW
ALUMNI_CREATE
ALUMNI_EDIT
ALUMNI_DELETE

ACADEMIC_VIEW
ACADEMIC_EDIT

AUDIT_VIEW
USER_MANAGE
ROLE_MANAGE
```

Then a role is simply a collection of permissions.

This means Master Admin can create future roles without us rewriting application logic.

---

# 8. Role matrix

| Module          | Master Admin | CRM Manager | Database Manager | Donation Manager | Event Manager | Report Viewer |
| --------------- | -----------: | ----------: | ---------------: | ---------------: | ------------: | ------------: |
| Dashboard       |         Full |        Full |             View |             View |          View |          View |
| Alumni          |         Full |        Full |             Full |          Limited |          Read |     Aggregate |
| Academics       |         Full |        Full |             Full |               No |            No |     Aggregate |
| Career          |         Full |        Full |             Full |          Limited |          Read |     Aggregate |
| Donations       |         Full |        Full |             Read |             Full |            No |       Reports |
| Pledges         |         Full |        Full |             Read |             Full |            No |       Reports |
| Events          |         Full |        Full |             Read |               No |          Full |       Reports |
| Engagement      |         Full |        Full |             Full |               No |          Full |       Reports |
| Communications  |         Full |        Full |          Limited |          Limited |       Limited |            No |
| Imports         |         Full |     Approve |             Full |               No |            No |            No |
| Duplicate/Merge |         Full |     Approve |             Full |               No |            No |            No |
| Reports         |         Full |        Full |             Full |          Finance |        Events |          View |
| Audit           |         Full |        View |          Limited |          Limited |       Limited |            No |
| User management |         Full |          No |               No |               No |            No |            No |
| System settings |         Full |     Limited |               No |               No |            No |            No |

The RFP's baseline roles and responsibilities are the basis for this matrix. 

---

# 9. Security architecture

Security should be **P0**, not something we add later.

```text
Request
   │
   ▼
IITGN Network Check
   │
   ▼
HTTPS
   │
   ▼
Google OAuth
   │
   ▼
Verify IITGN domain
   │
   ▼
Create/lookup internal user
   │
   ▼
RBAC
   │
   ▼
Module permission
   │
   ▼
Field permission
   │
   ▼
Data query
   │
   ▼
Audit
```

## Mandatory controls

### Authentication

* Google OAuth
* IITGN domain restriction
* verified email
* session expiration
* secure cookies/token handling

### Authorization

* RBAC
* module permissions
* field-level restrictions
* object ownership for alumni portal
* server-side enforcement

### Network

* IITGN network/IP allowlist
* HTTPS only
* reverse proxy/firewall

### Audit

Every modification:

```text
who
what
when
from where
old value
new value
```

The RFP requires timestamp, user ID and IP address for modifications. 

### Sensitive data

```text
PAN
Aadhaar
SSAC
Family data
Detailed academic records
```

should receive explicit sensitivity classifications.

PAN should be encrypted/masked.

Aadhaar should **not automatically be collected merely because the RFP lists it**; the institution should define its lawful purpose, access and retention policy first.

---

# 10. Data model

## Central identity

I would **not use Roll No as the database foreign key**, despite the RFP wording.

Use:

```text
person_id UUID PRIMARY KEY
```

and retain:

```text
roll_no UNIQUE
donor_id UNIQUE
```

as business identifiers.

### Core model

```text
                    CONSTITUENT
                         │
               ┌─────────┴──────────┐
               │                    │
             PERSON            ORGANISATION
               │                    │
        ┌──────┼──────┐             │
        ▼      ▼      ▼             ▼
     ALUMNI   DONOR  OTHER         DONOR
```

This allows:

```text
Person
 ├── Alumni
 └── Donor
```

simultaneously.

And:

```text
Organisation
 └── Donor
```

for CSR/private organisational donations.

---

# 11. Core database domains

```text
identity
├── constituents
├── persons
├── organisations
├── alumni_profiles
├── donor_profiles
├── contact_methods
├── addresses
├── communication_preferences
└── family_relationships

academics
├── qualifications
├── programmes
├── disciplines
├── courses
├── UG_performance
├── PG_performance
├── PhD_performance
├── hostel_history
├── GPS_assignments
├── awards
├── scholarships
├── internships
├── placements
├── SSAC_records
├── POR
├── publications
└── overseas_exposure

career
├── organisations
├── current_affiliations
├── affiliation_history
└── startups

advancement
├── donations
├── payment_transactions
├── donation_adjustments
├── pledges
├── campaigns
├── funds
├── fund_allocations
├── receipts
└── donor_tiers

engagement
├── events
├── event_registrations
├── attendance
├── chapters
├── chapter_members
├── mentorship_programmes
├── mentor_profiles
├── mentorship_matches
├── mentorship_sessions
└── campus_visits

communication
├── templates
├── campaigns
├── campaign_recipients
├── communication_logs
├── DNC
└── delivery_events

governance
├── users
├── roles
├── permissions
├── audit_logs
├── approval_requests
├── workflow_tasks
├── data_quality_issues
├── merge_history
└── consent_records

files
├── documents
├── photos
└── attachments

reporting
├── reporting_views
└── reporting_snapshots
```

The RFP requires the core profile plus T2–T25 related entities, including academic history, donations, hostel, courses, performance, scholarships, internships, placements, startups, SSAC, POR, affiliations, publications, engagements, overseas exposure, communication logs and family details.  

---

# 12. RFP entities we must eventually cover

The implementation will eventually cover all of these:

| RFP | Entity                      | Priority                  |
| --- | --------------------------- | ------------------------- |
| T1  | Core Alumni/Donor Profile   | **P0**                    |
| T2  | Educational Qualifications  | **P1**                    |
| T3  | Donations                   | **P1**                    |
| T4  | Hostel History              | P2                        |
| T5  | UG Course Details           | P2                        |
| T6  | UG Performance              | P2                        |
| T7  | GPS Assignments             | P3                        |
| T8  | PG Course Details           | P2                        |
| T9  | PG Performance              | P2                        |
| T10 | PhD Course Details          | P2                        |
| T11 | PhD Performance             | P2                        |
| T12 | Awards/Medals/Recognition   | P2                        |
| T13 | Scholarships/Financial Aid  | P1                        |
| T14 | Internships                 | P2                        |
| T15 | Placements                  | P2                        |
| T16 | Startup/Entrepreneurship    | P3                        |
| T17 | SSAC Records                | **P1 security-sensitive** |
| T18 | Positions of Responsibility | P2                        |
| T19 | Current Affiliation         | **P1**                    |
| T20 | Previous Affiliations       | **P1**                    |
| T21 | Publications                | P2                        |
| T22 | Meetups & Engagements       | **P1**                    |
| T23 | Overseas Exposure           | P2                        |
| T24 | Communication Logs          | **P1**                    |
| T25 | Family Details              | P2/security-sensitive     |

The source explicitly marks many core fields as Mandatory, High, Optional or System-calculated, so our implementation priority should respect that rather than treating all 35+ entities equally.  

---

# 13. Priority framework

I recommend **five implementation priorities**.

### P0 — Foundation / Security

Must exist before meaningful CRM usage.

### P1 — Core operational CRM

The things that immediately replace Excel/manual work.

### P2 — Important expansion

Required by the RFP but dependent on the P0/P1 foundation.

### P3 — Advanced/complex features

Still required eventually, but shouldn't block the core system.

### P4 — Nice-to-have

Explicitly low/nice-to-have requirements.

This is **our implementation priority**, not a replacement for the RFP's own Mandatory/High/Medium/Low labels.

---

# 14. P0 — Foundation

## Authentication & access

* Google OAuth
* IITGN email/domain verification
* IITGN network restriction
* Master Admin
* user management
* roles
* permissions
* module access
* field-level permissions
* session timeout
* secure session management

## Security

* HTTPS
* secure headers
* CSRF protection where applicable
* rate limiting
* audit logs
* sensitive-field masking
* encryption strategy
* access logging
* server-side authorization
* input validation
* SQL injection protection through ORM/parameterization

## Core infrastructure

* PostgreSQL
* Redis
* object storage
* FastAPI
* React
* Docker
* Nginx
* database migrations
* configuration management
* health checks
* structured logging

## Core identity

* constituent
* person
* organisation
* alumni profile
* donor profile
* contacts
* addresses

---

# 15. P1 — Core CRM

This is the first genuinely useful release.

## Alumni/Donor

Implement:

* ALM-001 CRUD
* ALM-002 duplicate detection
* ALM-003 profile completeness
* ALM-005 audit
* ALM-006 bulk import
* ALM-009 deceased tracking
* ALM-010 opt-out
* ALM-011 360° profile
* ALM-012 quick search

These are all Mandatory in the RFP. 

Also:

* current affiliation
* previous affiliation
* contact management
* profile photo
* basic academic information
* donor profile
* scholarships
* communication logs

## Search

Implement:

* full-text search
* filters
* name
* roll number
* email
* programme
* YOG
* discipline
* gender
* country
* sector
* profile score
* membership

The RFP explicitly requires these search/filter capabilities. 

---

# 16. P1 — Data migration

This should start **very early**, not at the end.

The RFP expects migration of approximately 6,100 existing records from Excel/Google Sheets, cleansing, duplicate detection, historical donations from 2008 onward, validation and rollback. 

Architecture:

```text
Excel / CSV
      ↓
Upload
      ↓
Staging
      ↓
Column mapping
      ↓
Validation
      ↓
Duplicate detection
      ↓
Review
      ↓
Import
      ↓
Reconciliation
```

We should be able to show:

```text
Import Batch #001

Total rows: 6100
Valid: 5800
Duplicates: 250
Errors: 50
```

---

# 17. P1 — Donations

Crucially, **donation management does not require a paid payment gateway to build.**

So we should build it early.

Implement:

* DON-001 multiple donations
* DON-002 financial year
* DON-003 80G generation
* DON-004 FCRA tracking
* DON-008 purpose tagging
* donation statements
* donor tiers
* receipt history
* acknowledgement workflow

These requirements are explicitly listed in the RFP. 

### Payment integration is separate

Build:

```text
PaymentProvider interface
        │
        ├── MockPaymentProvider
        └── RazorpayProvider (later)
```

So the system is complete architecturally without pretending Razorpay/CCAvenue is free.

---

# 18. P1 — Basic reporting

Build the reports using PostgreSQL + React.

No Power BI dependency initially.

Required executive metrics include:

* alumni/donor count
* donations
* unique donors
* engagements
* profile completeness
* top donors
* upcoming events
* geographic distribution. 

And standard reports:

* year/programme/discipline alumni counts
* programme listings
* incomplete profiles
* geographic distribution
* current affiliations
* sector distribution
* FY donation summary
* programme-wise donations
* discipline-wise donations
* donor statements



---

# 19. P1 — Alumni portal foundation

Build the portal after the core CRM exists.

### Mandatory portal features

* Google/IITGN authentication
* own profile
* profile update
* address
* phone
* email
* affiliation
* LinkedIn
* photo
* communication preferences

These are explicitly mandatory/high priority in the RFP. 

### Important security rule

The portal uses:

```text
/api/me/...
```

rather than allowing the browser to specify arbitrary person IDs.

Example:

```http
PATCH /api/me/profile
```

The server obtains the person ID from the authenticated user.

---

# 20. P2 — Advanced CRM

After P1 works:

### Academics

* UG courses
* PG courses
* PhD courses
* semester performance
* hostel
* GPS
* awards
* internships
* placements
* POR
* publications
* overseas exposure

### Career

* detailed affiliation history
* startups
* leadership roles
* career analytics

### Data quality

* fuzzy duplicate detection
* merge UI
* merge history
* bulk update
* advanced validation

### Search

* saved searches
* segments
* geographic map
* export CSV/XLSX/PDF

The RFP explicitly lists saved segments, geographic maps, LinkedIn lookup and filtered exports. 

---

# 21. P2 — Engagement

Build:

```text
Events
 ├── Event types
 ├── Registration
 ├── RSVP
 ├── Attendance
 ├── Accompanying persons
 └── Invitations

Chapters
 ├── City
 ├── Country
 ├── Lead
 └── Members

Mentorship
 ├── Mentor
 ├── Student
 ├── Match
 └── Sessions

Campus Visits
```

The RFP requires event/engagement tracking, attendance, invitations, RSVP, chapters, mentorship and campus visits, with varying priorities. 

---

# 22. P2 — Communication architecture

First build the **communication engine** without expensive providers.

```text
Communication Service
       │
       ├── EmailProvider
       ├── WhatsAppProvider
       └── SMSProvider
```

Development:

```text
EmailProvider      → local/mock
WhatsAppProvider   → mock
SMSProvider        → mock
```

Production:

```text
EmailProvider      → IITGN SMTP/Exchange
WhatsAppProvider   → WhatsApp Business API
SMSProvider        → IITGN-approved SMS gateway
```

This is exactly why provider abstraction matters.

---

# 23. P2 — Free automation

These can be developed without paid services:

### Birthday automation

```text
Daily 8 AM
    ↓
Find today's birthdays
    ↓
Check DNC/deceased/preferences
    ↓
Create communication job
```

The RFP specifically requires the daily birthday workflow. 

### Work anniversary

```text
Current affiliation joining date
        ↓
Anniversary
        ↓
ARO notification
```

### Weekly digest

Generate:

* emails
* calls
* WhatsApp records
* new engagements

### Monthly summary

Generate:

* new alumni
* donations
* engagements
* affiliation changes

### Affiliation workflow

```text
Current affiliation changed
        ↓
Close old affiliation
        ↓
Create historical record
        ↓
Audit
        ↓
Notify ARO
```

### Lost contact

```text
No meaningful interaction > 12 months
        ↓
Flag
        ↓
Create task
```

All of these are explicitly required/high-priority automations. 

---

# 24. P2 — AI search

This remains mandatory according to the RFP, but it should come **after structured search**.

Architecture:

```text
User
 │
 ▼
Natural language query
 │
 ▼
Local LLM
 │
 ▼
Structured JSON
 │
 ▼
Schema validation
 │
 ▼
Permission enforcement
 │
 ▼
PostgreSQL query
 │
 ▼
Results
```

Example:

```text
"BTech 2020 alumni in IT sector in USA"
```

becomes:

```json
{
  "programme": "BTech",
  "graduation_year": 2020,
  "sector": "IT",
  "country": "USA"
}
```

The RFP requires natural-language search, but it does **not** require a particular LLM/provider. 

Therefore we can develop this using a local model without creating an API-cost dependency.

---

# 25. P3 — Advanced integrations

These require IITGN/external systems and therefore should come later.

### Email

```text
IITGN Exchange/SMTP
```

The RFP explicitly requires Exchange/Office 365 integration. 

### WhatsApp

```text
WhatsApp Business API
```

Requires an actual provider/account.

### SMS

Requires SMS gateway.

### Payment

```text
Razorpay / CCAvenue
```

Requires gateway account and applicable transaction/provider charges.

### Donation Portal

```text
Donation Portal
      ↓
Webhook/API
      ↓
CRM
```

### ERP

```text
CRM
 ↕
IITGN ERP
```

Exact API/data ownership must be determined with IITGN.

### LinkedIn

Implement initially as:

```text
LinkedIn URL
      ↓
Open profile
      ↓
Staff verifies
      ↓
Update CRM
```

Do not build around scraping.

The RFP requests LinkedIn API integration, so actual API feasibility must be validated before committing to automatic updates. 

---

# 26. P3 — Advanced portal

After basic portal:

### Directory

```text
Search alumni
      ↓
Only public fields
```

### Mentorship

```text
Mentor signup
Expertise
Availability
Matching
```

### Campus visit

```text
Request
 ↓
ARO notification
 ↓
Approval
```

### Calendar integration

Generate `.ics` invitations.

The RFP marks directory and mentorship as High/Medium priority and job board/startup showcase as Low. 

---

# 27. P4 — Explicitly low priority

These should **not delay the core CRM**.

### Job board

RFP:

> Low / nice-to-have. 

### Startup showcase

RFP:

> Low / nice-to-have. 

### Predictive analytics

Such as:

```text
Donor propensity
Engagement churn
```

The RFP explicitly calls predictive analytics nice-to-have. 

---

# 28. Full implementation priority

Here's the order I would actually follow:

```text
P0
│
├── Google/IITGN authentication
├── IITGN network restriction
├── Master Admin
├── RBAC
├── Permissions
├── Audit
├── Security foundation
├── PostgreSQL
├── Redis
├── File storage
└── Core application architecture

        ↓

P1
│
├── Constituent / Person
├── Alumni
├── Donor
├── Contacts
├── Addresses
├── 360° profile
├── Current/Previous affiliation
├── Basic academic information
├── Donations
├── 80G
├── FCRA tracking
├── Scholarships
├── Communication logs
├── DNC
├── Profile completeness
├── Duplicate detection
├── Import
├── Basic search
├── Basic reports
└── Portal authentication/profile

        ↓

P2
│
├── Full academic entities
├── Career history
├── Advanced duplicate merge
├── Saved searches
├── Geographic search
├── Export
├── Events
├── RSVP
├── Attendance
├── Chapters
├── Mentorship
├── Campus visits
├── Communication engine
├── Email automation
├── Birthday automation
├── Anniversary automation
├── Lost-contact workflow
└── Local AI search

        ↓

P3
│
├── Payment gateway
├── WhatsApp
├── SMS
├── IITGN donation portal
├── ERP
├── LinkedIn API
├── Power BI
├── Advanced portal directory
└── Advanced analytics

        ↓

P4
│
├── Job board
├── Startup showcase
└── Predictive analytics
```

---

# 29. What is free-first?

This is important because we don't want to postpone things merely because the final deployment requires paid infrastructure.

| Feature                  | Can develop now without paid provider?      |
| ------------------------ | ------------------------------------------- |
| CRM                      | **Yes**                                     |
| Database                 | **Yes**                                     |
| Authentication logic     | **Yes**                                     |
| Google OAuth development | **Yes**                                     |
| RBAC                     | **Yes**                                     |
| Audit                    | **Yes**                                     |
| Alumni profiles          | **Yes**                                     |
| Donor profiles           | **Yes**                                     |
| Academics                | **Yes**                                     |
| Career                   | **Yes**                                     |
| Donations/manual entry   | **Yes**                                     |
| FY calculation           | **Yes**                                     |
| 80G PDF generation       | **Yes**                                     |
| FCRA tracking            | **Yes**                                     |
| Pledges                  | **Yes**                                     |
| Events                   | **Yes**                                     |
| RSVP                     | **Yes**                                     |
| Attendance               | **Yes**                                     |
| Chapters                 | **Yes**                                     |
| Mentorship               | **Yes**                                     |
| Portal                   | **Yes**                                     |
| DNC                      | **Yes**                                     |
| Email templates          | **Yes**                                     |
| Automation engine        | **Yes**                                     |
| AI search                | **Yes — local model**                       |
| Dashboards               | **Yes**                                     |
| Reports                  | **Yes**                                     |
| Excel import/export      | **Yes**                                     |
| Duplicate detection      | **Yes**                                     |
| File storage             | **Yes, with self-hosted object storage**    |
| WhatsApp actual sending  | **No — external service**                   |
| SMS actual sending       | **No — external service**                   |
| Payment processing       | **No — gateway**                            |
| Production cloud         | **No — infrastructure cost**                |
| 99.9% SLA                | **No — requires production infrastructure** |
| Geo-redundant DR         | **No — infrastructure cost**                |
| Annual VAPT              | **No — professional/security service cost** |

This is the honest interpretation of "free."

---

# 30. RFP priority vs our implementation priority

One subtle but important point:

The RFP already gives requirements labels such as:

```text
Mandatory
High
Medium
Low
Optional
System-calculated
```

We should **not change those labels**.

Instead, maintain two priorities:

```text
RFP Priority
+
Implementation Priority
```

Example:

| Requirement          | RFP priority | Our implementation |
| -------------------- | ------------ | ------------------ |
| CRUD                 | Mandatory    | P1                 |
| Duplicate detection  | Mandatory    | P1                 |
| Audit                | Mandatory    | **P0**             |
| Search               | Mandatory    | P1                 |
| AI Search            | Mandatory    | P2                 |
| Donations            | Mandatory    | P1                 |
| 80G                  | Mandatory    | P1                 |
| FCRA                 | Mandatory    | P1                 |
| WhatsApp             | High         | P3                 |
| SMS                  | Medium       | P3                 |
| Events               | Mandatory    | P2                 |
| RSVP                 | High         | P2                 |
| Chapters             | High         | P2                 |
| Mentorship           | Medium       | P2                 |
| Job board            | Low          | P4                 |
| Startup showcase     | Low          | P4                 |
| Predictive analytics | Nice-to-have | P4                 |

That is much more realistic than saying "all Mandatory requirements must be built first."

---

# 31. Production architecture later

When IITGN is ready for production, the application doesn't fundamentally change.

```text
                        INTERNET
                            │
                            X
                      not allowed
                            │
                   IITGN Network
                            │
                            ▼
                    Firewall / WAF
                            │
                            ▼
                    Nginx / Gateway
                            │
                            ▼
                     FastAPI App
                    ┌───────┴───────┐
                    ▼               ▼
               PostgreSQL         Redis
                    │
                    ▼
              Object Storage
```

Then production infrastructure can satisfy the RFP's requirements:

```text
India data centre
Backups
DR
Monitoring
TLS
Encryption
Scaling
99.9% SLA
```

The RFP specifically requires primary data residency in India, geo-redundant backups, RPO ≤4 hours, RTO ≤8 hours and 99.9% uptime. 

---

# 32. Performance targets

We should design toward the RFP from day one.

| Requirement       |                 Target |
| ----------------- | ---------------------: |
| Page load         |                 <3 sec |
| Search            |                 <1 sec |
| Dashboard refresh |                 <5 sec |
| Standard report   |                <30 sec |
| Complex report    |                 <2 min |
| Bulk import       | 10,000 records <10 min |
| Concurrent users  |                     50 |
| Data scale        |        200,000 records |

These are explicitly specified in the RFP. 

At 200k records, PostgreSQL is still perfectly reasonable with proper indexes and query design. We don't need Elasticsearch/microservices/Kubernetes on day one.

---

# 33. API architecture

```text
/api/v1
│
├── /auth
├── /users
├── /roles
├── /permissions
│
├── /constituents
├── /persons
├── /alumni
├── /donors
│
├── /academics
├── /qualifications
├── /courses
├── /performance
├── /affiliations
├── /publications
│
├── /donations
├── /pledges
├── /campaigns
├── /funds
├── /receipts
│
├── /events
├── /registrations
├── /attendance
├── /chapters
├── /mentorship
│
├── /communications
├── /templates
├── /campaigns
├── /preferences
│
├── /search
├── /search/ai
│
├── /imports
├── /exports
├── /reports
│
├── /portal
├── /me
│
├── /files
├── /audit
└── /integrations
```

FastAPI automatically provides OpenAPI documentation, satisfying the RFP's requirement for REST/OpenAPI support for core entities. 

---

# 34. Background job architecture

Anything slow should leave the HTTP request.

```text
FastAPI
   │
   ├── Create job
   │
   ▼
Redis Queue
   │
   ▼
Worker
   │
   ├── Generate 80G PDF
   ├── Import 10k records
   ├── Send campaign
   ├── Generate report
   ├── Birthday automation
   ├── Monthly summary
   └── Duplicate analysis
```

This is important for meeting the RFP's performance targets.

---

# 35. Data workflow for sensitive changes

We should distinguish:

### Normal profile change

```text
Phone number
   ↓
Alumni updates
   ↓
Validation
   ↓
Save
   ↓
Audit
```

### Sensitive change

```text
PAN / academic / SSAC / other restricted field
             ↓
          Request
             ↓
       Approval workflow
             ↓
          Approved?
          /      \
        Yes       No
         │         │
       Save      Reject
         │
       Audit
```

This also addresses the RFP's requirement that CRM managers approve data changes. 

---

# 36. Donation workflow

```text
Manual / Portal / Payment Gateway
              │
              ▼
       Payment Transaction
              │
        validation/idempotency
              │
              ▼
          Donation
              │
       ┌──────┼─────────┐
       ▼      ▼         ▼
      FY    Purpose    FCRA
       │
       ▼
    Fund Allocation
       │
       ▼
    Receipt
       │
       ▼
     80G PDF
       │
       ▼
 Acknowledgement
```

Posted donations should not simply be edited destructively.

For example:

```text
Donation
₹100,000
```

followed by:

```text
Refund / reversal
₹100,000
```

rather than changing the original donation to ₹0.

This preserves financial auditability.

---

# 37. Portal architecture

```text
                  IITGN Google
                      │
                      ▼
                Google OAuth
                      │
                      ▼
               Alumni Portal
                      │
                      ▼
                  FastAPI
                      │
                      ▼
                  /api/me
                      │
                      ▼
                 PostgreSQL
```

The portal **does not get unrestricted CRM APIs**.

It gets a restricted API surface:

```text
GET  /me/profile
PATCH /me/profile

GET /me/events
POST /me/events/{id}/rsvp

GET /me/donations
POST /me/donation

GET /directory
PATCH /me/preferences

POST /me/mentorship
```

This dramatically reduces attack surface.

---

# 38. Audit architecture

```text
audit_logs

id
timestamp
user_id
ip_address
entity_type
entity_id
action
field_name
old_value
new_value
request_id
```

For example:

```text
2026-09-17 14:32

User:
database.manager@iitgn.ac.in

Entity:
Alumni 2020CS001

Field:
current_country

Old:
India

New:
USA

IP:
10.x.x.x
```

The RFP explicitly requires complete field-change audit history. 

---

# 39. Data-quality architecture

```text
                 Record
                    │
            ┌───────┴────────┐
            ▼                ▼
       Exact matching    Fuzzy matching
            │                │
      roll/email/id       name/contact/
                          YOG/company
            │                │
            └───────┬────────┘
                    ▼
             Duplicate score
                    │
          ┌─────────┼──────────┐
          ▼         ▼          ▼
        Clean    Possible    Duplicate
                    │
                    ▼
               Review queue
                    │
              ┌─────┴─────┐
              ▼           ▼
            Merge       Keep separate
```

Merge must preserve:

```text
donations
events
academic records
communications
documents
```

rather than deleting the losing person's history.

---

# 40. What we should build first

Not the entire CRM.

Our first development milestone should be:

## **Release 0 — Secure CRM foundation**

```text
Google Login
      +
IITGN network restriction
      +
Master Admin
      +
RBAC
      +
PostgreSQL
      +
FastAPI
      +
React
      +
Audit
      +
Person/Constituent
```

Then:

## **Release 1 — Core Alumni/Donor CRM**

```text
Alumni
Donor
Contacts
Academics basic
Career
Donations
80G
FCRA
360° profile
Search
Import
Duplicate detection
Reports
```

Then:

## **Release 2 — Engagement & Portal**

```text
Events
RSVP
Attendance
Chapters
Mentorship
Portal
Preferences
Automations
```

Then:

## **Release 3 — Communications & AI**

```text
Email
WhatsApp adapter
SMS adapter
Campaigns
AI search
Advanced reports
```

Then:

## **Release 4 — External integrations**

```text
Payment gateway
Donation portal
ERP
LinkedIn
Power BI
```

Then:

## **Release 5 — Nice-to-have**

```text
Job board
Startup showcase
Predictive analytics
```

---

# 41. Final technology decision

I would **lock this stack** unless we encounter a concrete requirement that forces a change:

```text
FRONTEND
React
TypeScript
Vite
Tailwind
TanStack Query
React Hook Form
Zod
Recharts

BACKEND
Python
FastAPI
SQLAlchemy
Pydantic
Alembic

DATABASE
PostgreSQL

ASYNC
Redis
ARQ / Celery

FILES
S3-compatible object storage
MinIO for self-hosted development

AUTH
Google OAuth 2.0
IITGN Workspace restriction

SECURITY
Nginx
HTTPS
RBAC
Field-level permissions
Audit logging
Rate limiting
CSRF/session protection

AI
Ollama
Local LLM
Structured-filter architecture

REPORTING
PostgreSQL reporting layer
React dashboards
Metabase
Power BI adapter later

DEPLOYMENT
Docker
Linux
Azure/AWS/GCP later
```

---

# 42. One correction to the RFP we should explicitly account for

The RFP says:

> all entities should be linked to the central Alumni profile via Roll Number. 

I would **not literally implement the database that way**.

Use:

```text
person_id UUID
```

as the immutable internal relational key.

Then:

```text
roll_no UNIQUE
donor_id UNIQUE
```

are business identifiers.

That gives us:

```text
person_id
   │
   ├── roll_no
   ├── donor_id
   ├── academic records
   ├── donations
   ├── events
   └── communications
```

If a business identifier ever changes/corrects, the relational integrity remains intact.

---

# 43. Final picture

The system we're actually going to build is therefore:

```text
                         ┌──────────────────────┐
                         │     IITGN Google     │
                         │     Workspace        │
                         └──────────┬───────────┘
                                    │
                              Google OAuth
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  IITGN Network       │
                         │  Restriction         │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Nginx / Gateway   │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  │                                    │
                  ▼                                    ▼
        ┌──────────────────┐                 ┌──────────────────┐
        │ Internal CRM     │                 │ Alumni Portal    │
        │ React            │                 │ React            │
        └────────┬─────────┘                 └────────┬─────────┘
                 │                                    │
                 └────────────────┬───────────────────┘
                                  ▼
                         ┌──────────────────┐
                         │     FastAPI      │
                         │ Modular Monolith │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        ┌───────────┐       ┌───────────┐       ┌───────────┐
        │ PostgreSQL│       │   Redis   │       │   Object  │
        │           │       │           │       │  Storage  │
        │   DATA    │       │ Jobs/cache│       │ PDFs/photos│
        └─────┬─────┘       └───────────┘       └───────────┘
              │
              ▼
       ┌──────────────┐
       │  Reporting   │
       │    Layer     │
       └──────┬───────┘
              │
        ┌─────┴──────┐
        ▼            ▼
     Metabase      Power BI
      /CRM         later
    Dashboard
```

with the business domains:

```text
             ┌─────────────────────────────┐
             │        CONSTITUENT          │
             └──────────────┬──────────────┘
                            │
       ┌────────────┬───────┼────────┬─────────────┐
       ▼            ▼       ▼        ▼             ▼
    Alumni        Donor  Academic   Career     Engagement
       │            │       │        │             │
       └────────────┴───────┴────────┴─────────────┘
                            │
                     Communication
                            │
                         Portal
                            │
                         Reports
```

## The guiding rule for the project

**We build the whole architecture, but implement it incrementally.**

We don't compromise the final architecture just because a feature isn't being implemented yet.

And we don't let a feature requiring a paid external service block development of everything around it.

For example:

```text
WhatsApp
   ↓
Provider interface now
   ↓
Mock provider now
   ↓
Real WhatsApp provider later
```

and:

```text
Payment Gateway
   ↓
Payment abstraction now
   ↓
Mock payment now
   ↓
Razorpay/CCAvenue later
```

and:

```text
Power BI
   ↓
Reporting schema now
   ↓
CRM dashboards now
   ↓
Power BI connector later
```

That gives us a **real, scalable architecture from day one**, while keeping the development environment entirely based on free/open-source software.

The RFP's own current-state analysis says the fundamental problem is fragmented Excel/Google Sheets, manual communication, manual reporting, lack of access controls, and lack of integrations.  Our **P0 → P1** directly attacks those problems first, rather than spending early development time on low-priority features like a job board or predictive analytics.
