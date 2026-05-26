from __future__ import annotations
import sqlite3
from app.db.database import init_db


def get_setting(key: str, default: str | None = None, conn: sqlite3.Connection | None = None) -> str | None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        if _owned:
            c.close()


def set_setting(key: str, value: str, conn: sqlite3.Connection | None = None) -> None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        c.commit()
    finally:
        if _owned:
            c.close()
