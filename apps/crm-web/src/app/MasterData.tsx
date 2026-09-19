import { useState, useEffect, useCallback } from "react";
import { api, Taxonomy } from "../api";

/* M1.1 Phase A — staff-managed segmentation vocabularies.
 *
 * People-filter UI consumes these values; Administration manages them.
 * Write controls are gated on profile-write permission here for usability,
 * but enforcement is server-side (constituents.write). */

export const TAXONOMY_CATEGORIES = [
  { slug: "industry", label: "Industry", hint: "Seeded from real affiliation sectors; staff-curated." },
  { slug: "company_type", label: "Company type", hint: "PRIVATE / GOVERNMENT / ACADEMIC / STARTUP / OTHER starter set." },
  { slug: "function", label: "Function", hint: "Starts empty — no structured source in the data. Staff populate it." },
  { slug: "seniority_level", label: "Seniority", hint: "Starts empty — no structured source in the data. Staff populate it." },
];

export function MasterDataPanel({ canWrite }: { canWrite: boolean }) {
  const [category, setCategory] = useState("industry");
  const [items, setItems] = useState<Taxonomy[]>([]);
  const [includeInactive, setIncludeInactive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newValue, setNewValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.taxonomies.list({ category, include_inactive: includeInactive });
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load values.");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [category, includeInactive]);

  useEffect(() => { load(); }, [load]);

  const refresh = load;
  const add = async () => {
    if (!newValue.trim()) return;
    setError(null);
    try {
      await api.taxonomies.create({ category, value: newValue.trim() });
      setNewValue("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add value.");
    }
  };
  const toggleActive = async (t: Taxonomy) => {
    setError(null);
    try {
      await api.taxonomies.update(t.id, { is_active: !t.is_active });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update value.");
    }
  };
  const rename = async (t: Taxonomy) => {
    if (!editValue.trim()) { setEditingId(null); return; }
    setError(null);
    try {
      await api.taxonomies.update(t.id, { value: editValue.trim() });
      setEditingId(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not rename value.");
    }
  };
  const remove = async (t: Taxonomy) => {
    if (!window.confirm(`Delete “${t.value}”? Only possible while nothing references it.`)) return;
    setError(null);
    try {
      await api.taxonomies.remove(t.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete value.");
    }
  };

  const hint = TAXONOMY_CATEGORIES.find((c) => c.slug === category)?.hint;
  return (
    <div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        {TAXONOMY_CATEGORIES.map((c) => (
          <button key={c.slug} type="button" className="quiet-button" disabled={category === c.slug}
            onClick={() => setCategory(c.slug)}>{c.label}</button>
        ))}
        <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13, color: "#4f5c62", marginLeft: "auto" }}>
          <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
          Show deactivated
        </label>
      </div>
      {hint && <p style={{ fontSize: 12, color: "#68777e", margin: "0 0 8px" }}>{hint}</p>}
      {error && <div className="note" style={{ background: "#fdeaea", borderLeftColor: "#c0392b", color: "#c0392b", marginBottom: 8 }}>{error}</div>}
      {loading ? <p style={{ fontSize: 13, color: "#65737a" }}>Loading values…</p> : (
        <div className="table-wrap"><table>
          <thead><tr><th>Value</th><th>In use</th><th>Status</th>{canWrite && <th>Actions</th>}</tr></thead>
          <tbody>
            {items.length === 0 && <tr><td colSpan={canWrite ? 4 : 3} style={{ textAlign: "center", color: "#65737a", padding: 16 }}>No values yet — staff can add the first one below.</td></tr>}
            {items.map((t) => (
              <tr key={t.id}>
                <td>
                  {editingId === t.id ? (
                    <span style={{ display: "inline-flex", gap: 6 }}>
                      <input type="text" value={editValue} onChange={(e) => setEditValue(e.target.value)}
                        style={{ padding: "4px 8px", fontSize: 13, border: "1px solid #cfd4d2", borderRadius: 4 }} />
                      <button type="button" className="quiet-button" onClick={() => rename(t)}>Save</button>
                      <button type="button" className="quiet-button" onClick={() => setEditingId(null)}>Cancel</button>
                    </span>
                  ) : <strong>{t.value}</strong>}
                </td>
                <td>{t.usage_count} record{t.usage_count === 1 ? "" : "s"}</td>
                <td>{t.is_active ? "Active" : "Deactivated"}</td>
                {canWrite && (
                  <td>
                    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
                      <button type="button" className="quiet-button" onClick={() => { setEditingId(t.id); setEditValue(t.value); }}>Rename</button>
                      <button type="button" className="quiet-button" onClick={() => toggleActive(t)}>{t.is_active ? "Deactivate" : "Reactivate"}</button>
                      <button type="button" className="quiet-button" onClick={() => remove(t)}>Delete</button>
                    </span>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table></div>
      )}
      {canWrite ? (
        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <input type="text" value={newValue} onChange={(e) => setNewValue(e.target.value)} placeholder={`New ${category.replace("_", " ")} value…`}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
            style={{ flex: 1, minWidth: 180, padding: "6px 10px", fontSize: 13, border: "1px solid #cfd4d2", borderRadius: 4 }} />
          <button type="button" className="quiet-button" onClick={add}>Add value</button>
        </div>
      ) : (
        <p style={{ fontSize: 12, color: "#68777e" }}>Read-only for your role — editing needs profile write permission (enforced server-side).</p>
      )}
      <p style={{ fontSize: 12, color: "#68777e" }}>Referenced values cannot be deleted (the server reports the usage count); deactivation is always allowed and keeps existing records matching.</p>
    </div>
  );
}
