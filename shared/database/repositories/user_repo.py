from __future__ import annotations

from ..connection import get_db


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = TRUE",
            (email,),
        ).fetchone()
    return dict(row) if row else None
