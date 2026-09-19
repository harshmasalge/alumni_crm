/**
 * Phase 2 — Fundraising preview (M2 scope): dashboard, ledger, donation
 * detail, pledges, funds, campaigns, 80G workflow, analytics.
 * All data fictional; actions are preview notices, never real postings.
 */
import { useState } from "react";
import { demoDonations, demoPledges, demoFunds, demoCampaigns, inr, pct } from "./demoData";
import { PreviewBanner, PageHead, Kpis, Tabs, Panel, Bar, PreviewAction, EmptyState } from "./ui";

function Badge({ tone, children }: { tone: "live" | "preview" | "dev"; children: string }) {
  const cls = tone === "live" ? "status status--live" : tone === "preview" ? "status status--preview" : "status status--under-development";
  return <span className={cls}>{children}</span>;
}

const TABS = ["Dashboard", "Ledger", "Pledges", "Funds & campaigns", "80G workflow", "Analytics"] as const;
type Tab = (typeof TABS)[number];

export function FundraisingPreview() {
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [selectedId, setSelectedId] = useState<string | null>(demoDonations[0].id);
  const selected = demoDonations.find((d) => d.id === selectedId) ?? null;

  const posted = demoDonations.filter((d) => d.lifecycle === "Posted");
  const fyTotal = posted.reduce((s, d) => s + d.amountInr, 0);

  return (
    <div>
      <PageHead
        eyebrow="M2 · Fundraising"
        title="Fundraising"
        blurb="Donation ledger, pledges, funds, campaigns, and 80G workflow as they will appear once the M2 backend lands. Figures below are fictional preview values."
        badge={<Badge tone="preview">Preview</Badge>}
      />
      <PreviewBanner
        what="Ledger rows, receipts, and 80G states are static demo content."
        needs="M2 donation ledger API, posting rules, receipt numbering, and finance approval."
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "Dashboard" && (
        <>
          <Kpis
            items={[
              { label: "Posted this FY (demo)", value: inr(fyTotal), detail: `${posted.length} posted transactions` },
              { label: "Pledged pipeline (demo)", value: inr(demoPledges.reduce((s, p) => s + (p.pledgedInr - p.receivedInr), 0)), detail: `${demoPledges.length} open pledges` },
              { label: "Active funds", value: String(demoFunds.filter((f) => f.status === "Active").length), detail: `${demoFunds.length} funds tracked` },
              { label: "80G pending review", value: String(demoDonations.filter((d) => d.eightGStatus === "Pending finance review").length), detail: "Finance queue in M2" },
            ]}
          />
          <div className="two-column">
            <Panel eyebrow="Ledger excerpt" title="Recent donations" badge={<Badge tone="preview">Preview</Badge>}
              footer="Posted transactions are immutable in M2 — corrections use adjustment records, never edits.">
              <div className="table-wrap"><table><thead><tr><th>Donation</th><th>Donor</th><th>Fund</th><th>Amount</th><th>State</th></tr></thead>
                <tbody>{demoDonations.slice(0, 4).map((d) => (
                  <tr key={d.id}><td><strong>{d.id}</strong><br /><span style={{ color: "#68777e" }}>{d.date}</span></td><td>{d.donor}</td><td>{d.fund}</td><td>{inr(d.amountInr)}</td><td>{d.lifecycle}</td></tr>
                ))}</tbody></table></div>
            </Panel>
            <Panel eyebrow="Campaigns" title="Active appeals" badge={<Badge tone="preview">Preview</Badge>}
              footer="Campaign pages, donor walls, and portal checkout arrive with the donation-portal work.">
              {demoCampaigns.map((c) => (
                <div key={c.code} style={{ padding: "12px 20px", borderBottom: "1px solid #ecece6" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13 }}>
                    <strong>{c.name}</strong><span style={{ color: "#68777e" }}>{c.status}</span>
                  </div>
                  <div style={{ marginTop: 8 }}><Bar valuePct={pct(c.raisedInr, c.goalInr)} /></div>
                  <p style={{ fontSize: 12, color: "#68777e", margin: "6px 0 0" }}>{inr(c.raisedInr)} of {inr(c.goalInr)} · {c.donors} donors · ends {c.endsOn}</p>
                </div>
              ))}
            </Panel>
          </div>
        </>
      )}

      {tab === "Ledger" && (
        <Panel eyebrow="M2 ledger" title={`Donations ledger (${demoDonations.length})`} badge={<Badge tone="preview">Preview</Badge>}
          footer={<span><PreviewAction label="Record donation (preview)" explain="In M2 this opens a validated posting form: donor, FY auto-tag, fund allocations that reconcile exactly, payment reference, and receipt generation." /> <PreviewAction label="Export ledger (preview)" explain="Exports are permissioned and audited in M2. PAN stays masked; amounts export with fund allocation lines." /></span>}>
          <div className="table-wrap"><table><thead><tr><th>ID</th><th>Donor</th><th>Date</th><th>Fund</th><th>Mode</th><th>Amount</th><th>Lifecycle</th><th>Receipt</th></tr></thead>
            <tbody>{demoDonations.map((d) => (
              <tr key={d.id} onClick={() => setSelectedId(d.id)} style={{ cursor: "pointer", background: d.id === selectedId ? "#faf8f2" : undefined }}>
                <td><strong>{d.id}</strong></td><td>{d.donor}<br /><span style={{ color: "#68777e", fontSize: 12 }}>{d.donorId}</span></td>
                <td>{d.date}</td><td>{d.fund}</td><td>{d.mode}</td><td>{inr(d.amountInr)}</td><td>{d.lifecycle}</td><td>{d.receiptNo}</td>
              </tr>
            ))}</tbody></table></div>
          {selected ? (
            <div style={{ padding: 20, borderTop: "1px solid #deded8" }}>
              <p className="eyebrow" style={{ margin: "0 0 4px" }}>Donation detail · {selected.id}</p>
              <h3 style={{ margin: "0 0 8px" }}>{selected.donor} — {inr(selected.amountInr)}</h3>
              <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "180px 1fr", gap: "6px 16px", fontSize: 13 }}>
                <dt>Fund allocation</dt><dd>{selected.fund} — {inr(selected.amountInr)} (reconciles 100%)</dd>
                <dt>Financial year</dt><dd>{selected.fy} (automatic in M2)</dd>
                <dt>Payment</dt><dd>{selected.mode}</dd>
                <dt>Lifecycle</dt><dd>{selected.lifecycle}{selected.lifecycle === "Adjusted" ? " — correction posted as reversal + re-post, original preserved" : ""}</dd>
                <dt>80G</dt><dd>{selected.eightGStatus}</dd>
                <dt>Receipt</dt><dd>{selected.receiptNo}</dd>
              </dl>
            </div>
          ) : null}
        </Panel>
      )}

      {tab === "Pledges" && (
        <Panel eyebrow="Commitments" title={`Pledges (${demoPledges.length})`} badge={<Badge tone="preview">Preview</Badge>}
          footer="Pledge reminders respect communication consent; overdue pledges surface in the stewardship queue.">
          <div className="table-wrap"><table><thead><tr><th>Pledge</th><th>Donor</th><th>Fund</th><th>Pledged</th><th>Received</th><th>Progress</th><th>Expected by</th><th>Status</th></tr></thead>
            <tbody>{demoPledges.map((p) => (
              <tr key={p.id}><td><strong>{p.id}</strong></td><td>{p.donor}</td><td>{p.fund}</td><td>{inr(p.pledgedInr)}</td><td>{inr(p.receivedInr)}</td>
                <td><Bar valuePct={pct(p.receivedInr, p.pledgedInr)} /></td><td>{p.expectedBy}</td><td>{p.status}</td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "Funds & campaigns" && (
        <>
          <Panel eyebrow="Chart of funds" title={`Funds (${demoFunds.length})`} badge={<Badge tone="preview">Preview</Badge>}
            footer="Restricted funds enforce purpose checks at posting time in M2.">
            <div className="table-wrap"><table><thead><tr><th>Code</th><th>Fund</th><th>Purpose</th><th>Corpus (demo)</th><th>FY received (demo)</th><th>Status</th></tr></thead>
              <tbody>{demoFunds.map((f) => (
                <tr key={f.code}><td><strong>{f.code}</strong></td><td>{f.name}</td><td>{f.purpose}</td><td>{inr(f.corpusInr)}</td><td>{inr(f.fyReceivedInr)}</td><td>{f.status}</td></tr>
              ))}</tbody></table></div>
          </Panel>
          <div style={{ height: 18 }} />
          <Panel eyebrow="Appeals" title={`Campaigns (${demoCampaigns.length})`} badge={<Badge tone="preview">Preview</Badge>}>
            <div className="table-wrap"><table><thead><tr><th>Campaign</th><th>Fund</th><th>Goal</th><th>Raised</th><th>Progress</th><th>Donors</th><th>Status</th></tr></thead>
              <tbody>{demoCampaigns.map((c) => (
                <tr key={c.code}><td><strong>{c.name}</strong><br /><span style={{ color: "#68777e", fontSize: 12 }}>{c.code} · ends {c.endsOn}</span></td>
                  <td>{c.fund}</td><td>{inr(c.goalInr)}</td><td>{inr(c.raisedInr)}</td><td><Bar valuePct={pct(c.raisedInr, c.goalInr)} /></td><td>{c.donors}</td><td>{c.status}</td></tr>
              ))}</tbody></table></div>
          </Panel>
        </>
      )}

      {tab === "80G workflow" && (
        <Panel eyebrow="Compliance" title="80G receipt workflow" badge={<Badge tone="preview">Preview</Badge>}
          footer="80G issuance needs the approved finance process; this preview shows the intended states, not valid certificates.">
          <div className="table-wrap"><table><thead><tr><th>Donation</th><th>Donor</th><th>Amount</th><th>Receipt</th><th>80G state</th><th>Next step</th></tr></thead>
            <tbody>{demoDonations.map((d) => (
              <tr key={d.id}><td><strong>{d.id}</strong></td><td>{d.donor}</td><td>{inr(d.amountInr)}</td><td>{d.receiptNo}</td><td>{d.eightGStatus}</td>
                <td style={{ color: "#52616a" }}>{d.eightGStatus === "Issued" ? "Download from finance vault (M2)" : d.eightGStatus === "Pending finance review" ? "Awaiting finance sign-off" : "Collect eligible donation first"}</td></tr>
            ))}</tbody></table></div>
          <div className="note"><strong>Posting rule (M2):</strong> receipts carry immutable numbers; a re-issued receipt keeps the original linked as revision history. PAN is masked by default and never appears in lists or exports.</div>
        </Panel>
      )}

      {tab === "Analytics" && (
        <>
          <Kpis items={[
            { label: "FY posted (demo)", value: inr(fyTotal), detail: "Posted only; pending excluded" },
            { label: "Largest gift (demo)", value: inr(2500000), detail: "Organisation · Infrastructure" },
            { label: "Median gift (demo)", value: inr(105000), detail: "Across posted demo rows" },
            { label: "Pledge fulfilment", value: `${pct(800000, 2550000)}%`, detail: "Received vs pledged (demo)" },
          ]} />
          <Panel eyebrow="Illustrative" title="Giving by fund (demo values)" badge={<Badge tone="preview">Preview</Badge>}
            footer="Charts bind to the posted ledger in M2 with FY and fund filters plus CSV export.">
            {demoFunds.map((f) => (
              <div key={f.code} style={{ display: "grid", gridTemplateColumns: "220px 1fr 140px", gap: 12, alignItems: "center", padding: "10px 20px", borderBottom: "1px solid #ecece6", fontSize: 13 }}>
                <span><strong>{f.code}</strong> · {f.name}</span>
                <Bar valuePct={pct(f.fyReceivedInr, 6300000)} />
                <span style={{ textAlign: "right" }}>{inr(f.fyReceivedInr)}</span>
              </div>
            ))}
            {demoFunds.length === 0 && <EmptyState title="No fund data" body="Fund analytics appear once the M2 ledger holds posted transactions." />}
          </Panel>
        </>
      )}
    </div>
  );
}
