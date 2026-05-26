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
