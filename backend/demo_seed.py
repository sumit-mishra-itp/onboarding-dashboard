"""Dev-only demo data: an admin, an HR user, 2 managers, and 3 joinees under Maya at different points in their 30 days.
Every demo account's password is DEMO_PASSWORD.
Run on a fresh database: docker compose down -v && docker compose up -d && docker compose exec api python demo_seed.py"""
import json, os, urllib.request
from http.cookiejar import CookieJar
from datetime import date, timedelta

import psycopg
from psycopg.rows import dict_row

from app import security
from app.config import settings
from app.db import migrate
from app.repositories import users

assert settings.dev, "demo_seed is for APP_ENV=dev only"
DEMO_PASSWORD = "demo-password"
BASE = os.environ.get("API_BASE", "http://localhost:8000/api")

migrate()
with psycopg.connect(settings.database_url, row_factory=dict_row) as db:
    for email, name, role in [("admin@example.com", "Ada Admin", "ADMIN"), ("hana.hr@example.com", "Hana HR", "HR"),
                              ("maya.manager@example.com", "Maya Manager", "MANAGER"), ("omar.manager@example.com", "Omar Manager", "MANAGER")]:
        u = users.get_for_login(db, email)
        uid = u["id"] if u else users.create(db, email=email, full_name=name, role=role)
        users.set_password(db, uid, security.hash_password(DEMO_PASSWORD))


def session():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    def call(path, method="GET", body=None):
        req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
        with op.open(req) as r:
            return json.loads(r.read() or "null")
    return call


def login(email):
    call = session(); call("/auth/login", "POST", {"email": email, "password": DEMO_PASSWORD}); return call


invites = {}
T = lambda title, cat, w, d, pri="MEDIUM", desc="", subs=(): {"title": title, "category": cat, "week_no": w, "day_offset": d, "priority": pri, "description": desc, "subtasks": list(subs)}
maya = login("maya.manager@example.com")
today = date.today()

def joinee(name, email, title, team, start, tasks, certs, conns, assign=True):
    r = maya("/manager/joinees", "POST", {"full_name": name, "email": email, "job_title": title, "team": team, "start_date": str(start)})
    invites[email] = r["invite_path"].split("#token=")[1]
    maya(f"/plans/{r['plan_id']}", "PUT", {"tasks": tasks, "certifications": certs, "connections": conns})
    if assign: maya(f"/plans/{r['plan_id']}/assign", "POST")
    return r["plan_id"]

priya_tasks = [
    T("Set up laptop and dev environment", "TECHNICAL_SETUP", 1, 0, "HIGH", "Install JDK 21, IntelliJ and the internal CLI.", ["Install JDK 21", "Clone payments-core", "Run the test suite"]),
    T("Request GitHub and Jira access", "ACCESS_AND_TOOLS", 1, 1, "HIGH", "Raise both requests in the service portal; your manager approves."),
    T("Read the payments architecture overview", "ROLE_RAMP_UP", 1, 3, "MEDIUM", "Focus on the ledger and settlement services."),
    T("Shadow a code review", "TEAM_AND_PROCESS", 2, 7, "MEDIUM", "Sit in on two reviews with Raj."),
    T("Ship your first small fix", "ROLE_RAMP_UP", 2, 9, "HIGH", "Pick a starter ticket tagged good-first-issue."),
    T("Complete data handling training", "COMPLIANCE", 2, 11, "HIGH"),
    T("Join sprint planning", "TEAM_AND_PROCESS", 2, 12, "LOW"),
    T("Pair on the on-call runbook", "TEAM_AND_PROCESS", 3, 15, "MEDIUM", "Walk through the top five alerts with the on-call engineer."),
    T("Own a small feature end to end", "ROLE_RAMP_UP", 4, 24, "MEDIUM"),
]
certs = [{"name": "Security awareness", "provider": "KnowBe4", "url": "https://example.com/security", "deadline": str(today - timedelta(days=1)), "is_mandatory": True},
         {"name": "Code of conduct", "provider": "HR portal", "url": "https://example.com/coc", "deadline": str(today + timedelta(days=4)), "is_mandatory": True},
         {"name": "PCI DSS basics", "provider": "Compliance team", "url": "https://example.com/pci", "deadline": str(today + timedelta(days=14)), "is_mandatory": False}]
conns = [{"contact_name": "Raj Patel", "contact_email": "raj.patel@example.com", "contact_title": "Tech lead, Payments", "reason": "Your onboarding buddy for the first month."},
         {"contact_name": "Anna Berg", "contact_email": "anna.berg@example.com", "contact_title": "Product manager", "reason": "Owns the payments roadmap; ask her about priorities."},
         {"contact_name": "Leo Kim", "contact_email": "leo.kim@example.com", "contact_title": "SRE", "reason": "Runs the on-call rotation you'll join in week 3."}]
joinee("Priya Sharma", "priya.sharma@example.com", "Backend engineer", "Payments", today - timedelta(days=9), priya_tasks, certs, conns)

ana_tasks = [T("Set up laptop", "TECHNICAL_SETUP", 1, 0, "HIGH"), T("Meet the design team", "TEAM_AND_PROCESS", 1, 2), T("Audit the checkout flow", "ROLE_RAMP_UP", 2, 8, "HIGH"),
             T("Present first findings", "ROLE_RAMP_UP", 3, 18), T("Plan Q4 research", "ROLE_RAMP_UP", 4, 25, "LOW")]
joinee("Ana Costa", "ana.costa@example.com", "Product designer", "Checkout", today - timedelta(days=19), ana_tasks, [], [conns[1]])
joinee("Tom Becker", "tom.becker@example.com", "Data analyst", "Risk", today + timedelta(days=6), [T("Set up laptop", "TECHNICAL_SETUP", 1, 0, "HIGH")], [], [], assign=False)

# Joinees accept their invites (sets DEMO_PASSWORD), then work their plans
def accept(email):
    call = session(); call("/auth/set-password", "POST", {"token": invites[email], "password": DEMO_PASSWORD}); return call
priya = accept("priya.sharma@example.com"); d = priya("/joinee/dashboard")
for i, s in [(0, "DONE"), (2, "DONE"), (3, "IN_PROGRESS")]: priya(f"/tasks/{d['tasks'][i]['id']}", "PATCH", {"status": s})
priya(f"/tasks/{d['tasks'][1]['id']}", "PATCH", {"status": "BLOCKED", "joinee_notes": "Jira request waiting on an approver"})
priya(f"/connections/{d['connections'][0]['id']}", "PATCH", {"status": "MET"})
priya(f"/connections/{d['connections'][1]['id']}", "PATCH", {"status": "SCHEDULED"})
ana = accept("ana.costa@example.com"); accept("tom.becker@example.com"); d = ana("/joinee/dashboard")
for i in range(3): ana(f"/tasks/{d['tasks'][i]['id']}", "PATCH", {"status": "DONE"})
print(f"seeded; every demo account's password is {DEMO_PASSWORD!r}")
