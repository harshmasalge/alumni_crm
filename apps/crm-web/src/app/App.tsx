import { useState, useEffect, useCallback } from "react";
import type { ReactNode } from "react";
import { api, getToken, setToken, ApiError, AuthUser, Constituent, Profile360, Person, AlumniProfile, EducationRecord, Affiliation, ContactMethod, Address, OrganisationSearchResult } from "../api";
import { FundraisingPreview } from "../preview/Fundraising";
import { ImportsPreview, ReportsPreview } from "../preview/ImportsReports";
import { EngagementPreview } from "../preview/Engagement";
import { CommunicationsPreview } from "../preview/Communications";
import { IntegrationsPreview } from "../preview/IntegrationsAdmin";
import { Admin } from "./Admin";
import { AuthPanel } from "./AuthPanel";

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
  { label: "Administration", state: "Live", description: "Users, roles, permissions, and audit log — served by the backend, admin-gated." },
];

export function StatusBadge({ state }: { state: ModuleState }) {
  return <span className={`status status--${state.toLowerCase().replaceAll(" ", "-")}`}>{state}</span>;
}

type Route = { view: string; profileId?: string; stale?: boolean };

const viewSlugs: Record<string, string> = {
  Overview: "",
  People: "people",
  Fundraising: "fundraising",
  Engagement: "engagement",
  Communications: "communications",
  Reports: "reports",
  Imports: "imports",
  Integrations: "integrations",
  Administration: "administration",
};

function parseHash(): Route {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const qIndex = raw.indexOf("?");
  const path = qIndex === -1 ? raw : raw.slice(0, qIndex);
  const params = new URLSearchParams(qIndex === -1 ? "" : raw.slice(qIndex + 1));
  if (path.startsWith("people/")) {
    const id = path.slice("people/".length);
    return { view: "People", profileId: id || undefined };
  }
  if (path === "people") {
    return { view: "People", stale: params.get("stale") === "1" };
  }
  const view = Object.keys(viewSlugs).find((label) => viewSlugs[label] === path);
  return { view: view ?? "Overview" };
}

function hashFor(route: Route): string {
  if (route.view === "People" && route.profileId) return `#/people/${route.profileId}`;
  if (route.view === "People") return route.stale ? "#/people?stale=1" : "#/people";
  const slug = viewSlugs[route.view] ?? "";
  return slug ? `#/${slug}` : "#/";
}

function navigate(route: Route) {
  const h = hashFor(route);
  if (window.location.hash === h) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    window.location.hash = h;
  }
}

