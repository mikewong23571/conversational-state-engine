"""Seed local SQLite database with initial data."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("state_engine.db")


def seed() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, current_version TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS states (session_id TEXT, version TEXT, schema_version TEXT, data TEXT)"
    )
    conn.execute(
        "INSERT OR REPLACE INTO sessions (session_id, current_version) VALUES (?, ?)",
        ("demo", "v1"),
    )
    state = {"stories": [], "glossary": []}
    conn.execute(
        "INSERT OR REPLACE INTO states (session_id, version, schema_version, data) VALUES (?, ?, ?, ?)",
        ("demo", "v1", "1.0.0", json.dumps(state)),
    )
    conn.commit()
    conn.close()
    print("Seeded demo data")


if __name__ == "__main__":
    seed()
