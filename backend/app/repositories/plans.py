"""Onboarding plans and their tasks, certifications and connections. Returns rows or None; never raises HTTP errors."""
from datetime import date
from uuid import UUID

from psycopg.types.json import Jsonb
from pydantic import BaseModel

from ..core import CertIn, ConnIn, TaskIn, due_date, metrics

PLAN_SQL = ("SELECT p.*, u.full_name, u.email, u.job_title, u.team, u.start_date FROM onboarding_plan p"
            " JOIN app_user u ON u.id = p.joinee_id")


def create(conn, joinee_id: UUID, manager_id: UUID) -> UUID:
    return conn.execute("INSERT INTO onboarding_plan (joinee_id, manager_id) VALUES (%s, %s) RETURNING id",
                        (joinee_id, manager_id)).fetchone()["id"]


def owned_by(conn, plan_id: UUID, manager_id: UUID) -> dict | None:
    """Ownership comes from the session, never from the request body (TSD §3.3)."""
    return conn.execute(f"{PLAN_SQL} WHERE p.id = %s AND p.manager_id = %s", (plan_id, manager_id)).fetchone()


def list_for_manager(conn, manager_id: UUID) -> list[dict]:
    return conn.execute(f"{PLAN_SQL} WHERE p.manager_id = %s ORDER BY u.start_date", (manager_id,)).fetchall()


def visible_to_joinee(conn, joinee_id: UUID) -> dict | None:
    """DRAFT plans are invisible to the joinee (BR-10)."""
    return conn.execute(f"{PLAN_SQL} WHERE p.joinee_id = %s AND p.status <> 'DRAFT'", (joinee_id,)).fetchone()


def children(conn, plan_ids: list) -> dict:
    """Tasks, certs and connections for many plans in 3 queries total, grouped by plan id."""
    out = {pid: {"tasks": [], "certifications": [], "connections": []} for pid in plan_ids}
    for key, sql in (
        ("tasks", "SELECT * FROM plan_task WHERE plan_id = ANY(%s::uuid[]) ORDER BY week_no, day_offset, created_at"),
        ("certifications", "SELECT * FROM certification WHERE plan_id = ANY(%s::uuid[]) ORDER BY deadline, created_at"),
        ("connections", "SELECT * FROM connection_contact WHERE plan_id = ANY(%s::uuid[]) ORDER BY created_at"),
    ):
        for row in conn.execute(sql, (plan_ids,)):
            out[row["plan_id"]][key].append(row)
    return out


def bundle(conn, plan: dict, kids: dict | None = None) -> dict:
    """The plan read model every screen uses: plan + children + computed metrics."""
    k = kids or children(conn, [plan["id"]])[plan["id"]]
    return {"plan": plan, **k, "metrics": metrics(k["tasks"], k["certifications"], k["connections"], date.today())}


def _sync_rows(conn, table: str, plan_id: UUID, items: list[BaseModel], rows: list[dict]):
    """Make the table's rows for this plan match `items`: update by id, insert new, delete missing.
    Joinee-owned columns (status, notes, completion) are never in `rows`, so they survive edits.
    `table` and column names are code constants, never user input."""
    keep = [i.id for i in items if i.id]
    conn.execute(f"DELETE FROM {table} WHERE plan_id = %s AND NOT (id = ANY(%s::uuid[]))", (plan_id, keep))
    for item, row in zip(items, rows):
        cols = list(row)
        if item.id:
            sets = ", ".join(f"{c} = %s" for c in cols)
            conn.execute(f"UPDATE {table} SET {sets} WHERE id = %s AND plan_id = %s", [*row.values(), item.id, plan_id])
        else:
            conn.execute(f"INSERT INTO {table} (plan_id, {', '.join(cols)}) VALUES (%s, {', '.join(['%s'] * len(cols))})",
                         [plan_id, *row.values()])


def save_contents(conn, plan: dict, tasks: list[TaskIn], certs: list[CertIn], conns: list[ConnIn]):
    active = plan["status"] != "DRAFT"
    task_rows = [{**t.model_dump(exclude={"id", "subtasks"}), "subtasks": Jsonb(t.subtasks),
                  "due_date": due_date(plan["start_date"], t.day_offset) if active else None} for t in tasks]
    _sync_rows(conn, "plan_task", plan["id"], tasks, task_rows)
    _sync_rows(conn, "certification", plan["id"], certs, [c.model_dump(exclude={"id"}) for c in certs])
    _sync_rows(conn, "connection_contact", plan["id"], conns, [c.model_dump(exclude={"id"}) for c in conns])


def has_tasks(conn, plan_id: UUID) -> bool:
    return conn.execute("SELECT 1 FROM plan_task WHERE plan_id = %s LIMIT 1", (plan_id,)).fetchone() is not None


def activate(conn, plan: dict):
    """DRAFT -> ACTIVE (BR-12, BR-13). Due dates are fixed here, from the joinee's real start date."""
    conn.execute("UPDATE plan_task SET due_date = %s::date + day_offset WHERE plan_id = %s", (plan["start_date"], plan["id"]))
    conn.execute("UPDATE onboarding_plan SET status = 'ACTIVE', approved_at = now() WHERE id = %s", (plan["id"],))


# ---------- joinee writes: each is scoped to their own ACTIVE plan in the same statement ----------

_OWN_ACTIVE = "FROM onboarding_plan p WHERE {a}.id = %(id)s AND p.id = {a}.plan_id AND p.joinee_id = %(u)s AND p.status = 'ACTIVE'"


def set_task_status(conn, joinee_id: UUID, task_id: UUID, status: str, notes: str | None) -> bool:
    return conn.execute(
        "UPDATE plan_task t SET status = %(s)s, joinee_notes = COALESCE(%(n)s, t.joinee_notes),"
        " completed_at = CASE WHEN %(s)s = 'DONE' THEN COALESCE(t.completed_at, now()) END "
        + _OWN_ACTIVE.format(a="t") + " RETURNING t.id",
        {"s": status, "n": notes, "id": task_id, "u": joinee_id}).fetchone() is not None


def set_cert_completed(conn, joinee_id: UUID, cert_id: UUID, done: bool) -> bool:
    return conn.execute(
        "UPDATE certification c SET is_completed = %(d)s, completed_at = CASE WHEN %(d)s THEN now() END "
        + _OWN_ACTIVE.format(a="c") + " RETURNING c.id",
        {"d": done, "id": cert_id, "u": joinee_id}).fetchone() is not None


def set_connection_status(conn, joinee_id: UUID, conn_id: UUID, status: str) -> bool:
    return conn.execute(
        "UPDATE connection_contact c SET status = %(s)s,"
        " met_date = CASE WHEN %(s)s = 'MET' THEN COALESCE(c.met_date, current_date) END "
        + _OWN_ACTIVE.format(a="c") + " RETURNING c.id",
        {"s": status, "id": conn_id, "u": joinee_id}).fetchone() is not None
