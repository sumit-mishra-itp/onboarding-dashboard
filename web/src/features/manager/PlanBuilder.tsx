import { useEffect, useState } from "react";
import PathBar from "../../components/PathBar";
import ShareLink from "../../components/ShareLink";
import { fmtDate, label, plural, today } from "../../lib/format";
import { managerApi } from "../../services/manager";
import { CATEGORIES, PRIORITIES, type Bundle, type Cert, type Conn, type Task } from "../../types";

const blankTask = (week: number): Task => ({
  title: "", description: "", category: "TECHNICAL_SETUP", week_no: week, day_offset: (week - 1) * 7, priority: "MEDIUM",
  subtasks: [], is_ai_generated: false, is_modified_by_manager: false,
});
const blankCert = (): Cert => ({ name: "", provider: "", url: "", deadline: today(), is_mandatory: true });
const blankConn = (): Conn => ({ contact_name: "", contact_email: "", contact_title: "", reason: "" });

// Generate, edit and approve on one screen (BRD usability NFR).
export default function PlanBuilder({ planId, invitePath, onBack }: { planId: string; invitePath?: string; onBack: () => void }) {
  const [b, setB] = useState<Bundle | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [certs, setCerts] = useState<Cert[]>([]);
  const [conns, setConns] = useState<Conn[]>([]);
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [link, setLink] = useState(invitePath ?? "");

  const show = (x: Bundle) => { setB(x); setTasks(x.tasks); setCerts(x.certifications); setConns(x.connections); };
  useEffect(() => void managerApi.getPlan(planId).then(show), [planId]);
  if (!b) return null;
  const draft = b.plan.status === "DRAFT";

  const run = async (what: string, fn: () => Promise<void>) => {
    setBusy(what); setMsg(null);
    try { await fn(); } catch (e: any) { setMsg({ kind: "error", text: e.message }); } finally { setBusy(""); }
  };
  const save = () => managerApi.savePlan(planId, { tasks, certifications: certs, connections: conns });

  const generate = () => run("ai", async () => {
    const r = await managerApi.draftTasks(planId, brief);
    // A regenerate replaces unsaved AI rows; saved and manual rows stay.
    setTasks([...tasks.filter((t) => t.id || !t.is_ai_generated), ...r.tasks]);
    setMsg({ kind: "ok", text: `Drafted ${plural(r.tasks.length, "task")}. Review each one before you assign the plan.` });
  });
  const onSave = () => run("save", async () => { show(await save()); setMsg({ kind: "ok", text: draft ? "Draft saved." : "Changes saved." }); });
  const onAssign = () => {
    if (!confirm(`Assign this plan to ${b.plan.full_name}? They'll see every task straight away.`)) return;
    run("assign", async () => {
      await save();
      show(await managerApi.assignPlan(planId));
      setMsg({ kind: "ok", text: "Plan assigned. Due dates now count from the start date." });
    });
  };

  const reinvite = () => run("invite", async () => setLink((await managerApi.reinvite(planId)).invite_path));

  const edit = <T,>(list: T[], setList: (l: T[]) => void) => (i: number, patch: Partial<T>) =>
    setList(list.map((x, j) => (j === i ? { ...x, ...patch } : x)));
  // Editing an AI row marks it modified: that feeds the BRD §16 edit-rate metric.
  const editTask = (i: number, p: Partial<Task>) =>
    edit(tasks, setTasks)(i, { ...p, is_modified_by_manager: tasks[i].is_ai_generated || tasks[i].is_modified_by_manager });
  const editCert = edit(certs, setCerts);
  const editConn = edit(conns, setConns);
  const m = b.metrics;
  const unreviewed = tasks.filter((t) => t.is_ai_generated && !t.is_modified_by_manager && !t.id).length;

  return (
    <section className="builder">
      <button className="link back" onClick={onBack}>Back to my joinees</button>
      <div className="page-head">
        <div>
          <h1>{b.plan.full_name} <span className={`badge ${b.plan.status}`}>{draft ? "Draft" : "Assigned"}</span></h1>
          <p className="lede">{b.plan.job_title}, {b.plan.team}. Starts {fmtDate(b.plan.start_date)}.</p>
        </div>
        {!draft && (
          <p className="progress-line">
            <strong>{m.task_completion_percentage ?? 0}%</strong> of tasks done
            {m.total_mandatory_certs > 0 && `, ${m.completed_mandatory_certs} of ${m.total_mandatory_certs} required certifications`}
            {m.total_connections > 0 && `, ${m.met_connections} of ${m.total_connections} people met`}
            {m.total_overdue_items > 0 && <>, <span className="late">{m.total_overdue_items} overdue</span></>}.
          </p>
        )}
      </div>
      {link && <ShareLink path={link} who={b.plan.full_name ?? "your joinee"} onClose={() => setLink("")} />}
      {!draft && <PathBar start={b.plan.start_date!} tasks={b.tasks} />}

      <div className="layout">
        <div className="main-col">
          <section className="panel ai">
            <h2>Draft tasks from a brief</h2>
            <p className="muted small">Describe the role in a few sentences. Only the job title, team, plan length and this brief are sent to the AI, never names or emails. Nothing reaches your joinee until you assign the plan.</p>
            <textarea rows={3} placeholder="Senior backend engineer joining Payments. Java 21 and Kafka. Joins the on-call rotation from week 3."
              value={brief} onChange={(e) => setBrief(e.target.value)} aria-label="Role brief" />
            <div className="row">
              <button onClick={generate} disabled={!!busy || brief.trim().length < 10}>{busy === "ai" ? "Drafting, up to 20 seconds…" : "Draft tasks"}</button>
              <span className="muted small">Or add tasks yourself below.</span>
            </div>
          </section>

          <section className="block">
            <h2>Tasks <span className="count">{plural(tasks.length, "task")}</span></h2>
            {unreviewed > 0 && <p className="hint">{plural(unreviewed, "suggested task")} still to review. Edit or delete anything that doesn't fit.</p>}
            {[1, 2, 3, 4].map((w) => (
              <div className="week" key={w}>
                <div className="week-head">
                  <h3>Week {w}</h3>
                  <button className="link" onClick={() => setTasks([...tasks, blankTask(w)])}>Add task</button>
                </div>
                {tasks.map((t, i) => t.week_no !== w ? null : (
                  <div key={t.id ?? `new-${i}`} className={`task-edit${t.is_ai_generated && !t.is_modified_by_manager && !t.id ? " suggested" : ""}`}>
                    <div className="te-main">
                      <input className="te-title" value={t.title} placeholder="Task title" aria-label="Task title" onChange={(e) => editTask(i, { title: e.target.value })} />
                      <input className="te-desc" value={t.description} placeholder="What does done look like? (optional)" aria-label="Description" onChange={(e) => editTask(i, { description: e.target.value })} />
                      {t.subtasks.length > 0 && <ul className="subtasks">{t.subtasks.map((s) => <li key={s}>{s}</li>)}</ul>}
                      {!draft && t.status && (
                        <p className="small"><span className={`status-text s-${t.status}`}>{label(t.status)}</span>{t.due_date && `, due ${fmtDate(t.due_date)}`}{t.joinee_notes && <span className="note">: “{t.joinee_notes}”</span>}</p>
                      )}
                    </div>
                    <div className="te-fields">
                      <label>Week<select value={t.week_no} onChange={(e) => editTask(i, { week_no: +e.target.value })}>{[1, 2, 3, 4].map((n) => <option key={n}>{n}</option>)}</select></label>
                      <label title="Days after the start date. 0 is the first day.">Day<input type="number" min={0} max={30} value={t.day_offset} onChange={(e) => editTask(i, { day_offset: +e.target.value })} /></label>
                      <label>Category<select value={t.category} onChange={(e) => editTask(i, { category: e.target.value })}>{CATEGORIES.map((c) => <option key={c} value={c}>{label(c)}</option>)}</select></label>
                      <label>Priority<select value={t.priority} onChange={(e) => editTask(i, { priority: e.target.value })}>{PRIORITIES.map((p) => <option key={p} value={p}>{label(p)}</option>)}</select></label>
                      <button className="remove" aria-label={`Remove ${t.title || "task"}`} onClick={() => setTasks(tasks.filter((_, j) => j !== i))}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </section>
        </div>

        <aside className="side-col">
          <section className="block">
            <h2>Certifications</h2>
            {!certs.length && <p className="muted small">Mandatory compliance courses, with a hard deadline.</p>}
            {certs.map((c, i) => (
              <div className="side-item" key={c.id ?? `new-${i}`}>
                <input placeholder="Course name" aria-label="Course name" value={c.name} onChange={(e) => editCert(i, { name: e.target.value })} />
                <input placeholder="Provider" aria-label="Provider" value={c.provider} onChange={(e) => editCert(i, { provider: e.target.value })} />
                <input placeholder="Course link" aria-label="Course link" value={c.url} onChange={(e) => editCert(i, { url: e.target.value })} />
                <div className="row">
                  <label className="inline-field">Complete by<input type="date" value={c.deadline} onChange={(e) => editCert(i, { deadline: e.target.value })} /></label>
                  <label className="check-field"><input type="checkbox" checked={c.is_mandatory} onChange={(e) => editCert(i, { is_mandatory: e.target.checked })} /> Required</label>
                </div>
                <div className="row between">
                  {!draft ? <span className={c.is_completed ? "status-text s-DONE" : "muted small"}>{c.is_completed ? "Completed" : "Not completed yet"}</span> : <span />}
                  <button className="remove" onClick={() => setCerts(certs.filter((_, j) => j !== i))}>Remove</button>
                </div>
              </div>
            ))}
            <button className="link" onClick={() => setCerts([...certs, blankCert()])}>Add certification</button>
          </section>

          <section className="block">
            <h2>People to meet</h2>
            {!conns.length && <p className="muted small">The people your joinee should get to know in their first month.</p>}
            {conns.map((c, i) => (
              <div className="side-item" key={c.id ?? `new-${i}`}>
                <input placeholder="Name" aria-label="Name" value={c.contact_name} onChange={(e) => editConn(i, { contact_name: e.target.value })} />
                <input placeholder="Job title" aria-label="Job title" value={c.contact_title} onChange={(e) => editConn(i, { contact_title: e.target.value })} />
                <input placeholder="Email" aria-label="Email" value={c.contact_email} onChange={(e) => editConn(i, { contact_email: e.target.value })} />
                <input placeholder="Why they should meet" aria-label="Why they should meet" value={c.reason} onChange={(e) => editConn(i, { reason: e.target.value })} />
                <div className="row between">
                  {!draft ? <span className={c.status === "MET" ? "status-text s-DONE" : "muted small"}>{c.status && label(c.status)}</span> : <span />}
                  <button className="remove" onClick={() => setConns(conns.filter((_, j) => j !== i))}>Remove</button>
                </div>
              </div>
            ))}
            <button className="link" onClick={() => setConns([...conns, blankConn()])}>Add person</button>
          </section>
        </aside>
      </div>

      <div className="actions">
        {msg && <p className={msg.kind === "error" ? "error" : "ok"} role="status">{msg.text}</p>}
        <button className="link" onClick={reinvite} disabled={!!busy} title="For a joinee who hasn't set their password yet">New sign-up link</button>
        <button onClick={onSave} disabled={!!busy}>{busy === "save" ? "Saving…" : draft ? "Save draft" : "Save changes"}</button>
        {draft && <button className="primary" onClick={onAssign} disabled={!!busy || !tasks.length}>Assign plan to {b.plan.full_name?.split(" ")[0]}</button>}
      </div>
    </section>
  );
}
