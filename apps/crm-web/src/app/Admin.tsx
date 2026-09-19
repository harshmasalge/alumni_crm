import { useState, useEffect, useCallback } from "react";
import { api, AuthUser, AdminUser, AdminRole, AdminPermission, AuditEvent } from "../api";

type Tab = "users" | "roles" | "audit";

const inputStyle = { padding: "6px 10px", fontSize: 13, border: "1px solid #cfd4d2", borderRadius: 4 };

function Err({ message }: { message: string | null }) {
  if (!message) return null;
  const staleBackend = /not found/i.test(message);
  return (
    <div className="note" style={{ background: "#fdeaea", borderLeftColor: "#c0392b", color: "#c0392b", marginBottom: 16 }}>
      {message}
      {staleBackend && (
        <span> The API may be serving older code without the admin endpoints — restart it (<code>uvicorn app.main:app</code> in <code>apps/api</code>) and reload this page.</span>
      )}
    </div>
  );
}

function Forbidden({ message }: { message: string }) {
  return (
    <div className="panel">
      <div className="panel__heading"><div><p className="eyebrow">Restricted</p><h3>Administration</h3></div></div>
      <div style={{ padding: 16, color: "#65737a", fontSize: 14 }}>
        {message} Sign in as an administrator (e.g. admin@iitgn.ac.in). Restrictions are enforced server-side.
      </div>
    </div>
  );
}

export function Admin({ user }: { user: AuthUser }) {
  const [tab, setTab] = useState<Tab>("users");
  const canAdmin = user.is_superuser || user.permissions.some((p) => p.startsWith("admin."));

  if (!canAdmin) return <Forbidden message="Your account has no administration permissions. " />;

  return (
    <section className="module-preview" style={{ maxWidth: 1100 }}>
      <p className="eyebrow">M1 · Live administration</p>
      <h2>Administration</h2>
      <div className="note">
        <strong>Live:</strong> users, roles, permissions, and the audit log are served by the
        PostgreSQL-backed API and gated server-side (<code>admin.users</code>, <code>admin.roles</code>,{' '}
        <code>admin.audit</code>). Per ADR-003, new users are email-allowlist entries — no passwords are stored.
      </div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["users", "roles", "audit"] as Tab[]).map((t) => (
          <button key={t} type="button" className="quiet-button" disabled={tab === t}
            onClick={() => setTab(t)}>
            {t === "users" ? "Users" : t === "roles" ? "Roles & permissions" : "Audit log"}
          </button>
        ))}
      </div>
      {tab === "users" && <UsersTab />}
      {tab === "roles" && <RolesTab />}
      {tab === "audit" && <AuditTab />}
    </section>
  );
}

