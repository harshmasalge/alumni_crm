/**
 * Phase 2 — Integrations preview (M7 scope) and Administration /
 * governance preview (M1/M7 scope). Adapter states follow the product rule:
 * Sandbox / Connected / Unavailable / Under development. Nothing here
 * connects to a real provider.
 */
import { useState } from "react";
import { demoIntegrations, demoUsers, demoAudit } from "./demoData";
import { PreviewBanner, PageHead, Kpis, Tabs, Panel, PreviewAction } from "./ui";

const INT_TABS = ["Dashboard", "Providers", "Configuration", "Logs"] as const;
type IntTab = (typeof INT_TABS)[number];

const ADMIN_TABS = ["Users & roles", "Permissions", "Audit log", "System config"] as const;
type AdminTab = (typeof ADMIN_TABS)[number];

function StateBadge({ state }: { state: string }) {
  const cls =
    state === "Connected"
      ? "status status--live"
      : state === "Sandbox"
        ? "status status--preview"
        : "status status--under-development";
  return <span className={cls}>{state}</span>;
}

export function IntegrationsPreview() {
  const [tab, setTab] = useState<IntTab>("Dashboard");
  const [selected, setSelected] = useState(demoIntegrations[0].provider);
  const provider = demoIntegrations.find((p) => p.provider === selected) ?? demoIntegrations[0];

  const counts = (s: string) => demoIntegrations.filter((p) => p.state === s).length;

  return (
    <div>
      <PageHead
        eyebrow="M7 · Integrations"
        title="Integrations"
        blurb="External systems are adapter interfaces, never product dependencies: mock provider now, IITGN-approved provider later. States below follow that rule."
        badge={<span className="status status--under-development">Under development</span>}
      />
      <PreviewBanner
        what="Provider cards, checks, and logs are static preview content."
        needs="M7 IITGN-approved credentials, adapter contracts, secret handling, and production hardening."
      />
      <Tabs tabs={INT_TABS} active={tab} onChange={setTab} />

      {tab === "Dashboard" && (
        <>
          <Kpis items={[
            { label: "Sandbox adapters", value: String(counts("Sandbox")), detail: "Mock now → approved later" },
            { label: "Under development", value: String(counts("Under development")), detail: "Template/receipt work pending" },
            { label: "Unavailable", value: String(counts("Unavailable")), detail: "Waiting on IITGN access" },
            { label: "Connected", value: String(counts("Connected")), detail: "No live provider in preview" },
          ]} />
          <div className="two-column">
            {demoIntegrations.slice(0, 4).map((p) => (
              <Panel key={p.provider} eyebrow={p.category} title={p.provider} badge={<StateBadge state={p.state} />}
                footer={`Last checked (mock): ${p.lastChecked}`}>
                <p style={{ margin: 0, padding: "14px 20px", fontSize: 13, color: "#52616a", lineHeight: 1.6 }}>{p.note}</p>
              </Panel>
            ))}
          </div>
        </>
      )}

      {tab === "Providers" && (
        <Panel eyebrow="Adapter registry" title={`Providers (${demoIntegrations.length})`} badge={<span className="status status--under-development">Under development</span>}
          footer="Production connection needs IITGN approval, scoped credentials, and a rollback plan — none of which exist in preview.">
          <div className="table-wrap"><table><thead><tr><th>Provider</th><th>Category</th><th>State</th><th>Note</th><th>Control</th></tr></thead>
            <tbody>{demoIntegrations.map((p) => (
              <tr key={p.provider} onClick={() => setSelected(p.provider)} style={{ cursor: "pointer", background: p.provider === selected ? "#faf8f2" : undefined }}>
                <td><strong>{p.provider}</strong></td><td>{p.category}</td><td><StateBadge state={p.state} /></td>
                <td style={{ color: "#52616a" }}>{p.note}</td>
                <td><PreviewAction label="Test (preview)" explain="M7 runs a sandboxed connectivity check with redacted credentials and logs the result — never a live call from preview." /></td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "Configuration" && (
        <Panel eyebrow="Adapter detail (mock)" title={provider.provider} badge={<StateBadge state={provider.state} />}
          footer="Secrets are never shown, logged, or exported. Rotation and break-glass access are M7 procedures.">
          <dl style={{ margin: 0, padding: "16px 20px", display: "grid", gridTemplateColumns: "180px 1fr", gap: "6px 16px", fontSize: 13 }}>
            <dt>Category</dt><dd>{provider.category}</dd>
            <dt>State</dt><dd>{provider.state} — {provider.note}</dd>
            <dt>Endpoint</dt><dd style={{ color: "#68777e" }}>sandbox.internal.invalid (mock — no route leaves this machine)</dd>
            <dt>Credentials</dt><dd style={{ color: "#68777e" }}>•••••••• (redacted mock; rotation due: on M7 approval)</dd>
            <dt>Last checked</dt><dd>{provider.lastChecked}</dd>
          </dl>
          <div className="note"><strong>Adapter rule:</strong> the product works fully offline; an unavailable provider degrades to a labelled state with a queue-and-retry path, never a dead end.</div>
        </Panel>
      )}

      {tab === "Logs" && (
        <Panel eyebrow="Adapter activity (mock)" title="Integration logs" badge={<span className="status status--under-development">Under development</span>}
          footer="Log retention and secret-scrubbing policy are set in M7 hardening.">
          <div className="table-wrap"><table><thead><tr><th>Time (mock)</th><th>Adapter</th><th>Event</th><th>Result</th></tr></thead>
            <tbody>
              <tr><td>2026-09-18 09:40 UTC</td><td>Email relay (mock)</td><td>Sandbox send — 12 messages</td><td>Logged in-app, 0 left the system</td></tr>
              <tr><td>2026-09-18 08:15 UTC</td><td>Payment gateway (mock)</td><td>Checkout render with sandbox banner</td><td>OK — no money moved</td></tr>
              <tr><td>2026-09-17 16:02 UTC</td><td>WhatsApp provider (mock)</td><td>Template sync attempt</td><td>Deferred — approval pending</td></tr>
              <tr><td>2026-09-10 11:00 UTC</td><td>ERP finance sync</td><td>Credential check</td><td>Unavailable — awaiting IITGN</td></tr>
            </tbody></table></div>
        </Panel>
      )}
    </div>
  );
}

export function AdminPreview() {
  const [tab, setTab] = useState<AdminTab>("Users & roles");

  return (
    <div>
      <PageHead
        eyebrow="Governance · M1 + M7"
        title="Administration"
        blurb="Users, roles, field permissions, audit, and system configuration. Enforcement lives server-side in M1; this preview shows the intended admin surface with fictional people."
        badge={<span className="status status--under-development">Under development</span>}
      />
      <PreviewBanner
        what="Users, roles, and audit rows are fictional."
        needs="M1 server-side RBAC + audit middleware (Session 1); break-glass and config approval land in M7."
      />
      <Tabs tabs={ADMIN_TABS} active={tab} onChange={setTab} />

      {tab === "Users & roles" && (
        <Panel eyebrow="Access control" title={`Users (${demoUsers.length})`} badge={<span className="status status--under-development">Under development</span>}
          footer="Production requires at least two controlled break-glass administrators — a single bootstrap admin is not the recovery model.">
          <div className="table-wrap"><table><thead><tr><th>User (fictional)</th><th>Role</th><th>Scope</th><th>Last active</th><th>Status</th><th>Control</th></tr></thead>
            <tbody>{demoUsers.map((u) => (
              <tr key={u.name}><td><strong>{u.name}</strong></td><td>{u.role}</td><td style={{ color: "#52616a" }}>{u.scope}</td>
                <td>{u.lastActive}</td><td>{u.status}</td>
                <td><PreviewAction label="Change role (preview)" explain="Role changes are audit-worthy in M1: actor, before/after, and reason are recorded, and permissions re-evaluate server-side." /></td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "Permissions" && (
        <Panel eyebrow="Least privilege" title="Module & field permissions" badge={<span className="status status--under-development">Under development</span>}
          footer="Frontend hiding is never a security control — every check here mirrors a server-side policy in M1.">
          <div className="table-wrap"><table><thead><tr><th>Capability</th><th>Administrator</th><th>Engagement Mgr</th><th>Finance Steward</th><th>Volunteer</th></tr></thead>
            <tbody>
              <tr><td><strong>People search & 360° profile</strong></td><td>✓</td><td>✓</td><td>Limited</td><td>Own chapter</td></tr>
              <tr><td><strong>Post donations / issue receipts</strong></td><td>✓</td><td>—</td><td>✓</td><td>—</td></tr>
              <tr><td><strong>Run imports / merge records</strong></td><td>✓</td><td>—</td><td>—</td><td>—</td></tr>
              <tr><td><strong>Send campaigns</strong></td><td>✓</td><td>✓</td><td>—</td><td>—</td></tr>
              <tr><td><strong>Exports (audited)</strong></td><td>✓</td><td>Scoped</td><td>Finance only</td><td>—</td></tr>
              <tr><td><strong>Restricted fields (DOB, PAN, CPI)</strong></td><td>Masked unless granted</td><td>Masked</td><td>PAN last-4</td><td>Hidden</td></tr>
            </tbody></table></div>
          <div className="note"><strong>Field-level rule:</strong> restricted fields never appear in ordinary list, search, or export responses — the server strips them before responding.</div>
        </Panel>
      )}

      {tab === "Audit log" && (
        <Panel eyebrow="Append-only" title={`Audit events (${demoAudit.length} shown)`} badge={<span className="status status--under-development">Under development</span>}
          footer="Every sensitive change records actor, time, IP/request id, and before/after state. Financial posting, receipts, exports, merges, and role changes are always audited.">
          <div className="table-wrap"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th></tr></thead>
            <tbody>{demoAudit.map((a, i) => (
              <tr key={i}><td>{a.time}</td><td>{a.actor}</td><td>{a.action}</td><td>{a.entity}</td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "System config" && (
        <div className="two-column">
          <Panel eyebrow="Lookups" title="Reference data" badge={<span className="status status--under-development">Under development</span>}
            footer="Programme/discipline values come from IITGN; completeness weights and approval rules are M1 field-freeze decisions.">
            <ul className="status-list">
              <li><span className="status status--under-development">Programmes</span><span>BTech · MTech · MSc · MA · PhD (values pending IITGN confirm)</span></li>
              <li><span className="status status--under-development">Sectors</span><span>Private · Government · Academic · Startup · Other</span></li>
              <li><span className="status status--under-development">Freshness</span><span>Substantive-update definition; 365-day stale threshold</span></li>
            </ul>
          </Panel>
          <Panel eyebrow="Policy" title="Guardrails" badge={<span className="status status--under-development">Under development</span>}>
            <ul className="status-list">
              <li><span className="status status--under-development">Aadhaar</span><span>Disabled until purpose, access, and retention are approved.</span></li>
              <li><span className="status status--under-development">Network</span><span>“IITGN Wi-Fi only” is a production gateway policy — never blocks local dev.</span></li>
              <li><span className="status status--under-development">Recovery</span><span>Two break-glass admins required for production.</span></li>
            </ul>
            <div className="note"><strong>Decision log:</strong> costly-to-reverse choices land as ADRs under <span style={{ fontFamily: "monospace" }}>docs/decisions/</span>.</div>
          </Panel>
        </div>
      )}
    </div>
  );
}
