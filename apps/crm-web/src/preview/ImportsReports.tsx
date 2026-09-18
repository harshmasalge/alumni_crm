/**
 * Phase 2 — Imports / migration workbench preview (M3 scope) and
 * Reporting / analytics preview (M3 scope). Fictional data; uploads and
 * exports are simulated notices, never real file processing.
 */
import { useState } from "react";
import { demoImportBatches, demoReports } from "./demoData";
import { PreviewBanner, PageHead, Kpis, Tabs, Panel, PreviewAction, EmptyState } from "./ui";

function Badge({ children }: { children: string }) {
  return <span className="status status--preview">{children}</span>;
}

const IMPORT_TABS = ["Workspace", "Column mapping", "Validation", "Duplicates", "History"] as const;
type ImportTab = (typeof IMPORT_TABS)[number];

const REPORT_TABS = ["Dashboard", "Standard reports", "Exports"] as const;
type ReportTab = (typeof REPORT_TABS)[number];

const SOURCE_COLUMNS = ["full_name", "roll_no", "grad_year", "employer", "city", "phone", "email_personal"];
const TARGET_FIELDS = ["person.full_name (M1)", "alumni_profile.roll_no (M1)", "alumni_profile.year_of_graduation (M1)", "affiliation.organisation_name_raw (M1)", "affiliation.city (M1)", "contact_methods.value[PHONE]", "contact_methods.value[EMAIL]"];

const VALIDATION_ROWS = [
  { row: 14, issue: "roll_no checksum pattern unrecognised", severity: "Error", action: "Fix in source or map to correction queue" },
  { row: 88, issue: "grad_year 2099 out of range", severity: "Error", action: "Quarantine row" },
  { row: 203, issue: "phone missing country code", severity: "Warning", action: "Auto-prefix +91 on confirm" },
  { row: 311, issue: "employer unmatched — kept as raw text", severity: "Info", action: "Preserved per affiliation rule" },
  { row: 402, issue: "duplicate of row 97 (name + phone)", severity: "Warning", action: "Send to duplicate review" },
];

const DUPLICATE_ROWS = [
  { candidate: "R. Iyer (fictional) · +91 98•••••21", score: "0.94", basis: "Name + phone + grad_year", decision: "Awaiting steward" },
  { candidate: "S. Banerjee (fictional) · 2017B4A••••", score: "0.87", basis: "Roll_no close match, one digit differs", decision: "Awaiting steward" },
  { candidate: "Bluepeak Systems (fictional)", score: "0.81", basis: "Organisation normalised name", decision: "Awaiting steward" },
];

