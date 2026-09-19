/**
 * Phase 2 — Full CRM Frontend Visualization: fictional demo data.
 *
 * Every record below is invented for product-preview purposes. No real
 * alumni, donor, financial, or credential data is used. These fixtures back
 * Preview / Under-development screens only and never touch the M1 API layer.
 */

export type DemoStatus = "Live" | "Preview" | "Under development";

export interface DemoDonation {
  id: string;
  donor: string;
  donorId: string;
  amountInr: number;
  date: string;
  fund: string;
  mode: string;
  lifecycle: "Posted" | "Pending reconciliation" | "Adjusted";
  fy: string;
  receiptNo: string;
  eightGStatus: "Issued" | "Pending finance review" | "Not applicable";
}

export interface DemoPledge {
  id: string;
  donor: string;
  fund: string;
  pledgedInr: number;
  receivedInr: number;
  expectedBy: string;
  status: "On track" | "Overdue" | "Partially received" | "New";
}

export interface DemoFund {
  code: string;
  name: string;
  purpose: string;
  corpusInr: number;
  fyReceivedInr: number;
  status: "Active" | "Restricted" | "Closing";
}

export interface DemoCampaign {
  code: string;
  name: string;
  fund: string;
  goalInr: number;
  raisedInr: number;
  donors: number;
  endsOn: string;
  status: "Active" | "Planned" | "Closed";
}

export interface DemoEvent {
  code: string;
  name: string;
  city: string;
  date: string;
  type: "Reunion" | "Chapter meet" | "Fundraiser" | "Webinar" | "Convocation";
  registered: number;
  attended: number;
  capacity: number;
  status: "Upcoming" | "Registrations open" | "Completed" | "Draft";
}

export interface DemoChapter {
  name: string;
  region: string;
  members: number;
  lead: string;
  lastActivity: string;
  health: "Active" | "Needs attention" | "Forming";
}

export interface DemoTask {
  id: string;
  title: string;
  owner: string;
  due: string;
  priority: "High" | "Medium" | "Low";
  queue: "Follow-ups" | "Verification" | "Stewardship" | "Data quality";
  status: "Open" | "In progress" | "Waiting on donor";
}

export interface DemoComm {
  id: string;
  name: string;
  channel: "Email" | "WhatsApp" | "SMS";
  audience: string;
  audienceCount: number;
  scheduledFor: string;
  status: "Draft" | "Scheduled (mock)" | "Sent (mock)" | "Blocked — no consent";
}

export interface DemoTemplate {
  name: string;
  channel: "Email" | "WhatsApp" | "SMS";
  purpose: string;
  lastUsed: string;
}

export interface DemoIntegration {
  provider: string;
  category: "Identity" | "Messaging" | "Payments" | "ERP" | "Analytics" | "Donation portal";
  state: "Sandbox" | "Connected" | "Unavailable" | "Under development";
  note: string;
  lastChecked: string;
}

export interface DemoImportBatch {
  id: string;
  fileName: string;
  rows: number;
  uploadedBy: string;
  uploadedAt: string;
  status: "Validated" | "Needs review" | "Imported (mock)" | "Failed validation";
  issues: number;
  duplicates: number;
}

export interface DemoReport {
  code: string;
  name: string;
  category: "Constituent" | "Donation" | "Engagement" | "Compliance";
  refresh: string;
  rows: string;
  description: string;
}

export interface DemoUser {
  name: string;
  role: string;
  scope: string;
  lastActive: string;
  status: "Active" | "Suspended";
}

export interface DemoAudit {
  time: string;
  actor: string;
  action: string;
  entity: string;
}

