"""User administration (ADMIN only). Joinees are created by their manager, together with their plan."""
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import security
from ..core import Email, Name, Role
from ..db import DB
from ..deps import Admin
from ..repositories import users

router = APIRouter(prefix="/api/admin", tags=["admin"])


def invite_path(token: str) -> str:
    """The token rides in the URL fragment, so it never reaches server logs or Referer headers."""
    return f"/set-password#token={token}"


@router.get("/users")
def list_users(_=Admin, conn=DB):
    return users.list_all(conn)


class StaffIn(BaseModel):
    email: Email
    full_name: Name
    role: Literal["ADMIN", "HR", "MANAGER"]


@router.post("/users", status_code=201)
def create_user(body: StaffIn, admin=Admin, conn=DB):
    try:
        uid = users.create(conn, **body.model_dump())
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "A user with that email already exists")
    token = users.issue_token(conn, uid, "INVITE", security.INVITE_TTL_HOURS, admin["id"])
    return {"user": users.get(conn, uid), "invite_path": invite_path(token)}


class UserPatch(BaseModel):
    full_name: Name | None = None
    role: Role | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
def update_user(user_id: UUID, body: UserPatch, admin=Admin, conn=DB):
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    target = users.get(conn, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if "role" in fields and (fields["role"] == "JOINEE") != (target["role"] == "JOINEE"):
        raise HTTPException(400, "Joinees can't be turned into staff or back: their plan depends on it")
    losing_admin = target["role"] == "ADMIN" and target["is_active"] and (
        fields.get("is_active") is False or fields.get("role", "ADMIN") != "ADMIN")
    if losing_admin and users.count_active_admins(conn) <= 1:
        raise HTTPException(400, "There must always be at least one active admin")
    return users.update(conn, user_id, fields)


@router.post("/users/{user_id}/reset-link")
def reset_link(user_id: UUID, admin=Admin, conn=DB):
    """A one-time link to (re)set the password. Share it with the user; the old password keeps working until used."""
    target = users.get(conn, user_id)
    if not target or not target["is_active"]:
        raise HTTPException(404, "Active user not found")
    token = users.issue_token(conn, user_id, "RESET", security.RESET_TTL_HOURS, admin["id"])
    return {"reset_path": invite_path(token)}
