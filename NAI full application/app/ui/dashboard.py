from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QInputDialog, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from app.db.database import (
    init_db, list_runs, delete_run, get_run,
    list_templates, get_template, delete_template, save_template,
)
from app.models.session import ProFormaSession

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "nai_logo.svg"


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
        bl.setSpacing(12)

        # ── Hero card ────────────────────────────────────────────────────────
        hero = QWidget()
        hero.setObjectName("card")
        hero.setFixedHeight(86)
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(20)

        if _LOGO_PATH.exists():
            logo_w = QSvgWidget(str(_LOGO_PATH))
            logo_w.setFixedSize(170, 37)
            logo_w.setStyleSheet("background: transparent;")
            hl.addWidget(logo_w)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("background: #E5E5EA; max-width: 1px;")
        div.setFixedWidth(1)
        hl.addWidget(div)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(3)
        title_lbl = QLabel("NAI Pro Forma Generator")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #1C1C1E;")
        sub_lbl = QLabel("Commercial real estate pro forma analysis & rent roll projection")
        sub_lbl.setStyleSheet("font-size: 12px; color: #8E8E93;")
        txt_col.addWidget(title_lbl)
        txt_col.addWidget(sub_lbl)
        hl.addLayout(txt_col, 1)

        # Stat pills on the right
        self._pill_runs = self._make_pill("0", "Pro Formas")
        self._pill_tmpl = self._make_pill("0", "Templates")
        hl.addWidget(self._pill_runs)
        hl.addWidget(self._pill_tmpl)

        bl.addWidget(hero)

        self._count_lbl = QLabel()
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

    @staticmethod
    def _make_pill(count: str, label: str) -> QWidget:
        pill = QWidget()
        pill.setStyleSheet(
            "background: #F2F2F7; border-radius: 10px; padding: 0px;"
        )
        pill.setFixedSize(90, 56)
        vl = QVBoxLayout(pill)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(1)
        n = QLabel(count)
        n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        n.setStyleSheet("font-size: 20px; font-weight: 700; color: #C8102E;")
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 10px; color: #8E8E93; font-weight: 500;")
        vl.addWidget(n)
        vl.addWidget(lbl)
        pill._num_lbl = n
        return pill

    def refresh(self):
        self._refresh_runs()
        self._refresh_templates()

    def _refresh_runs(self):
        self.table.setSortingEnabled(False)
        runs = list_runs(conn=self._db)
        self.table.setRowCount(0)
        count = len(runs)
        self._pill_runs._num_lbl.setText(str(count))
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
        self._pill_tmpl._num_lbl.setText(str(len(templates)))
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
