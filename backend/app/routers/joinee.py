"""Joinee: their dashboard, and status updates on their own ACTIVE plan."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..core import ConnectionStatus, TaskStatus, current_week
from ..db import DB
from ..deps import Joinee
from ..repositories import plans

router = APIRouter(prefix="/api", tags=["joinee"])


def _found(ok: bool) -> dict:
    if not ok:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@router.get("/joinee/dashboard")
def dashboard(user=Joinee, conn=DB):
    plan = plans.visible_to_joinee(conn, user["id"])
    if not plan:
        return {"plan": None}
    return {**plans.bundle(conn, plan), "current_week": current_week(user["start_date"], date.today())}


class TaskStatusIn(BaseModel):
    status: TaskStatus
    joinee_notes: str | None = Field(default=None, max_length=1000)


@router.patch("/tasks/{item_id}")
def update_task(item_id: UUID, body: TaskStatusIn, user=Joinee, conn=DB):
    return _found(plans.set_task_status(conn, user["id"], item_id, body.status, body.joinee_notes))


class CertStatusIn(BaseModel):
    is_completed: bool


@router.patch("/certifications/{item_id}")
def update_cert(item_id: UUID, body: CertStatusIn, user=Joinee, conn=DB):
    return _found(plans.set_cert_completed(conn, user["id"], item_id, body.is_completed))


class ConnStatusIn(BaseModel):
    status: ConnectionStatus


@router.patch("/connections/{item_id}")
def update_connection(item_id: UUID, body: ConnStatusIn, user=Joinee, conn=DB):
    return _found(plans.set_connection_status(conn, user["id"], item_id, body.status))
