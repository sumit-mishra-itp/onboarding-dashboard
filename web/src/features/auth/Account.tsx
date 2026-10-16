import BlurTitle from "../../components/BlurTitle";
import { useState } from "react";
import { roleLabel } from "../../lib/format";
import { authApi } from "../../services/auth";
import type { User } from "../../types";
import { MIN_PASSWORD } from "./SetPassword";

export default function Account({ user }: { user: User }) {
  const [f, setF] = useState({ current: "", next: "", again: "" });
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (f.next !== f.again) return setMsg({ kind: "error", text: "The two new passwords don't match." });
    authApi.changePassword(f.current, f.next).then(() => {
      setF({ current: "", next: "", again: "" });
      setMsg({ kind: "ok", text: "Password changed. You've been signed out on your other devices." });
    }, (e: Error) => setMsg({ kind: "error", text: e.message }));
  };

  return (
    <section>
      <div className="page-head"><div><BlurTitle text="Account" /><p className="lede">{user.full_name}, {user.email}. {roleLabel(user.role)}.</p></div></div>
      <form className="panel form" onSubmit={submit}>
        <h2>Change password</h2>
        <div className="fields">
          <label>Current password<input type="password" required autoComplete="current-password" value={f.current} onChange={set("current")} /></label>
          <label>New password<input type="password" required minLength={MIN_PASSWORD} maxLength={128} autoComplete="new-password" value={f.next} onChange={set("next")} /></label>
          <label>Repeat new password<input type="password" required autoComplete="new-password" value={f.again} onChange={set("again")} /></label>
        </div>
        {msg && <p className={msg.kind} role="status">{msg.text}</p>}
        <div className="row"><button className="primary">Change password</button></div>
      </form>
    </section>
  );
}
