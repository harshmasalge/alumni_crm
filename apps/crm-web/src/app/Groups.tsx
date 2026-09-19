import { useState, useEffect, useCallback } from "react";
import { api, ApiError, AuthUser, Constituent, FilterFieldSpec, FilterGroup, Group, GroupMember, PopulationQuery, Proposal, RuleVersion } from "../api";
import { StatusBadge, FilterSidebar, describeCondition, leavesWithPaths } from "./App";
import { ExportDialog, canExport } from "./Export";

/* M1.1 Phase B2 — Manual Groups UI + read-only rule-based surfacing.
 * Rule/proposal workflows arrive in B3; this module is structurally ready
 * (detail route, tabs, activity feed) without fake workflow screens. */

function hasPerm(user: AuthUser | null, perm: string): boolean {
  return !!user && (user.is_superuser || user.permissions.includes(perm));
}

function Err({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="note" style={{ background: "#fdeaea", borderLeftColor: "#c0392b", color: "#c0392b", marginBottom: 16 }}>
      {message}
    </div>
  );
}

export function Groups({ groupId, onOpenGroup, onOpenProfile, user }: {
  groupId?: string;
  onOpenGroup: (id?: string) => void;
  onOpenProfile: (id: string) => void;
  user: AuthUser | null;
}) {
  if (!hasPerm(user, "groups.read")) {
    return (
      <section className="people-page" aria-label="Groups">
        <div className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Restricted</p><h3>Groups</h3></div></div>
          <div style={{ padding: 16, color: "#65737a", fontSize: 14 }}>
            Your account cannot view groups. Sign in with a role holding <code>groups.read</code> — enforced server-side.
          </div>
        </div>
      </section>
    );
  }
  if (groupId) {
    return <GroupDetail groupId={groupId} onBack={() => onOpenGroup(undefined)} onOpenProfile={onOpenProfile} user={user} />;
  }
  return <GroupsList onOpenGroup={onOpenGroup} user={user} />;
}

type ListFilter = "ALL" | "MANUAL" | "RULE_BASED" | "NEEDS_REVIEW";

