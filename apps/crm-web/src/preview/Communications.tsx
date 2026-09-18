/**
 * Phase 2 — Communications / campaigns preview (M6 scope).
 * Consent-aware design: DNC overrides all providers; blocked sends are
 * shown explicitly. Delivery here is in-app mock only.
 */
import { useState } from "react";
import { demoComms, demoTemplates } from "./demoData";
import { PreviewBanner, PageHead, Kpis, Tabs, Panel, PreviewAction, EmptyState } from "./ui";

function Badge({ tone, children }: { tone: "preview" | "dev"; children: string }) {
  return <span className={tone === "preview" ? "status status--preview" : "status status--under-development"}>{children}</span>;
}

const TABS = ["Dashboard", "Campaigns", "Audience", "Templates", "History"] as const;
type Tab = (typeof TABS)[number];

export function CommunicationsPreview() {
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [channel, setChannel] = useState<string>("All");
  const campaigns = demoComms.filter((c) => channel === "All" || c.channel === channel);
  const blocked = demoComms.filter((c) => c.status === "Blocked — no consent");

  return (
    <div>
      <PageHead
        eyebrow="M6 · Communications"
        title="Communications"
        blurb="Consent-aware campaigns with audience segments, templates, scheduling, and delivery tracking. Every send below is a labelled mock — no provider is connected."
        badge={<Badge tone="dev">Under development</Badge>}
      />
      <PreviewBanner
        what="Audiences, schedules, and delivery states are fictional."
        needs="M6 campaign engine, consent enforcement, template approval, and mock/in-app delivery log."
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "Dashboard" && (
        <>
          <Kpis items={[
            { label: "Mailable (demo)", value: "4,102", detail: "Email opt-in, DNC excluded" },
            { label: "WhatsApp reachable (demo)", value: "2,870", detail: "Opt-in + linked numbers" },
            { label: "Scheduled (mock)", value: "1", detail: "Reunion save-the-date" },
            { label: "Blocked by consent", value: String(blocked.length), detail: "DNC overrides providers" },
          ]} />
          <div className="two-column">
            <Panel eyebrow="Pipeline" title="Campaigns at a glance" badge={<Badge tone="dev">Under development</Badge>}
              footer="Campaigns move Draft → Scheduled → Sending → Done with consent re-checked at send time.">
              <div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Channel</th><th>Audience</th><th>Status</th></tr></thead>
                <tbody>{demoComms.map((c) => (
                  <tr key={c.id}><td><strong>{c.name}</strong></td><td>{c.channel}</td><td>{c.audience}</td><td>{c.status}</td></tr>
                ))}</tbody></table></div>
            </Panel>
            <Panel eyebrow="Compliance first" title="Consent guardrails" badge={<Badge tone="dev">Under development</Badge>}>
              <ul className="status-list">
                <li><span className="status status--under-development">Global DNC</span><span>Overrides every provider, every campaign.</span></li>
                <li><span className="status status--under-development">Channel opt-ins</span><span>Email / WhatsApp / SMS tracked separately with source + time.</span></li>
                <li><span className="status status--under-development">Birthday rule</span><span>Automation uses month/day only, never the birth year.</span></li>
              </ul>
              <div className="note"><strong>Blocked sends stay visible:</strong> a campaign that fails consent shows why, who is excluded, and what approval would unblock it — it never sends silently.</div>
            </Panel>
          </div>
        </>
      )}

      {tab === "Campaigns" && (
        <Panel eyebrow="Workflow" title={`Campaigns (${campaigns.length} shown)`} badge={<Badge tone="dev">Under development</Badge>}
          footer={<span><label style={{ fontSize: 12, color: "#68777e" }}>Channel&nbsp;</label><select value={channel} onChange={(e) => setChannel(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
            {["All", "Email", "WhatsApp", "SMS"].map((c) => <option key={c}>{c}</option>)}
          </select> <PreviewAction label="New campaign (preview)" explain="M6 guides audience → template → consent check → schedule, with a pre-send summary of eligible vs excluded contacts." /></span>}>
          <div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Channel</th><th>Audience</th><th>Scheduled</th><th>Status</th><th>Control</th></tr></thead>
            <tbody>{campaigns.map((c) => (
              <tr key={c.id}><td><strong>{c.name}</strong><br /><span style={{ color: "#68777e", fontSize: 12 }}>{c.id}</span></td>
                <td>{c.channel}</td><td>{c.audience}</td><td>{c.scheduledFor}</td><td>{c.status}</td>
                <td><PreviewAction label="Open (preview)" explain="M6 campaign detail shows content, eligibility counts, delivery batches, and per-recipient outcomes." /></td></tr>
            ))}</tbody></table></div>
          {campaigns.length === 0 && <EmptyState title="No campaigns on this channel" body="Change the channel filter to browse the mock campaign pipeline." />}
        </Panel>
      )}

      {tab === "Audience" && (
        <Panel eyebrow="Segment builder (mock)" title="Audience selection" badge={<Badge tone="dev">Under development</Badge>}
          footer="Segments are saved with their definition so a re-run months later is explainable and auditable.">
          <div className="table-wrap"><table><thead><tr><th>Segment (demo)</th><th>Definition</th><th>Eligible</th><th>Excluded (DNC)</th></tr></thead>
            <tbody>
              <tr><td><strong>Batch of 2016, mailable</strong></td><td style={{ color: "#52616a" }}>grad_year = 2016 AND email_opt_in</td><td>1,204</td><td>88</td></tr>
              <tr><td><strong>FY donors, WhatsApp</strong></td><td style={{ color: "#52616a" }}>donated FY 2026–27 AND whatsapp_opt_in</td><td>486</td><td>21</td></tr>
              <tr><td><strong>Lapsed Delhi NCR</strong></td><td style={{ color: "#52616a" }}>chapter = Delhi NCR AND no touch 18 months</td><td>312</td><td>17</td></tr>
            </tbody></table></div>
          <div className="note"><strong>Eligibility preview:</strong> counts show eligible vs DNC-excluded before scheduling, so staff never mistake a small send for a data problem.</div>
        </Panel>
      )}

      {tab === "Templates" && (
        <Panel eyebrow="Approved content" title={`Templates (${demoTemplates.length})`} badge={<Badge tone="dev">Under development</Badge>}
          footer="WhatsApp templates need provider approval in production; drafts stay in-app until then.">
          <div className="table-wrap"><table><thead><tr><th>Template</th><th>Channel</th><th>Purpose</th><th>Last used</th><th>Control</th></tr></thead>
            <tbody>{demoTemplates.map((t) => (
              <tr key={t.name}><td><strong>{t.name}</strong></td><td>{t.channel}</td><td>{t.purpose}</td><td>{t.lastUsed}</td>
                <td><PreviewAction label="Use template (preview)" explain="M6 inserts approved content with merge fields (name, batch, receipt link) and re-checks consent at send." /></td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "History" && (
        <Panel eyebrow="Delivery log (mock)" title="Communication history" badge={<Badge tone="dev">Under development</Badge>}
          footer="Per-recipient outcomes (delivered / bounced / opted-out-since) feed the engagement timeline in M6.">
          <div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Channel</th><th>Sent (mock)</th><th>Delivered</th><th>Bounced</th><th>Opt-outs</th></tr></thead>
            <tbody>
              <tr><td><strong>Webinar reminder — Climate Tech</strong></td><td>SMS</td><td>428</td><td>411</td><td>9</td><td>2</td></tr>
              <tr><td><strong>Reunion 2016 — early bird</strong></td><td>Email</td><td>1,204</td><td>1,139</td><td>41</td><td>6</td></tr>
              <tr><td><strong>Diwali greeting (mock)</strong></td><td>WhatsApp</td><td>2,102</td><td>2,044</td><td>33</td><td>11</td></tr>
            </tbody></table></div>
        </Panel>
      )}
    </div>
  );
}
