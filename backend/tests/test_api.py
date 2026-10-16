"""End-to-end API check against a real, throwaway Postgres database (eod_test, recreated each run).
Run: docker compose exec api python -m tests.test_api"""
import os
from datetime import date

import psycopg

base = os.environ["DATABASE_URL"]
with psycopg.connect(base, autocommit=True) as c:
    c.execute("DROP DATABASE IF EXISTS eod_test WITH (FORCE)")
    c.execute("CREATE DATABASE eod_test")
os.environ["DATABASE_URL"] = base.rsplit("/", 1)[0] + "/eod_test"
os.environ["APP_ENV"] = "dev"

from fastapi.testclient import TestClient  # noqa: E402

from app import security  # noqa: E402
from app.db import pool  # noqa: E402
from app.main import app  # noqa: E402
from app.repositories import users  # noqa: E402

PW = "a-good-password-1"


def client():
    return TestClient(app)


def ok(r, code=200):
    assert r.status_code == code, (r.status_code, r.text)
    return r.json() if r.content else None


def token_of(path):
    return path.split("#token=")[1]


with TestClient(app) as anon:  # runs lifespan: migrations + pool
    with pool.connection() as conn:
        admin_id = users.create(conn, email="root@example.com", full_name="Root Admin", role="ADMIN")
        users.set_password(conn, admin_id, security.hash_password(PW))

    # --- login, lockout ---
    ok(anon.get("/api/auth/me"), 401)
    ok(anon.post("/api/auth/login", json={"email": "nobody@example.com", "password": PW}), 401)
    admin = client()
    me = ok(admin.post("/api/auth/login", json={"email": "ROOT@example.com ", "password": PW}))
    assert me["role"] == "ADMIN" and "password_hash" not in me and "session_version" not in me
    assert "password_hash" not in ok(admin.get("/api/auth/me"))

    # --- admin invites a manager and an HR person; invite links are single use ---
    r = ok(admin.post("/api/admin/users", json={"email": "maya@example.com", "full_name": "Maya M", "role": "MANAGER"}), 201)
    ok(admin.post("/api/admin/users", json={"email": "maya@example.com", "full_name": "Dup", "role": "MANAGER"}), 409)
    ok(admin.post("/api/admin/users", json={"email": "x@example.com", "full_name": "X", "role": "JOINEE"}), 422)
    maya = client()
    ok(maya.post("/api/auth/set-password", json={"token": token_of(r["invite_path"]), "password": "short"}), 422)
    assert ok(maya.post("/api/auth/set-password", json={"token": token_of(r["invite_path"]), "password": PW}))["role"] == "MANAGER"
    ok(client().post("/api/auth/set-password", json={"token": token_of(r["invite_path"]), "password": PW}), 400)
    maya_id = r["user"]["id"]

    for _ in range(security.MAX_FAILED_LOGINS):
        ok(anon.post("/api/auth/login", json={"email": "maya@example.com", "password": "wrong-password"}), 401)
    ok(anon.post("/api/auth/login", json={"email": "maya@example.com", "password": PW}), 429)  # locked, even if right
    ok(maya.get("/api/manager/joinees"))  # existing session unaffected by lockout

    r = ok(admin.post("/api/admin/users", json={"email": "hana@example.com", "full_name": "Hana HR", "role": "HR"}), 201)
    hr = client()
    ok(hr.post("/api/auth/set-password", json={"token": token_of(r["invite_path"]), "password": PW}))

    # --- manager adds a joinee, builds and assigns a plan ---
    r = ok(maya.post("/api/manager/joinees", json={"full_name": "Priya S", "email": "priya@example.com", "job_title": "Engineer",
                                                    "team": "Payments", "start_date": str(date.today())}), 201)
    plan_id, invite = r["plan_id"], r["invite_path"]
    ok(maya.post(f"/api/plans/{plan_id}/assign"), 400)  # no tasks yet
    task = {"title": "Set up laptop", "category": "TECHNICAL_SETUP", "week_no": 1, "day_offset": 0}
    cert = {"name": "Security", "provider": "KnowBe4", "url": "javascript:alert(1)", "deadline": str(date.today())}
    ok(maya.put(f"/api/plans/{plan_id}", json={"tasks": [task], "certifications": [cert], "connections": []}), 422)
    cert["url"] = "https://example.com/sec"
    b = ok(maya.put(f"/api/plans/{plan_id}", json={"tasks": [task], "certifications": [cert], "connections": []}))
    assert b["plan"]["status"] == "DRAFT" and b["tasks"][0]["due_date"] is None

    priya = client()
    ok(priya.post("/api/auth/set-password", json={"token": token_of(invite), "password": PW}))
    assert ok(priya.get("/api/joinee/dashboard"))["plan"] is None  # draft is invisible
    ok(maya.post(f"/api/plans/{plan_id}/invite"), 409)  # password already set: only an admin can reset
    b = ok(maya.post(f"/api/plans/{plan_id}/assign"))
    assert b["plan"]["status"] == "ACTIVE" and b["tasks"][0]["due_date"] == str(date.today())

    d = ok(priya.get("/api/joinee/dashboard"))
    ok(priya.patch(f"/api/tasks/{d['tasks'][0]['id']}", json={"status": "DONE"}))
    rows = ok(maya.get("/api/manager/joinees"))
    assert rows[0]["metrics"]["task_completion_percentage"] == 100, rows

    # --- role and ownership isolation ---
    ok(priya.get("/api/manager/joinees"), 403)
    ok(maya.get("/api/joinee/dashboard"), 403)
    ok(maya.get("/api/admin/users"), 403)
    ok(hr.get(f"/api/plans/{plan_id}"), 403)
    r = ok(admin.post("/api/admin/users", json={"email": "omar@example.com", "full_name": "Omar M", "role": "MANAGER"}), 201)
    omar = client()
    ok(omar.post("/api/auth/set-password", json={"token": token_of(r["invite_path"]), "password": PW}))
    ok(omar.get(f"/api/plans/{plan_id}"), 403)
    ok(omar.patch(f"/api/tasks/{d['tasks'][0]['id']}", json={"status": "TO_DO"}), 403)

    # --- Info Hub: seeded once, everyone reads, HR/Admin edit ---
    seeded = ok(priya.get("/api/info-hub"))
    assert seeded, "seed content missing"
    assert ok(priya.get("/api/info-hub", params={"search": "100%_"})) == []
    entry = {"category": "IT and Access", "title": "Wi-Fi", "body_md": "Network: corp", "link_url": "https://wifi.example.com"}
    ok(priya.post("/api/info-hub", json=entry), 403)
    ok(maya.post("/api/info-hub", json=entry), 403)
    ok(hr.post("/api/info-hub", json={**entry, "link_url": "javascript:alert(1)"}), 422)
    e = ok(hr.post("/api/info-hub", json=entry), 201)
    assert e["last_reviewed_date"] == str(date.today())
    assert any(x["id"] == e["id"] for x in ok(priya.get("/api/info-hub", params={"search": "wi-fi"})))
    ok(hr.put(f"/api/info-hub/{e['id']}", json={**entry, "is_active": False}))
    assert all(x["id"] != e["id"] for x in ok(priya.get("/api/info-hub")))
    ok(priya.get("/api/info-hub", params={"include_inactive": True}), 403)
    assert any(x["id"] == e["id"] for x in ok(hr.get("/api/info-hub", params={"include_inactive": True})))
    ok(admin.delete(f"/api/info-hub/{e['id']}"), 204)
    ok(admin.delete(f"/api/info-hub/{e['id']}"), 404)

    # --- password change signs out other sessions, keeps this one ---
    priya2 = client()
    ok(priya2.post("/api/auth/login", json={"email": "priya@example.com", "password": PW}))
    ok(priya.post("/api/auth/change-password", json={"current_password": "nope-nope-nope", "new_password": PW + "x"}), 400)
    ok(priya.post("/api/auth/change-password", json={"current_password": PW, "new_password": PW + "x"}))
    ok(priya.get("/api/auth/me"))
    ok(priya2.get("/api/auth/me"), 401)

    # --- admin: reset link, deactivate (kills session), last-admin guard ---
    r = ok(admin.post(f"/api/admin/users/{maya_id}/reset-link"))
    ok(client().post("/api/auth/set-password", json={"token": token_of(r["reset_path"]), "password": PW + "y"}))
    ok(maya.get("/api/auth/me"), 401)  # reset bumps the session version
    ok(maya.post("/api/auth/login", json={"email": "maya@example.com", "password": PW + "y"}))
    ok(admin.patch(f"/api/admin/users/{maya_id}", json={"is_active": False}))
    ok(maya.get("/api/auth/me"), 401)
    ok(maya.post("/api/auth/login", json={"email": "maya@example.com", "password": PW + "y"}), 401)
    ok(admin.patch(f"/api/admin/users/{admin_id}", json={"role": "HR"}), 400)
    ok(admin.patch(f"/api/admin/users/{d['plan']['joinee_id']}", json={"role": "MANAGER"}), 400)

    ok(admin.post("/api/auth/logout"))
    ok(admin.get("/api/auth/me"), 401)
    ok(anon.get("/api/health"))

print("ok")
