# NAI Pro Forma Generator — Feature Additions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four features to the NAI Pro Forma Generator: deal templates, deal notes, IRR/NPV return analysis, and one-click email delivery.

**Architecture:** All features extend existing modules — no new subsystems. Templates live in a new SQLite table. Notes are a new session field rendered in PDF/Excel. IRR/NPV adds a calculator function and Review page UI. Email opens Outlook (via COM) or Gmail (via browser) with the generated PDF.

**Tech Stack:** PySide6, SQLite (sqlite3), openpyxl, QPdfWriter, pywin32 (win32com), Python stdlib (webbrowser, urllib.parse, html)

---

## File Map

**Create:**
- `app/ui/wizard/page_notes.py` — Notes wizard page (QPlainTextEdit)
- `app/ui/email_dialog.py` — Email delivery dialog (Outlook + Gmail)
- `tests/test_templates.py` — Template CRUD tests
- `tests/test_notes.py` — Notes serialization + output tests
- `tests/test_irr_npv.py` — IRR/NPV calculator tests
- `tests/test_email.py` — Email dialog tests (mocked)

**Modify:**
- `app/db/database.py` — Add `templates` table + 4 CRUD functions
- `app/models/session.py` — Add `notes`, `purchase_price`, `exit_cap_rate`, `discount_rate` fields
- `app/logic/calculator.py` — Add `_irr`, `_npv`, `calculate_irr_npv`
- `app/ui/dashboard.py` — Add QTabWidget with Saved Runs + Templates tabs
- `app/ui/wizard/wizard.py` — Add NotesPage, update step count 3→4
- `app/ui/wizard/page_review.py` — Add IRR QGroupBox + Email button
- `app/excel/pdf_writer.py` — Add notes section + Return Analysis section
- `app/excel/writer.py` — Add Notes sheet, accept `irr_data` param
- `app/excel/inputs_sheet.py` — Add Return Analysis block below tenant data
- `NAI_ProForma_Generator.spec` — Add pywin32 hidden imports

---

## Task 1: Templates — Database Layer

**Files:**
- Modify: `app/db/database.py`
- Create: `tests/test_templates.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_templates.py`:

```python
import pytest
from app.db.database import (
    init_db, save_template, list_templates, get_template, delete_template,
    save_run, delete_run,
)
from app.models.session import ProFormaSession


@pytest.fixture
def db():
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_save_and_list_template(db, basic_session):
    tid = save_template("Office Standard", basic_session, conn=db)
    rows = list_templates(conn=db)
    assert len(rows) == 1
    assert rows[0]["template_name"] == "Office Standard"
    assert rows[0]["building_name"] == "Test Tower"
    assert rows[0]["id"] == tid


def test_get_template_restores_session(db, basic_session):
    tid = save_template("Test Tmpl", basic_session, conn=db)
    row = get_template(tid, conn=db)
    restored = ProFormaSession.from_json(row["inputs_json"])
    assert restored.building_name == "Test Tower"
    assert len(restored.tenants) == 1


def test_get_template_returns_none_for_missing(db):
    assert get_template(999, conn=db) is None


def test_delete_template(db, basic_session):
    tid = save_template("Temp", basic_session, conn=db)
    delete_template(tid, conn=db)
    assert list_templates(conn=db) == []


def test_duplicate_template_names_allowed(db, basic_session):
    save_template("Same", basic_session, conn=db)
    save_template("Same", basic_session, conn=db)
    assert len(list_templates(conn=db)) == 2


def test_deleting_run_does_not_affect_templates(db, basic_session):
    save_template("Keeper", basic_session, conn=db)
    run_id = save_run(basic_session, "/tmp/x.xlsx", 0.0, 0.0, conn=db)
    delete_run(run_id, conn=db)
    assert len(list_templates(conn=db)) == 1


def test_list_templates_ordered_newest_first(db, basic_session):
    save_template("First", basic_session, conn=db)
    save_template("Second", basic_session, conn=db)
    rows = list_templates(conn=db)
    assert rows[0]["template_name"] == "Second"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_templates.py -v
```

Expected: `ImportError` or `FAILED` — `save_template` not defined.

- [ ] **Step 3: Implement the templates DB layer**

Replace the contents of `app/db/database.py` with:

```python
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            building_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            inputs_json TEXT NOT NULL
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


def save_template(
    name: str, session: ProFormaSession,
    conn: sqlite3.Connection | None = None,
) -> int:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        cur = c.execute(
            "INSERT INTO templates (template_name, building_name, created_at, inputs_json) "
            "VALUES (?,?,?,?)",
            (name, session.building_name, datetime.now().isoformat(), session.to_json()),
        )
        c.commit()
        return cur.lastrowid
    finally:
        if _owned:
            c.close()


def list_templates(conn: sqlite3.Connection | None = None) -> list[dict]:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        rows = c.execute(
            "SELECT id, template_name, building_name, created_at "
            "FROM templates ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [{"id": r[0], "template_name": r[1], "building_name": r[2],
                 "created_at": r[3]} for r in rows]
    finally:
        if _owned:
            c.close()


def get_template(template_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        r = c.execute(
            "SELECT id, template_name, building_name, created_at, inputs_json "
            "FROM templates WHERE id=?",
            (template_id,),
        ).fetchone()
        if not r:
            return None
        return {"id": r[0], "template_name": r[1], "building_name": r[2],
                "created_at": r[3], "inputs_json": r[4]}
    finally:
        if _owned:
            c.close()


def delete_template(template_id: int, conn: sqlite3.Connection | None = None) -> None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        c.execute("DELETE FROM templates WHERE id=?", (template_id,))
        c.commit()
    finally:
        if _owned:
            c.close()
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_templates.py tests/test_database.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```
git add app/db/database.py tests/test_templates.py
git commit -m "feat: add templates table and CRUD functions to database"
```

---

## Task 2: Templates — Dashboard UI

**Files:**
- Modify: `app/ui/dashboard.py`

No new test file for this UI task — the DB functions are already tested. The test is: launch the app and verify the Templates tab appears and works.

- [ ] **Step 1: Replace `app/ui/dashboard.py` with the updated version**

```python
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QTabWidget, QInputDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from app.db.database import (
    init_db, list_runs, delete_run, get_run,
    list_templates, get_template, delete_template, save_template,
)
from app.models.session import ProFormaSession

_LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "nai_logo.svg"


class _NumericItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)
        except TypeError:
            return super().__lt__(other)


