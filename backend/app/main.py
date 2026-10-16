"""App assembly: middleware, routers, startup. No business logic here.

Layers (each only calls the one below it):
  routers/       HTTP: validation, auth dependencies, status codes
  repositories/  SQL, one module per aggregate
  core.py        pure domain rules and shared field types
  ai/            LLM providers behind one interface + the drafting capability
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .db import DB, migrate, pool
from .routers import admin, auth, info_hub, joinee, manager


@asynccontextmanager
async def lifespan(_):
    migrate()
    pool.open(wait=True)
    yield
    pool.close()


app = FastAPI(title="Employee Onboarding Dashboard", lifespan=lifespan,
              docs_url="/api/docs" if settings.dev else None, redoc_url=None,
              openapi_url="/api/openapi.json" if settings.dev else None)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, session_cookie="onb_session",
                   max_age=settings.session_max_age, same_site="lax", https_only=settings.cookie_secure)

for r in (auth, admin, manager, joinee, info_hub):
    app.include_router(r.router)


@app.get("/api/health", tags=["ops"])
def health(conn=DB):
    conn.execute("SELECT 1")
    return {"ok": True}