export function App() {
  const [route, setRoute] = useState<Route>(() => (typeof window === "undefined" ? { view: "Overview" } : parseHash()));
  const [peopleStaleSignal, setPeopleStaleSignal] = useState(() => (route.stale ? 1 : 0));
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  const checkAuth = useCallback(() => {
    setAuthChecked(false);
    if (!getToken()) { setUser(null); setAuthChecked(true); return; }
    api.auth.me()
      .then((u) => setUser(u))
      .catch(() => { setToken(null); setUser(null); })
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => { checkAuth(); }, [checkAuth]);

  useEffect(() => {
    const onHash = () => {
      const r = parseHash();
      setRoute(r);
      if (r.view === "People" && r.stale) setPeopleStaleSignal((n) => n + 1);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const active = navigation.find((n) => n.label === route.view) ?? navigation[0];

  const goToStalePeople = useCallback(() => {
    navigate({ view: "People", stale: true });
  }, []);

  if (!authChecked) {
    return <section className="module-preview" style={{ maxWidth: 560, margin: "48px auto" }}><p>Loading…</p></section>;
  }

  if (!user) {
    return (
      <div className="application-shell" style={{ display: "block" }}>
        <main className="main-content">
          <section className="content" style={{ maxWidth: 560, margin: "48px auto" }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
              <div className="brand__mark">IITGN</div>
              <div>
                <strong>Alumni &amp; Donor CRM</strong>
                <p className="eyebrow">IIT Gandhinagar · ARO &amp; IAO</p>
              </div>
            </div>
            <AuthPanel user={null} onAuthChange={checkAuth} />
            <div className="note">Staff only. Every page behind this screen requires sign-in; permissions are enforced server-side.</div>
          </section>
        </main>
      </div>
    );
  }

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
              onClick={() => navigate({ view: item.label })}
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
            <span style={{ fontSize: 13, color: "#65737a" }}>{user.full_name} · {user.roles.join(", ") || "staff"}</span>
            <button className="quiet-button" type="button" onClick={() => { api.auth.logout(); checkAuth(); }}>Sign out</button>
            <button className="quiet-button" type="button">Help &amp; feedback</button>
          </div>
        </header>

        <section className="content" aria-live="polite">
          {active.label === "Overview" ? <Overview onShowStale={goToStalePeople} /> : active.label === "People" ? <People staleSignal={peopleStaleSignal} profileId={route.view === "People" ? route.profileId : undefined} onOpenProfile={(id) => navigate({ view: "People", profileId: id })} onAuthChange={checkAuth} user={user} /> : active.label === "Fundraising" ? <FundraisingPreview /> : active.label === "Reports" ? <ReportsPreview /> : active.label === "Imports" ? <ImportsPreview /> : active.label === "Engagement" ? <EngagementPreview /> : active.label === "Communications" ? <CommunicationsPreview /> : active.label === "Integrations" ? <IntegrationsPreview /> : active.label === "Administration" ? <Admin user={user} /> : <ModulePreview module={active} />}
        </section>
      </main>
    </div>
  );
}

function Overview({ onShowStale }: { onShowStale: () => void }) {
  const [staleCount, setStaleCount] = useState<number | null>(null);
  const [staleError, setStaleError] = useState<string | null>(null);

  useEffect(() => {
    api.constituents.getStaleCount(365)
      .then((d) => { setStaleCount(d.count); setStaleError(null); })
      .catch((e) => setStaleError(e instanceof Error ? e.message : "Stale count unavailable"));
  }, []);

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
        <Metric label="Stale profiles (>365d)" value={staleCount === null ? "…" : String(staleCount)} detail={staleError ?? "Live M1 query"} />
        <Metric label="Upcoming events" value="—" detail="M4 engagement workspace" />
      </section>

      <section className="two-column">
        <article className="panel">
          <div className="panel__heading"><div><p className="eyebrow">M1 live</p><h3>People needing attention</h3></div><StatusBadge state="Live" /></div>
          <div className="table-wrap"><table><thead><tr><th>Name</th><th>Academic profile</th><th>Location</th><th>Completeness</th></tr></thead><tbody><tr><td colSpan={4} style={{textAlign:"center",color:"#65737a"}}>{staleCount === null ? "Sign in via People to load the live stale-profile count." : `${staleCount} alumni with no substantive update for >365 days.`} <button type="button" className="quiet-button" onClick={onShowStale}>Open stale list →</button></td></tr></tbody></table></div>
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

function People({ staleSignal, profileId, onOpenProfile, onAuthChange, user }: { staleSignal: number; profileId?: string; onOpenProfile: (id: string) => void; onAuthChange: () => void; user: AuthUser | null }) {
  const canWrite = !!user && (user.is_superuser || user.permissions.includes("constituents.write"));
  const [searchQuery, setSearchQuery] = useState("");
  const [rollNoQuery, setRollNoQuery] = useState("");
  const [orgQuery, setOrgQuery] = useState("");
  const [mode, setMode] = useState<"people" | "org">("people");
  const [staleOnly, setStaleOnly] = useState(false);
  const [thresholdDays, setThresholdDays] = useState(365);
  const [results, setResults] = useState<Constituent[]>([]);
  const [orgResults, setOrgResults] = useState<OrganisationSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<Profile360 | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    if (staleSignal > 0) {
      setMode("people");
      setStaleOnly(true);
      setPage(1);
    }
  }, [staleSignal]);

  const doSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (mode === "org") {
        if (!orgQuery.trim()) { setOrgResults([]); setTotal(0); return; }
        const data = await api.constituents.searchOrganisations({ q: orgQuery, page, page_size: pageSize });
        setOrgResults(data.items);
        setTotal(data.total);
      } else if (staleOnly) {
        const data = await api.constituents.getStaleProfiles({ threshold_days: thresholdDays, page, page_size: pageSize });
        setResults(data.items);
        setTotal(data.total);
      } else {
        const data = await api.constituents.search({
          q: searchQuery || undefined,
          roll_no: rollNoQuery || undefined,
          kind: "PERSON",
          page,
          page_size: pageSize,
        });
        setResults(data.items);
        setTotal(data.total);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("Session expired. Signing out — please sign in again.");
        onAuthChange();
      } else {
        setError(e instanceof Error ? e.message : "Search failed");
      }
      setResults([]); setOrgResults([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, rollNoQuery, orgQuery, mode, staleOnly, thresholdDays, page, pageSize, onAuthChange]);

  useEffect(() => {
    const timer = setTimeout(doSearch, 300);
    return () => clearTimeout(timer);
  }, [doSearch]);

  const handleProfileClick = async (constituent: Constituent) => {
    onOpenProfile(constituent.id);
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

  // URL-driven sync: deep links open the profile; browser back/forward
  // moves between list and profile without losing history.
  useEffect(() => {
    if (profileId && profileId !== selectedProfile?.constituent.id) {
      setProfileLoading(true);
      api.constituents.getProfile360(profileId)
        .then(setSelectedProfile)
        .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
        .finally(() => setProfileLoading(false));
    } else if (!profileId && selectedProfile) {
      setSelectedProfile(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

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

  const reloadProfile = async (constituentId: string) => {
    setProfileLoading(true);
    try {
      const profile = await api.constituents.getProfile360(constituentId);
      setSelectedProfile(profile);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setProfileLoading(false);
    }
  };

  if (selectedProfile) {
    return (
      <ProfileDetail
        profile={selectedProfile}
        onChanged={() => reloadProfile(selectedProfile.constituent.id)}
        loading={profileLoading}
        canWrite={canWrite}
      />
    );
  }

  const openOrgProfile = async (constituentId: string) => {
    onOpenProfile(constituentId);
    setProfileLoading(true);
    try {
      const profile = await api.constituents.getProfile360(constituentId);
      setSelectedProfile(profile);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setProfileLoading(false);
    }
  };

  return (
    <section className="module-preview">
      <div style={{display:"flex",gap:8,marginBottom:16}}>
        <button type="button" className="quiet-button" disabled={mode === "people"} onClick={() => { setMode("people"); setPage(1); }}>People search</button>
        <button type="button" className="quiet-button" disabled={mode === "org"} onClick={() => { setMode("org"); setPage(1); }}>Organisation search</button>
        <label style={{display:"flex",gap:6,alignItems:"center",fontSize:13,color:"#4f5c62",marginLeft:8}}>
          <input type="checkbox" checked={staleOnly} disabled={mode !== "people"} onChange={(e) => { setStaleOnly(e.target.checked); setPage(1); }} />
          Stale only (&gt; <input type="number" value={thresholdDays} min={1} onChange={(e) => { setThresholdDays(Number(e.target.value) || 365); setPage(1); }} style={{width:64,padding:"4px 6px",fontSize:13}} /> days)
        </label>
      </div>

      {mode === "people" ? (
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
      ) : (
      <div style={{display:"flex",gap:12,flexWrap:"wrap",marginBottom:16,alignItems:"flexEnd"}}>
        <div style={{flex:1,minWidth:280}}>
          <label style={{display:"block",fontSize:11,color:"#68777e",marginBottom:4}}>Organisation name (searches current + past affiliations)</label>
          <input
            type="text"
            value={orgQuery}
            onChange={(e) => { setOrgQuery(e.target.value); setPage(1); }}
            placeholder="e.g., Google"
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
      )}

      {error && <div className="note" style={{background:"#fdeaea",borderLeftColor:"#c0392b",color:"#c0392b",marginBottom:16}}>{error}</div>}

      <div className="panel">
        <div className="table-wrap">
          {mode === "org" ? (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Roll No.</th>
                <th>Organisation</th>
                <th>Status</th>
                <th>Designation</th>
                <th>Period</th>
              </tr>
            </thead>
            <tbody>
              {orgResults.length === 0 && !loading ? (
                <tr><td colSpan={6} style={{textAlign:"center",color:"#65737a",padding:32}}>No matches. Organisation search covers current and past affiliations; each alumnus appears once.</td></tr>
              ) : (
                orgResults.map((o) => (
                  <tr key={o.constituent_id} onClick={() => openOrgProfile(o.constituent_id)} style={{cursor:"pointer"}}>
                    <td><strong>{o.display_name}</strong></td>
                    <td>{o.roll_no || "—"}</td>
                    <td>{o.organisation_name}</td>
                    <td>{o.affiliation_status}</td>
                    <td>{o.designation || "—"}</td>
                    <td>{formatDate(o.start_date)} – {o.end_date ? formatDate(o.end_date) : "Present"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          ) : (
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
                <tr><td colSpan={6} style={{textAlign:"center",color:"#65737a",padding:32}}>{staleOnly ? "No stale profiles on this page. The dashboard count and this list use the same server-side filter." : "No results. Try a name search or exact Roll Number."}</td></tr>
              ) : (
                results.map((c) => (
                  <tr key={c.id} onClick={() => handleProfileClick(c)} style={{cursor:"pointer"}}>
                    <td><strong>{c.display_name}</strong></td>
                    <td>{c.kind === "PERSON" ? "—" : c.normalised_display_name}</td>
                    <td>{getAcademicSummary(null)}</td>
                    <td>{getLocation(null, [])}</td>
                    <td>{c.profile_completeness_percent}%</td>
                    <td>{formatDate(c.last_substantive_profile_update_at)} ({freshnessLabel(c.days_since_profile_update)})</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          )}
        </div>
        {total > 0 && (
          <div className="panel__footer" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
            <span>Showing {mode === "org" ? orgResults.length : results.length} of {total} result{total !== 1 ? "s" : ""}{staleOnly && mode === "people" ? " (stale filter applied)" : ""}</span>
            <div style={{display:"flex",gap:8}}>
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="quiet-button">Previous</button>
              <button onClick={() => setPage(p => p + 1)} disabled={page * pageSize >= total} className="quiet-button">Next</button>
            </div>
          </div>
        )}
      </div>

      <div className="note" style={{marginTop:16}}>
        <strong>M1 Live:</strong> This view queries the PostgreSQL-backed FastAPI at <code>{import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"}</code>.
        Exact Roll Number returns one record; name search uses partial matching. Organisation search covers current and past affiliations with a visible status. Click a row to open the 360° profile. Restricted fields are withheld server-side when your role lacks permission.
      </div>
    </section>
  );
}

function freshnessLabel(days: number | null | undefined) {
  if (days === null || days === undefined) return "never updated";
  if (days === 0) return "updated today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

function ChildPanel({ title, count, columns, children, footnote, form }: {
  title: string; count: number; columns: string[]; children: ReactNode; footnote?: string; form?: ReactNode;
}) {
  return (
    <article className="panel">
      <div className="panel__heading"><h3>{title} ({count})</h3></div>
      <div className="table-wrap">
        <table><thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{children}</tbody></table>
      </div>
      {form}
      {footnote && <div className="panel__footer">{footnote}</div>}
    </article>
  );
}

type ChildFieldDef = { key: string; label: string; kind: "text" | "number" | "date" | "select" | "check"; options?: string[] };

function AddChildForm({ slug, constituentId, fields, buttonLabel, onAdded, canWrite, onDenied }: {
  slug: string; constituentId: string; fields: ChildFieldDef[]; buttonLabel: string; onAdded: () => void;
  canWrite: boolean; onDenied: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const set = (k: string, v: string | boolean) => setValues((s) => ({ ...s, [k]: v }));

  const submit = async () => {
    const payload: Record<string, unknown> = {};
    for (const f of fields) {
      const v = values[f.key];
      if (f.kind === "check") { payload[f.key] = v === true; continue; }
      if (v === undefined || v === "") continue;
      payload[f.key] = f.kind === "number" ? Number(v) : v;
    }
    setBusy(true); setMsg(null);
    try {
      await api.constituents.addChildRecord(constituentId, slug, payload);
      setValues({}); setOpen(false);
      onAdded();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not add record.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return <div style={{ padding: 12, borderTop: "1px solid #ecece6" }}><button type="button" className="quiet-button" onClick={() => canWrite ? setOpen(true) : onDenied()}>{buttonLabel}</button></div>;
  }
  return (
    <div style={{ padding: 12, borderTop: "1px solid #ecece6", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flexEnd" }}>
      {fields.map((f) => (
        <label key={f.key} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, color: "#68777e", minWidth: 140, flex: "1 1 140px" }}>
          {f.label}
          {f.kind === "select" ? (
            <select value={String(values[f.key] ?? "")} onChange={(e) => set(f.key, e.target.value)} style={{ padding: "6px 10px", fontSize: 13, border: "1px solid #cfd4d2", borderRadius: 4 }}>
              <option value="">—</option>
              {(f.options ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : f.kind === "check" ? (
            <input type="checkbox" checked={values[f.key] === true} onChange={(e) => set(f.key, e.target.checked)} />
          ) : (
            <input type={f.kind === "number" ? "number" : f.kind === "date" ? "date" : "text"}
              value={String(values[f.key] ?? "")} onChange={(e) => set(f.key, e.target.value)}
              style={{ padding: "6px 10px", fontSize: 13, border: "1px solid #cfd4d2", borderRadius: 4 }} />
          )}
        </label>
      ))}
      <button type="button" className="quiet-button" disabled={busy} onClick={submit}>Save</button>
      <button type="button" className="quiet-button" onClick={() => { setOpen(false); setMsg(null); }}>Cancel</button>
      {msg && <span style={{ fontSize: 13, color: "#c0392b" }}>{msg}</span>}
    </div>
  );
}

const CHILD_FORMS: Record<string, ChildFieldDef[]> = {
  "hostel-history": [
    { key: "hostel_name", label: "Hostel", kind: "text" },
    { key: "room_number", label: "Room", kind: "text" },
    { key: "academic_year", label: "Academic year", kind: "text" },
    { key: "semester", label: "Semester", kind: "text" },
  ],
  "academic-courses": [
    { key: "programme_level", label: "Level", kind: "select", options: ["UG", "PG", "PHD"] },
    { key: "course_code", label: "Course code", kind: "text" },
    { key: "course_name", label: "Course name", kind: "text" },
    { key: "credits", label: "Credits", kind: "number" },
    { key: "year", label: "Year", kind: "number" },
    { key: "semester", label: "Semester", kind: "text" },
    { key: "instructor", label: "Instructor", kind: "text" },
    { key: "grade", label: "Grade", kind: "text" },
  ],
  "semester-performance": [
    { key: "programme_level", label: "Level", kind: "select", options: ["UG", "PG", "PHD"] },
    { key: "year", label: "Year", kind: "number" },
    { key: "semester", label: "Semester", kind: "text" },
    { key: "spi", label: "SPI", kind: "number" },
    { key: "cpi", label: "CPI", kind: "number" },
  ],
  "gps-assignments": [
    { key: "year", label: "Year", kind: "number" },
    { key: "semester", label: "Semester", kind: "text" },
    { key: "coordinator_name", label: "Coordinator", kind: "text" },
  ],
  "awards": [
    { key: "award_type", label: "Type", kind: "text" },
    { key: "award_date", label: "Date", kind: "date" },
    { key: "agency", label: "Agency", kind: "text" },
    { key: "details", label: "Details", kind: "text" },
    { key: "academic_year", label: "Academic year", kind: "text" },
  ],
  "scholarships": [
    { key: "aid_type", label: "Type", kind: "text" },
    { key: "name", label: "Name", kind: "text" },
    { key: "year", label: "Year", kind: "number" },
    { key: "amount", label: "Amount", kind: "number" },
    { key: "remarks", label: "Remarks", kind: "text" },
  ],
  "internships": [
    { key: "organisation", label: "Organisation", kind: "text" },
    { key: "scope", label: "Scope", kind: "select", options: ["Domestic", "International"] },
    { key: "format", label: "Format", kind: "select", options: ["Online", "Offline", "Hybrid"] },
    { key: "duration_text", label: "Duration", kind: "text" },
    { key: "year", label: "Year", kind: "number" },
    { key: "funding_source", label: "Funding source", kind: "text" },
    { key: "funding_amount", label: "Funding amount", kind: "number" },
  ],
  "placements": [
    { key: "company", label: "Company", kind: "text" },
    { key: "sector", label: "Sector", kind: "text" },
    { key: "city", label: "City", kind: "text" },
    { key: "country", label: "Country", kind: "text" },
    { key: "ctc", label: "CTC", kind: "number" },
    { key: "date_of_joining", label: "Joined", kind: "date" },
    { key: "scope", label: "Scope", kind: "select", options: ["Domestic", "International"] },
  ],
  "startups": [
    { key: "startup_name", label: "Startup", kind: "text" },
    { key: "startup_type", label: "Type", kind: "text" },
    { key: "year", label: "Year", kind: "number" },
    { key: "sector", label: "Sector", kind: "text" },
    { key: "location", label: "Location", kind: "text" },
    { key: "website", label: "Website", kind: "text" },
    { key: "incubator", label: "Incubator", kind: "text" },
  ],
  "responsibilities": [
    { key: "title", label: "Title", kind: "text" },
    { key: "domain", label: "Domain", kind: "select", options: ["Council", "Club", "Event", "Other"] },
    { key: "academic_year", label: "Academic year", kind: "text" },
  ],
  "publications": [
    { key: "title", label: "Title", kind: "text" },
    { key: "doi", label: "DOI", kind: "text" },
    { key: "pub_date", label: "Date", kind: "date" },
  ],
  "overseas-exposure": [
    { key: "organisation", label: "Organisation", kind: "text" },
    { key: "year", label: "Year", kind: "number" },
    { key: "start_date", label: "From", kind: "date" },
    { key: "end_date", label: "To", kind: "date" },
    { key: "funding_details", label: "Funding", kind: "text" },
    { key: "funding_amount", label: "Amount", kind: "number" },
  ],
  "family-members": [
    { key: "name", label: "Name", kind: "text" },
    { key: "relation", label: "Relationship", kind: "text" },
    { key: "contact_number", label: "Contact", kind: "text" },
    { key: "email", label: "Email", kind: "text" },
  ],
  "ssac-records": [
    { key: "incident_details", label: "Incident details", kind: "text" },
    { key: "sanction_letter_date", label: "Sanction date", kind: "date" },
  ],
};

function emptyRow(cols: number, text: string) {
  return <tr><td colSpan={cols} style={{textAlign:"center",color:"#65737a",padding:16}}>{text}</td></tr>;
}

function initialsOf(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function avatarHue(name: string) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return h;
}

/** Profile photo placeholder: deterministic initials avatar.
 *  File serving for person.profile_photo_file_id is not built yet; when it
 *  lands, swap the placeholder for the served image here. */
function Avatar({ name, size }: { name: string; size?: number }) {
  const s = size ?? 112;
  return (
    <div title={name} aria-label={`Profile photo placeholder for ${name}`}
      style={{
        width: s, height: s, borderRadius: "50%",
        display: "grid", placeItems: "center",
        background: `hsl(${avatarHue(name)}, 28%, 32%)`,
        color: "#fff", fontSize: Math.round(s / 3), fontWeight: 700, letterSpacing: ".02em",
        flexShrink: 0,
      }}>
      {initialsOf(name)}
    </div>
  );
}

function ProfileDetail({ profile, onChanged, loading, canWrite }: { profile: Profile360; onChanged: () => void; loading: boolean; canWrite: boolean }) {
  // Default every collection to []: an older API build returns 200 OK with a
  // profile shape that lacks the newer keys, and that must render as empty
  // panels — never crash.
  const { constituent, person, alumni_profile, communication_preferences,
    education_records = [], affiliations = [], contact_methods = [], addresses = [],
    audit_events = [], hostel_history = [], academic_courses = [],
    semester_performance = [], gps_assignments = [], awards_recognition = [],
    scholarships_financial_aid = [], internships = [], placements = [], startups = [],
    ssac_records = [], positions_of_responsibility = [], publications = [],
    overseas_exposure = [], family_members = [], profile_photos = [] } = profile;
  const [eduForm, setEduForm] = useState({ qualification: "", institution_name: "", completion_year: "" });
  const [affForm, setAffForm] = useState({ organisation_name_raw: "", designation: "", city: "", country: "", start_date: "", is_current: true });
  const [writeMsg, setWriteMsg] = useState<string | null>(null);
  const [writing, setWriting] = useState(false);

  const denyWrite = () => {
    setWriteMsg("You don't have write permission for profiles. Ask an administrator for the staff role — this is enforced server-side, so the form will not open.");
  };
  const guardWrite = () => {
    if (!canWrite) { denyWrite(); return false; }
    return true;
  };

  const formatDate = (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleDateString() : "—";
  const formatDateTime = (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleString() : "—";

  const submitEducation = async () => {
    if (!guardWrite()) return;
    if (!eduForm.qualification.trim() || !eduForm.institution_name.trim()) {
      setWriteMsg("Qualification and institution are required.");
      return;
    }
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.addEducation(constituent.id, {
        education_stage: "POST_IITGN",
        qualification: eduForm.qualification.trim(),
        institution_name: eduForm.institution_name.trim(),
        completion_year: eduForm.completion_year ? Number(eduForm.completion_year) : undefined,
      });
      setEduForm({ qualification: "", institution_name: "", completion_year: "" });
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not add education record.");
    } finally {
      setWriting(false);
    }
  };

  const submitAffiliation = async () => {
    if (!guardWrite()) return;
    if (!affForm.organisation_name_raw.trim() && !affForm.designation.trim()) {
      setWriteMsg("Organisation or designation is required.");
      return;
    }
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.addAffiliation(constituent.id, {
        organisation_name_raw: affForm.organisation_name_raw.trim() || undefined,
        designation: affForm.designation.trim() || undefined,
        city: affForm.city.trim() || undefined,
        country: affForm.country.trim() || undefined,
        start_date: affForm.start_date || undefined,
        is_current: affForm.is_current,
      });
      setAffForm({ organisation_name_raw: "", designation: "", city: "", country: "", start_date: "", is_current: true });
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not add affiliation.");
    } finally {
      setWriting(false);
    }
  };

  const [editingIdentity, setEditingIdentity] = useState(false);
  const [identityForm, setIdentityForm] = useState({ first_name: "", full_name: "", gender: "", date_of_birth: "", blood_group: "", spouse_name: "", status: "", notes: "" });
  const startIdentityEdit = () => {
    setIdentityForm({
      first_name: person?.first_name || "",
      full_name: person?.full_name || "",
      gender: person?.gender || "",
      date_of_birth: person?.date_of_birth || "",
      blood_group: person?.blood_group || "",
      spouse_name: person?.spouse_name || "",
      status: constituent.status,
      notes: constituent.notes || "",
    });
    setEditingIdentity(true);
  };
  const submitIdentity = async () => {
    if (!guardWrite()) return;
    if (!identityForm.full_name.trim()) { setWriteMsg("Full name is required."); return; }
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.updatePerson(constituent.id, {
        first_name: identityForm.first_name.trim() || undefined,
        full_name: identityForm.full_name.trim(),
        gender: identityForm.gender || undefined,
        date_of_birth: identityForm.date_of_birth || undefined,
        blood_group: identityForm.blood_group || undefined,
        spouse_name: identityForm.spouse_name.trim() || undefined,
      });
      await api.constituents.updateConstituent(constituent.id, {
        status: identityForm.status || undefined,
        notes: identityForm.notes,
      });
      setEditingIdentity(false);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not save identity.");
    } finally {
      setWriting(false);
    }
  };

  const [editingAlumni, setEditingAlumni] = useState(false);
  const [alumniForm, setAlumniForm] = useState({ iitgn_email: "", year_of_graduation: "", final_cpi: "", thesis_title: "", thesis_defence_date: "", jee_air: "", gate_air: "", jam_air: "", csir_net_rank: "" });
  const startAlumniEdit = () => {
    if (!alumni_profile) return;
    setAlumniForm({
      iitgn_email: alumni_profile.iitgn_email || "",
      year_of_graduation: alumni_profile.year_of_graduation !== null ? String(alumni_profile.year_of_graduation) : "",
      final_cpi: alumni_profile.final_cpi !== null ? String(alumni_profile.final_cpi) : "",
      thesis_title: alumni_profile.thesis_title || "",
      thesis_defence_date: alumni_profile.thesis_defence_date || "",
      jee_air: alumni_profile.jee_air !== null ? String(alumni_profile.jee_air) : "",
      gate_air: alumni_profile.gate_air !== null ? String(alumni_profile.gate_air) : "",
      jam_air: alumni_profile.jam_air !== null ? String(alumni_profile.jam_air) : "",
      csir_net_rank: alumni_profile.csir_net_rank !== null ? String(alumni_profile.csir_net_rank) : "",
    });
    setEditingAlumni(true);
  };
  const numOrUndef = (v: string) => (v.trim() === "" ? undefined : Number(v));
  const submitAlumni = async () => {
    if (!guardWrite()) return;
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.updateAlumniProfile(constituent.id, {
        iitgn_email: alumniForm.iitgn_email.trim() || undefined,
        year_of_graduation: numOrUndef(alumniForm.year_of_graduation),
        final_cpi: numOrUndef(alumniForm.final_cpi),
        thesis_title: alumniForm.thesis_title.trim() || undefined,
        thesis_defence_date: alumniForm.thesis_defence_date || undefined,
        jee_air: numOrUndef(alumniForm.jee_air),
        gate_air: numOrUndef(alumniForm.gate_air),
        jam_air: numOrUndef(alumniForm.jam_air),
        csir_net_rank: numOrUndef(alumniForm.csir_net_rank),
      });
      setEditingAlumni(false);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not save alumni profile.");
    } finally {
      setWriting(false);
    }
  };

  const [contactForm, setContactForm] = useState({ contact_type: "EMAIL_PERSONAL", value: "" });
  const submitContact = async () => {
    if (!guardWrite()) return;
    if (!contactForm.value.trim()) { setWriteMsg("Contact value is required."); return; }
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.addContactMethod(constituent.id, {
        contact_type: contactForm.contact_type, value: contactForm.value.trim(),
      });
      setContactForm({ contact_type: "EMAIL_PERSONAL", value: "" });
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not add contact.");
    } finally {
      setWriting(false);
    }
  };

  const [addressForm, setAddressForm] = useState({ address_type: "CURRENT", line1: "", city: "", country: "" });
  const submitAddress = async () => {
    if (!guardWrite()) return;
    if (!addressForm.line1.trim()) { setWriteMsg("Address line 1 is required."); return; }
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.addAddress(constituent.id, {
        address_type: addressForm.address_type,
        line1: addressForm.line1.trim(),
        city: addressForm.city.trim() || undefined,
        country: addressForm.country.trim() || undefined,
      });
      setAddressForm({ address_type: "CURRENT", line1: "", city: "", country: "" });
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not add address.");
    } finally {
      setWriting(false);
    }
  };

  const [commsForm, setCommsForm] = useState({ email_opt_in: true, whatsapp_opt_in: true, sms_opt_in: true, global_dnc: false });
  const [commsInit, setCommsInit] = useState(false);
  if (!commsInit && communication_preferences) {
    setCommsForm({
      email_opt_in: communication_preferences.email_opt_in,
      whatsapp_opt_in: communication_preferences.whatsapp_opt_in,
      sms_opt_in: communication_preferences.sms_opt_in,
      global_dnc: communication_preferences.global_dnc,
    });
    setCommsInit(true);
  }
  const submitComms = async () => {
    if (!guardWrite()) return;
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.setCommunicationPreferences(constituent.id, commsForm);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not save preferences.");
    } finally {
      setWriting(false);
    }
  };

  const [photoIndex, setPhotoIndex] = useState(0);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const currentPhoto = profile_photos.length === 0
    ? null
    : profile_photos[Math.min(photoIndex, profile_photos.length - 1)];
  const currentPhotoId = currentPhoto?.id;

  useEffect(() => { setPhotoIndex(0); }, [constituent.id]);
  useEffect(() => {
    if (!currentPhotoId) { setPhotoUrl(null); return; }
    let dead = false;
    let url: string | null = null;
    const photo = profile_photos.find((p) => p.id === currentPhotoId) ?? null;
    if (!photo) { setPhotoUrl(null); return; }
    api.constituents.getPhotoContent(constituent.id, photo.id)
      .then((blob) => {
        if (dead) return;
        url = URL.createObjectURL(blob);
        setPhotoUrl(url);
      })
      .catch(() => { if (!dead) setPhotoUrl(null); });
    return () => { dead = true; if (url) URL.revokeObjectURL(url); };
  }, [constituent.id, currentPhotoId]);

  const uploadPhotos = async (files: FileList | null) => {
    if (!guardWrite() || !files || files.length === 0) return;
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.uploadPhotos(constituent.id, files);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not upload photos.");
    } finally {
      setWriting(false);
    }
  };

  const deletePhoto = async () => {
    if (!currentPhoto || !guardWrite()) return;
    if (!window.confirm(`Delete this photo (${currentPhoto.original_name})?`)) return;
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.deletePhoto(constituent.id, currentPhoto.id);
      setPhotoIndex(0);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not delete photo.");
    } finally {
      setWriting(false);
    }
  };

  const makePrimary = async () => {
    if (!currentPhoto || !guardWrite()) return;
    setWriting(true); setWriteMsg(null);
    try {
      await api.constituents.setPhotoPrimary(constituent.id, currentPhoto.id);
      onChanged();
    } catch (e) {
      setWriteMsg(e instanceof Error ? e.message : "Could not set primary photo.");
    } finally {
      setWriting(false);
    }
  };

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
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",gap:8,marginTop:8}}>
          {currentPhoto && photoUrl ? (
            <img src={photoUrl} alt={`Photo of ${constituent.display_name}`}
              style={{ width: 112, height: 112, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }} />
          ) : (
            <Avatar name={constituent.display_name} />
          )}
          {profile_photos.length > 1 && currentPhoto && (
            <div style={{display:"flex",gap:8,alignItems:"center",fontSize:13,color:"#4f5c62"}}>
              <button type="button" className="quiet-button" aria-label="Previous photo"
                onClick={() => setPhotoIndex((i) => (i - 1 + profile_photos.length) % profile_photos.length)}>‹</button>
              <span>{profile_photos.findIndex((p) => p.id === currentPhoto.id) + 1} / {profile_photos.length}{currentPhoto.is_primary ? " · primary" : ""}</span>
              <button type="button" className="quiet-button" aria-label="Next photo"
                onClick={() => setPhotoIndex((i) => (i + 1) % profile_photos.length)}>›</button>
            </div>
          )}
          {profile_photos.length === 1 && currentPhoto?.is_primary && (
            <span style={{fontSize:12,color:"#65737a"}}>primary photo</span>
          )}
          <div style={{display:"flex",gap:8,flexWrap:"wrap",justifyContent:"center"}}>
            <label className="quiet-button" style={{cursor:"pointer"}}>
              Add photos
              <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" multiple hidden
                onChange={(e) => { uploadPhotos(e.target.files); e.target.value = ""; }} />
            </label>
            {currentPhoto && !currentPhoto.is_primary && (
              <button type="button" className="quiet-button" disabled={writing} onClick={makePrimary}>Set primary</button>
            )}
            {currentPhoto && (
              <button type="button" className="quiet-button" disabled={writing} onClick={deletePhoto}>Delete</button>
            )}
          </div>
        </div>
      </div>
      {writeMsg && <div className="note" style={{background:"#fdeaea",borderLeftColor:"#c0392b",color:"#c0392b",marginBottom:16}}>{writeMsg}</div>}

      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))",gap:16}}>
        <article className="panel">
          <div className="panel__heading"><h3>Identity & Contact</h3><button type="button" className="quiet-button" onClick={() => { if (editingIdentity) { setEditingIdentity(false); return; } if (!guardWrite()) return; startIdentityEdit(); }}>{editingIdentity ? "Cancel" : "Edit"}</button></div>
          {editingIdentity ? (
            <div style={{padding:16, display:"grid", gridTemplateColumns:"120px 1fr", gap:"8px 16px", fontSize:14, alignItems:"center"}}>
              <dt>Full name</dt><dd><input type="text" value={identityForm.full_name} onChange={(e) => setIdentityForm({...identityForm, full_name: e.target.value})} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>First name</dt><dd><input type="text" value={identityForm.first_name} onChange={(e) => setIdentityForm({...identityForm, first_name: e.target.value})} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Gender</dt><dd><select value={identityForm.gender} onChange={(e) => setIdentityForm({...identityForm, gender: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}}><option value="">—</option><option>MALE</option><option>FEMALE</option><option>OTHER</option><option>PREFER_NOT_TO_SAY</option></select></dd>
              <dt>Date of birth</dt><dd><input type="date" value={identityForm.date_of_birth} onChange={(e) => setIdentityForm({...identityForm, date_of_birth: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Blood group</dt><dd><select value={identityForm.blood_group} onChange={(e) => setIdentityForm({...identityForm, blood_group: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}}><option value="">—</option>{["A+","A-","B+","B-","AB+","AB-","O+","O-"].map((b) => <option key={b} value={b}>{b}</option>)}</select></dd>
              <dt>Spouse</dt><dd><input type="text" value={identityForm.spouse_name} onChange={(e) => setIdentityForm({...identityForm, spouse_name: e.target.value})} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Status</dt><dd><select value={identityForm.status} onChange={(e) => setIdentityForm({...identityForm, status: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}}>{["ACTIVE","DECEASED","LOST_CONTACT","OPTED_OUT","ARCHIVED"].map((s) => <option key={s} value={s}>{s}</option>)}</select></dd>
              <dt>Notes</dt><dd><textarea value={identityForm.notes} onChange={(e) => setIdentityForm({...identityForm, notes: e.target.value})} rows={2} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt></dt><dd><button type="button" className="quiet-button" disabled={writing} onClick={submitIdentity}>Save identity</button></dd>
            </div>
          ) : (
          <dl style={{margin:0,padding:16,display:"grid",gridTemplateColumns:"120px 1fr",gap:"8px 16px"}}>
            <dt>Full name</dt><dd>{person?.full_name || "—"}</dd>
            <dt>First name</dt><dd>{person?.first_name || "—"}</dd>
            <dt>Gender</dt><dd>{person?.gender || "—"}</dd>
            <dt>Date of birth</dt><dd>{formatDate(person?.date_of_birth || null)}</dd>
            <dt>Blood group</dt><dd>{person?.blood_group || "—"}</dd>
            <dt>Spouse</dt><dd>{person?.spouse_name || "—"}</dd>
            <dt>Status</dt><dd>{constituent.status}</dd>
            <dt>Notes</dt><dd>{constituent.notes || "—"}</dd>
            <dt>Completeness</dt><dd>{constituent.profile_completeness_percent}%</dd>
            <dt>Last substantive update</dt><dd>{formatDate(constituent.last_substantive_profile_update_at)} ({freshnessLabel(constituent.days_since_profile_update)})</dd>
          </dl>
          )}
        </article>

        {/* Alumni Profile */}
        {alumni_profile && (
          <article className="panel">
            <div className="panel__heading"><h3>Alumni Profile</h3><button type="button" className="quiet-button" onClick={() => { if (editingAlumni) { setEditingAlumni(false); return; } if (!guardWrite()) return; startAlumniEdit(); }}>{editingAlumni ? "Cancel" : "Edit"}</button></div>
            {editingAlumni ? (
            <div style={{padding:16, display:"grid", gridTemplateColumns:"140px 1fr", gap:"8px 16px", fontSize:14, alignItems:"center"}}>
              <dt>Roll Number</dt><dd>{alumni_profile.roll_no} (immutable)</dd>
              <dt>IITGN Email</dt><dd><input type="text" value={alumniForm.iitgn_email} onChange={(e) => setAlumniForm({...alumniForm, iitgn_email: e.target.value})} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Year of graduation</dt><dd><input type="number" value={alumniForm.year_of_graduation} onChange={(e) => setAlumniForm({...alumniForm, year_of_graduation: e.target.value})} style={{width:110,padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Final CPI</dt><dd><input type="number" step="0.01" value={alumniForm.final_cpi} onChange={(e) => setAlumniForm({...alumniForm, final_cpi: e.target.value})} style={{width:110,padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Thesis title</dt><dd><input type="text" value={alumniForm.thesis_title} onChange={(e) => setAlumniForm({...alumniForm, thesis_title: e.target.value})} style={{width:"100%",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>Thesis defence</dt><dd><input type="date" value={alumniForm.thesis_defence_date} onChange={(e) => setAlumniForm({...alumniForm, thesis_defence_date: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>JEE AIR</dt><dd><input type="number" value={alumniForm.jee_air} onChange={(e) => setAlumniForm({...alumniForm, jee_air: e.target.value})} style={{width:110,padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt>GATE AIR</dt><dd><input type="number" value={alumniForm.gate_air} onChange={(e) => setAlumniForm({...alumniForm, gate_air: e.target.value})} style={{width:110,padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} /></dd>
              <dt></dt><dd><button type="button" className="quiet-button" disabled={writing} onClick={submitAlumni}>Save alumni profile</button></dd>
            </div>
            ) : (
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
            )}
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
          <div style={{padding:12, borderTop:"1px solid #ecece6", display:"flex", gap:8, flexWrap:"wrap", alignItems:"flexEnd"}}>
            <select value={contactForm.contact_type} onChange={(e) => setContactForm({...contactForm, contact_type: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}}>
              {["EMAIL_IITGN","EMAIL_PERSONAL","EMAIL_WORK","PHONE_PRIMARY","PHONE_SECONDARY","LINKEDIN","INSTAGRAM","WHATSAPP"].map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input type="text" placeholder="Value" value={contactForm.value} onChange={(e) => setContactForm({...contactForm, value: e.target.value})} style={{flex:"1 1 200px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <button type="button" className="quiet-button" disabled={writing} onClick={submitContact}>Add contact</button>
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
          <div style={{padding:12, borderTop:"1px solid #ecece6", display:"flex", gap:8, flexWrap:"wrap", alignItems:"flexEnd"}}>
            <select value={addressForm.address_type} onChange={(e) => setAddressForm({...addressForm, address_type: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}}>
              <option>CURRENT</option><option>PERMANENT</option>
            </select>
            <input type="text" placeholder="Street" value={addressForm.line1} onChange={(e) => setAddressForm({...addressForm, line1: e.target.value})} style={{flex:"2 1 200px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="text" placeholder="City" value={addressForm.city} onChange={(e) => setAddressForm({...addressForm, city: e.target.value})} style={{flex:"1 1 120px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="text" placeholder="Country" value={addressForm.country} onChange={(e) => setAddressForm({...addressForm, country: e.target.value})} style={{flex:"1 1 120px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <button type="button" className="quiet-button" disabled={writing} onClick={submitAddress}>Add address</button>
          </div>
        </article>

        <article className="panel">
          <div className="panel__heading"><h3>Communication Preferences</h3></div>
          <div style={{padding:16, display:"flex", gap:16, flexWrap:"wrap", fontSize:14, alignItems:"center"}}>
            <label style={{display:"flex",gap:6,alignItems:"center"}}><input type="checkbox" checked={commsForm.email_opt_in} onChange={(e) => setCommsForm({...commsForm, email_opt_in: e.target.checked})} /> Email</label>
            <label style={{display:"flex",gap:6,alignItems:"center"}}><input type="checkbox" checked={commsForm.whatsapp_opt_in} onChange={(e) => setCommsForm({...commsForm, whatsapp_opt_in: e.target.checked})} /> WhatsApp</label>
            <label style={{display:"flex",gap:6,alignItems:"center"}}><input type="checkbox" checked={commsForm.sms_opt_in} onChange={(e) => setCommsForm({...commsForm, sms_opt_in: e.target.checked})} /> SMS</label>
            <label style={{display:"flex",gap:6,alignItems:"center"}}><input type="checkbox" checked={commsForm.global_dnc} onChange={(e) => setCommsForm({...commsForm, global_dnc: e.target.checked})} /> Global DNC</label>
            <button type="button" className="quiet-button" disabled={writing} onClick={submitComms}>Save preferences</button>
          </div>
          <div className="panel__footer">Global DNC overrides all channels. Changes are audited.</div>
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
          <div style={{padding:12, borderTop:"1px solid #ecece6", display:"flex", gap:8, flexWrap:"wrap", alignItems:"flexEnd"}}>
            <input type="text" placeholder="Qualification (e.g., MTech)" value={eduForm.qualification} onChange={(e) => setEduForm({...eduForm, qualification: e.target.value})} style={{flex:"1 1 160px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="text" placeholder="Institution" value={eduForm.institution_name} onChange={(e) => setEduForm({...eduForm, institution_name: e.target.value})} style={{flex:"1 1 160px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="number" placeholder="Year" value={eduForm.completion_year} onChange={(e) => setEduForm({...eduForm, completion_year: e.target.value})} style={{width:90,padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <button type="button" className="quiet-button" disabled={writing} onClick={submitEducation}>Add qualification</button>
          </div>
          <div className="panel__footer">Appended as a dated POST_IITGN record — earlier qualifications are preserved, never overwritten.</div>
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
          <div style={{padding:12, borderTop:"1px solid #ecece6", display:"flex", gap:8, flexWrap:"wrap", alignItems:"flexEnd"}}>
            <input type="text" placeholder="Organisation" value={affForm.organisation_name_raw} onChange={(e) => setAffForm({...affForm, organisation_name_raw: e.target.value})} style={{flex:"1 1 150px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="text" placeholder="Designation" value={affForm.designation} onChange={(e) => setAffForm({...affForm, designation: e.target.value})} style={{flex:"1 1 130px",padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <input type="date" value={affForm.start_date} onChange={(e) => setAffForm({...affForm, start_date: e.target.value})} style={{padding:"6px 10px",fontSize:13,border:"1px solid #cfd4d2",borderRadius:4}} />
            <label style={{display:"flex",gap:6,alignItems:"center",fontSize:13,color:"#4f5c62"}}><input type="checkbox" checked={affForm.is_current} onChange={(e) => setAffForm({...affForm, is_current: e.target.checked})} /> Current</label>
            <button type="button" className="quiet-button" disabled={writing} onClick={submitAffiliation}>Add job</button>
          </div>
          <div className="panel__footer">A new current job closes the previous current affiliation (kept as past history) and refreshes profile freshness.</div>
        </article>

        <article className="panel">
          <div className="panel__heading"><h3>Donation History (0)</h3></div>
          <div className="table-wrap">
            <table><thead><tr><th>Date</th><th>Amount</th><th>Fund / Purpose</th><th>Receipt</th></tr></thead>
            <tbody><tr><td colSpan={4} style={{textAlign:"center",color:"#65737a",padding:16}}>No donations recorded for this profile.</td></tr></tbody>
            </table>
          </div>
          <div className="panel__footer">Donation ledger with lifetime and past-1-year totals arrives with M2 (currently on hold). No donation data exists yet — neither in the database nor in the source Excel.</div>
        </article>

        <ChildPanel title="Hostel History" count={hostel_history.filter((h) => h.hostel_name !== "DEMO-FIXTURE").length} columns={["Hostel", "Room", "Academic year", "Semester"]} form={<AddChildForm slug="hostel-history" constituentId={constituent.id} fields={CHILD_FORMS["hostel-history"]} buttonLabel="Add hostel stay" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {hostel_history.length === 0 ? emptyRow(4, "No hostel history") : hostel_history.filter((h) => h.hostel_name !== "DEMO-FIXTURE").map((h) => (
            <tr key={h.id}><td>{h.hostel_name}</td><td>{h.room_number || "—"}</td><td>{h.academic_year || "—"}</td><td>{h.semester || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Academic Transcript" count={academic_courses.length} columns={["Level", "Code", "Course", "Credits", "Year/Sem", "Instructor", "Grade"]} form={<AddChildForm slug="academic-courses" constituentId={constituent.id} fields={CHILD_FORMS["academic-courses"]} buttonLabel="Add course" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {academic_courses.length === 0 ? emptyRow(7, "No course records") : academic_courses.map((c) => (
            <tr key={c.id}><td>{c.programme_level}</td><td>{c.course_code}</td><td>{c.course_name || "—"}</td><td>{c.credits ?? "—"}</td><td>{c.year || "—"} / {c.semester || "—"}</td><td>{c.instructor || "—"}</td><td>{c.grade || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Semester Performance" count={semester_performance.length} columns={["Level", "Year", "Semester", "SPI", "CPI"]} form={<AddChildForm slug="semester-performance" constituentId={constituent.id} fields={CHILD_FORMS["semester-performance"]} buttonLabel="Add semester result" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {semester_performance.length === 0 ? emptyRow(5, "No performance records") : semester_performance.map((s) => (
            <tr key={s.id}><td>{s.programme_level}</td><td>{s.year || "—"}</td><td>{s.semester || "—"}</td><td>{s.spi ?? "—"}</td><td>{s.cpi ?? "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="GPS Assignments" count={gps_assignments.length} columns={["Year", "Semester", "Coordinator"]} form={<AddChildForm slug="gps-assignments" constituentId={constituent.id} fields={CHILD_FORMS["gps-assignments"]} buttonLabel="Add assignment" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {gps_assignments.length === 0 ? emptyRow(3, "No GPS assignments") : gps_assignments.map((g) => (
            <tr key={g.id}><td>{g.year || "—"}</td><td>{g.semester || "—"}</td><td>{g.coordinator_name || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Awards & Recognition" count={awards_recognition.length} columns={["Type", "Date", "Agency", "Details"]} form={<AddChildForm slug="awards" constituentId={constituent.id} fields={CHILD_FORMS["awards"]} buttonLabel="Add award" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {awards_recognition.length === 0 ? emptyRow(4, "No awards") : awards_recognition.map((a) => (
            <tr key={a.id}><td>{a.award_type}</td><td>{formatDate(a.award_date)}</td><td>{a.agency || "—"}</td><td>{a.details || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Scholarships & Financial Aid" count={scholarships_financial_aid.length} columns={["Type", "Name", "Year", "Amount", "Remarks"]} form={<AddChildForm slug="scholarships" constituentId={constituent.id} fields={CHILD_FORMS["scholarships"]} buttonLabel="Add scholarship" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {scholarships_financial_aid.length === 0 ? emptyRow(5, "No scholarships") : scholarships_financial_aid.map((s) => (
            <tr key={s.id}><td>{s.aid_type || "—"}</td><td>{s.name}</td><td>{s.year || "—"}</td><td>{s.amount ?? "—"}</td><td>{s.remarks || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Internships" count={internships.length} columns={["Organisation", "Scope", "Format", "Year", "Funding"]} form={<AddChildForm slug="internships" constituentId={constituent.id} fields={CHILD_FORMS["internships"]} buttonLabel="Add internship" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {internships.length === 0 ? emptyRow(5, "No internships") : internships.map((i) => (
            <tr key={i.id}><td>{i.organisation || "—"}</td><td>{i.scope || "—"}</td><td>{i.format || "—"}</td><td>{i.year || "—"}</td><td>{i.funding_source || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Placements" count={placements.length} columns={["Company", "Sector", "Location", "CTC", "Joined"]} form={<AddChildForm slug="placements" constituentId={constituent.id} fields={CHILD_FORMS["placements"]} buttonLabel="Add placement" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {placements.length === 0 ? emptyRow(5, "No placements") : placements.map((p) => (
            <tr key={p.id}><td>{p.company || "—"}</td><td>{p.sector || "—"}</td><td>{[p.city, p.country].filter(Boolean).join(", ") || "—"}</td><td>{p.ctc ?? "—"}</td><td>{formatDate(p.date_of_joining)}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Startups" count={startups.length} columns={["Startup", "Type", "Year", "Sector", "Location"]} form={<AddChildForm slug="startups" constituentId={constituent.id} fields={CHILD_FORMS["startups"]} buttonLabel="Add startup" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {startups.length === 0 ? emptyRow(5, "No startups") : startups.map((s) => (
            <tr key={s.id}><td>{s.startup_name}</td><td>{s.startup_type || "—"}</td><td>{s.year || "—"}</td><td>{s.sector || "—"}</td><td>{s.location || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Positions of Responsibility" count={positions_of_responsibility.length} columns={["Title", "Domain", "Academic year"]} form={<AddChildForm slug="responsibilities" constituentId={constituent.id} fields={CHILD_FORMS["responsibilities"]} buttonLabel="Add position" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {positions_of_responsibility.length === 0 ? emptyRow(3, "No positions") : positions_of_responsibility.map((p) => (
            <tr key={p.id}><td>{p.title}</td><td>{p.domain || "—"}</td><td>{p.academic_year || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Publications" count={publications.length} columns={["Title", "DOI", "Date"]} form={<AddChildForm slug="publications" constituentId={constituent.id} fields={CHILD_FORMS["publications"]} buttonLabel="Add publication" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {publications.length === 0 ? emptyRow(3, "No publications") : publications.map((p) => (
            <tr key={p.id}><td>{p.title}</td><td>{p.doi || "—"}</td><td>{formatDate(p.pub_date)}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Overseas Exposure" count={overseas_exposure.length} columns={["Organisation", "Year", "Period", "Funding"]} form={<AddChildForm slug="overseas-exposure" constituentId={constituent.id} fields={CHILD_FORMS["overseas-exposure"]} buttonLabel="Add exposure" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {overseas_exposure.length === 0 ? emptyRow(4, "No overseas exposure") : overseas_exposure.map((o) => (
            <tr key={o.id}><td>{o.organisation || "—"}</td><td>{o.year || "—"}</td><td>{formatDate(o.start_date)} – {o.end_date ? formatDate(o.end_date) : "—"}</td><td>{o.funding_details || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="Family Details" count={family_members.length} columns={["Name", "Relationship", "Contact", "Email"]} footnote="Restricted third-party information — withheld server-side without people.read_family." form={<AddChildForm slug="family-members" constituentId={constituent.id} fields={CHILD_FORMS["family-members"]} buttonLabel="Add family member" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {family_members.length === 0 ? emptyRow(4, "No family records on file") : family_members.map((f) => (
            <tr key={f.id}><td>{f.name}</td><td>{f.relation || "—"}</td><td>{f.contact_number || "—"}</td><td>{f.email || "—"}</td></tr>
          ))}
        </ChildPanel>

        <ChildPanel title="SSAC Records" count={ssac_records.length} columns={["Incident", "Sanction date", "Attachment"]} footnote="Restricted conduct records — visible only with ssac.read_restricted (admin role). Separate policy approval required." form={<AddChildForm slug="ssac-records" constituentId={constituent.id} fields={CHILD_FORMS["ssac-records"]} buttonLabel="Add record" onAdded={onChanged} canWrite={canWrite} onDenied={denyWrite} />}>
          {ssac_records.length === 0 ? emptyRow(3, "No SSAC records") : ssac_records.map((s) => (
            <tr key={s.id}><td>{s.incident_details || "—"}</td><td>{formatDate(s.sanction_letter_date)}</td><td>{s.attachment_storage_key || "—"}</td></tr>
          ))}
        </ChildPanel>

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