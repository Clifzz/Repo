import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NAI Pro Forma Generator")
    icon = Path(__file__).parent / "assets" / "nai_logo.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    w = MainWindow(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
