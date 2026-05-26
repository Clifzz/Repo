# UI Modernisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dated dark-sidebar aesthetic with an Apple-inspired look: white top bar, system grays, 12 px card radii, ghost back button, dot progress indicator, and an Apple system-gray input style.

**Architecture:** All changes are confined to the stylesheet (`styles.qss`), two structural files (`main_window.py`, `dashboard.py`), the wizard container (`wizard.py`), and minor margin/title tweaks on each wizard page. No data model, database, or logic changes. Existing 70-test suite must stay green after every task.

**Tech Stack:** PySide6 QSS, PySide6.QtSvgWidgets, PySide6.QtGui (QPainter for dot indicator)

---

## File Map

**Overwrite:**
- `app/ui/styles.qss` — complete new Apple-palette stylesheet

**Modify:**
- `app/ui/main_window.py` — remove sidebar, add 56 px top bar, change root layout to QVBoxLayout
- `app/ui/dashboard.py` — remove header + stats bar widgets, inline count label above tabs
- `app/ui/wizard/wizard.py` — add `_DotIndicator`, replace step label, ghost back button, #navBar widget
- `app/ui/wizard/page_building.py` — margins 32/28, form spacing 16, title size 22 px
- `app/ui/wizard/page_tenants.py` — margins 32/28, title size 22 px
- `app/ui/wizard/page_notes.py` — margins 32/28, title size 22 px, objectName on QPlainTextEdit
- `app/ui/wizard/page_review.py` — margins 32/28, title size 22 px, card padding 20 px

---

## Task 1: Rewrite `styles.qss`

**Files:**
- Overwrite: `app/ui/styles.qss`

No automated tests for stylesheet changes. After writing the file, run the full test suite to confirm nothing broke, then launch the app to verify visually.

- [ ] **Step 1: Overwrite `app/ui/styles.qss` with the complete new stylesheet**

```qss
/* ── Base ──────────────────────────────────────────────────────────────── */
QWidget {
    background-color: #F2F2F7;
    color: #1C1C1E;
    font-family: "SF Pro Display", "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
}

/* ── Top bar ───────────────────────────────────────────────────────────── */
#topBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E5E5EA;
}
#topBarTitle {
    color: #8E8E93;
    font-size: 14px;
}

/* ── Stats label (dashboard) ─────────────────────────────────────────── */
#statsLabel {
    color: #8E8E93;
    font-size: 12px;
    padding: 0 0 4px 0;
}

/* ── Cards ─────────────────────────────────────────────────────────────── */
#card {
    background-color: #FFFFFF;
    border-radius: 12px;
    border: 1px solid #E5E5EA;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
QPushButton#primaryBtn {
    background-color: #C8102E;
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover    { background-color: #A00C24; }
QPushButton#primaryBtn:disabled { background-color: #AEAEB2; }

QPushButton#secondaryBtn {
    background-color: #F2F2F7;
    color: #1C1C1E;
    border: none;
    border-radius: 10px;
    padding: 10px 24px;
    font-weight: 600;
}
QPushButton#secondaryBtn:hover { background-color: #E5E5EA; }

QPushButton#ghostBtn {
    background: transparent;
    color: #8E8E93;
    border: none;
    padding: 10px 16px;
    font-size: 14px;
}
QPushButton#ghostBtn:hover { color: #1C1C1E; }

QPushButton#dangerBtn {
    background-color: #FFF1F2;
    color: #C8102E;
    border: 1px solid #C8102E;
    border-radius: 10px;
    padding: 8px 16px;
}
QPushButton#dangerBtn:hover {
    background-color: #C8102E;
    color: #FFFFFF;
}

QPushButton#tableBtn {
    background-color: #F2F2F7;
    color: #1C1C1E;
    border: none;
    border-radius: 6px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 500;
}
QPushButton#tableBtn:hover { background-color: #E5E5EA; }

/* ── Form inputs ─────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit {
    background-color: #F2F2F7;
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    color: #1C1C1E;
    selection-background-color: #FFF1F2;
    selection-color: #1C1C1E;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus,
QSpinBox:focus, QDateEdit:focus {
    border: 2px solid #C8102E;
}
QLineEdit[invalid="true"] {
    background-color: #FFF1F2;
    border: 2px solid #C8102E;
}

/* Notes editor */
QPlainTextEdit#notesEdit {
    background-color: #F2F2F7;
    border: none;
    border-radius: 10px;
    padding: 12px;
    color: #1C1C1E;
}
QPlainTextEdit#notesEdit:focus { border: 2px solid #C8102E; }

/* ── Tables ──────────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 12px;
    gridline-color: #F0F0F0;
    alternate-background-color: #F9F9F9;
}
QTableWidget::item          { padding: 8px 4px; color: #1C1C1E; }
QTableWidget::item:selected { background-color: #FFF1F2; color: #1C1C1E; }
QHeaderView::section {
    background-color: #F9F9F9;
    color: #8E8E93;
    font-size: 11px;
    font-weight: 600;
    padding: 8px 6px;
    border: none;
    border-bottom: 1px solid #E5E5EA;
}

/* ── Tab widget (segmented-control style) ───────────────────────────── */
QTabWidget::pane  { border: none; background: transparent; margin-top: 8px; }
QTabBar           { background: #F2F2F7; border-radius: 10px; }
QTabBar::tab {
    background: transparent;
    color: #8E8E93;
    border-radius: 8px;
    padding: 6px 20px;
    min-width: 110px;
    font-size: 14px;
    font-weight: 500;
    margin: 3px 2px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #1C1C1E;
    font-weight: 600;
    border: 1px solid #E5E5EA;
}
QTabBar::tab:hover:!selected { color: #1C1C1E; }

/* ── Group box ───────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 600;
    color: #8E8E93;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
    top: -1px;
}

/* ── Wizard nav bar ──────────────────────────────────────────────────── */
#navBar { background-color: #FFFFFF; border-top: 1px solid #E5E5EA; }

/* ── Spinbox up/down buttons ─────────────────────────────────────────── */
QSpinBox::up-button, QDoubleSpinBox::up-button, QDateEdit::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border: none;
    border-left: 1px solid #E5E5EA;
    border-top-right-radius: 9px;
    background-color: #F2F2F7;
}
QSpinBox::down-button, QDoubleSpinBox::down-button, QDateEdit::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border: none;
    border-left: 1px solid #E5E5EA;
    border-top: 1px solid #E5E5EA;
    border-bottom-right-radius: 9px;
    background-color: #F2F2F7;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QDateEdit::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QDateEdit::down-button:hover {
    background-color: #E5E5EA;
}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed, QDateEdit::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed, QDateEdit::down-button:pressed {
    background-color: #D1D1D6;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QDateEdit::up-arrow   { width: 8px; height: 5px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QDateEdit::down-arrow { width: 8px; height: 5px; }

/* ── Scroll bars ─────────────────────────────────────────────────────── */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #C7C7CC;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical  { height: 0; border: none; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical  { background: none; }
```

