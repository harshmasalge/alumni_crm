/**
 * Phase 2 preview UI primitives.
 * Institutional, calm styling that reuses the existing M0/M1 design tokens
 * (panel, metric, table-wrap, note, status, quiet-button). No new palette.
 */
import { useState, type ReactNode } from "react";

export function PreviewBanner({ what, needs }: { what: string; needs: string }) {
  return (
    <div className="note" style={{ margin: "0 0 18px" }}>
      <strong>Preview — not production.</strong> {what} Backend capability required: {needs} No money,
      messages, or receipts move in this view; actions open an explanatory notice instead.
    </div>
  );
}

export function PageHead({
  eyebrow,
  title,
  blurb,
  badge,
}: {
  eyebrow: string;
  title: string;
  blurb: string;
  badge: ReactNode;
}) {
  return (
    <div style={{ marginBottom: 18 }}>
      <p className="eyebrow" style={{ margin: "0 0 4px" }}>{eyebrow}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0, fontFamily: 'Georgia, "Times New Roman", serif', fontWeight: 500, fontSize: 30 }}>{title}</h2>
        {badge}
      </div>
      <p style={{ color: "#52616a", lineHeight: 1.6, maxWidth: 860, margin: "8px 0 0" }}>{blurb}</p>
    </div>
  );
}

export function Kpis({ items }: { items: { label: string; value: string; detail: string }[] }) {
  return (
    <section className="metric-grid" aria-label="Key figures" style={{ marginTop: 0 }}>
      {items.map((k) => (
        <article className="metric" key={k.label}>
          <p>{k.label}</p>
          <strong>{k.value}</strong>
          <span>{k.detail}</span>
        </article>
      ))}
    </section>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly T[];
  active: T;
  onChange: (t: T) => void;
}) {
  return (
    <div role="tablist" aria-label="Module views" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
      {tabs.map((t) => (
        <button
          key={t}
          role="tab"
          aria-selected={active === t}
          type="button"
          onClick={() => onChange(t)}
          className="quiet-button"
          style={
            active === t
              ? { background: "#1f2d38", color: "#fff", borderColor: "#1f2d38" }
              : undefined
          }
        >
          {t}
        </button>
      ))}
    </div>
  );
}

export function Panel({
  eyebrow,
  title,
  badge,
  children,
  footer,
}: {
  eyebrow?: string;
  title: string;
  badge?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <article className="panel">
      <div className="panel__heading">
        <div>
          {eyebrow ? <p className="eyebrow" style={{ margin: 0 }}>{eyebrow}</p> : null}
          <h3>{title}</h3>
        </div>
        {badge}
      </div>
      {children}
      {footer ? <div className="panel__footer">{footer}</div> : null}
    </article>
  );
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: string }) {
  return (
    <div style={{ padding: "28px 20px", textAlign: "center", color: "#65737a" }}>
      <p style={{ margin: "0 0 6px", fontWeight: 700, color: "#3d4a52" }}>{title}</p>
      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55 }}>{body}</p>
      {action ? <p style={{ margin: "10px 0 0", fontSize: 13 }}>{action}</p> : null}
    </div>
  );
}

export function Bar({ valuePct }: { valuePct: number }) {
  const v = Math.max(0, Math.min(100, valuePct));
  return (
    <div aria-hidden="true" style={{ minWidth: 120 }}>
      <div style={{ height: 8, background: "#ecece6", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${v}%`, height: "100%", background: "#b96f2b" }} />
      </div>
      <span style={{ fontSize: 12, color: "#68777e" }}>{v}%</span>
    </div>
  );
}

export function PreviewAction({ label, explain }: { label: string; explain: string }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ display: "inline-block" }}>
      <button type="button" className="quiet-button" onClick={() => setOpen(true)}>
        {label}
      </button>
      {open ? (
        <span
          role="dialog"
          aria-label={`${label} unavailable`}
          style={{
            display: "block",
            marginTop: 8,
            padding: 12,
            background: "#f7f3eb",
            borderLeft: "3px solid #b96f2b",
            fontSize: 13,
            lineHeight: 1.5,
            color: "#4f5c62",
            maxWidth: 420,
          }}
        >
          <strong>Preview action — nothing was executed.</strong> {explain}{" "}
          <button
            type="button"
            className="quiet-button"
            style={{ marginLeft: 8 }}
            onClick={() => setOpen(false)}
          >
            Dismiss
          </button>
        </span>
      ) : null}
    </span>
  );
}

export function Timeline({ items }: { items: { time: string; title: string; body: string }[] }) {
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: "8px 20px 16px" }}>
      {items.map((it) => (
        <li
          key={`${it.time}-${it.title}`}
          style={{ display: "grid", gridTemplateColumns: "150px 1fr", gap: 12, padding: "10px 0", borderBottom: "1px solid #ecece6", fontSize: 13 }}
        >
          <span style={{ color: "#68777e" }}>{it.time}</span>
          <span>
            <strong style={{ display: "block", color: "#1f2d38" }}>{it.title}</strong>
            <span style={{ color: "#52616a" }}>{it.body}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
