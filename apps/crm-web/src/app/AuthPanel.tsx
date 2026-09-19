import { useState } from "react";
import { api, AuthUser } from "../api";

/** Shared staff sign-in panel (dev password sign-in per ADR-003).
 *  Used by People and Administration so every protected page can
 *  authenticate in place instead of dead-ending. */
export function AuthPanel({ user, onAuthChange }: { user: AuthUser | null; onAuthChange: () => void }) {
  const [email, setEmail] = useState("staff@iitgn.ac.in");
  const [password, setPassword] = useState("staff123");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (user) {
    return (
      <div className="note" style={{marginTop:0, marginBottom:16}}>
        Signed in as <strong>{user.full_name}</strong> ({user.email}) · roles: {user.roles.join(", ") || "—"}{" "}
        <button
          type="button"
          className="quiet-button"
          style={{marginLeft:8}}
          onClick={() => { api.auth.logout(); onAuthChange(); }}
        >
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className="panel" style={{marginBottom:16}}>
      <div className="panel__heading"><div><p className="eyebrow">M1 · Server-side auth (dev sign-in)</p><h3>Staff sign-in</h3></div><span className="status status--live">Live</span></div>
      <div style={{padding:16, display:"flex", gap:12, flexWrap:"wrap", alignItems:"flexEnd"}}>
        <div style={{minWidth:220}}>
          <label style={{display:"block",fontSize:11,color:"#68777e",marginBottom:4}}>Email</label>
          <input type="text" value={email} onChange={(e) => setEmail(e.target.value)} style={{width:"100%",padding:"8px 12px",fontSize:14,border:"1px solid #cfd4d2",borderRadius:4}} />
        </div>
        <div style={{minWidth:180}}>
          <label style={{display:"block",fontSize:11,color:"#68777e",marginBottom:4}}>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{width:"100%",padding:"8px 12px",fontSize:14,border:"1px solid #cfd4d2",borderRadius:4}} />
        </div>
        <button
          type="button"
          disabled={busy}
          className="quiet-button"
          onClick={async () => {
            setBusy(true); setMsg(null);
            try { await api.auth.login(email, password); onAuthChange(); }
            catch (e) { setMsg(e instanceof Error ? e.message : "Sign-in failed"); }
            finally { setBusy(false); }
          }}
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {msg && <span style={{fontSize:13,color:"#c0392b"}}>{msg}</span>}
      </div>
      <div className="panel__footer">Dev-only password sign-in (see ADR-003). Production uses Sign in with Google once IITGN provides the OAuth client ID. Seeded dev accounts: staff@iitgn.ac.in / staff123 · viewer@iitgn.ac.in / viewer123 · finance@iitgn.ac.in / finance123 · admin@iitgn.ac.in / admin123. Tokens are stored only in this browser.</div>
    </div>
  );
}