- [ ] **Step 2: Run the test suite**

```
cd C:\Users\evasi\nai_proforma
.venv\Scripts\pytest -v 2>&1 | tail -5
```

Expected: `70 passed`.

- [ ] **Step 3: Commit**

```
git add app/ui/styles.qss
git commit -m "style: rewrite stylesheet with Apple-inspired palette and components"
```

---

## Task 2: Replace sidebar with top bar (`main_window.py`)

**Files:**
- Modify: `app/ui/main_window.py`

- [ ] **Step 1: Overwrite `app/ui/main_window.py` with the new version**

```python
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from app.models.session import ProFormaSession

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "nai_logo.svg"


def _load_styles() -> str:
    p = Path(__file__).parent / "styles.qss"
    return p.read_text(encoding="utf-8") if p.exists() else ""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NAI Pro Forma Generator")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(_load_styles())
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._make_top_bar())
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        from app.ui.dashboard import DashboardView
        from app.ui.wizard.wizard import WizardView
        self.dashboard = DashboardView(
            on_new=self.show_wizard,
            on_edit=lambda session: self.show_wizard(session=session),
        )
        self.wizard = WizardView(on_complete=self.show_dashboard, on_cancel=self.show_dashboard)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.wizard)
        self.show_dashboard()
        self._check_for_draft()

    def _make_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(12)
        if _LOGO_PATH.exists():
            logo = QSvgWidget(str(_LOGO_PATH))
            logo.setFixedSize(140, 30)
            logo.setStyleSheet("background: transparent;")
            hl.addWidget(logo)
        title = QLabel("Pro Forma Generator")
        title.setObjectName("topBarTitle")
        hl.addWidget(title)
        hl.addStretch()
        self._new_btn = QPushButton("+ New Pro Forma")
        self._new_btn.setObjectName("primaryBtn")
        self._new_btn.clicked.connect(self.show_wizard)
        hl.addWidget(self._new_btn)
        return bar

    def _check_for_draft(self):
        from app.db.draft import load_draft, clear_draft
        draft = load_draft()
        if not draft:
            return
        bname = draft.building_name or "Unnamed"
        reply = QMessageBox.question(
            self,
            "Restore Draft",
            f'An unsaved pro forma for "{bname}" was found. Restore it?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.wizard.load_session(draft)
            self.show_wizard()
        else:
            clear_draft()

    def show_dashboard(self):
        self.dashboard.refresh()
        self.stack.setCurrentIndex(0)
        self._new_btn.setVisible(True)

    def show_wizard(self, session: ProFormaSession | None = None):
        if not isinstance(session, ProFormaSession):
            session = None
        if session is None and self.stack.currentIndex() == 1:
            return
        if session is not None:
            self.wizard.load_session(session)
        else:
            self.wizard.reset()
        self.stack.setCurrentIndex(1)
        self._new_btn.setVisible(False)
```

