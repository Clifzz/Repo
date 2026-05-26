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
