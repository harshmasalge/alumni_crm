/**
 * Phase 2 — Engagement preview (M4 scope): events dashboard/list/detail,
 * registration & attendance, chapters, engagement timeline, staff queues,
 * follow-ups and tasks. Fictional data; no real RSVPs or check-ins.
 */
import { useState } from "react";
import { demoEvents, demoChapters, demoTasks, inr, pct } from "./demoData";
import { PreviewBanner, PageHead, Kpis, Tabs, Panel, Bar, PreviewAction, Timeline, EmptyState } from "./ui";

function Badge({ tone, children }: { tone: "preview" | "dev"; children: string }) {
  return <span className={tone === "preview" ? "status status--preview" : "status status--under-development"}>{children}</span>;
}

const TABS = ["Dashboard", "Events", "Chapters", "Staff queues", "Timeline"] as const;
type Tab = (typeof TABS)[number];

const TIMELINE = [
  { time: "2026-09-12", title: "Webinar attended (demo)", body: "Careers in Climate Tech — 301 attendees, recording link queued (mock)." },
  { time: "2026-08-14", title: "Donation posted (demo)", body: "₹5,00,000 to Student Scholarship Endowment; thank-you call queued." },
  { time: "2026-08-02", title: "Employment verified (demo)", body: "Affiliation confirmed by data steward; previous role kept as history." },
  { time: "2026-07-19", title: "Chapter mixer attended (demo)", body: "Mumbai Chapter Monsoon Mixer — checked in 18:42, feedback 4/5." },
];

