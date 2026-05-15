from __future__ import annotations
import os
from pathlib import Path
from app.models.session import ProFormaSession


def _draft_path() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home())
    return Path(appdata) / "NAI_ProForma" / "draft.json"


def save_draft(session: ProFormaSession) -> None:
    p = _draft_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(session.to_json(), encoding="utf-8")


def load_draft() -> ProFormaSession | None:
    p = _draft_path()
    if not p.exists():
        return None
    try:
        return ProFormaSession.from_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def clear_draft() -> None:
    p = _draft_path()
    if p.exists():
        p.unlink()
