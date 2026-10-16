import { useState } from "react";
import BlurTitle from "../../components/BlurTitle";
import { authApi } from "../../services/auth";
import type { User } from "../../types";

export default function Login({ onDone }: { onDone: (u: User) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setErr("");
    authApi.login(email, password).then(onDone, (e: Error) => setErr(e.message)).finally(() => setBusy(false));
  };

  return (
    <main className="login">
      <div className="login-intro">
        <BlurTitle text="Your first 30 days, in one place." />
        <p className="lede">Your plan, the people to meet, and where to get IT, HR and workplace help.</p>
      </div>
      <form className="panel form login-form" onSubmit={submit}>
        <h2>Sign in</h2>
        <div className="stack">
          <label>Work email<input type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus /></label>
          <label>Password<input type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        </div>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="primary wide" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="muted small">First time here? Open the sign-up link your manager or admin sent you. Forgot your password? Ask an admin for a reset link.</p>
      </form>
    </main>
  );
}
