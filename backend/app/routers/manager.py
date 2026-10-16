"""Manager: joinees, plan building, AI drafting, assignment."""
from datetime import date
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import ai, security
from ..core import CertIn, ConnIn, Email, Name, TaskIn
from ..db import DB
from ..deps import Manager
from ..repositories import ai_runs, plans, users
from .admin import invite_path

router = APIRouter(prefix="/api", tags=["manager"])


def _owned(conn, plan_id: UUID, mgr: dict) -> dict:
    plan = plans.owned_by(conn, plan_id, mgr["id"])
    if not plan:
        raise HTTPException(403, "This plan does not belong to one of your joinees")
    return plan


@router.get("/manager/joinees")
def list_joinees(mgr=Manager, conn=DB):
    rows = plans.list_for_manager(conn, mgr["id"])
    kids = plans.children(conn, [r["id"] for r in rows])
    return [{**r, "metrics": (b := plans.bundle(conn, r, kids[r["id"]]))["metrics"], "tasks": b["tasks"]} for r in rows]


class JoineeIn(BaseModel):
    full_name: Name
    email: Email
    job_title: Name
    team: Name
    start_date: date


@router.post("/manager/joinees", status_code=201)
def add_joinee(body: JoineeIn, mgr=Manager, conn=DB):
    """Creates the joinee's account (no password yet) and an empty DRAFT plan. Returns an invite link to share."""
    try:
        uid = users.create(conn, role="JOINEE", manager_id=mgr["id"], **body.model_dump())
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "A user with that email already exists")
    plan_id = plans.create(conn, uid, mgr["id"])
    token = users.issue_token(conn, uid, "INVITE", security.INVITE_TTL_HOURS, mgr["id"])
    return {"joinee_id": uid, "plan_id": plan_id, "invite_path": invite_path(token)}


@router.post("/plans/{plan_id}/invite")
def reinvite(plan_id: UUID, mgr=Manager, conn=DB):
    """New invite link for a joinee who hasn't set a password yet (e.g. the first link expired).
    Resetting an existing password is admin-only, so a manager can't take over a joinee's account."""
    plan = _owned(conn, plan_id, mgr)
    if users.get_password_hash(conn, plan["joinee_id"]):
        raise HTTPException(409, "This joinee has already set a password. An admin can send a reset link.")
    token = users.issue_token(conn, plan["joinee_id"], "INVITE", security.INVITE_TTL_HOURS, mgr["id"])
    return {"invite_path": invite_path(token)}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: UUID, mgr=Manager, conn=DB):
    return plans.bundle(conn, _owned(conn, plan_id, mgr))


class PlanIn(BaseModel):
    tasks: list[TaskIn] = Field(max_length=60)
    certifications: list[CertIn] = Field(max_length=30)
    connections: list[ConnIn] = Field(max_length=30)


@router.put("/plans/{plan_id}")
def save_plan(plan_id: UUID, body: PlanIn, mgr=Manager, conn=DB):
    plan = _owned(conn, plan_id, mgr)
    plans.save_contents(conn, plan, body.tasks, body.certifications, body.connections)
    return plans.bundle(conn, plan)


@router.post("/plans/{plan_id}/assign")
def assign_plan(plan_id: UUID, mgr=Manager, conn=DB):
    plan = _owned(conn, plan_id, mgr)
    if plan["status"] != "DRAFT":
        raise HTTPException(409, "Plan is already assigned")
    if not plans.has_tasks(conn, plan_id):
        raise HTTPException(400, "Add at least one task before assigning")
    plans.activate(conn, plan)
    ai_runs.score_last_draft(conn, plan_id)
    return plans.bundle(conn, {**plan, "status": "ACTIVE"})


class BriefIn(BaseModel):
    brief: str = Field(min_length=10, max_length=2000)


@router.post("/plans/{plan_id}/ai-draft")
def ai_draft(plan_id: UUID, body: BriefIn, mgr=Manager, conn=DB):
    plan = _owned(conn, plan_id, mgr)
    if not ai.ENABLED:
        raise HTTPException(503, "AI drafting is not configured. Add tasks manually.")
    if ai_runs.recent_count(conn, plan_id) >= 6:  # up to 2 attempts per request -> ~3 generations per plan per hour (TSD §5.2)
        raise HTTPException(429, "Generation limit reached for this plan. Try again later or add tasks manually.")
    conn.commit()  # end the read transaction: don't sit "idle in transaction" during a ~20s model call
    tasks, logs = ai.draft_tasks(ai.provider, plan["job_title"], plan["team"], plan["duration_days"], body.brief)
    ai_runs.insert(conn, plan_id, mgr["id"], logs)
    if tasks is None:
        conn.commit()  # keep the failure logs; the HTTPException below would otherwise roll them back
        raise HTTPException(502, "AI draft failed. Your data is kept; add tasks manually.")
    return {"tasks": tasks}