export function EngagementPreview() {
  const [tab, setTab] = useState<Tab>("Dashboard");
  const [eventCode, setEventCode] = useState<string>(demoEvents[0].code);
  const [queue, setQueue] = useState<string>("All");
  const event = demoEvents.find((e) => e.code === eventCode) ?? demoEvents[0];
  const tasks = demoTasks.filter((t) => queue === "All" || t.queue === queue);

  const upcoming = demoEvents.filter((e) => e.status === "Upcoming" || e.status === "Registrations open");
  const totalRegistered = demoEvents.reduce((s, e) => s + e.registered, 0);

  return (
    <div>
      <PageHead
        eyebrow="M4 · Engagement"
        title="Engagement"
        blurb="Events, attendance, chapters, relationship timelines, and staff work queues as designed for M4. Registrations and check-ins are simulated here."
        badge={<Badge tone="dev">Under development</Badge>}
      />
      <PreviewBanner
        what="Events, chapters, tasks, and timelines use fictional fixtures."
        needs="M4 events/attendance/chapter APIs, check-in flow, queue assignment, and engagement history."
      />
      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === "Dashboard" && (
        <>
          <Kpis items={[
            { label: "Upcoming events (demo)", value: String(upcoming.length), detail: `${totalRegistered.toLocaleString("en-IN")} total registrations` },
            { label: "Active chapters", value: String(demoChapters.filter((c) => c.health === "Active").length), detail: `of ${demoChapters.length} chapters tracked` },
            { label: "Open staff tasks", value: String(demoTasks.filter((t) => t.status !== "Waiting on donor").length), detail: "Across 4 queues" },
            { label: "Chapters needing attention", value: String(demoChapters.filter((c) => c.health !== "Active").length), detail: "Ownership or recency gaps" },
          ]} />
          <div className="two-column">
            <Panel eyebrow="Next up" title="Upcoming events" badge={<Badge tone="dev">Under development</Badge>}
              footer="Registration pages, guest allowances, and waitlists are M4 workflows.">
              <div className="table-wrap"><table><thead><tr><th>Event</th><th>Date</th><th>Fill</th><th>Status</th></tr></thead>
                <tbody>{upcoming.map((e) => (
                  <tr key={e.code}><td><strong>{e.name}</strong><br /><span style={{ color: "#68777e", fontSize: 12 }}>{e.city} · {e.type}</span></td>
                    <td>{e.date}</td><td><Bar valuePct={pct(e.registered, e.capacity)} /></td><td>{e.status}</td></tr>
                ))}</tbody></table></div>
            </Panel>
            <Panel eyebrow="Work allocation" title="Staff queues" badge={<Badge tone="dev">Under development</Badge>}
              footer="Queues assign by role and chapter ownership; every touch is logged to the engagement timeline.">
              <ul className="status-list">
                <li><span className="status status--under-development">Follow-ups</span><span>2 open · oldest due 2026-09-22 (demo)</span></li>
                <li><span className="status status--under-development">Verification</span><span>1 in progress · 14 employment records (demo)</span></li>
                <li><span className="status status--under-development">Stewardship</span><span>1 open · first-gift thank-you calls (demo)</span></li>
                <li><span className="status status--under-development">Data quality</span><span>1 open · 23 duplicate candidates (demo)</span></li>
              </ul>
            </Panel>
          </div>
        </>
      )}

      {tab === "Events" && (
        <div className="two-column">
          <Panel eyebrow="Event list" title={`Events (${demoEvents.length})`} badge={<Badge tone="dev">Under development</Badge>}>
            {demoEvents.map((e) => (
              <button key={e.code} type="button" onClick={() => setEventCode(e.code)}
                style={{ display: "block", width: "100%", textAlign: "left", background: e.code === eventCode ? "#faf8f2" : "#fff", border: 0, borderBottom: "1px solid #ecece6", padding: "12px 20px", cursor: "pointer" }}>
                <strong style={{ fontSize: 13 }}>{e.name}</strong>
                <span style={{ display: "block", fontSize: 12, color: "#68777e" }}>{e.code} · {e.date} · {e.city} · {e.status}</span>
              </button>
            ))}
          </Panel>
          <Panel eyebrow={`Event detail · ${event.code}`} title={event.name} badge={<Badge tone="dev">Under development</Badge>}
            footer={<span><PreviewAction label="Register (preview)" explain="M4 validates capacity, guest policy, and consent before confirming a registration with a reference code." /> <PreviewAction label="Check in (preview)" explain="M4 check-in records attendance time, mode (onsite/online), and staff owner for reporting." /></span>}>
            <dl style={{ margin: 0, padding: "16px 20px", display: "grid", gridTemplateColumns: "150px 1fr", gap: "6px 16px", fontSize: 13 }}>
              <dt>Type</dt><dd>{event.type}</dd>
              <dt>Date / city</dt><dd>{event.date} · {event.city}</dd>
              <dt>Capacity</dt><dd>{event.registered.toLocaleString("en-IN")} registered of {event.capacity.toLocaleString("en-IN")}</dd>
              <dt>Attendance</dt><dd>{event.status === "Completed" ? `${event.attended} attended (${pct(event.attended, event.registered)}% of registered)` : "Recorded at check-in (M4)"}</dd>
              <dt>Status</dt><dd>{event.status}</dd>
            </dl>
            <div style={{ padding: "0 20px 8px" }}><Bar valuePct={pct(event.registered, event.capacity)} /></div>
            <div className="table-wrap"><table><thead><tr><th>Participant (demo)</th><th>Batch</th><th>RSVP</th><th>Attendance</th></tr></thead>
              <tbody>
                <tr><td><strong>N. Rao (fictional)</strong></td><td>2018</td><td>Confirmed</td><td>{event.status === "Completed" ? "Checked in" : "—"}</td></tr>
                <tr><td><strong>D. Solanki (fictional)</strong></td><td>2020</td><td>Confirmed +1 guest</td><td>{event.status === "Completed" ? "Checked in" : "—"}</td></tr>
                <tr><td><strong>I. Kulkarni (fictional)</strong></td><td>2021</td><td>Waitlisted</td><td>—</td></tr>
              </tbody></table></div>
            <div className="note"><strong>Performance summary (M4):</strong> registration fill, attendance rate, no-show rate, and per-chapter comparison generate automatically after check-in closes.</div>
          </Panel>
        </div>
      )}

      {tab === "Chapters" && (
        <Panel eyebrow="Groups" title={`Chapters (${demoChapters.length})`} badge={<Badge tone="dev">Under development</Badge>}
          footer="Chapter detail pages in M4 show members, leads, event history, and the engagement timeline per chapter.">
          <div className="table-wrap"><table><thead><tr><th>Chapter</th><th>Region</th><th>Members</th><th>Lead / owner</th><th>Last activity</th><th>Health</th><th>Steward</th></tr></thead>
            <tbody>{demoChapters.map((c) => (
              <tr key={c.name}><td><strong>{c.name}</strong></td><td>{c.region}</td><td>{c.members.toLocaleString("en-IN")}</td>
                <td style={{ color: "#52616a" }}>{c.lead}</td><td>{c.lastActivity}</td><td>{c.health}</td>
                <td><PreviewAction label="Assign owner (preview)" explain="M4 assigns a staff owner per chapter; unassigned chapters raise a queue task automatically." /></td></tr>
            ))}</tbody></table></div>
        </Panel>
      )}

      {tab === "Staff queues" && (
        <Panel eyebrow="Follow-ups & tasks" title={`Staff queues (${tasks.length} shown)`} badge={<Badge tone="dev">Under development</Badge>}
          footer={<span><label style={{ fontSize: 12, color: "#68777e" }}>Queue&nbsp;</label><select value={queue} onChange={(e) => setQueue(e.target.value)} style={{ padding: "6px 10px", fontSize: 13 }}>
            {["All", "Follow-ups", "Verification", "Stewardship", "Data quality"].map((q) => <option key={q}>{q}</option>)}
          </select></span>}>
          <div className="table-wrap"><table><thead><tr><th>Task</th><th>Queue</th><th>Owner</th><th>Due</th><th>Priority</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{tasks.map((t) => (
              <tr key={t.id}><td><strong>{t.title}</strong><br /><span style={{ color: "#68777e", fontSize: 12 }}>{t.id}</span></td>
                <td>{t.queue}</td><td>{t.owner}</td><td>{t.due}</td><td>{t.priority}</td><td>{t.status}</td>
                <td><PreviewAction label="Take up (preview)" explain="M4 assigns the task, sets a due date, and logs every state change to the audit trail." /></td></tr>
            ))}</tbody></table></div>
          {tasks.length === 0 && <EmptyState title="Queue clear" body="No tasks in this queue. New verification, stewardship, and data-quality items route here automatically in M4." />}
        </Panel>
      )}

      {tab === "Timeline" && (
        <Panel eyebrow="Relationship view" title="Engagement history (demo constituent)" badge={<Badge tone="dev">Under development</Badge>}
          footer={`Lifetime demo giving: ${inr(625000)} · last gift 2026-08-14 · preferred channel: email (mock consent).`}>
          <Timeline items={TIMELINE} />
        </Panel>
      )}
    </div>
  );
}