function UsersTab() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [newName, setNewName] = useState("");
  const [newRoles, setNewRoles] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [users, allRoles] = await Promise.all([
        api.admin.listUsers({ q: q || undefined, page, page_size: 20 }),
        api.admin.listRoles().catch(() => [] as AdminRole[]),
      ]);
      setItems(users.items); setTotal(users.total); setRoles(allRoles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
      setItems([]); setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [q, page]);

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [load]);

  const refreshSelected = async (id: string) => {
    const data = await api.admin.listUsers({ page: 1, page_size: 100 });
    const found = data.items.find((u) => u.id === id) ?? null;
    setSelected(found);
  };

  const create = async () => {
    if (!newEmail.trim() || !newName.trim()) { setError("Email and full name are required."); return; }
    setBusy(true); setError(null);
    try {
      await api.admin.createUser({ email: newEmail.trim(), full_name: newName.trim(), role_ids: newRoles });
      setNewEmail(""); setNewName(""); setNewRoles([]); setPage(1);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create user");
    } finally {
      setBusy(false);
    }
  };

  const toggleRole = (id: string) =>
    setNewRoles((r) => (r.includes(id) ? r.filter((x) => x !== id) : [...r, id]));

  const setActive = async (u: AdminUser, active: boolean) => {
    setBusy(true); setError(null);
    try {
      const updated = await api.admin.updateUser(u.id, { is_active: active });
      setSelected(updated); await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update user");
    } finally {
      setBusy(false);
    }
  };

  const saveRoles = async (u: AdminUser, roleIds: string[]) => {
    setBusy(true); setError(null);
    try {
      const updated = await api.admin.setUserRoles(u.id, roleIds);
      setSelected(updated); await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update roles");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Err message={error} />
      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="panel__heading"><div><p className="eyebrow">Allowlist</p><h3>Add user</h3></div></div>
        <div style={{ padding: 16, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flexEnd" }}>
          <input type="text" placeholder="email@iitgn.ac.in" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} style={{ ...inputStyle, minWidth: 220 }} />
          <input type="text" placeholder="Full name" value={newName} onChange={(e) => setNewName(e.target.value)} style={{ ...inputStyle, minWidth: 180 }} />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", fontSize: 13 }}>
            {roles.map((r) => (
              <label key={r.id} style={{ display: "flex", gap: 4, alignItems: "center" }}>
                <input type="checkbox" checked={newRoles.includes(r.id)} onChange={() => toggleRole(r.id)} /> {r.name}
              </label>
            ))}
          </div>
          <button type="button" className="quiet-button" disabled={busy} onClick={create}>Add user</button>
        </div>
        <div className="panel__footer">The person signs in with Google; access is granted because this email is listed here with roles.</div>
      </div>

      <div className="panel">
        <div style={{ padding: 16 }}>
          <input type="text" placeholder="Search email or name…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} style={{ ...inputStyle, width: "100%", maxWidth: 360 }} />
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Email</th><th>Name</th><th>Active</th><th>Superuser</th><th>Roles</th></tr></thead>
            <tbody>
              {items.length === 0 && !loading ? (
                <tr><td colSpan={5} style={{ textAlign: "center", color: "#65737a", padding: 24 }}>No users match.</td></tr>
              ) : items.map((u) => (
                <tr key={u.id} onClick={() => setSelected(u)} style={{ cursor: "pointer", background: selected?.id === u.id ? "#f7f3eb" : undefined }}>
                  <td><strong>{u.email}</strong></td>
                  <td>{u.full_name}</td>
                  <td>{u.is_active ? "✓" : "—"}</td>
                  <td>{u.is_superuser ? "✓" : "—"}</td>
                  <td>{u.roles.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="panel__footer" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Showing {items.length} of {total}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="quiet-button" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button>
              <button className="quiet-button" disabled={page * 20 >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>

      {selected && (
        <UserDetail user={selected} allRoles={roles} busy={busy}
          onToggleActive={(a) => setActive(selected, a)}
          onSaveRoles={(ids) => saveRoles(selected, ids)}
          onClose={() => setSelected(null)}
          onRefresh={() => refreshSelected(selected.id)} />
      )}
    </>
  );
}

function UserDetail({ user, allRoles, busy, onToggleActive, onSaveRoles, onClose, onRefresh }: {
  user: AdminUser; allRoles: AdminRole[]; busy: boolean;
  onToggleActive: (active: boolean) => void; onSaveRoles: (ids: string[]) => void;
  onClose: () => void; onRefresh: () => void;
}) {
  const [checked, setChecked] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const ids = allRoles.filter((r) => user.roles.includes(r.name)).map((r) => r.id);
    setChecked(ids); setLoaded(true);
  }, [user.id, allRoles]);

  if (!loaded) return null;
  return (
    <div className="panel" style={{ marginTop: 16 }}>
      <div className="panel__heading">
        <div><p className="eyebrow">User detail</p><h3>{user.email}</h3></div>
        <button className="quiet-button" onClick={onClose}>Close</button>
      </div>
      <div style={{ padding: 16, display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 16px", fontSize: 14 }}>
        <dt>Full name</dt><dd>{user.full_name}</dd>
        <dt>Status</dt><dd>{user.is_active ? "Active" : "Inactive"}{user.is_superuser ? " · Superuser" : ""}</dd>
        <dt>Roles</dt><dd>{user.roles.join(", ") || "—"}</dd>
      </div>
      <div style={{ padding: 16, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", borderTop: "1px solid #ecece6" }}>
        <button className="quiet-button" disabled={busy} onClick={() => onToggleActive(!user.is_active)}>
          {user.is_active ? "Deactivate" : "Reactivate"}
        </button>
        <span style={{ fontSize: 13, color: "#65737a" }}>Roles:</span>
        {allRoles.map((r) => (
          <label key={r.id} style={{ display: "flex", gap: 4, alignItems: "center", fontSize: 13 }}>
            <input type="checkbox" checked={checked.includes(r.id)}
              onChange={() => setChecked((c) => (c.includes(r.id) ? c.filter((x) => x !== r.id) : [...c, r.id]))} /> {r.name}
          </label>
        ))}
        <button className="quiet-button" disabled={busy} onClick={() => onSaveRoles(checked)}>Save roles</button>
        <button className="quiet-button" disabled={busy} onClick={onRefresh}>Refresh</button>
      </div>
      <div className="panel__footer">Deactivating or demoting the last active superuser is refused server-side (400).</div>
    </div>
  );
}

function RolesTab() {
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [catalog, setCatalog] = useState<AdminPermission[]>([]);
  const [selected, setSelected] = useState<AdminRole | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [r, c] = await Promise.all([api.admin.listRoles(), api.admin.listPermissions()]);
      setRoles(r); setCatalog(c); setError(null);
      if (selected) {
        const fresh = r.find((x) => x.id === selected.id) ?? null;
        setSelected(fresh);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load roles");
    }
  }, [selected?.id]);

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!selected || catalog.length === 0) return;
    setChecked(catalog.filter((p) => selected.permissions.includes(p.name)).map((p) => p.id));
  }, [selected?.id, catalog.length]);

  const create = async () => {
    if (!name.trim()) { setError("Role name is required."); return; }
    setBusy(true); setError(null);
    try {
      await api.admin.createRole({ name: name.trim(), description: desc.trim() || undefined });
      setName(""); setDesc("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create role");
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!selected) return;
    setBusy(true); setError(null);
    try {
      const updated = await api.admin.setRolePermissions(selected.id, checked);
      setSelected(updated);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save permissions");
    } finally {
      setBusy(false);
    }
  };

  const byModule = new Map<string, AdminPermission[]>();
  for (const p of catalog) {
    if (!byModule.has(p.module)) byModule.set(p.module, []);
    byModule.get(p.module)!.push(p);
  }

  return (
    <>
      <Err message={error} />
      <div className="two-column">
        <div className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Roles</p><h3>All roles ({roles.length})</h3></div></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Permissions</th></tr></thead>
              <tbody>
                {roles.map((r) => (
                  <tr key={r.id} onClick={() => setSelected(r)} style={{ cursor: "pointer", background: selected?.id === r.id ? "#f7f3eb" : undefined }}>
                    <td><strong>{r.name}</strong><br /><span style={{ fontSize: 12, color: "#65737a" }}>{r.description || ""}</span></td>
                    <td>{r.permissions.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: 12, borderTop: "1px solid #ecece6", display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input type="text" placeholder="New role name" value={name} onChange={(e) => setName(e.target.value)} style={{ ...inputStyle, flex: "1 1 140px" }} />
            <input type="text" placeholder="Description" value={desc} onChange={(e) => setDesc(e.target.value)} style={{ ...inputStyle, flex: "2 1 200px" }} />
            <button type="button" className="quiet-button" disabled={busy} onClick={create}>Add role</button>
          </div>
        </div>
        <div className="panel">
          <div className="panel__heading"><div><p className="eyebrow">Permission matrix</p><h3>{selected ? selected.name : "Select a role"}</h3></div></div>
          {!selected ? (
            <div style={{ padding: 16, color: "#65737a", fontSize: 14 }}>Pick a role to review or change its permission matrix. Changes are audited.</div>
          ) : (
            <div style={{ padding: 16 }}>
              {[...byModule.entries()].map(([mod, perms]) => (
                <div key={mod} style={{ marginBottom: 12 }}>
                  <p className="eyebrow">{mod}</p>
                  {perms.map((p) => (
                    <label key={p.id} style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 13, padding: "4px 0" }} title={p.description || p.name}>
                      <input type="checkbox" checked={checked.includes(p.id)}
                        onChange={() => setChecked((c) => (c.includes(p.id) ? c.filter((x) => x !== p.id) : [...c, p.id]))} />
                      <span><code>{p.name}</code> <span style={{ color: "#65737a" }}>— {p.description || p.action}</span></span>
                    </label>
                  ))}
                </div>
              ))}
              <button type="button" className="quiet-button" disabled={busy} onClick={save}>Save matrix</button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function AuditTab() {
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.admin.listAuditEvents({
        entity_type: entityType || undefined,
        action: action || undefined,
        page, page_size: 20,
      });
      setItems(data.items); setTotal(data.total); setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit log");
      setItems([]); setTotal(0);
    }
  }, [entityType, action, page]);

  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [load]);

  const fmt = (s: string | null) => (s ? new Date(s).toLocaleString() : "—");

  return (
    <>
      <Err message={error} />
      <div className="panel">
        <div style={{ padding: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input type="text" placeholder="entity_type (e.g., user, role, constituent)" value={entityType}
            onChange={(e) => { setEntityType(e.target.value); setPage(1); }} style={{ ...inputStyle, minWidth: 240 }} />
          <input type="text" placeholder="action (e.g., CREATE, UPDATE, READ_PROFILE)" value={action}
            onChange={(e) => { setAction(e.target.value); setPage(1); }} style={{ ...inputStyle, minWidth: 240 }} />
          <button type="button" className="quiet-button" onClick={load}>Apply</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Time</th><th>Actor</th><th>Entity</th><th>Action</th><th>IP</th><th>Request</th></tr></thead>
            <tbody>
              {items.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: "center", color: "#65737a", padding: 24 }}>No audit events match.</td></tr>
              ) : items.map((a) => (
                <tr key={a.id}>
                  <td>{fmt(a.created_at)}</td>
                  <td>{a.actor_type} ({a.actor_id?.slice(0, 8) || "—"})</td>
                  <td>{a.entity_type} ({a.entity_id.slice(0, 8)})</td>
                  <td>{a.action}</td>
                  <td>{a.ip_address || "—"}</td>
                  <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis" }}>{a.request_id || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {total > 0 && (
          <div className="panel__footer" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Showing {items.length} of {total}</span>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="quiet-button" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Previous</button>
              <button className="quiet-button" disabled={page * 20 >= total} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>
        )}
      </div>
      <div className="note" style={{ marginTop: 16 }}>
        Append-only: rows are never edited or deleted. Constituent reads, stale-list views, and every admin write are recorded with actor, IP, and request id.
      </div>
    </>
  );
}
