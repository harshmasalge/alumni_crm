import { useState } from "react";

type ModuleState = "Live" | "Preview" | "Under development";

type NavItem = {
  label: string;
  state: ModuleState;
  description: string;
};

const navigation: NavItem[] = [
  { label: "Overview", state: "Live", description: "M0 product preview and delivery progress." },
  { label: "People", state: "Preview", description: "Alumni and donor registry becomes operational in M1." },
  { label: "Fundraising", state: "Preview", description: "Donation ledger and sample receipts arrive in M2." },
  { label: "Engagement", state: "Under development", description: "Events, attendance, chapters, and work queues arrive in M4." },
  { label: "Communications", state: "Under development", description: "Consent-aware campaigns and automation arrive in M6." },
  { label: "Reports", state: "Preview", description: "Migration workbench and standard reports arrive in M3." },
  { label: "Integrations", state: "Under development", description: "External services are enabled only after IITGN provides access." },
];

const people = [
  ["Aarav Mehta", "BTech · Computer Science · 2020", "Bengaluru, India", "82%"],
  ["Nandini Rao", "MTech · Electrical Engineering · 2018", "Pune, India", "76%"],
  ["Rohan Patel", "PhD · Physics · 2016", "Boston, USA", "91%"],
];

function StatusBadge({ state }: { state: ModuleState }) {
  return <span className={`status status--${state.toLowerCase().replaceAll(" ", "-")}`}>{state}</span>;
}

export function App() {
  const [active, setActive] = useState<NavItem>(navigation[0]);

  return (
    <div className="application-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__mark">IITGN</div>
          <div>
            <strong>Alumni &amp; Donor CRM</strong>
            <span>Internal preview</span>
          </div>
        </div>
        <nav aria-label="Primary navigation">
          <p className="navigation-label">Workspace</p>
          {navigation.map((item) => (
            <button
              className={`navigation-item ${active.label === item.label ? "navigation-item--active" : ""}`}
              key={item.label}
              onClick={() => setActive(item)}
              type="button"
            >
              <span>{item.label}</span>
              <span className="navigation-item__dot" aria-hidden="true" />
            </button>
          ))}
        </nav>
        <div className="sidebar__footer">
          <span className="environment-label">DEMO DATA</span>
          <p>Fictional records only. No external service is connected.</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">IIT Gandhinagar · ARO &amp; IAO</p>
            <h1>{active.label}</h1>
          </div>
          <div className="topbar__actions">
            <StatusBadge state={active.state} />
            <button className="quiet-button" type="button">Help &amp; feedback</button>
          </div>
        </header>

        <section className="content" aria-live="polite">
          {active.label === "Overview" ? <Overview /> : <ModulePreview module={active} />}
        </section>
      </main>
    </div>
  );
}

function Overview() {
  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">M0 · Project foundation</p>
          <h2>A trusted relationship system, built in visible steps.</h2>
          <p>Each release leaves behind an independently useful CRM capability. This preview shows the intended staff experience while persistent data services are being developed.</p>
        </div>
        <div className="hero__meta"><span>Current checkpoint</span><strong>M0 in progress</strong></div>
      </section>

      <section className="metric-grid" aria-label="Preview metrics">
        <Metric label="Constituents" value="6,100" detail="Representative demo value" />
        <Metric label="Profile completeness" value="78%" detail="M1 calculation planned" />
        <Metric label="Donations this FY" value="₹—" detail="M2 ledger under development" />
        <Metric label="Upcoming events" value="—" detail="M4 engagement workspace" />
      </section>

      <section className="two-column">
        <article className="panel">
          <div className="panel__heading"><div><p className="eyebrow">M1 preview</p><h3>People needing attention</h3></div><StatusBadge state="Preview" /></div>
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Academic profile</th><th>Location</th><th>Completeness</th></tr></thead><tbody>{people.map((person) => <tr key={person[0]}>{person.map((value) => <td key={value}>{value}</td>)}</tr>)}</tbody></table></div>
          <div className="panel__footer">Search, profile editing, affiliation history, permissions, and audit trail are the next operational slice.</div>
        </article>
        <article className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Delivery transparency</p><h3>Capability status</h3></div></div>
          <ul className="status-list">
            <li><StatusBadge state="Live" /><span>Professional application shell and product-status language</span></li>
            <li><StatusBadge state="Preview" /><span>People, fundraising, and reporting information architecture</span></li>
            <li><StatusBadge state="Under development" /><span>Persistent registry, integrations, portal, and communication services</span></li>
          </ul>
          <div className="note"><strong>What happens next:</strong> M1 replaces the people preview with a permissioned, auditable PostgreSQL-backed registry.</div>
        </article>
      </section>
    </>
  );
}

function ModulePreview({ module }: { module: NavItem }) {
  return (
    <section className="module-preview">
      <p className="eyebrow">Delivery roadmap</p>
      <h2>{module.label}</h2>
      <StatusBadge state={module.state} />
      <p>{module.description}</p>
      <div className="note"><strong>Transparent status:</strong> This area is included so stakeholders can see the final information architecture early. Operational actions are enabled only after their API, data, permissions, audit behaviour, and tests are complete.</div>
    </section>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <article className="metric"><p>{label}</p><strong>{value}</strong><span>{detail}</span></article>;
}
