from __future__ import annotations
import urllib.parse
import webbrowser
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox,
)
from app.models.session import ProFormaSession


class EmailDialog(QDialog):
    def __init__(self, parent, session: ProFormaSession, pdf_path: str | None):
        super().__init__(parent)
        self._session = session
        self._pdf_path = pdf_path or ""
        self.setWindowTitle("Email Pro Forma")
        self.setFixedWidth(320)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl = QLabel("Send this pro forma via:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        outlook_btn = QPushButton("Open in Outlook")
        outlook_btn.setObjectName("primaryBtn")
        outlook_btn.clicked.connect(self._send_outlook)
        gmail_btn = QPushButton("Open in Gmail")
        gmail_btn.setObjectName("secondaryBtn")
        gmail_btn.clicked.connect(self._send_gmail)
        btn_row.addWidget(outlook_btn)
        btn_row.addWidget(gmail_btn)
        layout.addLayout(btn_row)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _send_outlook(self):
        if not self._pdf_path:
            QMessageBox.warning(self, "No PDF", "No PDF has been generated yet.")
            return
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.Subject = f"Pro Forma — {self._session.building_name or 'Unnamed Building'}"
            mail.Attachments.Add(self._pdf_path)
            mail.Display()
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Outlook Error", f"Could not open Outlook: {e}")

    def _send_gmail(self):
        if not self._pdf_path:
            QMessageBox.warning(self, "No PDF", "No PDF has been generated yet.")
            return
        from PySide6.QtGui import QGuiApplication
        subject = urllib.parse.quote(f"Pro Forma — {self._session.building_name or 'Unnamed Building'}")
        webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&su={subject}")
        QGuiApplication.clipboard().setText(self._pdf_path)
        QMessageBox.information(
            self,
            "Gmail Opened",
            "Gmail opened in your browser.\n\n"
            "Your PDF path has been copied to the clipboard — "
            "click the paperclip icon in Gmail to attach it.",
        )
        self.accept()
