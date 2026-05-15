from __future__ import annotations
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from app.models.session import ProFormaSession


def _default_path() -> str:
    appdata = os.environ.get("APPDATA") or str(Path.home())
    db_dir = Path(appdata) / "NAI_ProForma"
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / "runs.db")


def init_db(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or _default_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            excel_path TEXT NOT NULL,
            noi_y1 REAL,
            value_y1 REAL
        )
    """)
    conn.commit()
    return conn


def save_run(
    session: ProFormaSession, excel_path: str,
    noi_y1: float, value_y1: float,
    conn: sqlite3.Connection | None = None,
) -> int:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        cur = c.execute(
            "INSERT INTO runs (building_name, created_at, inputs_json, excel_path, noi_y1, value_y1) "
            "VALUES (?,?,?,?,?,?)",
            (session.building_name, datetime.now().isoformat(),
             session.to_json(), excel_path, noi_y1, value_y1),
        )
        c.commit()
        return cur.lastrowid
    finally:
        if _owned:
            c.close()


def list_runs(conn: sqlite3.Connection | None = None) -> list[dict]:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        rows = c.execute(
            "SELECT id, building_name, created_at, excel_path, noi_y1, value_y1 "
            "FROM runs ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [{"id": r[0], "building_name": r[1], "created_at": r[2],
                 "excel_path": r[3], "noi_y1": r[4], "value_y1": r[5]} for r in rows]
    finally:
        if _owned:
            c.close()


def get_run(run_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        r = c.execute(
            "SELECT id, building_name, created_at, inputs_json, excel_path, noi_y1, value_y1 "
            "FROM runs WHERE id=?",
            (run_id,),
        ).fetchone()
        if not r:
            return None
        return {"id": r[0], "building_name": r[1], "created_at": r[2],
                "inputs_json": r[3], "excel_path": r[4], "noi_y1": r[5], "value_y1": r[6]}
    finally:
        if _owned:
            c.close()


def delete_run(run_id: int, conn: sqlite3.Connection | None = None) -> None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        c.execute("DELETE FROM runs WHERE id=?", (run_id,))
        c.commit()
    finally:
        if _owned:
            c.close()