class DashboardView(QWidget):
    def __init__(self, on_new, on_edit):
        super().__init__()
        self._on_new = on_new
        self._on_edit = on_edit
        self._db = init_db()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # White header bar
        header = QWidget()
        header.setStyleSheet("background: #FFFFFF; border-bottom: 1px solid #DDDDDD;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 14, 24, 14)
        hl.setSpacing(0)

        if _LOGO_PATH.exists():
            logo = QSvgWidget(str(_LOGO_PATH))
            logo.setFixedSize(170, 37)
            logo.setStyleSheet("background: transparent;")
            hl.addWidget(logo)
        else:
            hl.addWidget(QLabel("NAI Horizon"))

        hl.addSpacing(20)
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("color: #DDDDDD; max-height: 30px;")
        hl.addWidget(div)
        hl.addSpacing(20)

        title = QLabel("Pro Forma Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #222222;")
        hl.addWidget(title)
        hl.addStretch()

        new_btn = QPushButton("+ New Pro Forma")
        new_btn.setObjectName("primaryBtn")
        new_btn.clicked.connect(self._on_new)
        hl.addWidget(new_btn)
        layout.addWidget(header)

        # Stats bar
        stats_bar = QWidget()
        stats_bar.setStyleSheet("background: #F0F0F0; border-bottom: 1px solid #E0E0E0;")
        sl = QHBoxLayout(stats_bar)
        sl.setContentsMargins(24, 7, 24, 7)
        self._count_lbl = QLabel("0 pro formas saved")
        self._count_lbl.setStyleSheet("color: #666666; font-size: 12px;")
        sl.addWidget(self._count_lbl)
        sl.addStretch()
        layout.addWidget(stats_bar)

        # Tab widget body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 24)
        bl.setSpacing(12)

        self._tabs = QTabWidget()

        # --- Saved Runs tab ---
        runs_tab = QWidget()
        runs_layout = QVBoxLayout(runs_tab)
        runs_layout.setContentsMargins(0, 12, 0, 0)
        runs_layout.setSpacing(8)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("card")
        self.table.setHorizontalHeaderLabels(
            ["Building Name", "Date Created", "NOI (Year 1)", "Value (Year 1)", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(4, 330)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().setSortIndicator(1, Qt.SortOrder.DescendingOrder)
        runs_layout.addWidget(self.table)

        self._empty = QLabel("No pro formas yet — click New Pro Forma to get started")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888888; font-size: 14px; padding: 60px;")
        runs_layout.addWidget(self._empty)
        self._tabs.addTab(runs_tab, "Saved Runs")

        # --- Templates tab ---
        tmpl_tab = QWidget()
        tmpl_layout = QVBoxLayout(tmpl_tab)
        tmpl_layout.setContentsMargins(0, 12, 0, 0)
        tmpl_layout.setSpacing(8)

        self.tmpl_table = QTableWidget(0, 4)
        self.tmpl_table.setObjectName("card")
        self.tmpl_table.setHorizontalHeaderLabels(
            ["Template Name", "Building", "Created", "Actions"]
        )
        self.tmpl_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tmpl_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tmpl_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tmpl_table.setColumnWidth(3, 160)
        self.tmpl_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tmpl_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tmpl_table.verticalHeader().setVisible(False)
        self.tmpl_table.setAlternatingRowColors(True)
        tmpl_layout.addWidget(self.tmpl_table)

        self._tmpl_empty = QLabel("No templates yet — use 'Save as Template' on a saved run to create one")
        self._tmpl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tmpl_empty.setStyleSheet("color: #888888; font-size: 14px; padding: 60px;")
        tmpl_layout.addWidget(self._tmpl_empty)
        self._tabs.addTab(tmpl_tab, "Templates")

        bl.addWidget(self._tabs)
        layout.addWidget(body, 1)

    def refresh(self):
        self._refresh_runs()
        self._refresh_templates()

    def _refresh_runs(self):
        self.table.setSortingEnabled(False)
        runs = list_runs(conn=self._db)
        self.table.setRowCount(0)
        count = len(runs)
        self._count_lbl.setText(f"{count} pro forma{'s' if count != 1 else ''} saved")
        self._empty.setVisible(not runs)
        self.table.setVisible(bool(runs))
        for run in runs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            dt = datetime.fromisoformat(run["created_at"]).strftime("%b %d, %Y  %I:%M %p")
            noi_val = run["noi_y1"] or 0.0
            val_val = run["value_y1"] or 0.0
            texts = [
                run["building_name"],
                dt,
                f"${noi_val:,.0f}" if run["noi_y1"] else "—",
                f"${val_val:,.0f}" if run["value_y1"] else "—",
            ]
            sort_keys = [None, None, noi_val, val_val]
            for c, (v, key) in enumerate(zip(texts, sort_keys)):
                if key is not None:
                    item = _NumericItem(v)
                    item.setData(Qt.ItemDataRole.UserRole, key)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                else:
                    item = QTableWidgetItem(v)
                self.table.setItem(r, c, item)
            acts = QWidget()
            al = QHBoxLayout(acts)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            for label, slot, obj_name in [
                ("Open",     lambda _, rid=run["id"]: self._open(rid),             "tableBtn"),
                ("Edit",     lambda _, rid=run["id"]: self._edit(rid),             "tableBtn"),
                ("Clone",    lambda _, rid=run["id"]: self._clone(rid),            "tableBtn"),
                ("Template", lambda _, rid=run["id"]: self._save_as_template(rid), "tableBtn"),
                ("Delete",   lambda _, rid=run["id"]: self._delete(rid),           "dangerBtn"),
            ]:
                b = QPushButton(label)
                b.setObjectName(obj_name)
                b.clicked.connect(slot)
                al.addWidget(b)
            self.table.setCellWidget(r, 4, acts)
        self.table.setSortingEnabled(True)

    def _refresh_templates(self):
        templates = list_templates(conn=self._db)
        self.tmpl_table.setRowCount(0)
        self._tmpl_empty.setVisible(not templates)
        self.tmpl_table.setVisible(bool(templates))
        for tmpl in templates:
            r = self.tmpl_table.rowCount()
            self.tmpl_table.insertRow(r)
            dt = datetime.fromisoformat(tmpl["created_at"]).strftime("%b %d, %Y")
            for c, v in enumerate([tmpl["template_name"], tmpl["building_name"], dt]):
                self.tmpl_table.setItem(r, c, QTableWidgetItem(v))
            acts = QWidget()
            al = QHBoxLayout(acts)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            for label, slot, obj_name in [
                ("Open",   lambda _, tid=tmpl["id"]: self._open_template(tid),   "tableBtn"),
                ("Delete", lambda _, tid=tmpl["id"]: self._delete_template(tid), "dangerBtn"),
            ]:
                b = QPushButton(label)
                b.setObjectName(obj_name)
                b.clicked.connect(slot)
                al.addWidget(b)
            self.tmpl_table.setCellWidget(r, 3, acts)

    def _open(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        path = row["excel_path"]
        if not os.path.exists(path):
            from app.excel.writer import write_workbook
            write_workbook(ProFormaSession.from_json(row["inputs_json"]), path)
        os.startfile(path)

    def _edit(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        self._on_edit(ProFormaSession.from_json(row["inputs_json"]))

    def _clone(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        session = ProFormaSession.from_json(row["inputs_json"])
        session.building_name = f"{session.building_name} (Copy)" if session.building_name else "Copy"
        self._on_edit(session)

    def _save_as_template(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        default_name = row["building_name"] or "My Template"
        name, ok = QInputDialog.getText(
            self, "Save as Template", "Template name:", text=default_name
        )
        if not ok or not name.strip():
            return
        try:
            session = ProFormaSession.from_json(row["inputs_json"])
            save_template(name.strip(), session, conn=self._db)
            self._refresh_templates()
            self._tabs.setCurrentIndex(1)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save template: {e}")

    def _open_template(self, template_id: int):
        row = get_template(template_id, conn=self._db)
        if not row:
            return
        try:
            session = ProFormaSession.from_json(row["inputs_json"])
            self._on_edit(session)
        except Exception as e:
            QMessageBox.warning(self, "Template Error", f"Could not load template: {e}")

    def _delete(self, run_id: int):
        if QMessageBox.question(
            self, "Delete", "Remove this run?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            delete_run(run_id, conn=self._db)
            self._refresh_runs()

    def _delete_template(self, template_id: int):
        if QMessageBox.question(
            self, "Delete Template", "Remove this template?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            delete_template(template_id, conn=self._db)
            self._refresh_templates()
```

- [ ] **Step 2: Run the full test suite to ensure nothing broke**

```
pytest -v
```

Expected: all existing tests PASS.

- [ ] **Step 3: Commit**

```
git add app/ui/dashboard.py
git commit -m "feat: add Templates tab to dashboard with save/open/delete"
```

---

## Task 3: Deal Notes — Session Model + Wizard Page

**Files:**
- Modify: `app/models/session.py`
- Create: `app/ui/wizard/page_notes.py`
- Modify: `app/ui/wizard/wizard.py`
- Create: `tests/test_notes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_notes.py`:

```python
import json
import pytest
from app.models.session import ProFormaSession


def test_notes_default_empty():
    s = ProFormaSession()
    assert s.notes == ""


def test_notes_round_trip(basic_session):
    basic_session.notes = "Deal note line 1.\nLine 2."
    restored = ProFormaSession.from_json(basic_session.to_json())
    assert restored.notes == "Deal note line 1.\nLine 2."


def test_old_json_without_notes_loads_empty():
    old = {
        "building_name": "Old", "start_year": 2024, "start_month": 1,
        "years": 5, "total_sqft": 1000.0, "occupied_sqft": 800.0,
        "opex_psf": 5.0, "market_avg_rate": 20.0, "market_growth_pct": 0.02,
        "cap_rate": 0.065, "cap_delta": 0.0025, "tenants": [],
    }
    s = ProFormaSession.from_json(json.dumps(old))
    assert s.notes == ""


def test_notes_preserved_in_template(basic_session):
    import sqlite3
    from app.db.database import init_db, save_template, get_template
    basic_session.notes = "Test assumption"
    conn = init_db(":memory:")
    tid = save_template("T", basic_session, conn=conn)
    row = get_template(tid, conn=conn)
    restored = ProFormaSession.from_json(row["inputs_json"])
    conn.close()
    assert restored.notes == "Test assumption"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_notes.py -v
```

Expected: FAIL — `ProFormaSession` has no `notes` attribute.

- [ ] **Step 3: Add `notes` field to `ProFormaSession`**

Replace `app/models/session.py` with:

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from app.models.tenant import TenantModel


@dataclass
class ProFormaSession:
    building_name: str = ""
    start_year: int = 2025
    start_month: int = 1
    years: int = 10
    total_sqft: float = 0.0
    occupied_sqft: float = 0.0
    opex_psf: float = 0.0
    market_avg_rate: float = 0.0
    market_growth_pct: float = 0.0
    cap_rate: float = 0.0
    cap_delta: float = 0.0025
    notes: str = ""
    purchase_price: float = 0.0
    exit_cap_rate: float = 0.0
    discount_rate: float = 0.08
    tenants: list[TenantModel] = field(default_factory=list)

    def to_json(self) -> str:
        d = {
            "building_name": self.building_name, "start_year": self.start_year,
            "start_month": self.start_month, "years": self.years,
            "total_sqft": self.total_sqft, "occupied_sqft": self.occupied_sqft,
            "opex_psf": self.opex_psf, "market_avg_rate": self.market_avg_rate,
            "market_growth_pct": self.market_growth_pct, "cap_rate": self.cap_rate,
            "cap_delta": self.cap_delta, "notes": self.notes,
            "purchase_price": self.purchase_price, "exit_cap_rate": self.exit_cap_rate,
            "discount_rate": self.discount_rate,
            "tenants": [t.to_dict() for t in self.tenants],
        }
        return json.dumps(d)

    @classmethod
    def from_json(cls, s: str) -> ProFormaSession:
        d = json.loads(s)
        tenants = [TenantModel.from_dict(t) for t in d.pop("tenants", [])]
        return cls(tenants=tenants, **d)
```

- [ ] **Step 4: Run the notes tests**

```
pytest tests/test_notes.py -v
```

Expected: all PASS.

- [ ] **Step 5: Create `app/ui/wizard/page_notes.py`**

```python
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit
from PySide6.QtCore import Qt
from app.models.session import ProFormaSession


class NotesPage(QWidget):
    def __init__(self, session: ProFormaSession):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 0)
        title = QLabel("Deal Notes & Assumptions")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)
        sub = QLabel("Optional. These notes will appear in the PDF and Excel output.")
        sub.setStyleSheet("color: #666666; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(sub)
        self._edit = QPlainTextEdit()
        self._edit.setPlaceholderText(
            "Enter deal assumptions, market commentary, or any relevant notes..."
        )
        layout.addWidget(self._edit, 1)
        self._count_lbl = QLabel("0 characters")
        self._count_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_lbl)
        self._edit.textChanged.connect(self._update_count)

    def _update_count(self):
        n = len(self._edit.toPlainText())
        self._count_lbl.setText(f"{n} character{'s' if n != 1 else ''}")

    def bind(self, session: ProFormaSession):
        self.session = session

    def refresh(self):
        self._edit.setPlainText(self.session.notes)
        self._update_count()

    def validate(self) -> bool:
        return True

    def commit(self):
        self.session.notes = self._edit.toPlainText()
```

- [ ] **Step 6: Update `app/ui/wizard/wizard.py` to add the Notes page**

Replace the file with:

```python
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame,
)
from app.models.session import ProFormaSession


class WizardView(QWidget):
    def __init__(self, on_complete, on_cancel):
        super().__init__()
        self._on_complete = on_complete
        self._on_cancel = on_cancel
        self.session = ProFormaSession()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        from app.ui.wizard.page_building import BuildingInfoPage
        from app.ui.wizard.page_tenants import TenantEntryPage
        from app.ui.wizard.page_notes import NotesPage
        from app.ui.wizard.page_review import ReviewPage

        self.page_building = BuildingInfoPage(self.session)
        self.page_tenants = TenantEntryPage(self.session)
        self.page_notes = NotesPage(self.session)
        self.page_review = ReviewPage(self.session, on_generate=self._on_generate_done)
        self.stack.addWidget(self.page_building)   # index 0
        self.stack.addWidget(self.page_tenants)    # index 1
        self.stack.addWidget(self.page_notes)      # index 2
        self.stack.addWidget(self.page_review)     # index 3

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)
        nav = QHBoxLayout()
        nav.setContentsMargins(24, 12, 24, 12)
        self._step_lbl = QLabel()
        self._step_lbl.setObjectName("stepLabel")
        self._back_btn = QPushButton()
        self._back_btn.setObjectName("secondaryBtn")
        self._next_btn = QPushButton()
        self._next_btn.setObjectName("primaryBtn")
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._step_lbl)
        nav.addStretch()
        nav.addWidget(self._back_btn)
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)
        self._update_nav()

    def reset(self):
        from app.db.draft import clear_draft
        clear_draft()
        self.session = ProFormaSession()
        self.page_building.bind(self.session)
        self.page_tenants.bind(self.session)
        self.page_notes.bind(self.session)
        self.page_review.bind(self.session)
        self.stack.setCurrentIndex(0)
        self._update_nav()

    def load_session(self, session: ProFormaSession) -> None:
        self.session = session
        self.page_building.bind(session)
        self.page_tenants.bind(session)
        self.page_notes.bind(session)
        self.page_review.bind(session)
        self.stack.setCurrentIndex(0)
        self._update_nav()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx == 0:
            self._on_cancel()
            return
        self.stack.setCurrentIndex(idx - 1)
        self._update_nav()

    def _go_next(self):
        idx = self.stack.currentIndex()
        page = self.stack.widget(idx)
        if hasattr(page, "validate") and not page.validate():
            return
        if hasattr(page, "commit"):
            page.commit()
        if idx < 3:
            from app.db.draft import save_draft
            save_draft(self.session)
            if idx == 2:
                self.page_review.refresh()
            self.stack.setCurrentIndex(idx + 1)
            self._update_nav()

    def _on_generate_done(self) -> None:
        from app.db.draft import clear_draft
        clear_draft()
        self._on_complete()

    def _update_nav(self):
        idx = self.stack.currentIndex()
        self._step_lbl.setText(f"Step {idx + 1} of 4")
        self._back_btn.setText("Cancel" if idx == 0 else "Back")
        self._next_btn.setText("Generate Pro Forma" if idx == 3 else "Next")
```

- [ ] **Step 7: Run the full test suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```
git add app/models/session.py app/ui/wizard/page_notes.py app/ui/wizard/wizard.py tests/test_notes.py
git commit -m "feat: add notes field to session and Notes wizard step"
```

---

## Task 4: Deal Notes — PDF and Excel Output

**Files:**
- Modify: `app/excel/pdf_writer.py`
- Modify: `app/excel/writer.py`

- [ ] **Step 1: Add notes output tests to `tests/test_notes.py`**

Append to `tests/test_notes.py`:

```python
def test_pdf_contains_notes(basic_session, tmp_path):
    from app.logic.calculator import calculate_proforma
    from app.excel.pdf_writer import _build_html
    basic_session.notes = "Important assumption here."
    result = calculate_proforma(basic_session)
    html = _build_html(basic_session, result, irr_data=None)
    assert "Important assumption here." in html


def test_pdf_omits_notes_section_when_empty(basic_session):
    from app.logic.calculator import calculate_proforma
    from app.excel.pdf_writer import _build_html
    basic_session.notes = ""
    result = calculate_proforma(basic_session)
    html = _build_html(basic_session, result, irr_data=None)
    assert "Deal Notes" not in html


def test_excel_notes_sheet_exists(basic_session, tmp_path):
    from openpyxl import load_workbook
    from app.excel.writer import write_workbook
    basic_session.notes = "Test note."
    path = str(tmp_path / "test.xlsx")
    write_workbook(basic_session, path)
    wb = load_workbook(path)
    assert "Notes" in wb.sheetnames


def test_excel_notes_sheet_contains_text(basic_session, tmp_path):
    from openpyxl import load_workbook
    from app.excel.writer import write_workbook
    basic_session.notes = "My deal note."
    path = str(tmp_path / "test.xlsx")
    write_workbook(basic_session, path)
    wb = load_workbook(path)
    ws = wb["Notes"]
    values = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert any("My deal note." in str(v) for v in values if v)


def test_excel_notes_sheet_placeholder_when_empty(basic_session, tmp_path):
    from openpyxl import load_workbook
    from app.excel.writer import write_workbook
    basic_session.notes = ""
    path = str(tmp_path / "test.xlsx")
    write_workbook(basic_session, path)
    wb = load_workbook(path)
    ws = wb["Notes"]
    values = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert any("No notes" in str(v) for v in values if v)
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_notes.py::test_pdf_contains_notes tests/test_notes.py::test_excel_notes_sheet_exists -v
```

Expected: FAIL — `_build_html` doesn't accept `irr_data` param; no Notes sheet.

- [ ] **Step 3: Update `app/excel/pdf_writer.py`**

Replace the file with:

```python
from __future__ import annotations
import html as html_mod
from datetime import datetime
from app.models.session import ProFormaSession


def export_pdf(
    session: ProFormaSession,
    result: dict,
    output_path: str,
    irr_data: dict | None = None,
) -> None:
    from PySide6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize, QMarginsF
    writer = QPdfWriter(output_path)
    writer.setPageLayout(QPageLayout(
        QPageSize(QPageSize.PageSizeId.Letter),
        QPageLayout.Orientation.Portrait,
        QMarginsF(15, 15, 15, 15),
    ))
    doc = QTextDocument()
    doc.setHtml(_build_html(session, result, irr_data=irr_data))
    doc.print_(writer)


def _build_html(
    session: ProFormaSession,
    result: dict,
    irr_data: dict | None = None,
) -> str:
    s = session
    tenant_rows = "".join(
        f"<tr><td>{t.name}</td><td>{t.suite}</td><td>{t.sqft:,.0f}</td>"
        f"<td>${t.rate_psf:.2f}</td><td>{t.lease_exp}</td>"
        f"<td>{t.projection_type}</td></tr>"
        for t in s.tenants
    )
    noi_y1 = result["nois"][0] if result.get("nois") else 0.0
    val_y1 = result["values"][0] if result.get("values") else 0.0
    rev_y1 = result["rental_revenue"][0] if result.get("rental_revenue") else 0.0
    cap = s.cap_rate
    delta = s.cap_delta
    low_val = noi_y1 / (cap - delta) if (cap - delta) > 0 else 0.0
    high_val = noi_y1 / (cap + delta) if (cap + delta) > 0 else 0.0

    # Notes section
    notes_html = ""
    if s.notes.strip():
        escaped = html_mod.escape(s.notes).replace("\n", "<br/>")
        notes_html = f"""
  <h3>Deal Notes &amp; Assumptions</h3>
  <p style="font-family: Segoe UI, Arial, sans-serif; white-space: pre-wrap;">{escaped}</p>
"""

    # Return Analysis section
    return_html = ""
    if irr_data is not None:
        irr_str = f"{irr_data['irr']:.2%}" if irr_data.get("irr") is not None else "N/A"
        eff_exit = irr_data.get("effective_exit_cap", s.cap_rate)
        return_html = f"""
  <h3>Return Analysis</h3>
  <table cellpadding="4">
    <tr><td><b>Purchase Price:</b></td><td>${irr_data['effective_purchase']:,.0f}</td></tr>
    <tr><td><b>Exit Cap Rate:</b></td><td>{eff_exit:.2%}</td></tr>
    <tr><td><b>Exit Value:</b></td><td>${irr_data['exit_value']:,.0f}</td></tr>
    <tr><td><b>IRR:</b></td><td>{irr_str}</td></tr>
    <tr><td><b>NPV ({s.discount_rate:.1%} discount rate):</b></td><td>${irr_data['npv']:,.0f}</td></tr>
  </table>
"""

    return f"""
<html>
<body style="font-family: Segoe UI, Arial, sans-serif; color: #222222; font-size: 10pt;">
  <h1 style="color: #C8102E; margin-bottom: 4px;">NAI Horizon — Pro Forma Summary</h1>
  <h2 style="margin-top: 0;">{s.building_name}</h2>
  <p style="color: #666666; margin-top: 0;">Generated: {datetime.now().strftime("%B %d, %Y")}</p>
  <hr style="border: none; border-top: 1px solid #DDDDDD;"/>

  <h3>Building Parameters</h3>
  <table cellpadding="4">
    <tr><td><b>Projection Period:</b></td><td>{s.start_month}/{s.start_year} — {s.years} years</td></tr>
    <tr><td><b>Total SF:</b></td><td>{s.total_sqft:,.0f}</td></tr>
    <tr><td><b>Occupied SF:</b></td><td>{s.occupied_sqft:,.0f}</td></tr>
    <tr><td><b>OpEx / SF:</b></td><td>${s.opex_psf:.2f}</td></tr>
    <tr><td><b>Market Avg Rate:</b></td><td>${s.market_avg_rate:.2f}/SF</td></tr>
    <tr><td><b>Market Rent Growth:</b></td><td>{s.market_growth_pct:.1%}</td></tr>
    <tr><td><b>Cap Rate:</b></td><td>{s.cap_rate:.2%}</td></tr>
  </table>

  <h3>Tenants</h3>
  <table border="1" cellpadding="5" width="100%"
         style="border-collapse: collapse; border-color: #DDDDDD;">
    <tr style="background-color: #4A4A4A; color: #FFFFFF;">
      <th>Name</th><th>Suite</th><th>SF</th>
      <th>Rate/SF</th><th>Lease Expiry</th><th>Type</th>
    </tr>
    {tenant_rows}
  </table>

  <h3>Year 1 Preview</h3>
  <table cellpadding="4">
    <tr><td><b>Rental Revenue:</b></td><td>${rev_y1:,.0f}</td></tr>
    <tr><td><b>NOI:</b></td><td>${noi_y1:,.0f}</td></tr>
    <tr><td><b>Building Value:</b></td><td>${val_y1:,.0f}</td></tr>
  </table>

  <h3>Cap Rate Sensitivity</h3>
  <table border="1" cellpadding="5"
         style="border-collapse: collapse; border-color: #DDDDDD;">
    <tr style="background-color: #4A4A4A; color: #FFFFFF;">
      <th>Scenario</th><th>Cap Rate</th><th>Value</th>
    </tr>
    <tr><td>Low (− {s.cap_delta:.2%})</td><td>{cap - delta:.2%}</td><td>${low_val:,.0f}</td></tr>
    <tr><td>Base</td><td>{cap:.2%}</td><td>${val_y1:,.0f}</td></tr>
    <tr><td>High (+ {s.cap_delta:.2%})</td><td>{cap + delta:.2%}</td><td>${high_val:,.0f}</td></tr>
  </table>

  {return_html}
  {notes_html}
</body>
</html>"""
```

- [ ] **Step 4: Update `app/excel/writer.py`**

Replace the file with:

```python
from openpyxl import Workbook
from openpyxl.styles import Font
from app.models.session import ProFormaSession
from app.excel.inputs_sheet import write_inputs_sheet
from app.excel.proforma_sheet import write_proforma_sheet


def write_workbook(
    session: ProFormaSession,
    output_path: str,
    irr_data: dict | None = None,
) -> None:
    wb = Workbook()
    write_inputs_sheet(wb.active, session, irr_data=irr_data)
    write_proforma_sheet(wb.create_sheet("ProForma"), session)
    _write_notes_sheet(wb.create_sheet("Notes"), session)
    wb.save(output_path)


def _write_notes_sheet(ws, session: ProFormaSession) -> None:
    ws.title = "Notes"
    header = ws.cell(row=1, column=1, value="Deal Notes & Assumptions")
    header.font = Font(bold=True, size=12)
    ws.column_dimensions["A"].width = 80
    if session.notes.strip():
        for i, line in enumerate(session.notes.split("\n"), start=2):
            ws.cell(row=i, column=1, value=line)
    else:
        ws.cell(row=2, column=1, value="No notes entered.")
```

- [ ] **Step 5: Run the notes tests**

```
pytest tests/test_notes.py -v
```

Expected: all PASS.

- [ ] **Step 6: Run the full suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```
git add app/excel/pdf_writer.py app/excel/writer.py tests/test_notes.py
git commit -m "feat: add notes section to PDF and Excel Notes sheet"
```

---

## Task 5: IRR/NPV — Calculator

**Files:**
- Modify: `app/logic/calculator.py`
- Create: `tests/test_irr_npv.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_irr_npv.py`:

```python
import pytest
from app.logic.calculator import _irr, _npv, calculate_irr_npv


def test_irr_simple_known_value():
    # Invest 1000, receive 100/yr for 9 years, receive 1100 in year 10 → IRR ≈ 10%
    cf = [-1000] + [100] * 9 + [1100]
    assert _irr(cf) == pytest.approx(0.10, abs=1e-4)


def test_npv_at_zero_discount_equals_sum():
    cf = [-1000, 400, 400, 400]
    assert _npv(cf, 0.0) == pytest.approx(200.0)


def test_npv_positive_at_low_discount(basic_session):
    from app.logic.calculator import calculate_proforma
    result = calculate_proforma(basic_session)
    basic_session.purchase_price = result["values"][0]
    basic_session.discount_rate = 0.01
    data = calculate_irr_npv(basic_session, result)
    assert data["npv"] > 0


def test_irr_returns_none_for_no_valid_irr():
    # All-positive cash flows → no valid IRR, algorithm diverges
    assert _irr([100, 100, 100]) is None


def test_calculate_irr_npv_uses_y1_value_when_purchase_zero(basic_session):
    from app.logic.calculator import calculate_proforma
    result = calculate_proforma(basic_session)
    basic_session.purchase_price = 0.0
    data = calculate_irr_npv(basic_session, result)
    assert data["effective_purchase"] == pytest.approx(result["values"][0])


def test_calculate_irr_npv_uses_explicit_purchase(basic_session):
    from app.logic.calculator import calculate_proforma
    result = calculate_proforma(basic_session)
    basic_session.purchase_price = 999_999.0
    data = calculate_irr_npv(basic_session, result)
    assert data["effective_purchase"] == pytest.approx(999_999.0)


def test_calculate_irr_npv_uses_session_cap_when_exit_zero(basic_session):
    from app.logic.calculator import calculate_proforma
    result = calculate_proforma(basic_session)
    basic_session.exit_cap_rate = 0.0
    data = calculate_irr_npv(basic_session, result)
    expected_exit = result["nois"][-1] / basic_session.cap_rate
    assert data["exit_value"] == pytest.approx(expected_exit)


def test_calculate_irr_npv_returns_all_keys(basic_session):
    from app.logic.calculator import calculate_proforma
    result = calculate_proforma(basic_session)
    data = calculate_irr_npv(basic_session, result)
    for key in ("irr", "npv", "exit_value", "effective_purchase", "effective_exit_cap"):
        assert key in data
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_irr_npv.py -v
```

Expected: FAIL — `_irr`, `_npv`, `calculate_irr_npv` not defined.

- [ ] **Step 3: Add IRR/NPV functions to `app/logic/calculator.py`**

Append the following to the end of `app/logic/calculator.py` (after `generate_assumptions`):

```python
def _irr(cash_flows: list[float]) -> float | None:
    rate = 0.1
    for _ in range(1000):
        try:
            npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cash_flows))
            dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cash_flows))
        except (ZeroDivisionError, OverflowError):
            return None
        if dnpv == 0:
            return None
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-7:
            return new_rate
        rate = new_rate
    return None


def _npv(cash_flows: list[float], discount_rate: float) -> float:
    return sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(cash_flows))


def calculate_irr_npv(session: ProFormaSession, result: dict) -> dict:
    effective_purchase = (
        session.purchase_price if session.purchase_price > 0 else result["values"][0]
    )
    effective_exit_cap = (
        session.exit_cap_rate if session.exit_cap_rate > 0 else session.cap_rate
    )
    exit_value = result["nois"][-1] / effective_exit_cap if effective_exit_cap > 0 else 0.0
    cash_flows = (
        [-effective_purchase]
        + list(result["nois"][:-1])
        + [result["nois"][-1] + exit_value]
    )
    irr = _irr(cash_flows)
    npv = _npv(cash_flows, session.discount_rate)
    return {
        "irr": irr,
        "npv": npv,
        "exit_value": exit_value,
        "effective_purchase": effective_purchase,
        "effective_exit_cap": effective_exit_cap,
    }
```

- [ ] **Step 4: Run the IRR tests**

```
pytest tests/test_irr_npv.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run the full suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add app/logic/calculator.py tests/test_irr_npv.py
git commit -m "feat: add IRR/NPV calculator functions"
```

---

## Task 6: IRR/NPV — Review Page UI

**Files:**
- Modify: `app/ui/wizard/page_review.py`

- [ ] **Step 1: Replace `app/ui/wizard/page_review.py` with the updated version**

```python
from __future__ import annotations
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QMessageBox, QCheckBox,
    QGroupBox, QDoubleSpinBox, QFormLayout,
)
from PySide6.QtCore import Qt
from app.models.session import ProFormaSession
from app.logic.calculator import calculate_proforma
from app.excel.writer import write_workbook
from app.db.database import init_db, save_run


class ReviewPage(QWidget):
    def __init__(self, session: ProFormaSession, on_generate):
        super().__init__()
        self.session = session
        self._on_generate = on_generate
        self._db = init_db()
        self._folder = str(Path.home() / "Desktop")
        self._last_pdf_path: str | None = None
        self._last_result: dict | None = None
        self._build_ui()

    def bind(self, session: ProFormaSession):
        self.session = session

    def refresh(self):
        s = self.session
        self._bldg_lbl.setText(
            f"<b>{s.building_name}</b><br>"
            f"Start: {s.start_month}/{s.start_year} | {s.years} years<br>"
            f"Total SF: {s.total_sqft:,.0f} | Occupied: {s.occupied_sqft:,.0f}<br>"
            f"OpEx/SF: ${s.opex_psf:.2f} | Cap Rate: {s.cap_rate*100:.2f}%"
        )
        self._ten_lbl.setText("".join(
            f"<b>{t.name}</b> - Suite {t.suite}, {t.sqft:,.0f} SF @ ${t.rate_psf:.2f}/SF<br>"
            for t in s.tenants) or "(no tenants)")
        self._last_result = None
        if s.tenants:
            try:
                res = calculate_proforma(s)
                self._last_result = res
                self._rev_lbl.setText(f"Rental Revenue Y1: <b>${res['rental_revenue'][0]:,.0f}</b>")
                self._noi_lbl.setText(f"NOI Y1: <b>${res['nois'][0]:,.0f}</b>")
                self._val_lbl.setText(f"Building Value Y1: <b>${res['values'][0]:,.0f}</b>")
                # Populate IRR inputs from session (0.0 = "Auto")
                self._purchase_spin.setValue(s.purchase_price)
                self._exit_cap_spin.setValue(s.exit_cap_rate * 100.0)
                self._discount_spin.setValue(s.discount_rate * 100.0)
                self._update_irr()
            except Exception as e:
                self._noi_lbl.setText(f"Preview error: {e}")
        safe = s.building_name.replace(" ", "_") or "ProForma"
        self._fname.setText(f"{safe}_Proforma.xlsx")
        self._last_pdf_path = None
        self._email_btn.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 0)
        title = QLabel("Review & Export")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        row = QHBoxLayout()
        for attr, lbl_text in [("_bldg_lbl", "Building"), ("_ten_lbl", "Tenants")]:
            card = QWidget()
            card.setObjectName("card")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(16, 16, 16, 16)
            cv.addWidget(QLabel(f"<b>{lbl_text}</b>"))
            lbl = QLabel()
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            setattr(self, attr, lbl)
            cv.addWidget(lbl)
            cv.addStretch()
            row.addWidget(card, 1)
        layout.addLayout(row)

        metrics = QHBoxLayout()
        self._rev_lbl = QLabel("--")
        self._noi_lbl = QLabel("--")
        self._val_lbl = QLabel("--")
        for lbl in (self._rev_lbl, self._noi_lbl, self._val_lbl):
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("font-size:14px; padding:8px;")
            metrics.addWidget(lbl)
        layout.addLayout(metrics)

        # IRR / NPV group
        irr_group = QGroupBox("Return Analysis (optional)")
        irr_form = QFormLayout(irr_group)
        irr_form.setContentsMargins(12, 8, 12, 12)

        self._purchase_spin = QDoubleSpinBox()
        self._purchase_spin.setRange(0, 999_999_999)
        self._purchase_spin.setDecimals(0)
        self._purchase_spin.setSingleStep(10_000)
        self._purchase_spin.setPrefix("$")
        self._purchase_spin.setSpecialValueText("Auto (Year 1 Value)")
        irr_form.addRow("Purchase Price:", self._purchase_spin)

        self._exit_cap_spin = QDoubleSpinBox()
        self._exit_cap_spin.setRange(0, 50)
        self._exit_cap_spin.setDecimals(2)
        self._exit_cap_spin.setSuffix(" %")
        self._exit_cap_spin.setSpecialValueText("Auto (Session Cap Rate)")
        irr_form.addRow("Exit Cap Rate:", self._exit_cap_spin)

        self._discount_spin = QDoubleSpinBox()
        self._discount_spin.setRange(0.1, 50)
        self._discount_spin.setDecimals(1)
        self._discount_spin.setSuffix(" %")
        self._discount_spin.setValue(8.0)
        irr_form.addRow("Discount Rate:", self._discount_spin)

        self._irr_lbl = QLabel("IRR: —")
        self._irr_lbl.setStyleSheet("font-size: 13px; padding: 2px 0;")
        self._npv_lbl = QLabel("NPV: —")
        self._npv_lbl.setStyleSheet("font-size: 13px; padding: 2px 0;")
        irr_form.addRow(self._irr_lbl)
        irr_form.addRow(self._npv_lbl)

        self._purchase_spin.valueChanged.connect(self._update_irr)
        self._exit_cap_spin.valueChanged.connect(self._update_irr)
        self._discount_spin.valueChanged.connect(self._update_irr)
        layout.addWidget(irr_group)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Filename:"))
        self._fname = QLineEdit()
        path_row.addWidget(self._fname, 1)
        browse = QPushButton("Choose Folder...")
        browse.setObjectName("secondaryBtn")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        layout.addLayout(path_row)

        self._folder_lbl = QLabel(f"Saving to: {self._folder}")
        self._folder_lbl.setStyleSheet("color:#666666; font-size:12px;")
        layout.addWidget(self._folder_lbl)

        self._pdf_check = QCheckBox("Also export PDF summary")
        self._pdf_check.setChecked(True)
        layout.addWidget(self._pdf_check)

        self._email_btn = QPushButton("Email Pro Forma")
        self._email_btn.setObjectName("secondaryBtn")
        self._email_btn.setEnabled(False)
        self._email_btn.clicked.connect(self._email_proforma)
        layout.addWidget(self._email_btn)

        layout.addStretch()

    def _update_irr(self):
        if self._last_result is None:
            return
        self.session.purchase_price = self._purchase_spin.value()
        self.session.exit_cap_rate = self._exit_cap_spin.value() / 100.0
        self.session.discount_rate = self._discount_spin.value() / 100.0
        try:
            from app.logic.calculator import calculate_irr_npv
            data = calculate_irr_npv(self.session, self._last_result)
            irr_str = f"{data['irr']:.2%}" if data["irr"] is not None else "N/A"
            self._irr_lbl.setText(f"IRR: <b>{irr_str}</b>")
            self._npv_lbl.setText(f"NPV: <b>${data['npv']:,.0f}</b>")
        except Exception:
            self._irr_lbl.setText("IRR: —")
            self._npv_lbl.setText("NPV: —")

    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Select Output Folder", self._folder)
        if f:
            self._folder = f
            self._folder_lbl.setText(f"Saving to: {f}")

    def _email_proforma(self):
        from app.ui.email_dialog import EmailDialog
        dlg = EmailDialog(self, self.session, self._last_pdf_path)
        dlg.exec()

    def validate(self) -> bool:
        return True

    def commit(self):
        s = self.session
        s.purchase_price = self._purchase_spin.value()
        s.exit_cap_rate = self._exit_cap_spin.value() / 100.0
        s.discount_rate = self._discount_spin.value() / 100.0

        fname = self._fname.text().strip() or "ProForma.xlsx"
        if not fname.endswith(".xlsx"):
            fname += ".xlsx"
        path = os.path.join(self._folder, fname)
        try:
            res = calculate_proforma(s)
            irr_data = None
            try:
                from app.logic.calculator import calculate_irr_npv
                irr_data = calculate_irr_npv(s, res)
            except Exception:
                pass
            write_workbook(s, path, irr_data=irr_data)
            save_run(s, path, res["nois"][0], res["values"][0], conn=self._db)
            if self._pdf_check.isChecked():
                from app.excel.pdf_writer import export_pdf
                pdf_path = path[:-5] + ".pdf"
                try:
                    export_pdf(s, res, pdf_path, irr_data=irr_data)
                    self._last_pdf_path = pdf_path
                    self._email_btn.setEnabled(True)
                except Exception as e_pdf:
                    QMessageBox.warning(
                        self, "PDF Export",
                        f"PDF export failed: {e_pdf}\nExcel was saved successfully.",
                    )
            os.startfile(path)
            self._on_generate()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
```

- [ ] **Step 2: Run the full test suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 3: Commit**

```
git add app/ui/wizard/page_review.py
git commit -m "feat: add IRR/NPV group box and Email button to Review page"
```

---

## Task 7: IRR/NPV — Inputs Sheet Output

**Files:**
- Modify: `app/excel/inputs_sheet.py`

- [ ] **Step 1: Add IRR output test to `tests/test_irr_npv.py`**

Append to `tests/test_irr_npv.py`:

```python
def test_inputs_sheet_contains_return_analysis(basic_session, tmp_path):
    from openpyxl import load_workbook
    from app.logic.calculator import calculate_proforma, calculate_irr_npv
    from app.excel.writer import write_workbook
    result = calculate_proforma(basic_session)
    irr_data = calculate_irr_npv(basic_session, result)
    path = str(tmp_path / "test.xlsx")
    write_workbook(basic_session, path, irr_data=irr_data)
    wb = load_workbook(path)
    ws = wb["Inputs"]
    all_values = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert any("Return Analysis" in str(v) for v in all_values if v)


def test_inputs_sheet_no_return_analysis_when_no_irr_data(basic_session, tmp_path):
    from openpyxl import load_workbook
    from app.excel.writer import write_workbook
    path = str(tmp_path / "test.xlsx")
    write_workbook(basic_session, path, irr_data=None)
    wb = load_workbook(path)
    ws = wb["Inputs"]
    all_values = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert not any("Return Analysis" in str(v) for v in all_values if v)
```

- [ ] **Step 2: Run to confirm failure**

```
pytest tests/test_irr_npv.py::test_inputs_sheet_contains_return_analysis -v
```

Expected: FAIL — `write_inputs_sheet` doesn't write a Return Analysis block.

- [ ] **Step 3: Update `app/excel/inputs_sheet.py` to accept and write IRR data**

At the end of `write_inputs_sheet`, add an `irr_data` parameter and write the block below the tenant data:

Change the function signature from:
```python
def write_inputs_sheet(ws, session: ProFormaSession) -> None:
```

To:
```python
def write_inputs_sheet(ws, session: ProFormaSession, irr_data: dict | None = None) -> None:
```

Then append the following block at the very end of the function (after the column auto-sizing loop):

```python
    if irr_data is not None:
        irr_str = f"{irr_data['irr']:.2%}" if irr_data.get("irr") is not None else "N/A"
        start_row = TENANT_DATA_START_ROW + max(len(session.tenants), 1) + 2
        hdr = ws.cell(row=start_row, column=1, value="Return Analysis")
        hdr.font = _BOLD
        hdr.fill = _HDR_FILL
        ws.cell(row=start_row, column=2, value="")
        rows_data = [
            ("Purchase Price", f"${irr_data['effective_purchase']:,.0f}"),
            ("Exit Cap Rate", f"{irr_data['effective_exit_cap']:.2%}"),
            ("Exit Value", f"${irr_data['exit_value']:,.0f}"),
            ("IRR", irr_str),
            (f"NPV ({session.discount_rate:.1%} discount)", f"${irr_data['npv']:,.0f}"),
        ]
        for i, (label, value) in enumerate(rows_data, start=start_row + 1):
            lbl_cell = ws.cell(row=i, column=1, value=label)
            lbl_cell.font = _BOLD
            lbl_cell.fill = _LABEL_FILL
            ws.cell(row=i, column=2, value=value)
```

- [ ] **Step 4: Run IRR tests**

```
pytest tests/test_irr_npv.py -v
```

Expected: all PASS.

- [ ] **Step 5: Run full suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```
git add app/excel/inputs_sheet.py tests/test_irr_npv.py
git commit -m "feat: add Return Analysis block to Inputs sheet when IRR data available"
```

---

## Task 8: Email — Dialog + Integration

**Files:**
- Create: `app/ui/email_dialog.py`
- Modify: `NAI_ProForma_Generator.spec`
- Create: `tests/test_email.py`

- [ ] **Step 1: Install pywin32**

```
.venv\Scripts\pip install pywin32
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_email.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


def test_email_dialog_constructs(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Email Pro Forma"


def test_outlook_sends_correct_subject(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    mock_mail = MagicMock()
    mock_outlook = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail
    with patch("win32com.client.Dispatch", return_value=mock_outlook):
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_mail.Display.assert_called_once()
    assert "Test Tower" in mock_mail.Subject


def test_outlook_attaches_pdf(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    mock_mail = MagicMock()
    mock_outlook = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail
    with patch("win32com.client.Dispatch", return_value=mock_outlook):
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_mail.Attachments.Add.assert_called_once_with("C:/fake/path.pdf")


def test_gmail_opens_browser_and_copies_clipboard(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    with patch("webbrowser.open") as mock_browser, \
         patch("PySide6.QtGui.QGuiApplication.clipboard") as mock_clipboard, \
         patch("PySide6.QtWidgets.QMessageBox.information"):
        mock_cb = MagicMock()
        mock_clipboard.return_value = mock_cb
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_gmail()
    mock_browser.assert_called_once()
    url = mock_browser.call_args[0][0]
    assert "mail.google.com" in url
    assert "Test+Tower" in url or "Test Tower" in url or "Test%20Tower" in url
    mock_cb.setText.assert_called_once_with("C:/fake/path.pdf")


def test_outlook_error_shows_warning(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    with patch("win32com.client.Dispatch", side_effect=Exception("COM error")), \
         patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_warn.assert_called_once()
```

- [ ] **Step 3: Run to confirm failure**

```
pytest tests/test_email.py -v
```

Expected: FAIL — `EmailDialog` not defined.

Note: these tests require `pytest-qt`. Install if missing:

```
.venv\Scripts\pip install pytest-qt
```

- [ ] **Step 4: Create `app/ui/email_dialog.py`**

```python
from __future__ import annotations
import urllib.parse
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
)
from app.models.session import ProFormaSession


class EmailDialog(QDialog):
    def __init__(self, parent, session: ProFormaSession, pdf_path: str):
        super().__init__(parent)
        self._session = session
        self._pdf_path = pdf_path
        self.setWindowTitle("Email Pro Forma")
        self.setFixedWidth(320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl = QLabel("Send this pro forma via:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        outlook_btn = QPushButton("Open in Outlook")
        outlook_btn.setObjectName("primaryBtn")
        outlook_btn.clicked.connect(self._send_outlook)
        gmail_btn = QPushButton("Open in Gmail")
        gmail_btn.setObjectName("secondaryBtn")
        gmail_btn.clicked.connect(self._send_gmail)
        btn_row.addWidget(outlook_btn)
        btn_row.addWidget(gmail_btn)
        layout.addLayout(btn_row)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _send_outlook(self):
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.Subject = f"Pro Forma — {self._session.building_name}"
            mail.Attachments.Add(self._pdf_path)
            mail.Display()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Outlook Error", f"Could not open Outlook: {e}")

    def _send_gmail(self):
        from PySide6.QtGui import QGuiApplication
        subject = urllib.parse.quote(f"Pro Forma — {self._session.building_name}")
        webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&su={subject}")
        QGuiApplication.clipboard().setText(self._pdf_path)
        QMessageBox.information(
            self,
            "Gmail Opened",
            "Gmail opened in your browser.\n\n"
            "Your PDF path has been copied to the clipboard — "
            "click the paperclip icon in Gmail to attach it.",
        )
        self.accept()
```

- [ ] **Step 5: Run the email tests**

```
pytest tests/test_email.py -v
```

Expected: all PASS.

- [ ] **Step 6: Update `NAI_ProForma_Generator.spec` to add pywin32 hidden imports**

Change the `hiddenimports` line from:

```python
hiddenimports=['openpyxl', 'dateutil', 'dateutil.relativedelta'],
```

To:

```python
hiddenimports=[
    'openpyxl', 'dateutil', 'dateutil.relativedelta',
    'win32com', 'win32com.client', 'pywintypes',
],
```

- [ ] **Step 7: Run the full test suite**

```
pytest -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```
git add app/ui/email_dialog.py NAI_ProForma_Generator.spec tests/test_email.py
git commit -m "feat: add Email Pro Forma dialog with Outlook and Gmail support"
```

---

## Final Step: Rebuild the Executable

- [ ] **Rebuild with PyInstaller**

```
.venv\Scripts\pyinstaller.exe NAI_ProForma_Generator.spec --noconfirm
```

Expected: `Building EXE from EXE-00.toc completed successfully`

- [ ] **Copy to Desktop**

```
Copy-Item "dist\NAI_ProForma_Generator.exe" "$env:USERPROFILE\Desktop\NAI_ProForma_Generator.exe" -Force
```

- [ ] **Commit**

```
git add -A
git commit -m "chore: rebuild exe with all four feature additions"
```
