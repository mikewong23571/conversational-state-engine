import sqlite3
from contextlib import contextmanager

DB_PATH = "state_engine.db"


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                current_version TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                version TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                UNIQUE(session_id, version)
            );

            CREATE TABLE IF NOT EXISTS draft_intentions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS patch_proposals (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                intention_set_id TEXT,
                patches TEXT NOT NULL,
                impact_analysis TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                selected_patch_indices TEXT DEFAULT '[]',
                applied_auto_fixes TEXT DEFAULT '{}',
                stage_confirmations TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id),
                FOREIGN KEY (intention_set_id) REFERENCES draft_intentions(id)
            );

            CREATE TABLE IF NOT EXISTS commits (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                parent_version TEXT NOT NULL,
                new_version TEXT NOT NULL,
                patches TEXT NOT NULL,
                reverse_patches TEXT NOT NULL,
                author TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                version TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
            """
        )
        conn.commit()
