"""ai_run_log: one row per model call, for cost, quality and rate limiting (BRD §16, TSD §5.2)."""
from uuid import UUID

from psycopg.types.json import Jsonb


def recent_count(conn, plan_id: UUID) -> int:
    return conn.execute("SELECT count(*) AS n FROM ai_run_log WHERE plan_id = %s AND created_at > now() - interval '1 hour'",
                        (plan_id,)).fetchone()["n"]


def insert(conn, plan_id: UUID, manager_id: UUID, logs: list[dict]):
    for log in logs:  # log keys are the ai_run_log column names (set in app.ai.planner)
        row = {**log, "raw_output": Jsonb(log["raw_output"]) if log["raw_output"] is not None else None}
        conn.execute(f"INSERT INTO ai_run_log (plan_id, manager_id, {', '.join(row)}) VALUES (%s, %s{', %s' * len(row)})",
                     [plan_id, manager_id, *row.values()])


def score_last_draft(conn, plan_id: UUID):
    """AI quality signal (BRD §16): did the last successful draft survive to assignment, and was it edited?"""
    conn.execute(
        "UPDATE ai_run_log SET"
        " is_accepted = EXISTS (SELECT 1 FROM plan_task WHERE plan_id = %(p)s AND is_ai_generated),"
        " is_edited = EXISTS (SELECT 1 FROM plan_task WHERE plan_id = %(p)s AND is_modified_by_manager)"
        " WHERE id = (SELECT id FROM ai_run_log WHERE plan_id = %(p)s AND validation_passed"
        "             ORDER BY created_at DESC LIMIT 1)",
        {"p": plan_id})
