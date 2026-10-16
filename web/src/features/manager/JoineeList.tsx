import BlurTitle from "../../components/BlurTitle";
import { useEffect, useState } from "react";
import PathBar from "../../components/PathBar";
import { fmtDate, initials, plural, today } from "../../lib/format";
import { managerApi } from "../../services/manager";
import type { JoineeRow } from "../../types";
import PlanBuilder from "./PlanBuilder";

export default function JoineeList() {
  const [rows, setRows] = useState<JoineeRow[] | null>(null);
  const [invite, setInvite] = useState<string | undefined>();
  const [open, setOpen] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const load = () => managerApi.listJoinees().then(setRows);
  useEffect(() => void load(), []);

  if (open) return <PlanBuilder planId={open} invitePath={invite} onBack={() => { setOpen(null); setInvite(undefined); load(); }} />;
  if (!rows) return null;

  const behind = rows.filter((r) => r.metrics.total_overdue_items > 0).length;
  const drafts = rows.filter((r) => r.status === "DRAFT").length;
  const summary = !rows.length ? "Add your first joinee to start their onboarding plan."
    : [plural(rows.length, "joinee"), behind && `${behind} with overdue items`, drafts && `${plural(drafts, "plan")} still in draft`].filter(Boolean).join(", ") + ".";

  return (
    <section>
      <div className="page-head">
        <div>
          <BlurTitle text="My joinees" />
          <p className="lede">{summary}</p>
        </div>
        {!adding && <button className="primary" onClick={() => setAdding(true)}>Add joinee</button>}
      </div>
      {adding && <AddJoinee onCancel={() => setAdding(false)} onDone={(planId, path) => { setAdding(false); setInvite(path); setOpen(planId); }} />}

      <ul className="joinees">
        {rows.map((r) => {
          const m = r.metrics;
          return (
            <li key={r.id} className={m.total_overdue_items ? "behind" : ""}>
              <span className="avatar" aria-hidden="true">{initials(r.full_name)}</span>
              <div className="who-col">
                <strong>{r.full_name}</strong>
                <span className="muted">{r.job_title}, {r.team}</span>
                <span className="muted small">Starts {fmtDate(r.start_date)}</span>
              </div>
              <div className="path-col">
                {r.status === "DRAFT" ? <span className="muted">Plan in draft. Your joinee can't see it yet.</span> : <PathBar start={r.start_date!} tasks={r.tasks} compact />}
              </div>
              <div className="num-col">
                {r.status !== "DRAFT" && <>
                  <strong className="big">{m.task_completion_percentage ?? 0}%</strong>
                  {m.total_overdue_items > 0 ? <span className="late">{m.total_overdue_items} overdue</span> : <span className="muted">On track</span>}
                </>}
              </div>
              <button className={r.status === "DRAFT" ? "primary" : ""} onClick={() => setOpen(r.id)}>
                {r.status === "DRAFT" ? "Continue plan" : "Open plan"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function AddJoinee({ onDone, onCancel }: { onDone: (planId: string, invitePath: string) => void; onCancel: () => void }) {
  const [f, setF] = useState({ full_name: "", email: "", job_title: "", team: "", start_date: today() });
  const [err, setErr] = useState("");
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    managerApi.addJoinee(f).then((r) => onDone(r.plan_id, r.invite_path), (e: Error) => setErr(e.message));
  };
  return (
    <form className="panel form" onSubmit={submit}>
      <h2>New joinee</h2>
      <div className="fields">
        <label>Full name<input required value={f.full_name} onChange={set("full_name")} autoFocus /></label>
        <label>Work email<input required type="email" value={f.email} onChange={set("email")} /></label>
        <label>Job title<input required value={f.job_title} onChange={set("job_title")} /></label>
        <label>Team<input required value={f.team} onChange={set("team")} /></label>
        <label>Start date<input required type="date" value={f.start_date} onChange={set("start_date")} /></label>
      </div>
      {err && <p className="error">{err}</p>}
      <div className="row">
        <button className="primary">Add joinee and start plan</button>
        <button type="button" className="link" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
