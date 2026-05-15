from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame,
)
from app.models.session import ProFormaSession


class WizardView(QWidget):
    def __init__(self, on_complete, on_cancel):
        super().__init__()
        self._on_complete = on_complete; self._on_cancel = on_cancel
        self.session = ProFormaSession(); self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.stack = QStackedWidget(); layout.addWidget(self.stack, 1)

        from app.ui.wizard.page_building import BuildingInfoPage
        from app.ui.wizard.page_tenants import TenantEntryPage
        from app.ui.wizard.page_review import ReviewPage

        self.page_building = BuildingInfoPage(self.session)
        self.page_tenants = TenantEntryPage(self.session)
        self.page_review = ReviewPage(self.session, on_generate=self._on_complete)
        self.stack.addWidget(self.page_building)
        self.stack.addWidget(self.page_tenants)
        self.stack.addWidget(self.page_review)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine); layout.addWidget(sep)
        nav = QHBoxLayout(); nav.setContentsMargins(24, 12, 24, 12)
        self._step_lbl = QLabel(); self._step_lbl.setObjectName("stepLabel")
        self._back_btn = QPushButton(); self._back_btn.setObjectName("secondaryBtn")
        self._next_btn = QPushButton(); self._next_btn.setObjectName("primaryBtn")
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn.clicked.connect(self._go_next)
        nav.addWidget(self._step_lbl); nav.addStretch()
        nav.addWidget(self._back_btn); nav.addWidget(self._next_btn)
        layout.addLayout(nav); self._update_nav()

    def reset(self):
        self.session = ProFormaSession()
        self.page_building.bind(self.session)
        self.page_tenants.bind(self.session)
        self.page_review.bind(self.session)
        self.stack.setCurrentIndex(0); self._update_nav()

    def _go_back(self):
        idx = self.stack.currentIndex()
        if idx == 0: self._on_cancel(); return
        self.stack.setCurrentIndex(idx - 1); self._update_nav()

    def _go_next(self):
        idx = self.stack.currentIndex()
        page = self.stack.widget(idx)
        if hasattr(page, "validate") and not page.validate(): return
        if hasattr(page, "commit"): page.commit()
        if idx < 2:
            if idx == 1: self.page_review.refresh()
            self.stack.setCurrentIndex(idx + 1); self._update_nav()

    def _update_nav(self):
        idx = self.stack.currentIndex()
        self._step_lbl.setText(f"Step {idx+1} of 3")
        self._back_btn.setText("Cancel" if idx == 0 else "Back")
        self._next_btn.setText("Generate Pro Forma" if idx == 2 else "Next")
