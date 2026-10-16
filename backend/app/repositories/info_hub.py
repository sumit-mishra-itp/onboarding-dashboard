"""info_resource data access. Returns rows or None; never raises HTTP errors."""
from uuid import UUID

COLS = "id, category, title, body_md, contact_email, link_url, display_order, last_reviewed_date, is_active, updated_at"
EDITABLE = ("category", "title", "body_md", "contact_email", "link_url", "display_order", "is_active")


def search(conn, q: str, include_inactive: bool) -> list[dict]:
    return conn.execute(
        f"SELECT {COLS} FROM info_resource"
        " WHERE (is_active OR %(all)s)"
        "   AND (%(q)s::text = '' OR tsv_search @@ websearch_to_tsquery('english', %(q)s::text)"
        "        OR title ILIKE '%%' || %(like)s || '%%' ESCAPE '\\')"
        " ORDER BY category, display_order, title",
        # Escape LIKE wildcards so a search for "100%" means the literal text.
        {"q": q, "like": q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_"), "all": include_inactive},
    ).fetchall()


def create(conn, data: dict, user_id: UUID) -> dict:
    cols = [c for c in EDITABLE if c in data]
    return conn.execute(
        f"INSERT INTO info_resource ({', '.join(cols)}, last_reviewed_date, updated_by)"
        f" VALUES ({', '.join(f'%({c})s' for c in cols)}, current_date, %(by)s) RETURNING {COLS}",
        {**data, "by": user_id}).fetchone()


def update(conn, entry_id: UUID, data: dict, user_id: UUID) -> dict | None:
    """Any edit counts as a review: last_reviewed_date moves to today."""
    sets = "".join(f"{c} = %({c})s, " for c in EDITABLE if c in data)
    return conn.execute(
        f"UPDATE info_resource SET {sets}last_reviewed_date = current_date, updated_at = now(), updated_by = %(by)s"
        f" WHERE id = %(id)s RETURNING {COLS}", {**data, "by": user_id, "id": entry_id}).fetchone()


def delete(conn, entry_id: UUID) -> bool:
    return conn.execute("DELETE FROM info_resource WHERE id = %s RETURNING id", (entry_id,)).fetchone() is not None
