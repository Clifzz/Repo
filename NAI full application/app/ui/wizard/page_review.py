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
            except Exception as e:
                self._noi_lbl.setText(f"Preview error: {e}")
        # Populate IRR inputs from session (0.0 = "Auto")
        for spin in (self._purchase_spin, self._exit_cap_spin, self._discount_spin):
            spin.blockSignals(True)
        self._purchase_spin.setValue(s.purchase_price)
        self._exit_cap_spin.setValue(s.exit_cap_rate * 100.0)
        self._discount_spin.setValue(s.discount_rate * 100.0)
        for spin in (self._purchase_spin, self._exit_cap_spin, self._discount_spin):
            spin.blockSignals(False)
        self._update_irr()
        safe = s.building_name.replace(" ", "_") or "ProForma"
        self._fname.setText(f"{safe}_Proforma.xlsx")
        self._last_pdf_path = None
        self._email_btn.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 0)
        title = QLabel("Review & Export")
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
        layout.addWidget(title)

        row = QHBoxLayout()
        for attr, lbl_text in [("_bldg_lbl", "Building"), ("_ten_lbl", "Tenants")]:
            card = QWidget()
            card.setObjectName("card")
            cv = QVBoxLayout(card)
            cv.setContentsMargins(20, 20, 20, 20)
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
        # calculate_irr_npv reads from session, so pre-update fields from spinboxes.
        # commit() repeats this write intentionally before saving.
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
        try:
            from app.ui.email_dialog import EmailDialog
        except ImportError:
            QMessageBox.information(self, "Email", "Email functionality is not yet available.")
            return
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