export const demoDonations: DemoDonation[] = [
  { id: "DON-2026-0411", donor: "Meera Krishnan (fictional)", donorId: "DNR-00114", amountInr: 500000, date: "2026-08-14", fund: "Student Scholarship Endowment", mode: "NEFT", lifecycle: "Posted", fy: "FY 2026–27", receiptNo: "RCP-2026-0891", eightGStatus: "Issued" },
  { id: "DON-2026-0408", donor: "Arvind Bhatt (fictional)", donorId: "DNR-00307", amountInr: 110000, date: "2026-08-02", fund: "Research Excellence Fund", mode: "Cheque", lifecycle: "Posted", fy: "FY 2026–27", receiptNo: "RCP-2026-0874", eightGStatus: "Issued" },
  { id: "DON-2026-0399", donor: "Northbridge Fabricators Pvt. Ltd. (fictional)", donorId: "DNR-00552", amountInr: 2500000, date: "2026-07-21", fund: "Infrastructure & Labs", mode: "RTGS", lifecycle: "Posted", fy: "FY 2026–27", receiptNo: "RCP-2026-0830", eightGStatus: "Pending finance review" },
  { id: "DON-2026-0395", donor: "Sana Merchant (fictional)", donorId: "DNR-00231", amountInr: 25000, date: "2026-07-11", fund: "Annual Giving — Unrestricted", mode: "UPI (mock ref)", lifecycle: "Pending reconciliation", fy: "FY 2026–27", receiptNo: "—", eightGStatus: "Not applicable" },
  { id: "DON-2026-0388", donor: "Devang Solanki (fictional)", donorId: "DNR-00098", amountInr: 100000, date: "2026-06-28", fund: "Student Scholarship Endowment", mode: "NEFT", lifecycle: "Adjusted", fy: "FY 2026–27", receiptNo: "RCP-2026-0799 (rev. 1)", eightGStatus: "Issued" },
  { id: "DON-2026-0377", donor: "Ira Kulkarni (fictional)", donorId: "DNR-00410", amountInr: 51000, date: "2026-06-09", fund: "Women in STEM Scholarship", mode: "Demand draft", lifecycle: "Posted", fy: "FY 2026–27", receiptNo: "RCP-2026-0762", eightGStatus: "Pending finance review" },
];

export const demoPledges: DemoPledge[] = [
  { id: "PLG-2026-0118", donor: "Farhan Qureshi (fictional)", fund: "Infrastructure & Labs", pledgedInr: 1000000, receivedInr: 400000, expectedBy: "2026-12-31", status: "Partially received" },
  { id: "PLG-2026-0121", donor: "Lata Deshmukh (fictional)", fund: "Student Scholarship Endowment", pledgedInr: 300000, receivedInr: 300000, expectedBy: "2026-07-31", status: "On track" },
  { id: "PLG-2025-0097", donor: "Karan Ahuja (fictional)", fund: "Research Excellence Fund", pledgedInr: 500000, receivedInr: 100000, expectedBy: "2026-03-31", status: "Overdue" },
  { id: "PLG-2026-0130", donor: "Bluepeak Systems (fictional)", fund: "Annual Giving — Unrestricted", pledgedInr: 750000, receivedInr: 0, expectedBy: "2027-01-15", status: "New" },
];

export const demoFunds: DemoFund[] = [
  { code: "SCH-END", name: "Student Scholarship Endowment", purpose: "Need- and merit-based scholarships", corpusInr: 42500000, fyReceivedInr: 6300000, status: "Active" },
  { code: "RES-EXC", name: "Research Excellence Fund", purpose: "Seed grants, equipment, travel", corpusInr: 18800000, fyReceivedInr: 2110000, status: "Active" },
  { code: "INF-LAB", name: "Infrastructure & Labs", purpose: "Capital projects and laboratory upgrades", corpusInr: 96400000, fyReceivedInr: 3900000, status: "Restricted" },
  { code: "WIS-SCH", name: "Women in STEM Scholarship", purpose: "Scholarships for women scholars", corpusInr: 7400000, fyReceivedInr: 861000, status: "Active" },
  { code: "ANN-UNR", name: "Annual Giving — Unrestricted", purpose: "Dean's discretionary priorities", corpusInr: 5200000, fyReceivedInr: 1475000, status: "Active" },
];

