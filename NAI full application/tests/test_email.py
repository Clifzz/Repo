import pytest
from unittest.mock import MagicMock, patch


def test_email_dialog_constructs(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "Email Pro Forma"


def test_outlook_sends_correct_subject(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    mock_mail = MagicMock()
    mock_outlook = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail
    with patch("win32com.client.Dispatch", return_value=mock_outlook):
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_mail.Display.assert_called_once()
    assert "Test Tower" in mock_mail.Subject


def test_outlook_attaches_pdf(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    mock_mail = MagicMock()
    mock_outlook = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail
    with patch("win32com.client.Dispatch", return_value=mock_outlook):
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_mail.Attachments.Add.assert_called_once_with("C:/fake/path.pdf")


def test_gmail_opens_browser_and_copies_clipboard(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    with patch("webbrowser.open") as mock_browser, \
         patch("PySide6.QtGui.QGuiApplication.clipboard") as mock_clipboard, \
         patch("PySide6.QtWidgets.QMessageBox.information"):
        mock_cb = MagicMock()
        mock_clipboard.return_value = mock_cb
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_gmail()
    mock_browser.assert_called_once()
    url = mock_browser.call_args[0][0]
    assert "mail.google.com" in url
    assert "Test%20Tower" in url
    mock_cb.setText.assert_called_once_with("C:/fake/path.pdf")


def test_outlook_error_shows_warning(qtbot, basic_session):
    from app.ui.email_dialog import EmailDialog
    with patch("win32com.client.Dispatch", side_effect=Exception("COM error")), \
         patch("PySide6.QtWidgets.QMessageBox.warning") as mock_warn:
        dlg = EmailDialog(None, basic_session, "C:/fake/path.pdf")
        qtbot.addWidget(dlg)
        dlg._send_outlook()
    mock_warn.assert_called_once()