- [ ] **Step 2: Run the test suite**

```
.venv\Scripts\pytest -v 2>&1 | tail -5
```

Expected: `70 passed`.

- [ ] **Step 3: Commit**

```
git add app/ui/main_window.py
git commit -m "style: replace dark sidebar with white top bar, QVBoxLayout root"
```

---

## Task 3: Strip dashboard header and stats bar (`dashboard.py`)

**Files:**
- Modify: `app/ui/dashboard.py`

The dashboard currently has three sections stacked vertically: (1) a white header bar containing the logo, a vertical divider, the title "Pro Forma Dashboard", and the "+ New Pro Forma" button; (2) a gray stats bar containing the pro-forma count label; (3) the body with the tab widget. The top bar in `main_window.py` now owns the logo and the "+ New Pro Forma" button, so sections (1) and (2) must be removed. The count label moves inline above the tab widget.

- [ ] **Step 1: Overwrite `app/ui/dashboard.py` with the updated version**

```python
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QInputDialog,
)
from PySide6.QtCore import Qt
from app.db.database import (
    init_db, list_runs, delete_run, get_run,
    list_templates, get_template, delete_template, save_template,
)
from app.models.session import ProFormaSession


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

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 24)
        bl.setSpacing(8)

        self._count_lbl = QLabel("0 pro formas saved")
        self._count_lbl.setObjectName("statsLabel")
        bl.addWidget(self._count_lbl)

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

        self._empty = QLabel("No pro formas yet — click + New Pro Forma to get started")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #AEAEB2; font-size: 14px; padding: 60px;")
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
        self._tmpl_empty.setStyleSheet("color: #AEAEB2; font-size: 14px; padding: 60px;")
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
            try:
                dt = datetime.fromisoformat(run["created_at"]).strftime("%b %d, %Y  %I:%M %p")
            except (ValueError, TypeError):
                dt = run["created_at"]
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
            try:
                dt = datetime.fromisoformat(tmpl["created_at"]).strftime("%b %d, %Y")
            except (ValueError, TypeError):
                dt = tmpl["created_at"]
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
        try:
            path = row["excel_path"]
            if not os.path.exists(path):
                from app.excel.writer import write_workbook
                write_workbook(ProFormaSession.from_json(row["inputs_json"]), path)
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Open Error", f"Could not open file: {e}")

    def _edit(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        try:
            self._on_edit(ProFormaSession.from_json(row["inputs_json"]))
        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Could not load run: {e}")

    def _clone(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        try:
            session = ProFormaSession.from_json(row["inputs_json"])
            session.building_name = f"{session.building_name} (Copy)" if session.building_name else "Copy"
            self._on_edit(session)
        except Exception as e:
            QMessageBox.warning(self, "Clone Error", f"Could not clone run: {e}")

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

- [ ] **Step 2: Run the test suite**

```
.venv\Scripts\pytest -v 2>&1 | tail -5
```

Expected: `70 passed`.

- [ ] **Step 3: Commit**

```
git add app/ui/dashboard.py
git commit -m "style: remove dashboard header and stats bar, inline count label above tabs"
```

---

## Task 4: Dot progress indicator + ghost back button (`wizard.py`)

**Files:**
- Modify: `app/ui/wizard/wizard.py`

Replace the `QLabel` step indicator ("Step 1 of 4") with a `_DotIndicator` custom widget that paints 4 dots. Replace the `QFrame` separator with a `#navBar` QWidget styled via QSS. Change the Back button's `objectName` from `"secondaryBtn"` to `"ghostBtn"`.

- [ ] **Step 1: Overwrite `app/ui/wizard/wizard.py` with the new version**

```python
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QBrush
from app.models.session import ProFormaSession


class _DotIndicator(QWidget):
    def __init__(self, count: int = 4):
        super().__init__()
        self._count = count
        self._active = 0
        self.setFixedSize(count * 18, 18)

    def set_step(self, idx: int):
        self._active = idx
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(self._count):
            color = QColor("#C8102E") if i == self._active else QColor("#E5E5EA")
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(i * 18 + 4, 4, 10, 10)
        p.end()


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

        nav_bar = QWidget()
        nav_bar.setObjectName("navBar")
        nav = QHBoxLayout(nav_bar)
        nav.setContentsMargins(24, 12, 24, 12)
        self._dots = _DotIndicator(4)
        self._back_btn = QPushButton()
        self._back_btn.setObjectName("ghostBtn")
        self._next_btn = QPushButton()
        self._next_btn.setObjectName("primaryBtn")
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._dots)
        nav.addStretch()
        nav.addWidget(self._back_btn)
        nav.addWidget(self._next_btn)
        layout.addWidget(nav_bar)
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
        self._dots.set_step(idx)
        self._back_btn.setText("Cancel" if idx == 0 else "Back")
        self._next_btn.setText("Generate Pro Forma" if idx == 3 else "Next")
```

