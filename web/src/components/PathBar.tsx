import { daysSince, fmtDate, label, today } from "../lib/format";
import type { Task } from "../types";

// The 30-day path: weeks, today, and every task as a dot at its day.
export default function PathBar({ start, days = 30, tasks, compact = false }: { start: string; days?: number; tasks: Task[]; compact?: boolean }) {
  const t0 = today();
  const now = Math.max(0, Math.min(days, daysSince(start)));
  const pos = (d: number) => `${(Math.min(d, days) / days) * 100}%`;
  const state = (t: Task) => (t.status !== "DONE" && t.due_date && t.due_date < t0 ? "OVERDUE" : t.status ?? "TO_DO");
  const done = tasks.filter((t) => t.status === "DONE").length;

  return (
    <div className={compact ? "path compact" : "path"} role="img"
      aria-label={`Day ${now} of ${days}. ${done} of ${tasks.length} tasks done.`}>
      <div className="path-track">
        <div className="path-elapsed" style={{ width: pos(now) }} />
        {[7, 14, 21].map((d) => <div key={d} className="path-week" style={{ left: pos(d) }} />)}
        {tasks.map((t, i) => (
          <span key={t.id ?? i} className={`path-dot s-${state(t)}`} style={{ left: pos(t.day_offset) }}
            title={`${t.title}: ${label(state(t))}, due ${fmtDate(t.due_date)}`} />
        ))}
        {daysSince(start) >= 0 && <div className="path-today" style={{ left: pos(now) }}>{!compact && <span>Today</span>}</div>}
      </div>
      {!compact && (
        <div className="path-weeks">
          {[0, 7, 14, 21].map((d, i) => (
            <span key={d} style={{ left: pos(d), width: pos((i === 3 ? days : d + 7) - d) }}>Week {i + 1}</span>
          ))}
        </div>
      )}
    </div>
  );
}
