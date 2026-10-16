"""Operator commands, run inside the api container.

  python -m app.cli create-admin you@company.com "Your Name"   # first admin, or recover admin access
  python -m app.cli reset-link someone@company.com              # one-time password link, if no admin can sign in
"""
import getpass
import sys

import psycopg
from psycopg.rows import dict_row

from . import security
from .config import settings
from .db import migrate
from .repositories import users


def main(cmd: str, email: str, *rest: str):
    migrate()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        email = email.strip().lower()
        u = users.get_for_login(conn, email)
        if cmd == "create-admin":
            pw = getpass.getpass("Password (10+ characters): ")
            if len(pw) < 10 or pw != getpass.getpass("Again: "):
                sys.exit("Passwords must match and be at least 10 characters.")
            if u:
                users.update(conn, u["id"], {"role": "ADMIN", "is_active": True})
                uid = u["id"]
            else:
                uid = users.create(conn, email=email, full_name=rest[0] if rest else email, role="ADMIN")
            users.set_password(conn, uid, security.hash_password(pw))
            print(f"Admin ready: {email}")
        elif cmd == "reset-link":
            if not u:
                sys.exit(f"No user {email}")
            token = users.issue_token(conn, u["id"], "RESET", security.RESET_TTL_HOURS, None)
            print(f"Open within {security.RESET_TTL_HOURS}h: <your site>/set-password#token={token}")
        else:
            sys.exit(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
