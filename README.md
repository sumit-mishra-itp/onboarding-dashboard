# Employee Onboarding Dashboard

React (Vite) + FastAPI + Postgres, all in Docker. Roles: **Admin** (users, Info Hub), **HR** (Info Hub),
**Manager** (joinees and their plans), **Joinee** (their plan).

## Run locally

```sh
cp .env.example .env          # add GROQ_API_KEY to enable AI drafting
docker compose up --build
docker compose exec api python demo_seed.py   # on a fresh DB: demo users, all with password "demo-password"
```

- App: http://localhost:5173 (sign in as admin@example.com, hana.hr@, maya.manager@ or priya.sharma@example.com)
- API docs (dev only): http://localhost:8000/api/docs
- Postgres: localhost:5433 (eod / eod)

## Host it

```sh
cp .env.example .env          # set SESSION_SECRET, POSTGRES_PASSWORD, GROQ_API_KEY
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api python -m app.cli create-admin you@company.com "Your Name"
```

Put HTTPS (load balancer, Caddy, Cloudflare…) in front of `HTTP_PORT`: the session cookie is Secure-only, so
sign-in won't stick over plain http. Back up the `pgdata` volume.

## How accounts work

There is no email integration: the app hands out **one-time links** and you send them yourself.

| Who | Gets a link from | How |
|---|---|---|
| Manager / HR / Admin | an admin | Users → Invite user |
| Joinee | their manager | Add joinee (or "New sign-up link" in their plan if it expired) |
| Anyone who forgot their password | an admin | Users → Reset link |
| Locked out admin | the server | `python -m app.cli create-admin <email>` or `reset-link <email>` |

Invite links last 7 days, reset links 24 hours, and each works once. 5 wrong passwords lock an account for 15
minutes. Changing a password, role or deactivating someone signs them out everywhere.

## Code map

```
backend/app/
  main.py          app assembly: middleware, routers, startup
  config.py        every env var, read once
  db.py            connection pool, per-request transaction, migration runner
  deps.py          auth dependencies: current_user, require_role
  security.py      argon2 password hashing, one-time tokens
  core.py          pure domain rules and shared validated field types
  routers/         HTTP layer, one per domain (auth, admin, manager, joinee, info_hub)
  repositories/    all SQL, one module per aggregate
  ai/              providers.py: Groq / Gemini / Anthropic behind one interface + factory; planner.py: brief -> tasks
  migrations/      numbered .sql files, each applied once
web/src/
  App.tsx          session + role-based navigation (NAV table)
  lib/             http client, formatting, useResource hook
  services/        one typed API module per backend domain
  features/        screens by domain: auth, admin, manager, joinee, infoHub
  components/      shared UI
```

| Change | How |
|---|---|
| Switch AI vendor | set `AI_PROVIDER` (groq / gemini / anthropic) and that vendor's key in `.env`, restart `api` |
| Add an AI vendor | subclass `Provider` in `backend/app/ai/providers.py`, add it to `PROVIDERS` |
| Schema | add `backend/app/migrations/00N_name.sql`; never edit an applied one |
| Info Hub content | in the app: Edit Info Hub (HR / Admin) |
| Reset all local data | `docker compose down -v` |
| Checks | `docker compose exec api sh -c "python -m tests.test_core && python -m tests.test_ai && python -m app.security && python -m tests.test_api"` |

Not built yet: email delivery of links, proof uploads, audit trail, self-service "forgot password".