export const demoCampaigns: DemoCampaign[] = [
  { code: "REU-2026", name: "Batch of 2016 Decennial Reunion Giving", fund: "Student Scholarship Endowment", goalInr: 5000000, raisedInr: 3275000, donors: 214, endsOn: "2026-12-20", status: "Active" },
  { code: "GIV-DAY", name: "Founders' Day Annual Giving", fund: "Annual Giving — Unrestricted", goalInr: 2000000, raisedInr: 2000000, donors: 486, endsOn: "2026-06-15", status: "Closed" },
  { code: "LAB-100", name: "100 Labs Microsite Drive (planned)", fund: "Infrastructure & Labs", goalInr: 10000000, raisedInr: 0, donors: 0, endsOn: "2027-03-31", status: "Planned" },
];

export const demoEvents: DemoEvent[] = [
  { code: "EVT-2026-031", name: "Bengaluru Chapter Annual Meet", city: "Bengaluru", date: "2026-10-11", type: "Chapter meet", registered: 186, attended: 0, capacity: 250, status: "Registrations open" },
  { code: "EVT-2026-028", name: "Founders' Day & Donor Recognition Evening", city: "Gandhinagar", date: "2026-09-27", type: "Fundraiser", registered: 342, attended: 0, capacity: 400, status: "Upcoming" },
  { code: "EVT-2026-024", name: "Careers in Climate Tech (webinar)", city: "Online", date: "2026-09-12", type: "Webinar", registered: 428, attended: 301, capacity: 1000, status: "Completed" },
  { code: "EVT-2026-019", name: "Batch of 2016 Decennial Reunion", city: "Gandhinagar", date: "2026-12-19", type: "Reunion", registered: 96, attended: 0, capacity: 350, status: "Registrations open" },
  { code: "EVT-2026-014", name: "Mumbai Chapter Monsoon Mixer", city: "Mumbai", date: "2026-07-19", type: "Chapter meet", registered: 143, attended: 118, capacity: 180, status: "Completed" },
];

export const demoChapters: DemoChapter[] = [
  { name: "Bengaluru Chapter", region: "South · India", members: 1240, lead: "Staff owner: ARO West (fictional)", lastActivity: "2026-08-30", health: "Active" },
  { name: "Mumbai Chapter", region: "West · India", members: 986, lead: "Staff owner: ARO West (fictional)", lastActivity: "2026-07-19", health: "Active" },
  { name: "Delhi NCR Chapter", region: "North · India", members: 874, lead: "Staff owner: ARO North (fictional)", lastActivity: "2026-06-02", health: "Needs attention" },
  { name: "Bay Area Chapter", region: "USA · West Coast", members: 642, lead: "Staff owner: Global Engagement (fictional)", lastActivity: "2026-08-09", health: "Active" },
  { name: "London Chapter", region: "UK & Europe", members: 318, lead: "Unassigned — needs a staff owner", lastActivity: "2026-02-14", health: "Needs attention" },
  { name: "Hyderabad Chapter (forming)", region: "South · India", members: 96, lead: "Volunteer convenor (fictional)", lastActivity: "2026-08-22", health: "Forming" },
];

export const demoTasks: DemoTask[] = [
  { id: "TSK-881", title: "Verify employment update — 2019 batch, 14 records", owner: "Data steward (fictional)", due: "2026-09-25", priority: "High", queue: "Verification", status: "In progress" },
  { id: "TSK-877", title: "Thank-you call — first-time donor ₹1L+", owner: "ARO officer (fictional)", due: "2026-09-22", priority: "High", queue: "Stewardship", status: "Open" },
  { id: "TSK-872", title: "Resolve 23 duplicate candidates from Aug import", owner: "Data steward (fictional)", due: "2026-09-30", priority: "Medium", queue: "Data quality", status: "Open" },
  { id: "TSK-869", title: "Re-engage 40 lapsed Delhi NCR contacts", owner: "Engagement exec (fictional)", due: "2026-10-05", priority: "Medium", queue: "Follow-ups", status: "Waiting on donor" },
  { id: "TSK-864", title: "Confirm reunion dinner seating + dietary needs", owner: "Events exec (fictional)", due: "2026-12-01", priority: "Low", queue: "Follow-ups", status: "Open" },
];

