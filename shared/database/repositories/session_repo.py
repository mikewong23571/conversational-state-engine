from __future__ import annotations

from ..connection import get_db


def create_session(session_id: str, initial_version: str = "v1") -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, current_version) VALUES (?, ?)",
            (session_id, initial_version),
        )
        conn.commit()


def get_session(session_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None
