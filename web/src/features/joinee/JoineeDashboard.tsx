import BlurTitle from "../../components/BlurTitle";
import { useEffect, useState } from "react";
import PathBar from "../../components/PathBar";
import { daysSince, fmtDate, initials, label, plural, today } from "../../lib/format";
import { joineeApi } from "../../services/joinee";
import { CONN_STATUSES, TASK_STATUSES, type JoineeDashboard as Dash, type Task, type User } from "../../types";

export default function JoineeDashboard({ user }: { user: User }) {
  const [d, setD] = useState<Dash | null>(null);
  const [err, setErr] = useState("");
  const load = () => joineeApi.dashboard().then(setD);
  useEffect(() => void load(), []);
  const run = (p: Promise<unknown>) => { setErr(""); p.then(load, (e: Error) => setErr(e.message)); };

  if (!d) return null;
  const first = user.full_name.split(" ")[0];
  if (!d.plan) {
    return (
      <section className="hello">
        <BlurTitle text={`Welcome, ${first}.`} />
        <p className="lede">Your manager is still preparing your onboarding plan. It will appear here as soon as they assign it.</p>
        <p className="muted">Until then, the Info Hub covers IT access, accounts, HR and workplace basics.</p>
      </section>
    );
  }

  const t0 = today();
  const start = user.start_date!;
  const isOverdue = (t: Task) => t.status !== "DONE" && !!t.due_date && t.due_date < t0;
  const overdueTasks = d.tasks.filter(isOverdue);
  const overdueCerts = d.certifications.filter((c) => !c.is_completed && c.deadline < t0);
  const thisWeek = d.tasks.filter((t) => t.week_no === d.current_week && !isOverdue(t));
  const leftThisWeek = thisWeek.filter((t) => t.status !== "DONE").length;
  const overdue = d.metrics.total_overdue_items;
  const day = daysSince(start);

  const summary =
    day < 0 ? `You start on ${fmtDate(start)}. Here's what's planned.`
    : overdue > 0 ? `You have ${plural(overdue, "overdue item")} and ${plural(leftThisWeek, "task")} left this week.`
    : leftThisWeek > 0 ? `You're on track, with ${plural(leftThisWeek, "task")} left this week.`
    : "You're all caught up for this week.";

  const setStatus = (t: Task, status: string) => {
    const note = status === "BLOCKED" ? prompt("What's blocking you? Your manager will see this note.") ?? undefined : undefined;
    run(joineeApi.setTaskStatus(t.id!, status, note));
  };
  const taskRow = (t: Task) => (
    <li key={t.id} className={`task s-${t.status}`}>
      <button className="check" aria-label={t.status === "DONE" ? `Mark ${t.title} as not done` : `Mark ${t.title} as done`}
        aria-pressed={t.status === "DONE"} onClick={() => setStatus(t, t.status === "DONE" ? "TO_DO" : "DONE")} />
      <div className="task-body">
        <div className="task-title">{t.title}{t.priority === "HIGH" && <span className="flag">High priority</span>}</div>
        {t.description && <p className="task-desc">{t.description}</p>}
        {t.subtasks.length > 0 && <ul className="subtasks">{t.subtasks.map((s) => <li key={s}>{s}</li>)}</ul>}
        {t.status === "BLOCKED" && t.joinee_notes && <p className="note">Blocked: {t.joinee_notes}</p>}
      </div>
      <div className="task-meta">
        <span className={isOverdue(t) ? "due late" : "due"}>{isOverdue(t) ? "Was due " : "Due "}{fmtDate(t.due_date)}</span>
        <select className={`status s-${t.status}`} value={t.status} onChange={(e) => setStatus(t, e.target.value)} aria-label={`Status of ${t.title}`}>
          {TASK_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>
    </li>
  );

  return (
    <section>
      <div className="trailhead">
        {/* Styled like a trail marker: where you are on the 30-day route. */}
        <p className="plate" aria-label={day < 0 ? `Starts in ${plural(-day, "day")}` : `Day ${Math.min(day, 30)} of 30`}>
          <span aria-hidden="true">{day < 0 ? "Starts in" : "Day"}</span>
          <strong aria-hidden="true">{day < 0 ? -day : Math.min(day, 30)}</strong>
          <span aria-hidden="true">{day < 0 ? (day === -1 ? "day" : "days") : "of 30"}</span>
        </p>
        <div>
          <BlurTitle text={`Welcome, ${first}.`} />
          <p className="lede">{summary}</p>
        </div>
      </div>
      <PathBar start={start} tasks={d.tasks} />
      {err && <p className="error">{err}</p>}

      <div className="layout">
        <div className="main-col">
          {(overdueTasks.length > 0 || overdueCerts.length > 0) && (
            <section className="panel attention">
              <h2>Needs attention</h2>
              <ul className="tasks">
                {overdueTasks.map(taskRow)}
                {overdueCerts.map((c) => (
                  <li key={c.id} className="task">
                    <span className="check cert" aria-hidden="true" />
                    <div className="task-body"><div className="task-title">{c.name}</div><p className="task-desc">Certification from {c.provider}. Tick it off under Certifications once complete.</p></div>
                    <div className="task-meta"><span className="due late">Was due {fmtDate(c.deadline)}</span></div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="block">
            <h2>This week <span className="count">Week {d.current_week}</span></h2>
            {thisWeek.length ? <ul className="tasks route">{thisWeek.map(taskRow)}</ul> : <p className="muted">Nothing else is planned for this week.</p>}
          </section>

          <details className="block">
            <summary><h2>Full plan <span className="count">{d.metrics.completed_tasks} of {plural(d.metrics.total_tasks, "task")} done</span></h2></summary>
            {[1, 2, 3, 4].map((w) => {
              const list = d.tasks.filter((t) => t.week_no === w);
              return list.length > 0 && <div key={w}><h3>Week {w}</h3><ul className="tasks route">{list.map(taskRow)}</ul></div>;
            })}
          </details>
        </div>

        <aside className="side-col">
          <section className="block">
            <h2>People to meet <span className="count">{d.metrics.met_connections} of {d.metrics.total_connections} met</span></h2>
            {!d.connections.length && <p className="muted">No introductions planned yet.</p>}
            <ul className="people">
              {d.connections.map((c) => (
                <li key={c.id}>
                  <span className="avatar" aria-hidden="true">{initials(c.contact_name)}</span>
                  <div>
                    <strong>{c.contact_name}</strong>
                    <span className="muted">{c.contact_title}</span>
                    <p className="task-desc">{c.reason}</p>
                    <a href={`mailto:${c.contact_email}`}>{c.contact_email}</a>
                  </div>
                  <select className={`status s-${c.status}`} value={c.status} onChange={(e) => run(joineeApi.setConnectionStatus(c.id!, e.target.value))} aria-label={`Status with ${c.contact_name}`}>
                    {CONN_STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
                  </select>
                </li>
              ))}
            </ul>
          </section>

          <section className="block">
            <h2>Certifications <span className="count">{d.metrics.completed_mandatory_certs} of {d.metrics.total_mandatory_certs} required done</span></h2>
            {!d.certifications.length && <p className="muted">No certifications assigned.</p>}
            <ul className="certs">
              {d.certifications.map((c) => (
                <li key={c.id}>
                  <label>
                    <input type="checkbox" checked={!!c.is_completed} onChange={(e) => run(joineeApi.setCertCompleted(c.id!, e.target.checked))} />
                    <span>
                      <span className="cert-name"><strong>{c.name}</strong>{c.is_mandatory && <span className="flag">Required</span>}</span>
                      <span className={!c.is_completed && c.deadline < t0 ? "due late" : "due"}>{c.provider}, complete by {fmtDate(c.deadline)}</span>
                    </span>
                  </label>
                  <a href={c.url} target="_blank" rel="noreferrer">Open course</a>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </section>
  );
}
