from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QMessageBox,
)
from PySide6.QtCore import Qt


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
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = self._make_sidebar()
        layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        from app.ui.dashboard import DashboardView
        from app.ui.wizard.wizard import WizardView
        self.dashboard = DashboardView(on_new=self.show_wizard)
        self.wizard = WizardView(on_complete=self.show_dashboard, on_cancel=self.show_dashboard)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.wizard)
        self.show_dashboard()

    def _make_sidebar(self) -> QWidget:
        sb = QWidget(); sb.setObjectName("sidebar"); sb.setFixedWidth(200)
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        logo_path = Path(__file__).parent.parent.parent / "assets" / "nai_logo.svg"
        if logo_path.exists():
            from PySide6.QtSvgWidgets import QSvgWidget
            logo_svg = QSvgWidget(str(logo_path))
            logo_svg.setFixedSize(160, 35)
            logo_svg.setStyleSheet("background: transparent; margin: 16px;")
            layout.addWidget(logo_svg)
            sub = QLabel("Pro Forma Generator")
            sub.setStyleSheet("color: #AAAAAA; font-size: 10px; padding: 0 16px 12px 16px;")
            layout.addWidget(sub)
        else:
            logo = QLabel("NAI\nPro Forma")
            logo.setObjectName("logo")
            logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(logo)
        self._btn_dash = self._nav_btn("Dashboard", self.show_dashboard)
        self._btn_new = self._nav_btn("New Pro Forma", self.show_wizard)
        layout.addWidget(self._btn_dash); layout.addWidget(self._btn_new)
        layout.addStretch()
        return sb

    def _nav_btn(self, label: str, slot) -> QPushButton:
        btn = QPushButton(label); btn.setObjectName("navBtn")
        btn.clicked.connect(slot); return btn

    def _set_active(self, active: QPushButton):
        for b in (self._btn_dash, self._btn_new):
            b.setProperty("active", b is active)
            b.style().unpolish(b); b.style().polish(b)

    def show_dashboard(self):
        self.dashboard.refresh()
        self.stack.setCurrentIndex(0)
        self._set_active(self._btn_dash)

    def show_wizard(self):
        if self.stack.currentIndex() == 1:
            return
        self.wizard.reset()
        self.stack.setCurrentIndex(1)
        self._set_active(self._btn_new)
