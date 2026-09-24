"""SQLite-backed user store for authentication (username + bcrypt password hash).

Kept intentionally simple (stdlib sqlite3, no ORM) since this app has exactly
one table. The DB file persists across restarts (unlike quiz sessions, which
are in-memory), so registered accounts survive server restarts/redeploys.
"""
import sqlite3
from pathlib import Path
from typing import Optional

from app.config import settings

_DB_PATH = Path(settings.users_db_path)


def _get_connection() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def create_user(username: str, display_name: str, password_hash: str) -> sqlite3.Row:
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
            (username, display_name, password_hash),
        )
        user_id = cursor.lastrowid
        row = conn.execute("SELECT id, username, display_name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        return row


def get_user_by_username(username: str) -> Optional[sqlite3.Row]:
    with _get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int) -> Optional[sqlite3.Row]:
    with _get_connection() as conn:
        return conn.execute(
            "SELECT id, username, display_name, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def username_exists(username: str) -> bool:
    return get_user_by_username(username) is not None
