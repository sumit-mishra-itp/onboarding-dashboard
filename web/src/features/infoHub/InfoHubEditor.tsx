import BlurTitle from "../../components/BlurTitle";
import { useState } from "react";
import { fmtDate } from "../../lib/format";
import { useResource } from "../../lib/useResource";
import { infoHubApi } from "../../services/infoHub";
import type { InfoEntry, InfoEntryInput } from "../../types";

const blank: InfoEntryInput = { category: "", title: "", body_md: "", contact_email: null, link_url: null, display_order: 0, is_active: true };

/** HR/Admin: manage Info Hub entries. Hidden entries stay here but joinees and managers don't see them. */
export default function InfoHubEditor() {
  const { data: items, error, reload } = useResource(() => infoHubApi.list("", true));
  const [editing, setEditing] = useState<{ id?: string; entry: InfoEntryInput } | null>(null);
  if (!items) return error ? <p className="error">{error}</p> : null;

  const categories = [...new Set(items.map((i) => i.category))];
  const open = (i?: InfoEntry) =>
    setEditing(i ? { id: i.id, entry: { category: i.category, title: i.title, body_md: i.body_md, contact_email: i.contact_email,
      link_url: i.link_url, display_order: i.display_order, is_active: i.is_active } } : { entry: { ...blank, category: categories[0] ?? "" } });

  return (
    <section>
      <div className="page-head">
        <div>
          <BlurTitle text="Edit Info Hub" />
          <p className="lede">What every new joinee sees under Info Hub. Saving an entry marks it as checked today.</p>
        </div>
        {!editing && <button className="primary" onClick={() => open()}>New entry</button>}
      </div>
      {editing && (
        <EntryForm key={editing.id ?? "new"} id={editing.id} initial={editing.entry} categories={categories}
          onClose={() => setEditing(null)} onSaved={() => { setEditing(null); reload(); }} />
      )}
      {categories.map((c) => (
        <section className="block" key={c}>
          <h2>{c}</h2>
          <ul className="tasks">
            {items.filter((i) => i.category === c).map((i) => (
              <li key={i.id} className="task">
                <div className="task-body">
                  <div className="task-title">{i.title}{!i.is_active && <span className="flag">Hidden</span>}</div>
                  <p className="task-desc">{i.body_md.slice(0, 160)}{i.body_md.length > 160 && "…"}</p>
                </div>
                <div className="task-meta">
                  <span className="muted small">Checked {fmtDate(i.last_reviewed_date)}</span>
                  <button onClick={() => open(i)}>Edit</button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}

function EntryForm({ id, initial, categories, onClose, onSaved }: {
  id?: string; initial: InfoEntryInput; categories: string[]; onClose: () => void; onSaved: () => void;
}) {
  const [f, setF] = useState(initial);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = <K extends keyof InfoEntryInput>(k: K, v: InfoEntryInput[K]) => setF({ ...f, [k]: v });
  const text = (k: "category" | "title" | "body_md") => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => set(k, e.target.value);
  const optional = (k: "contact_email" | "link_url") => (e: React.ChangeEvent<HTMLInputElement>) => set(k, e.target.value.trim() || null);

  const act = (p: Promise<unknown>) => {
    setBusy(true); setErr("");
    p.then(onSaved, (e: Error) => setErr(e.message)).finally(() => setBusy(false));
  };
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    act(id ? infoHubApi.update(id, f) : infoHubApi.create(f));
  };
  const remove = () => {
    if (id && confirm(`Delete "${f.title}" for good? To take it down for a while, untick "Visible" instead.`)) act(infoHubApi.remove(id));
  };

  return (
    <form className="panel form" onSubmit={submit}>
      <h2>{id ? "Edit entry" : "New entry"}</h2>
      <div className="fields">
        <label>Category<input required maxLength={60} list="info-categories" value={f.category} onChange={text("category")} /></label>
        <datalist id="info-categories">{categories.map((c) => <option key={c} value={c} />)}</datalist>
        <label>Title<input required maxLength={200} value={f.title} onChange={text("title")} autoFocus /></label>
        <label>Contact email (optional)<input type="email" value={f.contact_email ?? ""} onChange={optional("contact_email")} /></label>
        <label>Link (optional)<input type="url" placeholder="https://" value={f.link_url ?? ""} onChange={optional("link_url")} /></label>
        <label>Order in category<input type="number" min={0} max={10000} value={f.display_order} onChange={(e) => set("display_order", +e.target.value)} /></label>
        <label className="check-field"><input type="checkbox" checked={f.is_active} onChange={(e) => set("is_active", e.target.checked)} /> Visible to everyone</label>
      </div>
      <label>Details<textarea required rows={6} maxLength={10000} value={f.body_md} onChange={text("body_md")} /></label>
      {err && <p className="error" role="alert">{err}</p>}
      <div className="row">
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="link" onClick={onClose}>Cancel</button>
        {id && <button type="button" className="remove" onClick={remove} disabled={busy}>Delete</button>}
      </div>
    </form>
  );
}
