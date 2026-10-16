import BlurTitle from "../../components/BlurTitle";
import { useState } from "react";
import { authApi } from "../../services/auth";
import type { User } from "../../types";

export const MIN_PASSWORD = 10;

/** Landing page for invite and reset links: /set-password#token=... */
export default function SetPassword({ onDone }: { onDone: (u: User) => void }) {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
  const [pw, setPw] = useState("");
  const [again, setAgain] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pw !== again) return setErr("The two passwords don't match.");
    setBusy(true); setErr("");
    authApi.setPassword(token, pw).then((u) => {
      window.history.replaceState(null, "", "/"); // drop the used token from the address bar
      onDone(u);
    }, (e: Error) => setErr(e.message)).finally(() => setBusy(false));
  };

  return (
    <main className="login single">
      <BlurTitle text="Set your password" />
      {!token ? <p className="error">This link is incomplete. Open the full link you were sent.</p> : (
        <form className="panel form login-form" onSubmit={submit}>
          <div className="stack">
            <label>New password<input type="password" required minLength={MIN_PASSWORD} maxLength={128} autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} autoFocus /></label>
            <label>Repeat it<input type="password" required autoComplete="new-password" value={again} onChange={(e) => setAgain(e.target.value)} /></label>
          </div>
          <p className="muted small">At least {MIN_PASSWORD} characters. A short phrase is easier to remember than a jumble.</p>
          {err && <p className="error" role="alert">{err}</p>}
          <button className="primary wide" disabled={busy}>{busy ? "Saving…" : "Set password and sign in"}</button>
        </form>
      )}
    </main>
  );
}
