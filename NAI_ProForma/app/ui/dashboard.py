from __future__ import annotations
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt
from app.db.database import init_db, list_runs, delete_run, get_run
from app.models.session import ProFormaSession


class DashboardView(QWidget):
    def __init__(self, on_new):
        super().__init__()
        self._on_new = on_new; self._db = init_db(); self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24); layout.setSpacing(16)
        hdr = QHBoxLayout()
        title = QLabel("Pro Forma Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        hdr.addWidget(title); hdr.addStretch()
        new_btn = QPushButton("+ New Pro Forma"); new_btn.setObjectName("primaryBtn")
        new_btn.clicked.connect(self._on_new); hdr.addWidget(new_btn)
        layout.addLayout(hdr)

        self.table = QTableWidget(0, 5); self.table.setObjectName("card")
        self.table.setHorizontalHeaderLabels(["Building Name","Date Created","NOI (Y1)","Value (Y1)","Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(4, 160)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self._empty = QLabel("No pro formas yet — click New Pro Forma to get started")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888888; font-size: 14px;")
        layout.addWidget(self._empty)

    def refresh(self):
        runs = list_runs(conn=self._db)
        self.table.setRowCount(0)
        self._empty.setVisible(not runs); self.table.setVisible(bool(runs))
        for run in runs:
            r = self.table.rowCount(); self.table.insertRow(r)
            dt = datetime.fromisoformat(run["created_at"]).strftime("%Y-%m-%d %H:%M")
            for c, v in enumerate([run["building_name"], dt,
                f"${run['noi_y1']:,.0f}" if run["noi_y1"] else "-",
                f"${run['value_y1']:,.0f}" if run["value_y1"] else "-"]):
                self.table.setItem(r, c, QTableWidgetItem(v))
            acts = QWidget(); al = QHBoxLayout(acts); al.setContentsMargins(4, 2, 4, 2)
            ob = QPushButton("Open"); ob.setObjectName("secondaryBtn")
            db = QPushButton("Delete"); db.setObjectName("dangerBtn")
            ob.clicked.connect(lambda _, rid=run["id"]: self._open(rid))
            db.clicked.connect(lambda _, rid=run["id"]: self._delete(rid))
            al.addWidget(ob); al.addWidget(db)
            self.table.setCellWidget(r, 4, acts)

    def _open(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row: return
        path = row["excel_path"]
        if not os.path.exists(path):
            from app.excel.writer import write_workbook
            write_workbook(ProFormaSession.from_json(row["inputs_json"]), path)
        os.startfile(path)

    def _delete(self, run_id: int):
        if QMessageBox.question(self, "Delete", "Remove this run?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            delete_run(run_id, conn=self._db); self.refresh()