export const demoComms: DemoComm[] = [
  { id: "CMP-301", name: "Reunion 2016 — Save the date", channel: "Email", audience: "Batch of 2016 · 1,204 contacts", audienceCount: 1204, scheduledFor: "2026-10-01", status: "Scheduled (mock)" },
  { id: "CMP-298", name: "Founders' Day donor invite", channel: "WhatsApp", audience: "FY donors · 486 contacts", audienceCount: 486, scheduledFor: "2026-09-20", status: "Draft" },
  { id: "CMP-295", name: "Webinar reminder — Climate Tech", channel: "SMS", audience: "Registrants · 428 contacts", audienceCount: 428, scheduledFor: "2026-09-11", status: "Sent (mock)" },
  { id: "CMP-290", name: "Annual giving appeal — general", channel: "Email", audience: "Mailable alumni · 4,102 contacts", audienceCount: 4102, scheduledFor: "—", status: "Blocked — no consent" },
];

export const demoTemplates: DemoTemplate[] = [
  { name: "Donor thank-you (80G attached)", channel: "Email", purpose: "Stewardship after posting", lastUsed: "2026-08-15" },
  { name: "Event reminder (24h)", channel: "WhatsApp", purpose: "Attendance uplift", lastUsed: "2026-09-11" },
  { name: "Pledge nudge (polite, 30d)", channel: "Email", purpose: "Pledge fulfilment", lastUsed: "2026-08-28" },
  { name: "Address verification request", channel: "SMS", purpose: "Data quality", lastUsed: "2026-07-30" },
];

export const demoIntegrations: DemoIntegration[] = [
  { provider: "IITGN SSO (mock adapter)", category: "Identity", state: "Sandbox", note: "Sign-in flow renders against a local mock. Production waits on IITGN identity approval.", lastChecked: "2026-09-18 09:40 UTC" },
  { provider: "Email relay (mock adapter)", category: "Messaging", state: "Sandbox", note: "Messages are logged in-app only. No real email leaves the system.", lastChecked: "2026-09-18 09:40 UTC" },
  { provider: "WhatsApp provider (mock adapter)", category: "Messaging", state: "Under development", note: "Template approval and opt-in sync are not implemented.", lastChecked: "2026-09-17 16:02 UTC" },
  { provider: "SMS provider (mock adapter)", category: "Messaging", state: "Under development", note: "Delivery receipts are simulated in-app.", lastChecked: "2026-09-17 16:02 UTC" },
  { provider: "Payment gateway (mock adapter)", category: "Payments", state: "Sandbox", note: "Donation-portal checkout shows a sandbox banner. No money moves.", lastChecked: "2026-09-18 08:15 UTC" },
  { provider: "ERP finance sync", category: "ERP", state: "Unavailable", note: "Awaiting IITGN finance system credentials and field mapping sign-off.", lastChecked: "2026-09-10 11:00 UTC" },
  { provider: "Power BI / analytics export", category: "Analytics", state: "Unavailable", note: "Product reports ship first (M3); BI adapters follow.", lastChecked: "2026-09-10 11:00 UTC" },
  { provider: "Donation portal webhook", category: "Donation portal", state: "Under development", note: "Idempotency and reconciliation design pending M2.", lastChecked: "2026-09-12 14:30 UTC" },
];