export function ImportsPreview() {
  const [tab, setTab] = useState<ImportTab>("Workspace");
  const batch = demoImportBatches[0];

  return (
    <div>
      <PageHead
        eyebrow="M3 · Imports & migration"
        title="Import workspace"
        blurb="Staged migration workbench: upload, map, validate, deduplicate, preview, then import. Nothing here writes to PostgreSQL — every commit control explains it needs the M3 backend."
        badge={<Badge>Preview</Badge>}
      />
      <PreviewBanner
        what="Batches, validation rows, and duplicate candidates are fictional fixtures."
        needs="M3 staging tables, validation engine, duplicate matcher, merge workflow, and audit."
      />
      <Tabs tabs={IMPORT_TABS} active={tab} onChange={setTab} />

      {tab === "Workspace" && (
        <>
          <Kpis items={[
            { label: "Rows staged (demo)", value: batch.rows.toLocaleString("en-IN"), detail: batch.fileName },
            { label: "Validation issues", value: String(batch.issues), detail: "Errors block import in M3" },
            { label: "Duplicate candidates", value: String(batch.duplicates), detail: "Steward decision required" },
            { label: "Batches in history", value: String(demoImportBatches.length), detail: "See History tab" },
          ]} />
          <Panel eyebrow="Drop zone (mock)" title="Upload a source file" badge={<Badge>Preview</Badge>}
            footer="Accepted in M3: CSV/XLSX under 50 MB. Files wait in object storage with scan status before parsing.">
            <div style={{ margin: 20, padding: "30px 20px", border: "2px dashed #cfd4d2", borderRadius: 6, textAlign: "center", color: "#65737a" }}>
              <p style={{ margin: "0 0 6px", fontWeight: 700, color: "#3d4a52" }}>Drag a file here, or browse (disabled in preview)</p>
              <p style={{ margin: 0, fontSize: 13 }}>Filenames are fictional. Real uploads need the M3 virus-scan + staging pipeline.</p>
              <p style={{ margin: "12px 0 0" }}><PreviewAction label="Simulate upload (preview)" explain="In M3 this stores the file in object storage, records a batch row, and starts async parsing with progress." /></p>
            </div>
          </Panel>
        </>
      )}

      {tab === "Column mapping" && (
        <Panel eyebrow="Template: alumni roster v3 (mock)" title="Map source columns to CRM fields" badge={<Badge>Preview</Badge>}
          footer="Unmapped columns are kept as batch metadata, never silently dropped. Date precision is preserved (never invented).">
          <div className="table-wrap"><table><thead><tr><th>Source column</th><th>CRM field</th><th>Confidence</th><th>Rule</th></tr></thead>
            <tbody>{SOURCE_COLUMNS.map((c, i) => (
              <tr key={c}><td><strong>{c}</strong></td><td>{TARGET_FIELDS[i]}</td>
                <td>{i < 5 ? "Auto-mapped" : "Needs confirm"}</td>
                <td style={{ color: "#52616a" }}>{i === 3 ? "Unmatched employers kept as raw text" : i === 5 ? "Normalised; original preserved" : "Direct map"}</td></tr>
            ))}</tbody></table></div>
          <div className="note"><strong>Never invent dates:</strong> partial dates keep their precision (year-only stays year-only) per the data-dictionary rule.</div>
        </Panel>
      )}

      {tab === "Validation" && (
        <Panel eyebrow="Batch IMP-2026-041 (demo)" title={`Validation results (${VALIDATION_ROWS.length} shown)`} badge={<Badge>Preview</Badge>}
          footer={<PreviewAction label="Re-run validation (preview)" explain="M3 re-validates every staged row against field rules, consent constraints, and lookup tables." />}>
          <div className="table-wrap"><table><thead><tr><th>Row</th><th>Issue</th><th>Severity</th><th>Steward action</th></tr></thead>
            <tbody>{VALIDATION_ROWS.map((r) => (
              <tr key={r.row}><td><strong>#{r.row}</strong></td><td>{r.issue}</td><td>{r.severity}</td><td style={{ color: "#52616a" }}>{r.action}</td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "Duplicates" && (
        <Panel eyebrow="Match review" title={`Duplicate candidates (${DUPLICATE_ROWS.length})`} badge={<Badge>Preview</Badge>}
          footer="Merges are audit-worthy operations: actor, before/after, and surviving record are all recorded in M3.">
          <div className="table-wrap"><table><thead><tr><th>Candidate pair</th><th>Score</th><th>Basis</th><th>Decision</th><th>Steward</th></tr></thead>
            <tbody>{DUPLICATE_ROWS.map((d) => (
              <tr key={d.candidate}><td><strong>{d.candidate}</strong></td><td>{d.score}</td><td>{d.basis}</td><td>{d.decision}</td>
                <td><PreviewAction label="Keep both (preview)" explain="In M3 this marks the pair as distinct with a reason, recorded in the merge audit log." /> <PreviewAction label="Merge (preview)" explain="In M3 this opens field-level survivorship picking, then writes a merge event — never a silent overwrite." /></td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "History" && (
        <Panel eyebrow="Batches" title={`Import history (${demoImportBatches.length})`} badge={<Badge>Preview</Badge>}
          footer="Each batch links to its validation report, duplicate decisions, and final row counts.">
          <div className="table-wrap"><table><thead><tr><th>Batch</th><th>File</th><th>Rows</th><th>Uploaded</th><th>Issues</th><th>Duplicates</th><th>Status</th></tr></thead>
            <tbody>{demoImportBatches.map((b) => (
              <tr key={b.id}><td><strong>{b.id}</strong></td><td>{b.fileName}</td><td>{b.rows.toLocaleString("en-IN")}</td>
                <td>{b.uploadedAt} · {b.uploadedBy}</td><td>{b.issues}</td><td>{b.duplicates}</td><td>{b.status}</td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}
    </div>
  );
}

export function ReportsPreview() {
  const [tab, setTab] = useState<ReportTab>("Dashboard");
  const [category, setCategory] = useState<string>("All");

  const visible = demoReports.filter((r) => category === "All" || r.category === category);

  return (
    <div>
      <PageHead
        eyebrow="M3 · Reporting"
        title="Reports"
        blurb="Standard reports with date and filter controls. Live M1 rows back the stale-profile report; everything else previews M2–M4 content with demo values."
        badge={<Badge>Preview</Badge>}
      />
      <PreviewBanner
        what="Report rows and KPI values are illustrative."
        needs="M3 reporting views; donation/engagement reports additionally need M2 and M4 ledgers."
      />
      <Tabs tabs={REPORT_TABS} active={tab} onChange={setTab} />

      {tab === "Dashboard" && (
        <>
          <Kpis items={[
            { label: "Constituents (demo)", value: "6,100", detail: "Registry roll-up" },
            { label: "FY donations posted (demo)", value: "₹3.19 Cr", detail: "Illustrative ledger total" },
            { label: "Event attendance (demo)", value: "71%", detail: "Completed events" },
            { label: "Mailable audience (demo)", value: "4,102", detail: "Consent-filtered" },
          ]} />
          <div className="two-column">
            <Panel eyebrow="Run queue" title="Standard reports" badge={<Badge>Preview</Badge>}
              footer="Each report documents its grain, refresh cadence, and permission requirements before it can be scheduled.">
              <div className="table-wrap"><table><thead><tr><th>Code</th><th>Report</th><th>Category</th><th>Refresh</th></tr></thead>
                <tbody>{demoReports.slice(0, 4).map((r) => (
                  <tr key={r.code}><td><strong>{r.code}</strong></td><td>{r.name}</td><td>{r.category}</td><td>{r.refresh}</td></tr>
                ))}</tbody></table></div>
            </Panel>
            <Panel eyebrow="How to read this" title="Grain & freshness" badge={<Badge>Preview</Badge>}>
              <ul className="status-list">
                <li><span className="status status--live">Live</span><span>Stale-profile report reads the M1 backend query.</span></li>
                <li><span className="status status--preview">Preview</span><span>Donation, engagement, and compliance layouts with demo rows.</span></li>
                <li><span className="status status--under-development">Under development</span><span>Scheduled delivery and BI adapters wait on M3/M7.</span></li>
              </ul>
              <div className="note"><strong>Date controls:</strong> FY auto-tagging (April–March) applies to donation reports in M2; other reports use explicit ranges.</div>
            </Panel>
          </div>
        </>
      )}

      {tab === "Standard reports" && (
        <Panel eyebrow="Catalogue" title={`Standard reports (${visible.length})`} badge={<Badge>Preview</Badge>}
          footer={<span><label style={{ fontSize: 12, color: "#68777e" }}>Category&nbsp;</label><select value={category} onChange={(e) => setCategory(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
            {["All", "Constituent", "Donation", "Engagement", "Compliance"].map((c) => <option key={c}>{c}</option>)}
          </select> <PreviewAction label="Run report (preview)" explain="M3 executes the report against permissioned views and logs the run with filters and row counts." /></span>}>
          <div className="table-wrap"><table><thead><tr><th>Code</th><th>Name</th><th>Category</th><th>Refresh</th><th>Rows</th><th>Description</th></tr></thead>
            <tbody>{visible.map((r) => (
              <tr key={r.code}><td><strong>{r.code}</strong></td><td>{r.name}</td><td>{r.category}</td><td>{r.refresh}</td><td>{r.rows}</td><td style={{ color: "#52616a" }}>{r.description}</td></tr>
            ))}</tbody></table></div>
          {visible.length === 0 && <EmptyState title="No reports in this category" body="Pick another category to browse the M3 report catalogue." />}
        </Panel>
      )}

      {tab === "Exports" && (
        <Panel eyebrow="Governed extracts" title="Export controls" badge={<Badge>Preview</Badge>}
          footer="Exports, role changes, and merges are audit-worthy: actor, time, filters, and row counts are logged.">
          <div className="table-wrap"><table><thead><tr><th>Export</th><th>Fields</th><th>Guardrail</th><th>Control</th></tr></thead>
            <tbody>
              <tr><td><strong>Alumni directory extract</strong></td><td>Name, batch, city, employer</td><td>Restricted fields excluded</td><td><PreviewAction label="Request export (preview)" explain="M3 queues the extract, applies field permissions, and records an audit event with the requester and filters." /></td></tr>
              <tr><td><strong>Donation register (finance)</strong></td><td>Posted lines + allocations</td><td>Finance role only · PAN masked</td><td><PreviewAction label="Request export (preview)" explain="Requires the finance role; every download is watermarked and audited." /></td></tr>
              <tr><td><strong>Event attendee list</strong></td><td>Registrants + consent flags</td><td>DNC-filtered</td><td><PreviewAction label="Request export (preview)" explain="Global-DNC contacts are excluded before the file is produced." /></td></tr>
            </tbody></table></div>
          <div className="note"><strong>Restricted by default:</strong> date of birth, PAN, CPI/ranks, and personal contacts never appear in ordinary list or export responses.</div>
        </Panel>
      )}
    </div>
  );
}
