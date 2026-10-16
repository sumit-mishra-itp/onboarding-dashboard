import BlurTitle from "../../components/BlurTitle";
import { useState } from "react";
import ShareLink from "../../components/ShareLink";
import { fmtDate, roleLabel } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { adminApi } from "../../services/admin";
import { STAFF_ROLES, type AdminUserRow, type Role, type User } from "../../types";

/** Admin: invite staff, change roles, deactivate, issue password reset links. Joinees are added by their manager. */
export default function Users({ me }: { me: User }) {
  const { data: rows, error, reload } = useResource(adminApi.listUsers);
  const [adding, setAdding] = useState(false);
  const [link, setLink] = useState<{ path: string; who: string } | null>(null);
  const [err, setErr] = useState("");
  if (!rows) return error ? <p className="error">{error}</p> : null;

  const act = (p: Promise<unknown>) => { setErr(""); p.then(reload, (e: Error) => setErr(e.message)); };
  const reset = (u: AdminUserRow) =>
    adminApi.resetLink(u.id).then((r) => setLink({ path: r.reset_path, who: u.full_name }), (e: Error) => setErr(e.message));

  return (
    <section>
      <div className="page-head">
        <div><BlurTitle text="Users" /><p className="lede">Invite managers, HR and admins. Managers add their own joinees.</p></div>
        {!adding && <button className="primary" onClick={() => setAdding(true)}>Invite user</button>}
      </div>
      {adding && <InviteForm onCancel={() => setAdding(false)} onDone={(path, who) => { setAdding(false); setLink({ path, who }); reload(); }} />}
      {link && <ShareLink path={link.path} who={link.who} onClose={() => setLink(null)} />}
      {err && <p className="error" role="alert">{err}</p>}

      <div className="block table-wrap">
        <table className="users">
          <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Last sign-in</th><th /></tr></thead>
          <tbody>
            {rows.map((u) => (
              <tr key={u.id} className={u.is_active ? "" : "muted"}>
                <td><strong>{u.full_name}</strong><br /><span className="muted small">{u.email}</span></td>
                <td>
                  {u.role === "JOINEE" ? "Joinee" : (
                    <select value={u.role} aria-label={`Role of ${u.full_name}`} disabled={u.id === me.id}
                      onChange={(e) => act(adminApi.updateUser(u.id, { role: e.target.value as Role }))}>
                      {STAFF_ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                    </select>
                  )}
                </td>
                <td>{!u.is_active ? "Deactivated" : u.has_password ? "Active" : "Invited"}</td>
                <td className="small">{u.last_login_at ? fmtDate(u.last_login_at) : "Never"}</td>
                <td className="row">
                  {u.is_active && <button onClick={() => reset(u)}>{u.has_password ? "Reset link" : "New invite link"}</button>}
                  {u.id !== me.id && (
                    <button className={u.is_active ? "remove" : ""} onClick={() => act(adminApi.updateUser(u.id, { is_active: !u.is_active }))}>
                      {u.is_active ? "Deactivate" : "Reactivate"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function InviteForm({ onDone, onCancel }: { onDone: (path: string, who: string) => void; onCancel: () => void }) {
  const [f, setF] = useState({ full_name: "", email: "", role: "MANAGER" as Role });
  const [err, setErr] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    adminApi.createUser(f).then((r) => onDone(r.invite_path, r.user.full_name), (e: Error) => setErr(e.message));
  };
  return (
    <form className="panel form" onSubmit={submit}>
      <h2>Invite a user</h2>
      <div className="fields">
        <label>Full name<input required maxLength={200} value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} autoFocus /></label>
        <label>Work email<input required type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></label>
        <label>Role<select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value as Role })}>
          {STAFF_ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
        </select></label>
      </div>
      {err && <p className="error" role="alert">{err}</p>}
      <div className="row">
        <button className="primary">Create and get invite link</button>
        <button type="button" className="link" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
