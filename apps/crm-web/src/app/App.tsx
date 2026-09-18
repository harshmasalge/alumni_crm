import { useState, useEffect, useCallback } from "react";
import { api, Constituent, Profile360, Person, AlumniProfile, EducationRecord, Affiliation, ContactMethod, Address } from "../api";
import { FundraisingPreview } from "../preview/Fundraising";
import { ImportsPreview, ReportsPreview } from "../preview/ImportsReports";
import { EngagementPreview } from "../preview/Engagement";
import { CommunicationsPreview } from "../preview/Communications";
import { IntegrationsPreview, AdminPreview } from "../preview/IntegrationsAdmin";

type ModuleState = "Live" | "Preview" | "Under development";

type NavItem = {
  label: string;
  state: ModuleState;
  description: string;
};

const navigation: NavItem[] = [
  { label: "Overview", state: "Live", description: "M0 product preview and delivery progress." },
  { label: "People", state: "Live", description: "Alumni and donor registry — connected to PostgreSQL backend." },
  { label: "Fundraising", state: "Preview", description: "Donation ledger and sample receipts arrive in M2." },
  { label: "Engagement", state: "Under development", description: "Events, attendance, chapters, and work queues arrive in M4." },
  { label: "Communications", state: "Under development", description: "Consent-aware campaigns and automation arrive in M6." },
  { label: "Reports", state: "Preview", description: "Migration workbench and standard reports arrive in M3." },
  { label: "Imports", state: "Preview", description: "Staged import/migration workbench arrives in M3." },
  { label: "Integrations", state: "Under development", description: "External services are enabled only after IITGN provides access." },
  { label: "Administration", state: "Under development", description: "Users, roles, permissions, audit, and system configuration." },
];

export function StatusBadge({ state }: { state: ModuleState }) {
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
            <strong>Alumni & Donor CRM</strong>
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
            <p className="eyebrow">IIT Gandhinagar · ARO & IAO</p>
            <h1>{active.label}</h1>
          </div>
          <div className="topbar__actions">
            <StatusBadge state={active.state} />
            <button className="quiet-button" type="button">Help & feedback</button>
          </div>
        </header>

        <section className="content" aria-live="polite">
          {active.label === "Overview" ? <Overview /> : active.label === "People" ? <People /> : active.label === "Fundraising" ? <FundraisingPreview /> : active.label === "Reports" ? <ReportsPreview /> : active.label === "Imports" ? <ImportsPreview /> : active.label === "Engagement" ? <EngagementPreview /> : active.label === "Communications" ? <CommunicationsPreview /> : active.label === "Integrations" ? <IntegrationsPreview /> : active.label === "Administration" ? <AdminPreview /> : <ModulePreview module={active} />}
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
        <div className="hero__meta"><span>Current checkpoint</span><strong>M1 in progress</strong></div>
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
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Academic profile</th><th>Location</th><th>Completeness</th></tr></thead><tbody><tr><td colSpan={4} style={{textAlign:"center",color:"#65737a"}}>Connect to API to load live data → <a href="#" onClick={(e)=>{e.preventDefault();(document.querySelector('[data-nav="People"]') as HTMLElement)?.click();}}>People</a></td></tr></tbody></table></div>
          <div className="panel__footer">Search, profile editing, affiliation history, permissions, and audit trail are the next operational slice.</div>
        </article>
        <article className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Delivery transparency</p><h3>Capability status</h3></div></div>
          <ul className="status-list">
            <li><StatusBadge state="Live" /><span>Professional application shell and product-status language</span></li>
            <li><StatusBadge state="Live" /><span>People registry with PostgreSQL persistence (M1)</span></li>
            <li><StatusBadge state="Preview" /><span>Fundraising and reporting information architecture</span></li>
            <li><StatusBadge state="Under development" /><span>Integrations, portal, and communication services</span></li>
          </ul>
          <div className="note"><strong>What happens next:</strong> M2 adds donation ledger, pledges, funds, and 80G workflow.</div>
        </article>
      </section>
    </>
  );
}