- [ ] **Step 2: Run the test suite**

```
.venv\Scripts\pytest -v 2>&1 | tail -5
```

Expected: `70 passed`.

- [ ] **Step 3: Commit**

```
git add app/ui/wizard/wizard.py
git commit -m "style: dot progress indicator, ghost back button, #navBar widget in wizard"
```

---

## Task 5: Wizard page tweaks (margins, titles, notes input)

**Files:**
- Modify: `app/ui/wizard/page_building.py`
- Modify: `app/ui/wizard/page_tenants.py`
- Modify: `app/ui/wizard/page_notes.py`
- Modify: `app/ui/wizard/page_review.py`

All changes are one-liners — no structural changes, just margin/spacing/size values and one `setObjectName` call.

- [ ] **Step 1: Update `app/ui/wizard/page_building.py`**

Make these three changes:

**Line with `outer.setContentsMargins`** — change from `(24, 24, 24, 0)` to `(32, 28, 32, 0)`:
```python
        outer = QVBoxLayout(self); outer.setContentsMargins(32, 28, 32, 0)
```

**Title inline style** — change font-size from `18px` to `22px`:
```python
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
```

**Form spacing** — change from `14` to `16`:
```python
        form = QFormLayout(card); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(16)
```

- [ ] **Step 2: Update `app/ui/wizard/page_tenants.py`**

**Line with `layout.setContentsMargins`** — change from `(24, 24, 24, 0)` to `(32, 28, 32, 0)`:
```python
        layout = QVBoxLayout(self); layout.setContentsMargins(32, 28, 32, 0)
```

**Title inline style** — change font-size from `18px` to `22px`:
```python
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
```

- [ ] **Step 3: Update `app/ui/wizard/page_notes.py`**

**Line with `layout.setContentsMargins`** — change from `(24, 24, 24, 0)` to `(32, 28, 32, 0)`:
```python
        layout.setContentsMargins(32, 28, 32, 0)
```

**Title inline style** — change font-size from `18px` to `22px`:
```python
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
```

**Subtitle style** — update colors to match new palette:
```python
        sub.setStyleSheet("color: #8E8E93; font-size: 13px; margin-bottom: 8px;")
```

**After constructing `self._edit = QPlainTextEdit()`**, add:
```python
        self._edit.setObjectName("notesEdit")
```

So the notes section reads:
```python
        self._edit = QPlainTextEdit()
        self._edit.setObjectName("notesEdit")
        self._edit.setPlaceholderText(
            "Enter deal assumptions, market commentary, or any relevant notes..."
        )
```

- [ ] **Step 4: Update `app/ui/wizard/page_review.py`**

**`_build_ui` margins** — change from `(24, 24, 24, 0)` to `(32, 28, 32, 0)`:
```python
        layout.setContentsMargins(32, 28, 32, 0)
```

**Title inline style** — change font-size from `18px` to `22px`:
```python
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
```

**Card content margins** — the two info cards (Building / Tenants) use `cv.setContentsMargins(16, 16, 16, 16)`. Change to `(20, 20, 20, 20)`. This line appears inside the `for attr, lbl_text in [...]` loop:
```python
            cv.setContentsMargins(20, 20, 20, 20)
```

- [ ] **Step 5: Run the full test suite**

```
.venv\Scripts\pytest -v 2>&1 | tail -5
```

Expected: `70 passed`.

- [ ] **Step 6: Commit**

```
git add app/ui/wizard/page_building.py app/ui/wizard/page_tenants.py \
        app/ui/wizard/page_notes.py app/ui/wizard/page_review.py
git commit -m "style: wider margins, 22px titles, notesEdit objectName on wizard pages"
```

---

## Task 6: Rebuild the executable

- [ ] **Step 1: Rebuild with PyInstaller**

```
.venv\Scripts\pyinstaller.exe NAI_ProForma_Generator.spec --noconfirm 2>&1 | tail -5
```

Expected: `Building EXE from EXE-00.toc completed successfully.`

- [ ] **Step 2: Copy to Desktop**

```powershell
Copy-Item "dist\NAI_ProForma_Generator.exe" "$env:USERPROFILE\Desktop\NAI_ProForma_Generator.exe" -Force
```

- [ ] **Step 3: Commit**

```
git add -A
git commit -m "chore: rebuild exe with Apple-inspired UI modernisation"
```
