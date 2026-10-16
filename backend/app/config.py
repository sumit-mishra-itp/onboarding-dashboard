"""Every environment variable the app reads, in one place, read once at import."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    dev: bool
    database_url: str
    session_secret: str
    session_max_age: int   # seconds; sliding: every response refreshes the cookie
    cookie_secure: bool    # Secure flag: cookie only sent over HTTPS
    db_pool_max: int
    ai_provider: str
    ai_model: str          # "" = the provider's default


def _load() -> Settings:
    dev = os.environ.get("APP_ENV", "production").lower() == "dev"
    secret = os.environ.get("SESSION_SECRET", "")
    if len(secret) < 32:
        if not dev:
            raise RuntimeError("SESSION_SECRET must be at least 32 random characters (e.g. `openssl rand -hex 32`)")
        secret = secret or "dev-only-not-a-secret-dev-only-not-a-secret"
    return Settings(
        dev=dev,
        database_url=os.environ["DATABASE_URL"],
        session_secret=secret,
        session_max_age=int(os.environ.get("SESSION_MAX_AGE", 12 * 3600)),
        cookie_secure=os.environ.get("COOKIE_SECURE", "false" if dev else "true").lower() == "true",
        db_pool_max=int(os.environ.get("DB_POOL_MAX", 20)),
        ai_provider=os.environ.get("AI_PROVIDER", "groq").strip().lower(),
        ai_model=os.environ.get("AI_MODEL", "").strip(),
    )


settings = _load()
