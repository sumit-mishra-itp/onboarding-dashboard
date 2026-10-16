"""app_user and auth_token data access. Returns rows or None; never raises HTTP errors."""
from uuid import UUID

from .. import security

# Safe to send to a browser. Never add password_hash, failed_logins or session_version here.
PUBLIC = "id, email, full_name, role, manager_id, job_title, team, start_date, is_active, last_login_at, created_at"


def get_session_user(conn, uid: str) -> dict | None:
    return conn.execute(f"SELECT {PUBLIC}, session_version FROM app_user WHERE id = %s AND is_active", (uid,)).fetchone()


def get(conn, uid: UUID) -> dict | None:
    return conn.execute(f"SELECT {PUBLIC} FROM app_user WHERE id = %s", (uid,)).fetchone()


def get_for_login(conn, email: str) -> dict | None:
    return conn.execute(
        "SELECT id, password_hash, is_active, session_version, (locked_until > now()) AS locked"
        " FROM app_user WHERE email = %s", (email,)).fetchone()


def list_all(conn) -> list[dict]:
    return conn.execute(
        f"SELECT {PUBLIC}, password_hash IS NOT NULL AS has_password FROM app_user"
        " ORDER BY is_active DESC, role, full_name").fetchall()


def create(conn, *, email: str, full_name: str, role: str, manager_id: UUID | None = None,
           job_title: str | None = None, team: str | None = None, start_date=None) -> UUID:
    """Raises psycopg.errors.UniqueViolation on a duplicate email."""
    return conn.execute(
        "INSERT INTO app_user (email, full_name, role, manager_id, job_title, team, start_date)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (email, full_name, role, manager_id, job_title, team, start_date)).fetchone()["id"]


def update(conn, uid: UUID, fields: dict) -> dict | None:
    """Changing role or deactivating also bumps session_version, which signs the user out everywhere."""
    if not fields:
        return get(conn, uid)
    sets = ", ".join(f"{c} = %({c})s" for c in fields)  # column names come from a pydantic model, never raw input
    revoke = ", session_version = session_version + 1" if {"role", "is_active"} & fields.keys() else ""
    return conn.execute(f"UPDATE app_user SET {sets}{revoke} WHERE id = %(uid)s RETURNING {PUBLIC}",
                        {**fields, "uid": uid}).fetchone()


def count_active_admins(conn) -> int:
    return conn.execute("SELECT count(*) AS n FROM app_user WHERE role = 'ADMIN' AND is_active").fetchone()["n"]


# ---------- login bookkeeping ----------

def record_failed_login(conn, uid: UUID):
    conn.execute(
        "UPDATE app_user SET"
        " failed_logins = CASE WHEN failed_logins + 1 >= %(max)s THEN 0 ELSE failed_logins + 1 END,"
        " locked_until = CASE WHEN failed_logins + 1 >= %(max)s THEN now() + make_interval(mins => %(mins)s)"
        "                ELSE locked_until END"
        " WHERE id = %(id)s",
        {"max": security.MAX_FAILED_LOGINS, "mins": security.LOCKOUT_MINUTES, "id": uid})


def record_login(conn, uid: UUID, new_hash: str | None = None):
    conn.execute("UPDATE app_user SET failed_logins = 0, locked_until = NULL, last_login_at = now(),"
                 " password_hash = COALESCE(%s, password_hash) WHERE id = %s", (new_hash, uid))


def set_password(conn, uid: UUID, password_hash: str) -> int:
    """Signs out every other session (session_version bump). Returns the new version for the current session."""
    return conn.execute(
        "UPDATE app_user SET password_hash = %s, session_version = session_version + 1, failed_logins = 0,"
        " locked_until = NULL WHERE id = %s RETURNING session_version", (password_hash, uid)).fetchone()["session_version"]


def get_password_hash(conn, uid: UUID) -> str | None:
    return conn.execute("SELECT password_hash FROM app_user WHERE id = %s", (uid,)).fetchone()["password_hash"]


# ---------- one-time tokens (invite / reset) ----------

def issue_token(conn, uid: UUID, purpose: str, ttl_hours: int, created_by: UUID | None) -> str:
    """Revokes the user's earlier unused tokens, so only the newest link works. Returns the raw token."""
    raw, digest = security.new_token()
    conn.execute("UPDATE auth_token SET used_at = now() WHERE user_id = %s AND used_at IS NULL", (uid,))
    conn.execute("INSERT INTO auth_token (user_id, token_hash, purpose, created_by, expires_at)"
                 " VALUES (%s, %s, %s, %s, now() + make_interval(hours => %s))",
                 (uid, digest, purpose, created_by, ttl_hours))
    return raw


def consume_token(conn, raw: str) -> UUID | None:
    """Marks the token used and returns its user id, if it is valid, unused, unexpired and the user is active."""
    row = conn.execute(
        "UPDATE auth_token t SET used_at = now() FROM app_user u"
        " WHERE t.token_hash = %s AND t.used_at IS NULL AND t.expires_at > now() AND u.id = t.user_id AND u.is_active"
        " RETURNING t.user_id", (security.token_hash(raw),)).fetchone()
    return row and row["user_id"]