function People() {
  const [searchQuery, setSearchQuery] = useState("");
  const [rollNoQuery, setRollNoQuery] = useState("");
  const [results, setResults] = useState<Constituent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<Profile360 | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);

  const doSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.constituents.search({
        q: searchQuery || undefined,
        roll_no: rollNoQuery || undefined,
        kind: "PERSON",
        page,
        page_size: pageSize,
      });
      setResults(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, rollNoQuery, page, pageSize]);

  useEffect(() => {
    const timer = setTimeout(doSearch, 300);
    return () => clearTimeout(timer);
  }, [doSearch]);

  const handleProfileClick = async (constituent: Constituent) => {
    setProfileLoading(true);
    try {
      const profile = await api.constituents.getProfile360(constituent.id);
      setSelectedProfile(profile);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setProfileLoading(false);
    }
  };

  const formatDate = (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleDateString() : "—";

  const getAcademicSummary = (profile: AlumniProfile | null) => {
    if (!profile) return "No alumni profile";
    const parts = [];
    if (profile.year_of_graduation) parts.push(String(profile.year_of_graduation));
    if (profile.roll_no) parts.push(profile.roll_no);
    return parts.join(" · ") || "Alumnus";
  };

  const getLocation = (profile: Person | null, affiliations: Affiliation[]) => {
    const currentAff = affiliations.find(a => a.is_current);
    if (currentAff?.city && currentAff?.country) return `${currentAff.city}, ${currentAff.country}`;
    if (currentAff?.city) return currentAff.city;
    if (currentAff?.country) return currentAff.country;
    return "—";
  };

  if (selectedProfile) {
    return (
      <ProfileDetail
        profile={selectedProfile}
        onClose={() => setSelectedProfile(null)}
        loading={profileLoading}
      />
    );
  }

  return (
    <section className="module-preview">
      <div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:16,alignItems:"flexEnd"}}>
        <div style={{flex:1,minWidth:280}}>
          <label style={{display:"block",fontSize:11,color:"#68777e",marginBottom:4}}>Search by name (partial)</label>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            placeholder="e.g., Aarav, Patel, Mehta"
            style={{width:"100%",padding:"8px 12px",fontSize:14,border:"1px solid #cfd4d2",borderRadius:4}}
          />
        </div>
        <div style={{minWidth:200}}>
          <label style={{display:"block",fontSize:11,color:"#68777e",marginBottom:4}}>Exact Roll Number</label>
          <input
            type="text"
            value={rollNoQuery}
            onChange={(e) => { setRollNoQuery(e.target.value.toUpperCase()); setPage(1); }}
            placeholder="e.g., 2020101001"
            style={{width:"100%",padding:"8px 12px",fontSize:14,border:"1px solid #cfd4d2",borderRadius:4}}
          />
        </div>
        <button
          onClick={doSearch}
          disabled={loading}
          style={{padding:"8px 16px",fontSize:14,background:"#1f2d38",color:"white",border:"none",borderRadius:4,cursor:loading?"not-allowed":"pointer",opacity:loading?0.7:1}}
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </div>

      {error && <div className="note" style={{background:"#fdeaea",borderLeftColor:"#c0392b",color:"#c0392b",marginBottom:16}}>{error}</div>}

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Roll No.</th>
                <th>Academic</th>
                <th>Location</th>
                <th>Completeness</th>
                <th>Last Update</th>
              </tr>
            </thead>
            <tbody>
              {results.length === 0 && !loading ? (
                <tr><td colSpan={6} style={{textAlign:"center",color:"#65737a",padding:32}}>No results. Try a name search or exact Roll Number.</td></tr>
              ) : (
                results.map((c) => (
                  <tr key={c.id} onClick={() => handleProfileClick(c)} style={{cursor:"pointer"}}>
                    <td><strong>{c.display_name}</strong></td>
                    <td>{c.kind === "PERSON" ? "—" : c.normalised_display_name}</td>
                    <td>{getAcademicSummary(null)}</td>
                    <td>{getLocation(null, [])}</td>
                    <td>{c.profile_completeness_percent}%</td>
                    <td>{formatDate(c.last_substantive_profile_update_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="panel__footer" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span>Showing {results.length} of {total} constituent{total !== 1 ? "s" : ""}</span>
            <div style={{display:"flex",gap:8}}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="quiet-button">Previous</button>
              <button onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total} className="quiet-button">Next</button>
            </div>
          </div>
        )}
      </div>

      <div className="note" style={{marginTop:16}}>
        <strong>M1 Live:</strong> This view queries the PostgreSQL-backed FastAPI at <code>{import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"}</code>.
        Exact Roll Number returns one record; name search uses partial matching. Click a row to open the 360° profile.
      </div>
    </section>
  );
}

function ProfileDetail({ profile, onClose, loading }: { profile: Profile360; onClose: () => void; loading: boolean }) {
  const { constituent, person, alumni_profile, education_records, affiliations, contact_methods, addresses, audit_events } = profile;

  const formatDate = (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleDateString() : "—";
  const formatDateTime = (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleString() : "—";

return (
    <section className="module-preview" style={{maxWidth:1000}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flexStart",marginBottom:16,gap:16,flexWrap:"wrap"}}>
        <div>
          <p className="eyebrow">360° Profile</p>
          <h2>{constituent.display_name}</h2>
          <div style={{display:"flex",gap:12,marginTop:8,flexWrap:"wrap"}}>
            <StatusBadge state="Live" />
            <span style={{fontSize:13,color:"#65737a"}}>Constituent ID: {constituent.id}</span>
            <span style={{fontSize:13,color:"#65737a"}}>Status: {constituent.status}</span>
            {alumni_profile && <span style={{fontSize:13,color:"#65737a"}}>Roll No: {alumni_profile.roll_no}</span>}
          </div>
        </div>
        <button onClick={onClose} className="quiet-button" style={{marginTop:8}}>← Back to list</button>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))",gap:16}}>
        <article className="panel">
          <div className="panel__heading"><h3>Identity & Contact</h3></div>
          <dl style={{margin:0,padding:16,display:"grid",gridTemplateColumns:"120px 1fr",gap:"8px 16px"}}>
            <dt>Full name</dt><dd>{person?.full_name || "—"}</dd>
            <dt>First name</dt><dd>{person?.first_name || "—"}</dd>
            <dt>Gender</dt><dd>{person?.gender || "—"}</dd>
            <dt>Date of birth</dt><dd>{formatDate(person?.date_of_birth || null)}</dd>
            <dt>Blood group</dt><dd>{person?.blood_group || "—"}</dd>
            <dt>Spouse</dt><dd>{person?.spouse_name || "—"}</dd>
            <dt>Status</dt><dd>{constituent.status}</dd>
            <dt>Completeness</dt><dd>{constituent.profile_completeness_percent}%</dd>
            <dt>Last substantive update</dt><dd>{formatDate(constituent.last_substantive_profile_update_at)}</dd>
          </dl>
        </article>

        {/* Alumni Profile */}
        {alumni_profile && (
          <article className="panel">
            <div className="panel__heading"><h3>Alumni Profile</h3></div>
            <dl style={{margin:0,padding:16,display:"grid",gridTemplateColumns:"140px 1fr",gap:"8px 16px"}}>
              <dt>Roll Number</dt><dd>{alumni_profile.roll_no}</dd>
              <dt>IITGN Email</dt><dd>{alumni_profile.iitgn_email || "—"}</dd>
              <dt>Year of graduation</dt><dd>{alumni_profile.year_of_graduation || "—"}</dd>
              <dt>Final CPI</dt><dd>{alumni_profile.final_cpi !== null ? String(alumni_profile.final_cpi) : "—"}</dd>
              <dt>Thesis title</dt><dd>{alumni_profile.thesis_title || "—"}</dd>
              <dt>Thesis defence</dt><dd>{formatDate(alumni_profile.thesis_defence_date)}</dd>
              <dt>JEE AIR</dt><dd>{alumni_profile.jee_air !== null ? String(alumni_profile.jee_air) : "—"}</dd>
              <dt>GATE AIR</dt><dd>{alumni_profile.gate_air !== null ? String(alumni_profile.gate_air) : "—"}</dd>
            </dl>
          </article>
        )}

        {/* Contact Methods */}
        <article className="panel">
          <div className="panel__heading"><h3>Contact Methods ({contact_methods.length})</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Type</th><th>Value</th><th>Primary</th><th>Verified</th><th>Active</th></tr></thead>
            <tbody>
              {contact_methods.map(cm => (
                <tr key={cm.id}>
                  <td>{cm.contact_type}</td>
                  <td>{cm.value}</td>
                  <td>{cm.is_primary ? "✓" : "—"}</td>
                  <td>{cm.is_verified ? "✓" : "—"}</td>
                  <td>{cm.is_active ? "✓" : "—"}</td>
                </tr>
              ))}
              {contact_methods.length === 0 && <tr><td colSpan={5} style={{textAlign:"center",color:"#65737a",padding:16}}>No contact methods</td></tr>}
            </tbody>
            </table>
          </div>
        </article>

        {/* Addresses */}
        <article className="panel">
          <div className="panel__heading"><h3>Addresses ({addresses.length})</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Type</th><th>Address</th><th>City</th><th>Country</th><th>Active</th></tr></thead>
            <tbody>
              {addresses.map(a => (
                <tr key={a.id}>
                  <td>{a.address_type}</td>
                  <td>{[a.line1, a.line2, a.line3].filter(Boolean).join(", ")}</td>
                  <td>{a.city || "—"}</td>
                  <td>{a.country || "—"}</td>
                  <td>{a.is_active ? "✓" : "—"}</td>
                </tr>
              ))}
              {addresses.length === 0 && <tr><td colSpan={5} style={{textAlign:"center",color:"#65737a",padding:16}}>No addresses</td></tr>}
            </tbody>
            </table>
          </div>
        </article>

        {/* Education Records */}
        <article className="panel">
          <div className="panel__heading"><h3>Education History ({education_records.length})</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Stage</th><th>Qualification</th><th>Institution</th><th>Field</th><th>Years</th><th>Verified</th></tr></thead>
            <tbody>
              {education_records.map(er => (
                <tr key={er.id}>
                  <td>{er.education_stage}</td>
                  <td>{er.qualification}</td>
                  <td>{er.institution_name}</td>
                  <td>{er.field_of_study || "—"}</td>
                  <td>{er.start_year || "—"} – {er.completion_year || "—"}</td>
                  <td>{er.is_verified ? "✓" : "—"}</td>
                </tr>
              ))}
              {education_records.length === 0 && <tr><td colSpan={6} style={{textAlign:"center",color:"#65737a",padding:16}}>No education records</td></tr>}
            </tbody>
            </table>
          </div>
        </article>

        {/* Affiliations */}
        <article className="panel">
          <div className="panel__heading"><h3>Career History ({affiliations.length})</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Organisation</th><th>Designation</th><th>Type</th><th>Location</th><th>Period</th><th>Current</th></tr></thead>
            <tbody>
              {affiliations.map(af => (
                <tr key={af.id}>
                  <td>{af.organisation_name_raw || "—"}</td>
                  <td>{af.designation || "—"}</td>
                  <td>{af.affiliation_type || "—"}</td>
                  <td>{[af.city, af.state, af.country].filter(Boolean).join(", ") || "—"}</td>
                  <td>{formatDate(af.start_date)} – {formatDate(af.end_date) || "Present"}</td>
                  <td>{af.is_current ? "✓ Current" : "Past"}</td>
                </tr>
              ))}
              {affiliations.length === 0 && <tr><td colSpan={6} style={{textAlign:"center",color:"#65737a",padding:16}}>No affiliations</td></tr>}
            </tbody>
            </table>
          </div>
        </article>

        {/* Audit Events */}
        <article className="panel" style={{gridColumn:"1/-1"}}>
          <div className="panel__heading"><h3>Audit Trail ({audit_events.length})</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Time</th><th>Actor</th><th>Entity</th><th>Action</th><th>IP</th></tr></thead>
            <tbody>
              {audit_events.slice(0, 20).map(ae => (
                <tr key={ae.id}>
                  <td>{formatDateTime(ae.created_at)}</td>
                  <td>{ae.actor_type} ({ae.actor_id?.slice(0,8) || "—"})</td>
                  <td>{ae.entity_type} ({ae.entity_id.slice(0,8)})</td>
                  <td>{ae.action}</td>
                  <td>{ae.ip_address || "—"}</td>
                </tr>
              ))}
              {audit_events.length === 0 && <tr><td colSpan={5} style={{textAlign:"center",color:"#65737a",padding:16}}>No audit events</td></tr>}
              {audit_events.length > 20 && <tr><td colSpan={5} style={{textAlign:"center",color:"#65737a",padding:8}}>Showing 20 of {audit_events.length} events</td></tr>}
            </tbody>
            </table>
          </div>
        </article>
      </div>
    </section>
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