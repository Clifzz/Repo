from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget
from app.db.database import init_db, list_runs, delete_run, get_run
from app.models.session import ProFormaSession

_LOGO_PATH = Path(__file__).parent.parent.parent / "assets" / "nai_logo.svg"


class DashboardView(QWidget):
    def __init__(self, on_new):
        super().__init__()
        self._on_new = on_new
        self._db = init_db()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # White header bar: logo | divider | title + New button
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

        # Grey stats strip
        stats_bar = QWidget()
        stats_bar.setStyleSheet("background: #F0F0F0; border-bottom: 1px solid #E0E0E0;")
        sl = QHBoxLayout(stats_bar)
        sl.setContentsMargins(24, 7, 24, 7)
        self._count_lbl = QLabel("0 pro formas saved")
        self._count_lbl.setStyleSheet("color: #666666; font-size: 12px;")
        sl.addWidget(self._count_lbl)
        sl.addStretch()
        layout.addWidget(stats_bar)

        # Table body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 20, 24, 24)
        bl.setSpacing(12)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("card")
        self.table.setHorizontalHeaderLabels(
            ["Building Name", "Date Created", "NOI (Year 1)", "Value (Year 1)", "Actions"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(4, 160)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        bl.addWidget(self.table)

        self._empty = QLabel("No pro formas yet — click New Pro Forma to get started")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888888; font-size: 14px; padding: 60px;")
        bl.addWidget(self._empty)
        layout.addWidget(body, 1)

    def refresh(self):
        runs = list_runs(conn=self._db)
        self.table.setRowCount(0)
        count = len(runs)
        self._count_lbl.setText(
            f"{count} pro forma{'s' if count != 1 else ''} saved"
        )
        self._empty.setVisible(not runs)
        self.table.setVisible(bool(runs))
        for run in runs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            dt = datetime.fromisoformat(run["created_at"]).strftime("%b %d, %Y  %I:%M %p")
            for c, v in enumerate([
                run["building_name"], dt,
                f"${run['noi_y1']:,.0f}" if run["noi_y1"] else "—",
                f"${run['value_y1']:,.0f}" if run["value_y1"] else "—",
            ]):
                item = QTableWidgetItem(v)
                if c in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(r, c, item)
            acts = QWidget()
            al = QHBoxLayout(acts)
            al.setContentsMargins(4, 2, 4, 2)
            ob = QPushButton("Open")
            ob.setObjectName("secondaryBtn")
            db = QPushButton("Delete")
            db.setObjectName("dangerBtn")
            ob.clicked.connect(lambda _, rid=run["id"]: self._open(rid))
            db.clicked.connect(lambda _, rid=run["id"]: self._delete(rid))
            al.addWidget(ob)
            al.addWidget(db)
            self.table.setCellWidget(r, 4, acts)

    def _open(self, run_id: int):
        row = get_run(run_id, conn=self._db)
        if not row:
            return
        path = row["excel_path"]
        if not os.path.exists(path):
            from app.excel.writer import write_workbook
            write_workbook(ProFormaSession.from_json(row["inputs_json"]), path)
        os.startfile(path)

    def _delete(self, run_id: int):
        if QMessageBox.question(
            self, "Delete", "Remove this run?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            delete_run(run_id, conn=self._db)
            self.refresh()
