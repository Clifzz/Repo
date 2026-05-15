from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QLabel, QScrollArea,
)
from app.models.session import ProFormaSession


class BuildingInfoPage(QWidget):
    def __init__(self, session: ProFormaSession):
        super().__init__(); self.session = session; self._build_ui()

    def bind(self, session: ProFormaSession):
        self.session = session; self._populate()

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(24, 24, 24, 0)
        title = QLabel("Building Information")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 12px;")
        outer.addWidget(title)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(scroll.Shape.NoFrame)
        card = QWidget(); card.setObjectName("card")
        form = QFormLayout(card); form.setContentsMargins(20, 20, 20, 20); form.setSpacing(14)
        scroll.setWidget(card); outer.addWidget(scroll)

        def spin(lo, hi, dec=0, step=1):
            w = QDoubleSpinBox() if dec else QSpinBox()
            if dec: w.setDecimals(dec); w.setSingleStep(step)
            w.setMinimum(lo); w.setMaximum(hi); return w

        self._name = QLineEdit()
        self._year = spin(2000, 2100)
        self._month = QComboBox(); self._month.addItems([str(m) for m in range(1, 13)])
        self._yrs = spin(1, 30); self._tot_sf = spin(0, 10_000_000)
        self._occ_sf = spin(0, 10_000_000)
        self._opex = spin(0, 1000, dec=2, step=0.5); self._opex.setPrefix("$")
        self._mkt_rt = spin(0, 1000, dec=2, step=0.5); self._mkt_rt.setPrefix("$")
        self._mkt_gw = spin(0, 100, dec=2, step=0.1); self._mkt_gw.setSuffix("%")
        self._cap = spin(0, 100, dec=4, step=0.25); self._cap.setSuffix("%")
        self._delta = spin(0, 10, dec=4, step=0.25); self._delta.setSuffix("%")

        for label, widget in [
            ("Building Name", self._name), ("Start Year", self._year),
            ("Start Month", self._month), ("Years to Project", self._yrs),
            ("Total SF", self._tot_sf), ("Occupied SF", self._occ_sf),
            ("OpEx / SF", self._opex), ("Market Avg Rate ($/SF)", self._mkt_rt),
            ("Market Rent Growth %", self._mkt_gw), ("Cap Rate %", self._cap),
            ("Cap Rate Sensitivity Delta %", self._delta),
        ]:
            form.addRow(label, widget)

        self._year.setToolTip("The first calendar year of the projection (e.g. 2025).")
        self._month.setToolTip("The month the projection begins within the start year.")
        self._yrs.setToolTip("Number of full years to model. Determines how many columns appear in the Excel output.")
        self._tot_sf.setToolTip("Gross leasable area of the building in square feet.")
        self._occ_sf.setToolTip("Currently occupied square footage. Must not exceed Total SF.")
        self._opex.setToolTip("Annual operating expenses per square foot. Grows at 2.5%/yr in the model.")
        self._mkt_rt.setToolTip("Current market asking rent per square foot per year. Used as a benchmark row in the output.")
        self._mkt_gw.setToolTip("Annual growth rate applied to the market rent benchmark.")
        self._cap.setToolTip("Capitalization rate: Building Value = NOI ÷ Cap Rate.")
        self._delta.setToolTip("The ± spread applied to the cap rate in the sensitivity analysis rows (e.g. 0.25% means ±0.25%).")

        self._err = QLabel(""); self._err.setStyleSheet("color: #C8102E;")
        outer.addWidget(self._err); self._populate()

    def _populate(self):
        s = self.session
        self._name.setText(s.building_name); self._year.setValue(s.start_year)
        self._month.setCurrentIndex(s.start_month - 1); self._yrs.setValue(s.years)
        self._tot_sf.setValue(int(s.total_sqft)); self._occ_sf.setValue(int(s.occupied_sqft))
        self._opex.setValue(s.opex_psf); self._mkt_rt.setValue(s.market_avg_rate)
        self._mkt_gw.setValue(s.market_growth_pct * 100)
        self._cap.setValue(s.cap_rate * 100); self._delta.setValue(s.cap_delta * 100)

    def validate(self) -> bool:
        name_ok = bool(self._name.text().strip())
        sf_ok = self._occ_sf.value() <= self._tot_sf.value()
        ok = name_ok and sf_ok
        if not name_ok:
            self._err.setText("Building name is required.")
        elif not sf_ok:
            self._err.setText("Occupied SF cannot exceed Total SF.")
        else:
            self._err.setText("")
        self._name.setProperty("invalid", "" if name_ok else "true")
        self._name.style().unpolish(self._name); self._name.style().polish(self._name)
        return ok

    def commit(self):
        s = self.session
        s.building_name = self._name.text().strip(); s.start_year = self._year.value()
        s.start_month = self._month.currentIndex() + 1; s.years = self._yrs.value()
        s.total_sqft = float(self._tot_sf.value()); s.occupied_sqft = float(self._occ_sf.value())
        s.opex_psf = self._opex.value(); s.market_avg_rate = self._mkt_rt.value()
        s.market_growth_pct = self._mkt_gw.value() / 100
        s.cap_rate = self._cap.value() / 100; s.cap_delta = self._delta.value() / 100