export const demoImportBatches: DemoImportBatch[] = [
  { id: "IMP-2026-041", fileName: "reunion_rsvp_aug2026.csv (fictional)", rows: 1240, uploadedBy: "ARO staff (fictional)", uploadedAt: "2026-08-30", status: "Needs review", issues: 46, duplicates: 23 },
  { id: "IMP-2026-038", fileName: "placement_cell_export_jul2026.xlsx (fictional)", rows: 861, uploadedBy: "Data steward (fictional)", uploadedAt: "2026-07-28", status: "Validated", issues: 3, duplicates: 11 },
  { id: "IMP-2026-035", fileName: "legacy_sheet_batch_07.csv (fictional)", rows: 2048, uploadedBy: "ARO staff (fictional)", uploadedAt: "2026-07-09", status: "Imported (mock)", issues: 0, duplicates: 0 },
  { id: "IMP-2026-033", fileName: "chapter_mumbai_signup.csv (fictional)", rows: 143, uploadedBy: "Engagement exec (fictional)", uploadedAt: "2026-06-25", status: "Failed validation", issues: 61, duplicates: 4 },
];

export const demoReports: DemoReport[] = [
  { code: "RPT-C01", name: "Alumni by batch, discipline & city", category: "Constituent", refresh: "Nightly (planned)", rows: "~6,100 demo rows", description: "Headcount roll-ups with current-city and employer-sector splits." },
  { code: "RPT-C02", name: "Stale profiles (>365 days)", category: "Constituent", refresh: "Live in M1", rows: "Backend query", description: "Same filter as the dashboard card; click-through opens People." },
  { code: "RPT-D01", name: "Donations by fund & FY", category: "Donation", refresh: "On post (M2)", rows: "Ledger-backed", description: "Posted transactions only; adjustments shown as separate lines." },
  { code: "RPT-D02", name: "80G issuance tracker", category: "Compliance", refresh: "Finance review", rows: "~320 demo rows", description: "Issued / pending / not-applicable with receipt linkage." },
  { code: "RPT-E01", name: "Event attendance & no-show rate", category: "Engagement", refresh: "On check-in (M4)", rows: "~40 demo events", description: "Registration vs attendance with chapter comparison." },
  { code: "RPT-E02", name: "Chapter health summary", category: "Engagement", refresh: "Weekly (planned)", rows: "6 demo chapters", description: "Members, recency, and staff ownership coverage." },
];

export const demoUsers: DemoUser[] = [
  { name: "A. Registrar (fictional)", role: "Administrator", scope: "All modules · PII visible", lastActive: "2026-09-18", status: "Active" },
  { name: "R. Officer — ARO (fictional)", role: "Engagement Manager", scope: "People · Events · Chapters", lastActive: "2026-09-17", status: "Active" },
  { name: "S. Accountant — IAO (fictional)", role: "Finance Steward", scope: "Fundraising · Receipts · 80G", lastActive: "2026-09-16", status: "Active" },
  { name: "D. Volunteer (fictional)", role: "Chapter Volunteer", scope: "Own chapter · No PII export", lastActive: "2026-08-29", status: "Suspended" },
];

export const demoAudit: DemoAudit[] = [
  { time: "2026-09-18 09:12 UTC", actor: "A. Registrar (fictional)", action: "Updated role → Finance Steward", entity: "user:S. Accountant" },
  { time: "2026-09-17 15:44 UTC", actor: "R. Officer (fictional)", action: "Exported event attendee list (mock)", entity: "event:EVT-2026-014" },
  { time: "2026-09-16 10:03 UTC", actor: "System (mock job)", action: "Nightly freshness recalculation", entity: "job:freshness" },
  { time: "2026-09-15 12:37 UTC", actor: "S. Accountant (fictional)", action: "Posted adjustment DON-2026-0388 rev.1", entity: "donation:DON-2026-0388" },
];

export function inr(n: number): string {
  return "₹" + n.toLocaleString("en-IN");
}

export function pct(part: number, whole: number): number {
  if (!whole) return 0;
  return Math.round((part / whole) * 100);
}
