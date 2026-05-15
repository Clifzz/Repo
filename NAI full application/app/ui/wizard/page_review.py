from __future__ import annotations
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFileDialog, QMessageBox, QCheckBox,
)
from PySide6.QtCore import Qt
from app.models.session import ProFormaSession
from app.logic.calculator import calculate_proforma
from app.excel.writer import write_workbook
from app.db.database import init_db, save_run


class ReviewPage(QWidget):
    def __init__(self, session: ProFormaSession, on_generate):
        super().__init__()
        self.session = session; self._on_generate = on_generate
        self._db = init_db(); self._folder = str(Path.home() / "Desktop")
        self._build_ui()

    def bind(self, session: ProFormaSession): self.session = session

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
        if s.tenants:
            try:
                res = calculate_proforma(s)
                self._rev_lbl.setText(f"Rental Revenue Y1: <b>${res['rental_revenue'][0]:,.0f}</b>")
                self._noi_lbl.setText(f"NOI Y1: <b>${res['nois'][0]:,.0f}</b>")
                self._val_lbl.setText(f"Building Value Y1: <b>${res['values'][0]:,.0f}</b>")
            except Exception as e:
                self._noi_lbl.setText(f"Preview error: {e}")
        safe = s.building_name.replace(" ", "_") or "ProForma"
        self._fname.setText(f"{safe}_Proforma.xlsx")

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 0)
        title = QLabel("Review & Export")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        row = QHBoxLayout()
        for attr, lbl_text in [("_bldg_lbl","Building"),("_ten_lbl","Tenants")]:
            card = QWidget(); card.setObjectName("card")
            cv = QVBoxLayout(card); cv.setContentsMargins(16, 16, 16, 16)
            cv.addWidget(QLabel(f"<b>{lbl_text}</b>"))
            lbl = QLabel(); lbl.setTextFormat(Qt.TextFormat.RichText); lbl.setWordWrap(True)
            setattr(self, attr, lbl); cv.addWidget(lbl); cv.addStretch()
            row.addWidget(card, 1)
        layout.addLayout(row)

        metrics = QHBoxLayout()
        self._rev_lbl = QLabel("--"); self._noi_lbl = QLabel("--"); self._val_lbl = QLabel("--")
        for lbl in (self._rev_lbl, self._noi_lbl, self._val_lbl):
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setStyleSheet("font-size:14px; padding:8px;")
            metrics.addWidget(lbl)
        layout.addLayout(metrics)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Filename:"))
        self._fname = QLineEdit(); path_row.addWidget(self._fname, 1)
        browse = QPushButton("Choose Folder..."); browse.setObjectName("secondaryBtn")
        browse.clicked.connect(self._browse); path_row.addWidget(browse)
        layout.addLayout(path_row)

        self._folder_lbl = QLabel(f"Saving to: {self._folder}")
        self._folder_lbl.setStyleSheet("color:#666666; font-size:12px;")
        layout.addWidget(self._folder_lbl)
        self._pdf_check = QCheckBox("Also export PDF summary")
        self._pdf_check.setChecked(True)
        layout.addWidget(self._pdf_check)
        layout.addStretch()

    def _browse(self):
        f = QFileDialog.getExistingDirectory(self, "Select Output Folder", self._folder)
        if f: self._folder = f; self._folder_lbl.setText(f"Saving to: {f}")

    def validate(self) -> bool: return True

    def commit(self):
        s = self.session
        fname = self._fname.text().strip() or "ProForma.xlsx"
        if not fname.endswith(".xlsx"):
            fname += ".xlsx"
        path = os.path.join(self._folder, fname)
        try:
            write_workbook(s, path)
            res = calculate_proforma(s)
            save_run(s, path, res["nois"][0], res["values"][0], conn=self._db)
            if self._pdf_check.isChecked():
                from app.excel.pdf_writer import export_pdf
                pdf_path = path[:-5] + ".pdf"
                try:
                    export_pdf(s, res, pdf_path)
                except Exception as e_pdf:
                    QMessageBox.warning(
                        self, "PDF Export",
                        f"PDF export failed: {e_pdf}\nExcel was saved successfully.",
                    )
            os.startfile(path)
            self._on_generate()
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))
