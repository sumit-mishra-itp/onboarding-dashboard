"""Request dependencies: who is calling, and are they allowed. Every protected route goes through these."""
from fastapi import Depends, HTTPException, Request

from .db import DB
from .repositories import users


def current_user(request: Request, conn=DB) -> dict:
    """The session holds the user id and the session_version it was issued under. A password change,
    role change or deactivation bumps the version in the DB, which invalidates every older session."""
    s = request.session
    user = s.get("uid") and users.get_session_user(conn, s["uid"])
    if not user or user.pop("session_version") != s.get("sv"):
        s.clear()
        raise HTTPException(401, "Not signed in")
    return user


def require_role(*roles: str):
    def check(user=Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, "You don't have access to this")
        return user
    return Depends(check)


CurrentUser = Depends(current_user)
Admin = require_role("ADMIN")
InfoEditor = require_role("ADMIN", "HR")
Manager = require_role("MANAGER")
Joinee = require_role("JOINEE")
