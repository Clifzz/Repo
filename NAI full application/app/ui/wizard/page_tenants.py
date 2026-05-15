from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFrame, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QCheckBox, QDateEdit, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from app.models.session import ProFormaSession
from app.models.tenant import TenantModel


class TenantEntryPage(QWidget):
    def __init__(self, session: ProFormaSession):
        super().__init__(); self.session = session
        self._sel: int | None = None; self._build_ui()

    def bind(self, session: ProFormaSession):
        self.session = session; self._refresh_table(); self._hide_detail()

    def _build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(24, 24, 24, 0)
        title = QLabel("Tenant Entry")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Name","Suite","SF","Rate/SF","Expiry","Projection",""])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(6, 50)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(lambda r, c: self._show_detail(r) if c != 6 else None)
        layout.addWidget(self.table, 1)

        add_btn = QPushButton("+ Add Tenant"); add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_tenant)
        layout.addWidget(add_btn, 0, Qt.AlignmentFlag.AlignLeft)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); layout.addWidget(sep)
        self._detail_scroll = self._build_detail(); layout.addWidget(self._detail_scroll)
        self._hide_detail()

    def _build_detail(self) -> QScrollArea:
        panel = QWidget(); panel.setObjectName("card")
        scroll = QScrollArea(); scroll.setWidget(panel); scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(300); scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        form = QFormLayout(panel); form.setContentsMargins(16, 16, 16, 16); form.setSpacing(10)

        def dspin(lo, hi, dec=2, pre="", suf=""):
            w = QDoubleSpinBox(); w.setMinimum(lo); w.setMaximum(hi); w.setDecimals(dec)
            if pre: w.setPrefix(pre)
            if suf: w.setSuffix(suf)
            return w

        self._dn = QLineEdit(); self._ds = QLineEdit()
        self._dsf = dspin(0, 10_000_000, dec=0)
        self._dr = dspin(0, 10_000, pre="$")
        self._dex = QDateEdit(); self._dex.setCalendarPopup(True); self._dex.setDisplayFormat("MM-dd-yyyy")
        self._dy1 = dspin(0, 100_000_000, pre="$"); self._dy1.setSpecialValueText("(no override)")
        self._dpt = QComboBox(); self._dpt.addItems(["compounded","pro_rated"])
        self._dgr = dspin(0, 100, suf="%"); self._dfl = dspin(0, 1000, pre="$")
        self._dpc = dspin(0, 100, suf="%"); self._drn = QCheckBox("Lease renews")
        self._drs = QDateEdit(); self._drs.setCalendarPopup(True); self._drs.setDisplayFormat("MM-dd-yyyy")
        self._dry = dspin(1, 30, dec=0)
        self._drp = QComboBox(); self._drp.addItems(["compounded","pro_rated"])
        self._drg = dspin(0, 100, suf="%"); self._drf = dspin(0, 1000, pre="$")
        self._drpc = dspin(0, 100, suf="%")

        self._dy1.setToolTip(
            "Optional: enter total annual rent for Year 1 to override the SF × Rate calculation. "
            "Leave at 0 for no override. Accepts $0 for a rent-free year."
        )
        self._dpt.setToolTip(
            "'compounded': rent grows by a fixed annual percentage each year.\n"
            "'pro_rated': rent increases by a flat $/SF or percentage each year."
        )
        self._dgr.setToolTip("Annual growth rate applied to rent (compounded projection type only).")
        self._dfl.setToolTip("Flat dollar increase to rate per SF each year (pro_rated flat type only).")
        self._dpc.setToolTip("Percentage increase in rent each year (pro_rated percentage type only).")
        self._drn.setToolTip("Check if this tenant has a renewal option within the projection window.")
        self._drs.setToolTip("Date the renewal term begins.")
        self._dry.setToolTip("Length of the renewal term in years.")
        self._drp.setToolTip("Projection type for the renewal term (same logic as the base term).")
        self._drg.setToolTip("Annual growth rate for the renewal term (compounded type only).")
        self._drf.setToolTip("Flat $/SF/yr increase for the renewal term (pro_rated flat type only).")
        self._drpc.setToolTip("Percentage increase per year for the renewal term (pro_rated pct type only).")

        for lbl, w in [
            ("Name", self._dn), ("Suite #", self._ds), ("SF", self._dsf),
            ("Rate/SF", self._dr), ("Lease Expiry", self._dex),
            ("Year 1 Override ($)", self._dy1), ("Projection Type", self._dpt),
            ("Growth Rate %", self._dgr), ("Flat $/SF/yr", self._dfl), ("Pct %", self._dpc),
            ("", self._drn), ("Renewal Start", self._drs), ("Renewal Term (yrs)", self._dry),
            ("Renewal Projection", self._drp), ("Renewal Growth %", self._drg),
            ("Renewal Flat $/SF/yr", self._drf), ("Renewal Pct %", self._drpc),
        ]:
            form.addRow(lbl, w)

        save_btn = QPushButton("Save Tenant"); save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_detail)
        form.addRow("", save_btn)
        return scroll

    def _hide_detail(self): self._detail_scroll.setVisible(False); self._sel = None

    def _show_detail(self, idx: int):
        if idx >= len(self.session.tenants): return
        self._sel = idx; t = self.session.tenants[idx]
        self._dn.setText(t.name); self._ds.setText(t.suite)
        self._dsf.setValue(t.sqft); self._dr.setValue(t.rate_psf)
        if t.lease_exp:
            p = t.lease_exp.split("-")
            self._dex.setDate(QDate(int(p[2]), int(p[0]), int(p[1])))
        self._dy1.setValue(t.year1_override or 0.0)
        self._dpt.setCurrentText(t.projection_type)
        self._dgr.setValue(t.growth_rate * 100); self._dfl.setValue(t.flat_increase)
        self._dpc.setValue(t.pct_increase * 100); self._drn.setChecked(t.renewed)
        if t.renewal_start:
            p = t.renewal_start.split("-")
            self._drs.setDate(QDate(int(p[2]), int(p[0]), int(p[1])))
        self._dry.setValue(t.renewal_term_years); self._drp.setCurrentText(t.renewal_projection_type)
        self._drg.setValue(t.renewal_growth_rate * 100); self._drf.setValue(t.renewal_flat_increase)
        self._drpc.setValue(t.renewal_pct_increase * 100)
        self._detail_scroll.setVisible(True)

    def _add_tenant(self):
        t = TenantModel("","",0,0,"",None,"compounded",0,0,0,False,"",5,"compounded",0,0,0)
        self.session.tenants.append(t); self._refresh_table()
        self._show_detail(len(self.session.tenants) - 1)

    def _save_detail(self):
        if self._sel is None: return
        t = self.session.tenants[self._sel]
        t.name = self._dn.text().strip(); t.suite = self._ds.text().strip()
        t.sqft = self._dsf.value(); t.rate_psf = self._dr.value()
        d = self._dex.date()
        t.lease_exp = f"{d.month():02d}-{d.day():02d}-{d.year()}"
        ov = self._dy1.value(); t.year1_override = ov if ov > 0 else None
        t.projection_type = self._dpt.currentText()
        t.growth_rate = self._dgr.value() / 100; t.flat_increase = self._dfl.value()
        t.pct_increase = self._dpc.value() / 100; t.renewed = self._drn.isChecked()
        rd = self._drs.date()
        t.renewal_start = f"{rd.month():02d}-{rd.day():02d}-{rd.year()}" if t.renewed else ""
        t.renewal_term_years = int(self._dry.value())
        t.renewal_projection_type = self._drp.currentText()
        t.renewal_growth_rate = self._drg.value() / 100
        t.renewal_flat_increase = self._drf.value()
        t.renewal_pct_increase = self._drpc.value() / 100
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        for i, t in enumerate(self.session.tenants):
            r = self.table.rowCount(); self.table.insertRow(r)
            for c, v in enumerate([t.name, t.suite, f"{t.sqft:,.0f}",
                    f"${t.rate_psf:.2f}", t.lease_exp, t.projection_type]):
                self.table.setItem(r, c, QTableWidgetItem(v))
            db = QPushButton("X"); db.setObjectName("dangerBtn")
            db.clicked.connect(lambda _, idx=i: self._del(idx))
            self.table.setCellWidget(r, 6, db)

    def _del(self, idx: int):
        if QMessageBox.question(self, "Delete", "Remove this tenant?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self.session.tenants.pop(idx); self._refresh_table(); self._hide_detail()

    def validate(self) -> bool:
        if not self.session.tenants:
            QMessageBox.warning(self, "No Tenants", "Add at least one tenant.")
            return False
        return True

    def commit(self):
        if self._sel is not None: self._save_detail()
