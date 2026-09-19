import { useState, useEffect } from "react";
import { api, ExportFieldInfo } from "../api";

/* M1.1 Phase C — permission-aware export dialog, shared by People and Groups.
 * The server re-evaluates the population and intersects columns with field
 * permissions; this UI only chooses from the server-provided catalog and
 * downloads the resulting file. Disallowed columns are shown disabled with
 * the reason, never silently hidden. */

export type ExportPopulation =
  | { kind: "ids"; ids: string[] }
  | { kind: "filtered"; query: Record<string, unknown> }
  | { kind: "group"; groupId: string; groupName: string }
  | { kind: "all" };

export function ExportDialog({ title, subtitle, population, onClose }: {
  title: string;
  subtitle: string;
  population: ExportPopulation;
  onClose: () => void;
}) {
  const [fields, setFields] = useState<ExportFieldInfo[]>([]);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true); setError(null);
    api.exports.fields()
      .then((d) => {
        setFields(d.items);
        const next: Record<string, boolean> = {};
        for (const f of d.items) if (f.allowed) next[f.key] = true;
        setChecked(next);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load export fields."))
      .finally(() => setLoading(false));
  }, []);

  const toggle = (key: string) =>
    setChecked((s) => ({ ...s, [key]: !s[key] }));
  const selected = fields.filter((f) => f.allowed && checked[f.key]).map((f) => f.key);
  const blocked = fields.filter((f) => !f.allowed);

  const generate = async () => {
    setBusy(true); setError(null); setDone(null);
    try {
      const body: Record<string, unknown> =
        population.kind === "ids" ? { constituent_ids: population.ids }
        : population.kind === "filtered" ? { ...population.query }
        : population.kind === "group" ? { group_id: population.groupId }
        : {};
      body.fields = selected;
      const { blob, filename } = await api.exports.download(body);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      setDone(`Downloaded ${filename}. The export is audited server-side (population + columns, never row contents in the log).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: 12 }}>
      <div className="panel__heading"><div>
        <p className="eyebrow">Permission-aware export · XLSX</p>
        <h3>{title}</h3>
      </div><button type="button" className="quiet-button" onClick={onClose}>Close</button></div>
      <div style={{ padding: 12, display: "grid", gap: 10 }}>
        <p style={{ fontSize: 13, color: "#4f5c62", margin: 0 }}>{subtitle}</p>
        {error && <div className="note" style={{ background: "#fdeaea", borderLeftColor: "#c0392b", color: "#c0392b", margin: 0 }}>{error}</div>}
        {done && <div className="note" style={{ margin: 0 }}>{done}</div>}
        {loading ? <p style={{ fontSize: 13, color: "#65737a" }}>Loading columns…</p> : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "4px 16px" }}>
              {fields.filter((f) => f.allowed).map((f) => (
                <label key={f.key} style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 13 }}>
                  <input type="checkbox" checked={!!checked[f.key]} onChange={() => toggle(f.key)} />
                  {f.label}
                </label>
              ))}
            </div>
            {blocked.length > 0 && (
              <div style={{ fontSize: 12, color: "#68777e" }}>
                Not available for your role: {blocked.map((f) => `${f.label} (needs ${f.requires?.join(", ") ?? "permission"})`).join(" · ")}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <button type="button" className="quiet-button" disabled={busy || selected.length === 0} onClick={generate}>
                {busy ? "Generating…" : `Export Excel (${selected.length} columns)`}
              </button>
              <span style={{ fontSize: 12, color: "#68777e" }}>
                {selected.length} of {fields.filter((f) => f.allowed).length} columns · population re-evaluated server-side at generation
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export function canExport(user: { is_superuser: boolean; permissions: string[] } | null): boolean {
  return !!user && (user.is_superuser || user.permissions.includes("constituents.export"));
}
