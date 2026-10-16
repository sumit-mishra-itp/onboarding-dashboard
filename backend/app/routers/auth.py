"""Sign in / out, accept an invite or reset link, change password."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .. import security
from ..core import Password
from ..db import DB
from ..deps import CurrentUser
from ..repositories import users

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


@router.post("/login")
def login(body: LoginIn, request: Request, conn=DB):
    u = users.get_for_login(conn, body.email.strip().lower())
    ok = security.verify_password(u and u["password_hash"], body.password)  # always hashes: no timing leak
    if u and u["locked"]:
        raise HTTPException(429, f"Too many failed attempts. Try again in {security.LOCKOUT_MINUTES} minutes.")
    if not (u and ok and u["is_active"]):
        if u:
            users.record_failed_login(conn, u["id"])
            conn.commit()  # keep the failure count; the HTTPException below would otherwise roll it back
        raise HTTPException(401, "Email or password is incorrect")
    users.record_login(conn, u["id"], security.hash_password(body.password) if security.needs_rehash(u["password_hash"]) else None)
    request.session.clear()
    request.session.update(uid=str(u["id"]), sv=u["session_version"])
    return users.get(conn, u["id"])


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(user=CurrentUser):
    return user


class SetPasswordIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: Password


@router.post("/set-password")
def set_password(body: SetPasswordIn, request: Request, conn=DB):
    """Accept an invite or reset link: sets the password and signs the user in."""
    uid = users.consume_token(conn, body.token)
    if not uid:
        raise HTTPException(400, "This link is invalid, expired or already used. Ask for a new one.")
    sv = users.set_password(conn, uid, security.hash_password(body.password))
    users.record_login(conn, uid)
    request.session.clear()
    request.session.update(uid=str(uid), sv=sv)
    return users.get(conn, uid)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: Password


@router.post("/change-password")
def change_password(body: ChangePasswordIn, request: Request, user=CurrentUser, conn=DB):
    """Signs out every other session; this one stays signed in."""
    if not security.verify_password(users.get_password_hash(conn, user["id"]), body.current_password):
        raise HTTPException(400, "Current password is incorrect")
    request.session["sv"] = users.set_password(conn, user["id"], security.hash_password(body.new_password))
    return {"ok": True}
