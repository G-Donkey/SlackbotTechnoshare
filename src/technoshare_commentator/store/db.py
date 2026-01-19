"""SQLite database connection and schema management.

Provides get_db_connection() context manager and init_db() for schema creation.
Stores messages and jobs tables for the event queue.
"""

import sqlite3
from ..config import get_settings
from contextlib import contextmanager

settings = get_settings()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL,
        message_ts TEXT NOT NULL,
        thread_ts TEXT,
        user_id TEXT,
        text TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'received',
        UNIQUE(channel_id, message_ts)
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL,
        message_ts TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        attempts INTEGER DEFAULT 0,
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(channel_id, message_ts) REFERENCES messages(channel_id, message_ts)
    );
    """
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.commit()
