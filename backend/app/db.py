"""Connection pool, the per-request connection dependency, and the migration runner."""
import json
from pathlib import Path

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

HERE = Path(__file__).parent

# Sized for ~50 users: most requests hold a connection for milliseconds; an AI draft holds one for up to ~40s.
pool = ConnectionPool(settings.database_url, min_size=2, max_size=settings.db_pool_max,
                      kwargs={"row_factory": dict_row}, check=ConnectionPool.check_connection, open=False)


def get_conn():
    with pool.connection() as conn:  # one transaction per request: commit on success, rollback on exception
        yield conn


# scope="function": commit before the response is sent, so the client's next request sees the write.
DB = Depends(get_conn, scope="function")


def migrate():
    """Apply migrations/NNN_*.sql once each, in name order, each in its own transaction.
    The advisory lock makes this safe when several workers start at once."""
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(727001)")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migration"
                     " (name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        done = {r[0] for r in conn.execute("SELECT name FROM schema_migration")}
        for f in sorted((HERE / "migrations").glob("*.sql")):
            if f.name not in done:
                with conn.transaction():
                    conn.execute(f.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migration (name) VALUES (%s)", (f.name,))
        if "seed:info_hub" not in done:
            with conn.transaction():
                _seed_info_hub(conn)
                conn.execute("INSERT INTO schema_migration (name) VALUES ('seed:info_hub')")
        conn.execute("SELECT pg_advisory_unlock(727001)")


def _seed_info_hub(conn):
    """One-time starter content. After this, HR/Admin own the Info Hub through the app."""
    if conn.execute("SELECT 1 FROM info_resource LIMIT 1").fetchone():
        return
    for i, r in enumerate(json.loads((HERE / "info_hub_seed.json").read_text(encoding="utf-8"))):
        conn.execute(
            "INSERT INTO info_resource (category, title, body_md, contact_email, link_url, display_order,"
            " last_reviewed_date, is_active) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (r["category"], r["title"], r["body_md"], r.get("contact_email"), r.get("link_url"), i * 10,
             r["last_reviewed_date"], r.get("is_active", True)),
        )
