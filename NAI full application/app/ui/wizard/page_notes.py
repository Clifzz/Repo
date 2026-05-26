from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit
from PySide6.QtCore import Qt
from app.models.session import ProFormaSession


class NotesPage(QWidget):
    def __init__(self, session: ProFormaSession):
        super().__init__()
        self.session = session
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 0)
        title = QLabel("Deal Notes & Assumptions")
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
        layout.addWidget(title)
        sub = QLabel("Optional. These notes will appear in the PDF and Excel output.")
        sub.setStyleSheet("color: #8E8E93; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(sub)
        self._edit = QPlainTextEdit()
        self._edit.setObjectName("notesEdit")
        self._edit.setPlaceholderText(
            "Enter deal assumptions, market commentary, or any relevant notes..."
        )
        layout.addWidget(self._edit, 1)
        self._count_lbl = QLabel("0 characters")
        self._count_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._count_lbl)
        self._edit.textChanged.connect(self._update_count)

    def _update_count(self):
        n = len(self._edit.toPlainText())
        self._count_lbl.setText(f"{n} character{'s' if n != 1 else ''}")

    def bind(self, session: ProFormaSession):
        self.session = session
        self.refresh()

    def refresh(self):
        self._edit.setPlainText(self.session.notes)
        self._update_count()

    def validate(self) -> bool:
        return True

    def commit(self):
        self.session.notes = self._edit.toPlainText()
