from __future__ import annotations

import json
from typing import Any

from ..connection import get_db


def create_initial_state(
    session_id: str, state: dict[str, Any], version: str = "v1"
) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
            (session_id, version, "1.0.0", json.dumps(state)),
        )
        conn.commit()


def get_state(session_id: str, version: str) -> dict[str, Any] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM states WHERE session_id = ? AND version = ?",
            (session_id, version),
        ).fetchone()
    return dict(row) if row else None