function GroupsList({ onOpenGroup, user }: { onOpenGroup: (id: string) => void; user: AuthUser | null }) {
  const canCreate = hasPerm(user, "groups.create");
  const [filter, setFilter] = useState<ListFilter>("ALL");
  const [q, setQ] = useState("");
  const [items, setItems] = useState<Group[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const params: Record<string, string | number | boolean> = { page, page_size: pageSize };
      if (filter === "MANUAL" || filter === "RULE_BASED") params.type = filter;
      if (filter === "NEEDS_REVIEW") params.needs_review = true;
      if (q.trim()) params.q = q.trim();
      const data = await api.groups.list(params);
      setItems(data.items); setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load groups.");
      setItems([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [filter, q, page, pageSize]);

  useEffect(() => {
    const t = setTimeout(load, q ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  return (
    <section className="people-page" aria-label="Groups workspace">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
        <div>
          <p className="eyebrow">M1.1 · Managed populations</p>
          <h2 style={{ margin: "4px 0 0" }}>Groups</h2>
        </div>
        {canCreate && (
          <button type="button" className="quiet-button" onClick={() => setShowCreate((v) => !v)} aria-expanded={showCreate}>
            {showCreate ? "Close" : "+ New group"}
          </button>
        )}
      </div>

      {showCreate && canCreate && <CreateGroupPanel onCreated={(id) => onOpenGroup(id)} onCancel={() => setShowCreate(false)} />}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 16 }}>
        <div className="segmented" role="tablist" aria-label="Group filter">
          {(["ALL", "MANUAL", "RULE_BASED", "NEEDS_REVIEW"] as ListFilter[]).map((f) => (
            <button key={f} type="button" role="tab" aria-selected={filter === f}
              className={`segmented__tab ${filter === f ? "segmented__tab--active" : ""}`}
              onClick={() => { setFilter(f); setPage(1); }}>
              {f === "ALL" ? "All" : f === "MANUAL" ? "Manual" : f === "RULE_BASED" ? "Rule-based" : "Needs review"}
            </button>
          ))}
        </div>
        <div style={{ flex: 1, minWidth: 220 }}>
          <label style={{ display: "block", fontSize: 11, color: "#68777e", marginBottom: 4 }}>Search by group name</label>
          <input type="text" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="e.g., Class of 2018"
            style={{ width: "100%", padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
        </div>
      </div>

      <Err message={error} />

      <div className="panel">
        <div className="table-wrap"><table>
          <thead><tr><th>Group</th><th>Type</th><th>Status</th><th>Members</th><th>Review</th><th>Updated</th></tr></thead>
          <tbody>
            {items.length === 0 && !loading ? (
              <tr><td colSpan={6} style={{ textAlign: "center", color: "#65737a", padding: 32 }}>
                No groups found. {canCreate ? "Create the first one with + New group." : ""}
              </td></tr>
            ) : items.map((g) => (
              <tr key={g.id} onClick={() => onOpenGroup(g.id)} style={{ cursor: "pointer" }}>
                <td><strong>{g.name}</strong>{g.description && <span style={{ display: "block", fontSize: 12, color: "#68777e" }}>{g.description}</span>}</td>
                <td>{g.type === "MANUAL" ? "Manual" : "Rule-based"}</td>
                <td>{g.status === "ACTIVE" ? "Active" : "Deactivated"}</td>
                <td>{g.member_count}</td>
                <td>{g.pending_proposal_count > 0 || g.has_pending_rule
                  ? `${g.pending_proposal_count > 0 ? `${g.pending_proposal_count} proposal${g.pending_proposal_count === 1 ? "" : "s"}` : ""}${g.pending_proposal_count > 0 && g.has_pending_rule ? " · " : ""}${g.has_pending_rule ? "rule to review" : ""}`
                  : "—"}</td>
                <td>{new Date(g.updated_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
        {total > 0 && (
          <div className="panel__footer" style={{ display: "flex", justifyContent: "flex-end" }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="quiet-button">Previous</button>
              <span style={{ alignSelf: "center" }}>Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="quiet-button">Next</button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function CreateGroupPanel({ onCreated, onCancel }: { onCreated: (id: string) => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<"MANUAL" | "RULE_BASED">("MANUAL");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!name.trim()) { setError("Name is required."); return; }
    setBusy(true); setError(null);
    try {
      const group = await api.groups.create({
        name: name.trim(),
        description: description.trim() || undefined,
        type,
      });
      onCreated(group.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create group.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: 16 }}>
      <div className="panel__heading"><div><p className="eyebrow">New group</p><h3>Create group</h3></div></div>
      <div style={{ padding: 16, display: "grid", gap: 10, maxWidth: 560 }}>
        <Err message={error} />
        <label style={{ display: "grid", gap: 4, fontSize: 11, color: "#68777e" }}>Name
          <input type="text" value={name} onChange={(e) => setName(e.target.value)}
            style={{ padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
        </label>
        <label style={{ display: "grid", gap: 4, fontSize: 11, color: "#68777e" }}>Description (optional)
          <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
            style={{ padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
        </label>
        <div className="segmented" role="radiogroup" aria-label="Group type" style={{ justifySelf: "start" }}>
          {(["MANUAL", "RULE_BASED"] as const).map((t) => (
            <button key={t} type="button" role="radio" aria-checked={type === t}
              className={`segmented__tab ${type === t ? "segmented__tab--active" : ""}`}
              onClick={() => setType(t)}>
              {t === "MANUAL" ? "Manual" : "Rule-based"}
            </button>
          ))}
        </div>
        {type === "RULE_BASED" && (
          <p style={{ fontSize: 12, color: "#68777e", margin: 0 }}>
            Rule-based groups start empty. Rule setup and approvals arrive in Phase B3 — no membership changes happen on creation.
          </p>
        )}
        <div style={{ display: "flex", gap: 8 }}>
          <button type="button" className="quiet-button" disabled={busy} onClick={submit}>Create group</button>
          <button type="button" className="quiet-button" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

type DetailTab = "members" | "rule" | "proposals" | "activity";

function shortId(id: string | null): string {
  return id ? `${id.slice(0, 8)}…` : "—";
}

function fmtDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : "—";
}

function GroupDetail({ groupId, onBack, onOpenProfile, user }: {
  groupId: string;
  onBack: () => void;
  onOpenProfile: (id: string) => void;
  user: AuthUser | null;
}) {
  const canManage = hasPerm(user, "groups.manage_members");
  const canEdit = hasPerm(user, "groups.update");
  const canDeactivate = hasPerm(user, "groups.deactivate");
  const canSeeActivity = hasPerm(user, "admin.audit") || !!user?.is_superuser;
  const [tab, setTab] = useState<DetailTab>("members");
  const [group, setGroup] = useState<Group | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const g = await api.groups.get(groupId);
      setGroup(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load group.");
      setGroup(null);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => { load(); }, [load]);

  const toggleStatus = async () => {
    if (!group) return;
    const action = group.status === "ACTIVE" ? "deactivate" : "reactivate";
    if (!window.confirm(`${action === "deactivate" ? "Deactivate" : "Reactivate"} group “${group.name}”?` +
      (action === "deactivate" ? " Members are kept; writes freeze until reactivation." : ""))) return;
    setError(null);
    try {
      const g = action === "deactivate"
        ? await api.groups.deactivate(group.id)
        : await api.groups.reactivate(group.id);
      setGroup(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not change group status.");
    }
  };

  const saveEdit = async () => {
    if (!group || !editName.trim()) { setError("Name is required."); return; }
    setError(null);
    try {
      const g = await api.groups.update(group.id, { name: editName.trim(), description: editDesc.trim() || undefined });
      setGroup(g); setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save group.");
    }
  };

  if (loading) {
    return <section className="people-page"><p style={{ color: "#65737a" }}>Loading group…</p></section>;
  }
  if (!group) {
    return <section className="people-page"><Err message={error ?? "Group not found."} />
      <button type="button" className="quiet-button" onClick={onBack}>← Groups</button></section>;
  }

  const isRule = group.type === "RULE_BASED";
  const frozen = group.status !== "ACTIVE";

  return (
    <section className="people-page" aria-label="Group detail">
      <button type="button" className="quiet-button" onClick={onBack} style={{ marginBottom: 12 }}>← Groups</button>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", marginBottom: 4 }}>
        <div>
          <p className="eyebrow">M1.1 · {isRule ? "Rule-based group" : "Manual group"}</p>
          <h2 style={{ margin: "4px 0" }}>{group.name}</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <StatusBadge state="Live" />
            <span style={{ fontSize: 13, color: "#65737a" }}>{isRule ? "Rule-based" : "Manual"} · {group.status === "ACTIVE" ? "Active" : "Deactivated"}</span>
          </div>
          <p style={{ fontSize: 14, color: "#1f2d38", margin: "8px 0 0" }}>
            <strong>{group.member_count} member{group.member_count === 1 ? "" : "s"}</strong>
            {group.pending_proposal_count > 0 && <span> · {group.pending_proposal_count} pending change{group.pending_proposal_count === 1 ? "" : "s"}</span>}
          </p>
          {group.description && <p style={{ fontSize: 13, color: "#4f5c62" }}>{group.description}</p>}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canEdit && !editing && (
            <button type="button" className="quiet-button" onClick={() => { setEditName(group.name); setEditDesc(group.description ?? ""); setEditing(true); }}>Edit</button>
          )}
          {canDeactivate && (
            <button type="button" className="quiet-button" onClick={toggleStatus}>
              {group.status === "ACTIVE" ? "Deactivate" : "Reactivate"}
            </button>
          )}
        </div>
      </div>

      {editing && canEdit && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div style={{ padding: 16, display: "grid", gap: 10, maxWidth: 560 }}>
            <label style={{ display: "grid", gap: 4, fontSize: 11, color: "#68777e" }}>Name
              <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
                style={{ padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
            </label>
            <label style={{ display: "grid", gap: 4, fontSize: 11, color: "#68777e" }}>Description
              <input type="text" value={editDesc} onChange={(e) => setEditDesc(e.target.value)}
                style={{ padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
            </label>
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="quiet-button" onClick={saveEdit}>Save</button>
              <button type="button" className="quiet-button" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {frozen && (
        <div className="note">This group is deactivated: members are kept, but membership and rule writes are frozen until reactivation.</div>
      )}
      {isRule && (
        <div className="note">
          Rule-based membership is governed: rows here reflect approved proposals only — never direct edits.
          Rule changes need approval before they take effect, and resulting membership changes need a second approval.
        </div>
      )}

      <Err message={error} />

      <div className="segmented" role="tablist" aria-label="Group detail" style={{ marginBottom: 16 }}>
        {((isRule ? ["members", "rule", "proposals", "activity"] : ["members", "activity"]) as DetailTab[]).map((t) => (
          <button key={t} type="button" role="tab" aria-selected={tab === t}
            className={`segmented__tab ${tab === t ? "segmented__tab--active" : ""}`}
            onClick={() => setTab(t)}>
            {t === "members" ? `Members (${group.member_count})`
              : t === "rule" ? "Rule"
              : t === "proposals" ? `Proposals${group.pending_proposal_count > 0 ? ` (${group.pending_proposal_count})` : ""}`
              : "Activity"}
          </button>
        ))}
      </div>

      {isRule && group.pending_proposal_count > 0 && (
        <div className="note" style={{ margin: "0 0 12px" }}>
          ⚠ {group.pending_proposal_count} membership change{group.pending_proposal_count === 1 ? " needs" : "s need"} review.{" "}
          <button type="button" className="quiet-button" onClick={() => setTab("proposals")}>Review proposals</button>
        </div>
      )}

      {tab === "members" && (
        <MembersTab group={group} frozen={frozen} readOnly={isRule} canManage={canManage && !isRule}
          showExport={canExport(user)} onChanged={load} onOpenProfile={onOpenProfile} />
      )}
      {tab === "rule" && isRule && (
        <RuleTab group={group} frozen={frozen}
          canPropose={hasPerm(user, "groups.manage_rules")}
          canApprove={hasPerm(user, "groups.approve")}
          onChanged={load} />
      )}
      {tab === "proposals" && isRule && (
        <ProposalsTab group={group} frozen={frozen}
          canApprove={hasPerm(user, "groups.approve")}
          onChanged={load} onOpenProfile={onOpenProfile} />
      )}
      {tab === "activity" && <ActivityTab groupId={group.id} canSee={canSeeActivity} />}
    </section>
  );
}

function RuleChips({ tree }: { tree: FilterGroup }) {
  const op = (tree as FilterGroup).op === "or" ? "any of (OR)" : "all of (AND)";
  let leaves: { cond: { field: string; operator: string; value?: string | number; values?: (string | number)[] } }[] = [];
  try {
    leaves = leavesWithPaths(tree as FilterGroup);
  } catch {
    leaves = [];
  }
  if (leaves.length === 0) return <span style={{ fontSize: 13, color: "#65737a" }}>(empty rule)</span>;
  return (
    <span style={{ display: "inline-flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      <span style={{ fontSize: 12, color: "#68777e" }}>Match {op}:</span>
      {leaves.map(({ cond }, i) => (
        <span key={i} className="filter-chip">{describeCondition(cond)}</span>
      ))}
    </span>
  );
}

function RuleTab({ group, frozen, canPropose, canApprove, onChanged }: {
  group: Group;
  frozen: boolean;
  canPropose: boolean;
  canApprove: boolean;
  onChanged: () => void;
}) {
  const [rules, setRules] = useState<RuleVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [building, setBuilding] = useState(false);
  const [draft, setDraft] = useState<FilterGroup>({ op: "and", conditions: [] });
  const [registry, setRegistry] = useState<Record<string, FilterFieldSpec> | null>(null);
  const [suggestions, setSuggestions] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      setRules(await api.groups.listRules(group.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load rules.");
      setRules([]);
    } finally {
      setLoading(false);
    }
  }, [group.id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!building || registry) return;
    api.segmentation.getFilterFields()
      .then((d) => setRegistry(d.fields))
      .catch(() => setRegistry(null));
    (async () => {
      try {
        const out: Record<string, string[]> = {};
        for (const cat of ["industry", "company_type", "function", "seniority_level"]) {
          const data = await api.taxonomies.list({ category: cat });
          out[cat] = data.items.filter((t) => t.is_active).map((t) => t.value);
        }
        setSuggestions(out);
      } catch { /* suggestions are advisory */ }
    })();
  }, [building, registry]);

  const refresh = async () => { await load(); onChanged(); };

  const startBuilder = (seed?: FilterGroup) => {
    setDraft(seed ? JSON.parse(JSON.stringify(seed)) : { op: "and", conditions: [] });
    setBuilding(true);
  };

  const submitDraft = async () => {
    setBusy(true); setError(null); setNotice(null);
    try {
      const v = await api.groups.proposeRule(group.id, draft);
      setNotice(`Rule v${v.version_number} proposed — it takes effect only after approval.`);
      setBuilding(false);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not propose rule.");
    } finally {
      setBusy(false);
    }
  };

  const approve = async (v: RuleVersion) => {
    if (!window.confirm(`Approve rule v${v.version_number} for “${group.name}”? The rule becomes active and its population is evaluated into membership proposals (members change only after the second approval).`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const res = await api.groups.approveRule(group.id, v.version_number);
      setNotice(`Rule v${v.version_number} active. Evaluation: ${res.evaluation.matched} match, ${res.evaluation.additions} proposed additions, ${res.evaluation.removals} proposed removals.`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not approve rule.");
    } finally {
      setBusy(false);
    }
  };

  const reject = async (v: RuleVersion) => {
    if (!window.confirm(`Reject rule v${v.version_number} for “${group.name}”?`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await api.groups.rejectRule(group.id, v.version_number);
      setNotice(`Rule v${v.version_number} rejected.`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reject rule.");
    } finally {
      setBusy(false);
    }
  };

  const reevaluate = async (v: RuleVersion) => {
    setBusy(true); setError(null); setNotice(null);
    try {
      const s = await api.groups.evaluateRule(group.id, v.version_number);
      setNotice(`Re-evaluated v${v.version_number}: ${s.matched} match, ${s.additions} new proposed additions, ${s.removals} new proposed removals (${s.skipped_existing_pending} already pending).`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not re-evaluate.");
    } finally {
      setBusy(false);
    }
  };

  const active = rules.find((r) => r.status === "ACTIVE") ?? null;
  const pending = rules.find((r) => r.status === "PENDING") ?? null;
  const history = rules.filter((r) => r.status === "SUPERSEDED" || r.status === "REJECTED");

  if (loading) return <p style={{ fontSize: 13, color: "#65737a" }}>Loading rules…</p>;
  return (
    <div style={{ display: "grid", gap: 12 }}>
      {notice && <div className="note" style={{ margin: 0 }}>{notice}</div>}
      <Err message={error} />

      <div className="panel">
        <div className="panel__heading"><div><p className="eyebrow">Approved definition</p><h3>Current approved rule{active ? ` · v${active.version_number}` : ""}</h3></div>
          {active && canPropose && !frozen && !building && (
            <button type="button" className="quiet-button" onClick={() => startBuilder(active.filter_tree)}>Propose rule change</button>
          )}
        </div>
        <div style={{ padding: 12, display: "grid", gap: 8 }}>
          {active ? (
            <>
              <RuleChips tree={active.filter_tree} />
              <span style={{ fontSize: 12, color: "#68777e" }}>
                Approved {fmtDate(active.decided_at)} · proposed by {shortId(active.proposed_by)} · approved by {shortId(active.reviewed_by)}
              </span>
              <div>
                <button type="button" className="quiet-button" disabled={busy || frozen || !canPropose}
                  title={canPropose ? "Re-run the active rule against current data (creates only new pending deltas)" : "Needs rule-management permission (server-enforced)"}
                  onClick={() => reevaluate(active)}>Re-evaluate against current data</button>
              </div>
            </>
          ) : (
            <p style={{ fontSize: 13, color: "#65737a", margin: 0 }}>
              No approved rule yet — this group has no governed membership until a first rule is approved.
              {canPropose && !frozen && !building && (
                <> <button type="button" className="quiet-button" onClick={() => startBuilder()}>Propose the first rule</button></>
              )}
            </p>
          )}
        </div>
      </div>

      {pending && (
        <div className="panel" style={{ borderLeft: "3px solid #b96f2b" }}>
          <div className="panel__heading"><div><p className="eyebrow">Awaiting review — not active</p><h3>Pending rule change · v{pending.version_number}</h3></div></div>
          <div style={{ padding: 12, display: "grid", gap: 8 }}>
            <RuleChips tree={pending.filter_tree} />
            <span style={{ fontSize: 12, color: "#68777e" }}>
              Proposed {fmtDate(pending.created_at)} by {shortId(pending.proposed_by)}
            </span>
            {canApprove && !frozen ? (
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" className="quiet-button" disabled={busy} onClick={() => approve(pending)}>Approve rule</button>
                <button type="button" className="quiet-button" disabled={busy} onClick={() => reject(pending)}>Reject</button>
              </div>
            ) : (
              <p style={{ fontSize: 12, color: "#68777e", margin: 0 }}>
                {frozen ? "Group is deactivated — review is frozen until reactivation."
                  : "Approval needs the reviewer permission and a different reviewer than the proposer (server-enforced)."}
              </p>
            )}
          </div>
        </div>
      )}

      {building && canPropose && !frozen && (
        <div className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Draft — nothing takes effect until approval</p><h3>Propose rule change</h3></div>
            <button type="button" className="quiet-button" onClick={() => setBuilding(false)}>Cancel</button>
          </div>
          <div style={{ padding: 12 }}>
            <FilterSidebar registry={registry} tree={draft} suggestions={suggestions}
              onChange={setDraft} onClear={() => setDraft({ op: "and", conditions: [] })} />
            <div style={{ marginTop: 8 }}>
              <button type="button" className="quiet-button" disabled={busy} onClick={submitDraft}>Submit for approval</button>
            </div>
          </div>
        </div>
      )}

      {history.length > 0 && (
        <div className="panel">
          <div className="panel__heading"><h3>Rule history ({history.length})</h3></div>
          <div className="table-wrap"><table>
            <thead><tr><th>Version</th><th>Status</th><th>Decided</th></tr></thead>
            <tbody>
              {history.map((r) => (
                <tr key={r.id}><td>v{r.version_number}</td><td>{r.status}</td><td>{fmtDate(r.decided_at)}</td></tr>
              ))}
            </tbody>
          </table></div>
          <div className="panel__footer">Versions are append-only; superseded definitions are preserved for audit.</div>
        </div>
      )}
    </div>
  );
}

function parseReasonLeaves(detail: string | null): Array<{ field: string; operator: string; expected: string; actual: string; matched: boolean }> {
  try {
    const d = JSON.parse(detail ?? "");
    return Array.isArray(d.leaves) ? d.leaves : [];
  } catch {
    return [];
  }
}

function ProposalsTab({ group, frozen, canApprove, onChanged, onOpenProfile }: {
  group: Group;
  frozen: boolean;
  canApprove: boolean;
  onChanged: () => void;
  onOpenProfile: (id: string) => void;
}) {
  const [statusFilter, setStatusFilter] = useState<"PENDING" | "APPROVED" | "REJECTED" | "ALL">("PENDING");
  const [items, setItems] = useState<Proposal[]>([]);
  const [pendingAdds, setPendingAdds] = useState(0);
  const [pendingRemoves, setPendingRemoves] = useState(0);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.groups.listProposals(group.id, {
        status: statusFilter === "ALL" ? undefined : statusFilter,
        page, page_size: pageSize,
      });
      setItems(data.items); setTotal(data.total);
      // Pending counts page through at the backend's max page size instead of
      // requesting an oversized page (422 beyond le=100).
      let adds = 0;
      let removes = 0;
      let p = 1;
      for (;;) {
        const chunk = await api.groups.listProposals(group.id, { status: "PENDING", page: p, page_size: 100 });
        for (const item of chunk.items) {
          if (item.action === "ADD") adds += 1;
          else removes += 1;
        }
        if (p >= chunk.total_pages || chunk.items.length === 0) break;
        p += 1;
      }
      setPendingAdds(adds);
      setPendingRemoves(removes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load proposals.");
      setItems([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [group.id, statusFilter, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  const selected = Object.keys(checked).filter((id) => checked[id]);
  const decide = async (approve: boolean) => {
    if (selected.length === 0) return;
    const verb = approve ? "Approve" : "Reject";
    if (!window.confirm(`${verb} ${selected.length} membership proposal${selected.length === 1 ? "" : "s"}?` +
      (approve ? " Approved additions join the group; approved removals leave it." : ""))) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const res = await api.groups.decideProposals(group.id, approve, selected);
      const parts = [`${res.approved_or_rejected.length} ${approve ? "approved and applied" : "rejected"}`];
      if (res.stale.length > 0) parts.push(`${res.stale.length} skipped as stale (rule moved on)`);
      if (res.already_decided.length > 0) parts.push(`${res.already_decided.length} already decided`);
      setNotice(`${verb}d: ${parts.join(", ")}.`);
      setChecked({});
      await load(); onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not decide proposals.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      {notice && <div className="note" style={{ margin: 0 }}>{notice}</div>}
      <Err message={error} />
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <strong style={{ fontSize: 14 }}>{pendingAdds} proposed additions · {pendingRemoves} proposed removals</strong>
        <div className="segmented" role="tablist" aria-label="Proposal status" style={{ marginLeft: "auto" }}>
          {(["PENDING", "APPROVED", "REJECTED", "ALL"] as const).map((s) => (
            <button key={s} type="button" role="tab" aria-selected={statusFilter === s}
              className={`segmented__tab ${statusFilter === s ? "segmented__tab--active" : ""}`}
              onClick={() => { setStatusFilter(s); setPage(1); setChecked({}); }}>
              {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
            </button>
          ))}
        </div>
      </div>
      {canApprove && !frozen && statusFilter === "PENDING" && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" className="quiet-button" disabled={busy || selected.length === 0}
            onClick={() => decide(true)}>Approve selected ({selected.length})</button>
          <button type="button" className="quiet-button" disabled={busy || selected.length === 0}
            onClick={() => decide(false)}>Reject selected ({selected.length})</button>
          <span style={{ fontSize: 12, color: "#68777e" }}>Approval applies immediately; stale rows (rule moved on) are skipped, never applied.</span>
        </div>
      )}
      {(!canApprove || frozen) && statusFilter === "PENDING" && (
        <p style={{ fontSize: 12, color: "#68777e", margin: 0 }}>
          {frozen ? "Group is deactivated — decisions are frozen until reactivation."
            : "Deciding proposals needs the approver permission; you cannot approve evaluations you produced (server-enforced)."}
        </p>
      )}
      <div className="panel">
        <div className="table-wrap"><table>
          <thead><tr>
            {canApprove && !frozen && statusFilter === "PENDING" && <th aria-label="Select"><input type="checkbox" aria-label="Select all on this page"
              checked={items.length > 0 && items.every((p) => checked[p.id])}
              onChange={(e) => {
                const next: Record<string, boolean> = { ...checked };
                for (const p of items) {
                  if (e.target.checked) next[p.id] = true;
                  else delete next[p.id];
                }
                setChecked(next);
              }} /></th>}
            <th>Person</th><th>Action</th><th>Reason</th><th>Rule</th><th>Detected</th><th>Status</th>
          </tr></thead>
          <tbody>
            {items.length === 0 && !loading ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "#65737a", padding: 32 }}>
                {statusFilter === "PENDING" ? "No pending changes — membership matches the approved rule." : "No proposals in this state."}
              </td></tr>
            ) : items.map((p) => {
              const leaves = parseReasonLeaves(p.reason_detail);
              const isOpen = !!expanded[p.id];
              return (
                <tr key={p.id}>
                  {canApprove && !frozen && statusFilter === "PENDING" && (
                    <td><input type="checkbox" aria-label={`Select proposal for ${p.display_name}`} checked={!!checked[p.id]}
                      onChange={() => setChecked((s) => {
                        const next = { ...s };
                        if (next[p.id]) delete next[p.id];
                        else next[p.id] = true;
                        return next;
                      })} /></td>
                  )}
                  <td><button type="button" className="quiet-button" style={{ border: "none", padding: 0, fontWeight: 700 }}
                    onClick={() => onOpenProfile(p.constituent_id)}>{p.display_name}</button></td>
                  <td>{p.action === "ADD" ? "Add" : "Remove"}</td>
                  <td>
                    <div style={{ fontSize: 13 }}>{p.reason_summary}</div>
                    {leaves.length > 0 && (
                      <button type="button" className="quiet-button" style={{ padding: "2px 6px", fontSize: 12, marginTop: 4 }}
                        onClick={() => setExpanded((s) => ({ ...s, [p.id]: !isOpen }))}>
                        {isOpen ? "Hide detail" : "Why?"}
                      </button>
                    )}
                    {isOpen && leaves.length > 0 && (
                      <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 12, color: "#4f5c62" }}>
                        {leaves.map((l, i) => (
                          <li key={i}>
                            {l.field} {l.operator}: expected <strong>{l.expected || "—"}</strong>, current <strong>{l.actual || "—"}</strong>{" "}
                            {l.matched ? "✓" : "✗"}
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td>v{p.rule_version_number}</td>
                  <td>{new Date(p.created_at).toLocaleDateString()}</td>
                  <td>{p.status.charAt(0) + p.status.slice(1).toLowerCase()}</td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
        {total > 0 && (
          <div className="panel__footer" style={{ display: "flex", justifyContent: "flex-end" }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="quiet-button">Previous</button>
              <span style={{ alignSelf: "center" }}>Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="quiet-button">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MembersTab({ group, frozen, readOnly, canManage, showExport, onChanged, onOpenProfile }: {
  group: Group;
  frozen: boolean;
  readOnly: boolean;
  canManage: boolean;
  showExport: boolean;
  onChanged: () => void;
  onOpenProfile: (id: string) => void;
}) {
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.groups.listMembers(group.id, { page, page_size: pageSize });
      setMembers(data.items); setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load members.");
      setMembers([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [group.id, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  const remove = async (m: GroupMember) => {
    if (!window.confirm(`Remove ${m.display_name} from “${group.name}”?`)) return;
    setError(null); setNotice(null);
    try {
      await api.groups.removeMember(group.id, m.constituent_id);
      setNotice(`${m.display_name} removed.`);
      setPage(1); await load(); onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not remove member.");
    }
  };

  return (
    <div>
      {readOnly && (
        <p style={{ fontSize: 13, color: "#4f5c62" }}>
          Rule-based membership is governed: rows here reflect approved proposals only.
        </p>
      )}
      {(canManage && !frozen) || showExport ? (
        <div style={{ marginBottom: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
          {canManage && !frozen && (
            <button type="button" className="quiet-button" onClick={() => setShowPicker((v) => !v)} aria-expanded={showPicker}>
              {showPicker ? "Close member picker" : "Add members"}
            </button>
          )}
          {showExport && (
            <button type="button" className="quiet-button" onClick={() => setShowExportDialog((v) => !v)} aria-expanded={showExportDialog}>
              {showExportDialog ? "Close export" : "Export members"}
            </button>
          )}
        </div>
      ) : null}
      {showExportDialog && showExport && (
        <ExportDialog title={`Export ${group.name} to Excel`}
          subtitle={`Exporting the group's current server-side membership (${group.member_count} members; re-evaluated at generation).`}
          population={{ kind: "group", groupId: group.id, groupName: group.name }}
          onClose={() => setShowExportDialog(false)} />
      )}
      {showPicker && canManage && !frozen && (
        <MemberPicker groupId={group.id}
          onDone={(msg) => { setNotice(msg); setShowPicker(false); setPage(1); load(); onChanged(); }} />
      )}
      {notice && <div className="note" style={{ margin: "0 0 12px" }}>{notice}</div>}
      <Err message={error} />
      <div className="panel">
        <div className="table-wrap"><table>
          <thead><tr><th>Name</th><th>Added</th>{canManage && !readOnly && !frozen && <th>Actions</th>}</tr></thead>
          <tbody>
            {members.length === 0 && !loading ? (
              <tr><td colSpan={3} style={{ textAlign: "center", color: "#65737a", padding: 32 }}>
                No members yet.{canManage && !readOnly && !frozen ? " Use Add members above." : ""}
              </td></tr>
            ) : members.map((m) => (
              <tr key={m.constituent_id}>
                <td><button type="button" className="quiet-button" style={{ border: "none", padding: 0, fontWeight: 700 }}
                  onClick={() => onOpenProfile(m.constituent_id)}>{m.display_name}</button></td>
                <td>{new Date(m.added_at).toLocaleDateString()}</td>
                {canManage && !readOnly && !frozen && (
                  <td><button type="button" className="quiet-button" onClick={() => remove(m)}>Remove</button></td>
                )}
              </tr>
            ))}
          </tbody>
        </table></div>
        {total > 0 && (
          <div className="panel__footer" style={{ display: "flex", justifyContent: "flex-end" }}>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="quiet-button">Previous</button>
              <span style={{ alignSelf: "center" }}>Page {page} of {Math.max(1, Math.ceil(total / pageSize))}</span>
              <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="quiet-button">Next</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MemberPicker({ groupId, onDone }: { groupId: string; onDone: (message: string) => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Constituent[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async () => {
    if (!q.trim()) { setResults([]); setTotal(0); return; }
    try {
      const data = await api.constituents.search({ q: q.trim(), kind: "PERSON", page, page_size: 10 });
      setResults(data.items); setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed.");
    }
  }, [q, page]);

  useEffect(() => {
    const t = setTimeout(search, 300);
    return () => clearTimeout(t);
  }, [search]);

  const toggle = (id: string) => setChecked((s) => ({ ...s, [id]: !s[id] }));
  const selected = Object.keys(checked).filter((id) => checked[id]);

  const add = async () => {
    if (selected.length === 0) return;
    setBusy(true); setError(null);
    try {
      const res = await api.groups.addMembers(groupId, selected);
      const parts = [];
      if (res.added.length > 0) parts.push(`${res.added.length} added`);
      if (res.already_members.length > 0) parts.push(`${res.already_members.length} already members`);
      if (res.invalid.length > 0) parts.push(`${res.invalid.length} invalid`);
      setChecked({});
      onDone(parts.length > 0 ? `Done: ${parts.join(", ")}.` : "Nothing to add.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add members.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div className="panel__heading"><div><p className="eyebrow">Explicit people, by search</p><h3>Add members</h3></div></div>
      <div style={{ padding: 12 }}>
        <Err message={error} />
        <input type="text" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} placeholder="Search people by name…"
          style={{ width: "100%", padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4, marginBottom: 8 }} />
        {results.map((c) => (
          <label key={c.id} style={{ display: "flex", gap: 8, alignItems: "center", padding: "6px 0", fontSize: 14 }}>
            <input type="checkbox" checked={!!checked[c.id]} onChange={() => toggle(c.id)} />
            <span><strong>{c.display_name}</strong></span>
          </label>
        ))}
        {q.trim() && results.length === 0 && <p style={{ fontSize: 13, color: "#65737a" }}>No matches.</p>}
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
          <button type="button" className="quiet-button" disabled={busy || selected.length === 0} onClick={add}>
            Add selected ({selected.length})
          </button>
          {total > 10 && <span style={{ fontSize: 12, color: "#68777e" }}>{total} match — refine the search or page:</span>}
          {total > 10 && (
            <span style={{ display: "inline-flex", gap: 4 }}>
              <button type="button" className="quiet-button" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
              <button type="button" className="quiet-button" disabled={page * 10 >= total} onClick={() => setPage((p) => p + 1)}>›</button>
            </span>
          )}
        </div>
        <p style={{ fontSize: 12, color: "#68777e" }}>Server-side search; only checked people are added. Existing members are reported, never duplicated.</p>
      </div>
    </div>
  );
}

export type GroupSelection =
  | { kind: "ids"; ids: string[] }
  | { kind: "filtered"; query: PopulationQuery };

/* People → Groups handoff. Two distinct semantics, never mixed:
 * explicit IDs (these specific people) vs a live filter definition that is
 * re-evaluated server-side at confirm time (never a stale browser count).
 * Uses only the B1 preview/materialize/add APIs. */
export function AddToGroupDialog({ selection, onClose, onDone }: {
  selection: GroupSelection;
  onClose: () => void;
  onDone: () => void;
}) {
  const [step, setStep] = useState<"pick" | "confirm" | "result">("pick");
  const [q, setQ] = useState("");
  const [groups, setGroups] = useState<Group[]>([]);
  const [picked, setPicked] = useState<Group | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<{ matched: number; already_members: number; would_add: number } | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const searchGroups = useCallback(async () => {
    try {
      const data = await api.groups.list({ type: "MANUAL", status: "ACTIVE", q: q.trim() || undefined, page_size: 10 });
      setGroups(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not search groups.");
    }
  }, [q]);

  useEffect(() => {
    const t = setTimeout(searchGroups, 250);
    return () => clearTimeout(t);
  }, [searchGroups]);

  const createAndPick = async () => {
    if (!newName.trim()) { setError("Group name is required."); return; }
    setBusy(true); setError(null);
    try {
      const g = await api.groups.create({ name: newName.trim(), type: "MANUAL" });
      setPicked(g); setNewName(""); setStep("confirm");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create group.");
    } finally {
      setBusy(false);
    }
  };

  const enterConfirm = async (g: Group) => {
    setPicked(g); setError(null); setPreview(null);
    setStep("confirm");
    // Re-evaluate NOW: the confirm screen must show the current server-side
    // population, never the count the browser saw earlier.
    try {
      const body: PopulationQuery = selection.kind === "ids"
        ? { constituent_ids: selection.ids }
        : { ...selection.query };
      const p = await api.groups.previewPopulation(g.id, body);
      setPreview(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not preview population.");
    }
  };

  const execute = async () => {
    if (!picked) return;
    setBusy(true); setError(null);
    try {
      if (selection.kind === "ids") {
        const res = await api.groups.addMembers(picked.id, selection.ids);
        const parts = [];
        if (res.added.length > 0) parts.push(`${res.added.length} added`);
        if (res.already_members.length > 0) parts.push(`${res.already_members.length} already members`);
        if (res.invalid.length > 0) parts.push(`${res.invalid.length} invalid`);
        setResult(`Done: ${parts.join(", ") || "nothing to add"}.`);
      } else {
        const res = await api.groups.materializePopulation(picked.id, { ...selection.query });
        setResult(`Done: ${res.matched} matched, ${res.added.length} added, ${res.already_members} already members.`);
      }
      setStep("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add to group.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div className="panel__heading"><div>
        <p className="eyebrow">{selection.kind === "ids" ? "Add specific people" : "Add filtered population"}</p>
        <h3>Add to group</h3>
      </div><button type="button" className="quiet-button" onClick={onClose}>Close</button></div>
      <div style={{ padding: 12 }}>
        <Err message={error} />
        {step === "pick" && (
          <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
            <input type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search Manual groups…"
              style={{ padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
            {groups.map((g) => (
              <label key={g.id} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 14 }}>
                <input type="radio" name="pick-group" checked={picked?.id === g.id} onChange={() => setPicked(g)} />
                <span><strong>{g.name}</strong> <span style={{ color: "#68777e" }}>· {g.member_count} members</span></span>
              </label>
            ))}
            {q.trim() && groups.length === 0 && <p style={{ fontSize: 13, color: "#65737a" }}>No Manual groups match.</p>}
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Or create new group…"
                style={{ flex: "1 1 200px", padding: "8px 12px", fontSize: 14, border: "1px solid #cfd4d2", borderRadius: 4 }} />
              <button type="button" className="quiet-button" disabled={busy} onClick={createAndPick}>Create + continue</button>
            </div>
            <div>
              <button type="button" className="quiet-button" disabled={!picked} onClick={() => picked && enterConfirm(picked)}>Continue →</button>
            </div>
          </div>
        )}
        {step === "confirm" && picked && (
          <div style={{ display: "grid", gap: 8, maxWidth: 560 }}>
            {selection.kind === "ids" ? (
              <p style={{ fontSize: 14 }}>
                Add <strong>{selection.ids.length} specific {selection.ids.length === 1 ? "person" : "people"}</strong> to <strong>{picked.name}</strong>?
                {preview && preview.already_members > 0 && <span> {preview.already_members} already members (reported, not duplicated).</span>}
              </p>
            ) : (
              <p style={{ fontSize: 14, margin: 0 }}>
                Add the <strong>current server-side filtered population</strong> (name, Roll Number, organisation,
                stale and structured filters combined) to <strong>{picked.name}</strong>?
                {preview !== null
                  ? <span> <strong>{preview.matched} people currently match</strong> (re-evaluated just now{preview.already_members > 0 ? `, ${preview.already_members} already members` : ""}).</span>
                  : <span> Evaluating current population…</span>}
              </p>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              <button type="button" className="quiet-button" disabled={busy || (selection.kind === "filtered" && preview === null)} onClick={execute}>
                {selection.kind === "ids" ? "Add to group" : "Add matching people"}
              </button>
              <button type="button" className="quiet-button" onClick={() => setStep("pick")}>Back</button>
            </div>
          </div>
        )}
        {step === "result" && (
          <div style={{ display: "grid", gap: 8 }}>
            <p style={{ fontSize: 14 }}>{result}</p>
            <div><button type="button" className="quiet-button" onClick={onDone}>Done</button></div>
          </div>
        )}
      </div>
    </div>
  );
}

const ACTIVITY_SENTENCES: Record<string, (after: Record<string, unknown>) => string> = {
  GROUP_CREATE: () => "Group created.",
  GROUP_UPDATE: () => "Group details edited.",
  GROUP_DEACTIVATE: () => "Group deactivated.",
  GROUP_REACTIVATE: () => "Group reactivated.",
  GROUP_MEMBER_ADD: (a) => {
    const added = Array.isArray(a.added) ? a.added.length : 0;
    const already = Array.isArray(a.already_members) ? a.already_members.length : 0;
    return `Members added explicitly: ${added} added${already > 0 ? `, ${already} already members` : ""}.`;
  },
  GROUP_MEMBER_REMOVE: () => "Member removed.",
  GROUP_MEMBER_MATERIALIZE: (a) => `Filtered population added: ${typeof a.matched === "number" ? a.matched : "?"} matched, ${Array.isArray(a.added) ? a.added.length : 0} added.`,
  GROUP_RULE_PROPOSE: (a) => `Rule v${typeof a.version === "number" ? a.version : "?"} proposed.`,
  GROUP_RULE_APPROVE: (a) => `Rule v${typeof a.version === "number" ? (a.version as number) : "?"} approved; membership proposals generated.`,
  GROUP_RULE_REJECT: () => "Rule change rejected.",
  GROUP_RULE_EVALUATE: () => "Rule re-evaluated; new deltas proposed.",
  GROUP_PROPOSAL_APPROVE: () => "Membership proposals approved and applied.",
  GROUP_PROPOSAL_REJECT: () => "Membership proposals rejected.",
};

function ActivityTab({ groupId, canSee }: { groupId: string; canSee: boolean }) {
  const [items, setItems] = useState<{ id: string; text: string; at: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canSee) return;
    setLoading(true); setError(null);
    api.admin.listAuditEvents({ entity_type: "group", page_size: 100 })
      .then((data) => {
        const rows = data.items
          .filter((e) => e.entity_id === groupId)
          .map((e) => {
            let after: Record<string, unknown> = {};
            try { after = e.after_state ? JSON.parse(e.after_state) : {}; } catch { /* keep empty */ }
            const say = ACTIVITY_SENTENCES[e.action];
            return { id: e.id, text: say ? say(after) : e.action, at: e.created_at };
          });
        setItems(rows);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load activity."))
      .finally(() => setLoading(false));
  }, [groupId, canSee]);

  if (!canSee) {
    return <p style={{ fontSize: 13, color: "#65737a" }}>Activity is unavailable for your role (audit viewing is permission-controlled server-side).</p>;
  }
  if (loading) return <p style={{ fontSize: 13, color: "#65737a" }}>Loading activity…</p>;
  if (error) return <Err message={error} />;
  if (items.length === 0) return <p style={{ fontSize: 13, color: "#65737a" }}>No recorded activity yet.</p>;
  return (
    <div className="panel"><div className="table-wrap"><table>
      <thead><tr><th>When</th><th>Activity</th></tr></thead>
      <tbody>
        {items.map((i) => (
          <tr key={i.id}><td>{new Date(i.at).toLocaleString()}</td><td>{i.text}</td></tr>
        ))}
      </tbody>
    </table></div></div>
  );
}
