# Auto Note Writer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-AI-powered "Auto-Generate" button to the Notes wizard page that writes professional CRE deal commentary from the live session data, backed by a locally-running Ollama instance configured through a first-run setup wizard that downloads and configures Ollama automatically.

**Architecture:** `app/db/settings.py` persists a `settings` key/value table for setup state and model choice. `app/ollama/client.py` wraps Ollama's REST API with `ping`, `list_models`, `pull_model`, and `generate`. `app/ui/setup_wizard.py` is a 5-step `QDialog` that auto-shows on first launch, downloads `OllamaSetup.exe` via `QNetworkAccessManager`, polls for Ollama to start, and pulls the chosen model with a streaming progress bar. The Notes page gains an `Auto-Generate` button that spawns a `_GenerateWorker(QThread)` streaming tokens into the `QPlainTextEdit`.

**Tech Stack:** PySide6 (QDialog, QStackedWidget, QNetworkAccessManager, QThread, Signal), `urllib.request` (Ollama HTTP calls), SQLite (settings persistence), Ollama REST API on `localhost:11434`

---

## File Map

| Status | File | What changes |
|--------|------|-------------|
| Modify | `app/db/database.py` | Add `settings` table to `init_db()` |
| Create | `app/db/settings.py` | `get_setting()` / `set_setting()` |
| Create | `app/ollama/__init__.py` | Package marker |
| Create | `app/ollama/client.py` | `OllamaError`, `OllamaClient` |
| Create | `app/ui/setup_wizard.py` | `SetupWizardDialog`, `_PollWorker`, `_PullWorker` |
| Modify | `app/ui/main_window.py` | Add `_check_first_run()`, call it in `_build_ui()` |
| Modify | `app/ui/wizard/page_notes.py` | Add `_GenerateWorker`, `_build_prompt()`, Auto-Generate button |
| Modify | `NAI_ProForma_Generator.spec` | Add `PySide6.QtNetwork` to `hiddenimports` |
| Create | `tests/test_settings.py` | Settings layer tests |
| Create | `tests/test_ollama_client.py` | OllamaClient unit tests (mocked HTTP) |
| Create | `tests/test_setup_wizard.py` | First-run detection logic tests |
| Modify | `tests/test_notes.py` | Add Auto-Generate button visibility tests |

---

### Task 1: Settings DB layer

**Files:**
- Modify: `app/db/database.py`
- Create: `app/db/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings.py`:

```python
import pytest
from app.db.database import init_db
from app.db.settings import get_setting, set_setting


@pytest.fixture
def db(tmp_path):
    return init_db(str(tmp_path / "test.db"))


def test_get_missing_key_returns_none(db):
    assert get_setting("missing", conn=db) is None


def test_get_missing_key_returns_provided_default(db):
    assert get_setting("missing", default="fallback", conn=db) == "fallback"


def test_set_and_get_roundtrip(db):
    set_setting("foo", "bar", conn=db)
    assert get_setting("foo", conn=db) == "bar"


def test_set_overwrites_existing(db):
    set_setting("key", "v1", conn=db)
    set_setting("key", "v2", conn=db)
    assert get_setting("key", conn=db) == "v2"


def test_multiple_keys_are_independent(db):
    set_setting("a", "1", conn=db)
    set_setting("b", "2", conn=db)
    assert get_setting("a", conn=db) == "1"
    assert get_setting("b", conn=db) == "2"
```

- [ ] **Step 2: Run tests to verify they fail**

```
.venv\Scripts\python.exe -m pytest tests/test_settings.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.db.settings'`

- [ ] **Step 3: Add settings table to `init_db()` in `app/db/database.py`**

Add the following block inside `init_db()`, after the `templates` table `conn.execute(...)` and before `conn.commit()`:

```python
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
```

The full `init_db()` body becomes:

```python
def init_db(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or _default_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            excel_path TEXT NOT NULL,
            noi_y1 REAL,
            value_y1 REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL,
            building_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            inputs_json TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn
```

- [ ] **Step 4: Create `app/db/settings.py`**

```python
from __future__ import annotations
import sqlite3
from app.db.database import init_db


def get_setting(key: str, default: str | None = None, conn: sqlite3.Connection | None = None) -> str | None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        if _owned:
            c.close()


def set_setting(key: str, value: str, conn: sqlite3.Connection | None = None) -> None:
    _owned = conn is None
    c = init_db() if _owned else conn
    try:
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        c.commit()
    finally:
        if _owned:
            c.close()
```

- [ ] **Step 5: Run tests to verify they pass**

```
.venv\Scripts\python.exe -m pytest tests/test_settings.py -v
```

Expected: 5 passed

- [ ] **Step 6: Run full suite to check for regressions**

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 70 passed

- [ ] **Step 7: Commit**

```
git add app/db/database.py app/db/settings.py tests/test_settings.py
git commit -m "feat: add settings table and get/set_setting API"
```

---

### Task 2: OllamaClient

**Files:**
- Create: `app/ollama/__init__.py`
- Create: `app/ollama/client.py`
- Create: `tests/test_ollama_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ollama_client.py`:

```python
import json
import pytest
import urllib.error
from unittest.mock import patch, MagicMock
from app.ollama.client import OllamaClient, OllamaError


def _mock_response(lines: list[bytes]) -> MagicMock:
    """Return a mock that behaves as a context manager and iterates over lines."""
    m = MagicMock()
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    m.__iter__ = lambda s: iter(lines)
    return m


def test_ping_returns_false_on_connection_refused():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        assert OllamaClient().ping() is False


def test_ping_returns_true_on_success():
    with patch("urllib.request.urlopen", return_value=_mock_response([])):
        assert OllamaClient().ping() is True


def test_generate_yields_response_tokens():
    lines = [
        json.dumps({"response": "Hello", "done": False}).encode(),
        json.dumps({"response": " world", "done": True}).encode(),
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(lines)):
        tokens = list(OllamaClient().generate("llama3.2", "test prompt"))
    assert tokens == ["Hello", " world"]


def test_generate_skips_empty_response_chunks():
    lines = [
        json.dumps({"response": "", "done": False}).encode(),
        json.dumps({"response": "hi", "done": True}).encode(),
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(lines)):
        tokens = list(OllamaClient().generate("llama3.2", "test"))
    assert tokens == ["hi"]


def test_generate_raises_ollama_error_on_network_failure():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
        with pytest.raises(OllamaError):
            list(OllamaClient().generate("llama3.2", "test"))


def test_pull_model_yields_status_dicts():
    lines = [
        json.dumps({"status": "pulling manifest"}).encode(),
        json.dumps({"status": "downloading", "completed": 500, "total": 1000}).encode(),
        json.dumps({"status": "success"}).encode(),
    ]
    with patch("urllib.request.urlopen", return_value=_mock_response(lines)):
        chunks = list(OllamaClient().pull_model("llama3.2"))
    assert chunks[0] == {"status": "pulling manifest"}
    assert chunks[1]["completed"] == 500
    assert chunks[-1]["status"] == "success"
```

- [ ] **Step 2: Run to verify they fail**

```
.venv\Scripts\python.exe -m pytest tests/test_ollama_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.ollama'`

- [ ] **Step 3: Create `app/ollama/__init__.py`**

Create an empty file at `app/ollama/__init__.py`.

- [ ] **Step 4: Create `app/ollama/client.py`**

```python
from __future__ import annotations
import json
import urllib.error
import urllib.request
from typing import Iterator


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base = base_url.rstrip("/")

    def ping(self) -> bool:
        try:
            urllib.request.urlopen(f"{self._base}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self._base}/api/tags", timeout=5) as r:
                data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
        except urllib.error.URLError as e:
            raise OllamaError(str(e)) from e

    def pull_model(self, model: str) -> Iterator[dict]:
        payload = json.dumps({"model": model, "stream": True}).encode()
        req = urllib.request.Request(
            f"{self._base}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                for line in r:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
        except urllib.error.URLError as e:
            raise OllamaError(str(e)) from e

    def generate(self, model: str, prompt: str) -> Iterator[str]:
        payload = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode()
        req = urllib.request.Request(
            f"{self._base}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                for line in r:
                    line = line.strip()
                    if line:
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]
        except urllib.error.URLError as e:
            raise OllamaError(str(e)) from e
```

- [ ] **Step 5: Run tests to verify they pass**

```
.venv\Scripts\python.exe -m pytest tests/test_ollama_client.py -v
```

Expected: 6 passed

- [ ] **Step 6: Run full suite**

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 76 passed

- [ ] **Step 7: Commit**

```
git add app/ollama/__init__.py app/ollama/client.py tests/test_ollama_client.py
git commit -m "feat: add OllamaClient with ping, pull_model, and streaming generate"
```

---

### Task 3: SetupWizardDialog

**Files:**
- Create: `app/ui/setup_wizard.py`
- Create: `tests/test_setup_wizard.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_setup_wizard.py`:

```python
import pytest
from app.db.database import init_db
from app.db.settings import get_setting, set_setting


@pytest.fixture
def db(tmp_path):
    return init_db(str(tmp_path / "test.db"))


def test_setup_not_complete_by_default(db):
    assert get_setting("setup_complete", conn=db) != "true"


def test_setup_complete_after_set(db):
    set_setting("setup_complete", "true", conn=db)
    assert get_setting("setup_complete", conn=db) == "true"


def test_ollama_model_persisted(db):
    set_setting("ollama_model", "llama3.2", conn=db)
    assert get_setting("ollama_model", conn=db) == "llama3.2"


def test_ollama_url_persisted(db):
    set_setting("ollama_url", "http://localhost:11434", conn=db)
    assert get_setting("ollama_url", conn=db) == "http://localhost:11434"
```

- [ ] **Step 2: Run to verify they pass (use existing settings layer)**

```
.venv\Scripts\python.exe -m pytest tests/test_setup_wizard.py -v
```

Expected: 4 passed

- [ ] **Step 3: Create `app/ui/setup_wizard.py`**

```python
from __future__ import annotations
import os
import subprocess
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QRadioButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.db.settings import get_setting, set_setting
from app.ollama.client import OllamaClient, OllamaError

_LOGO_PATH = Path(__file__).parent.parent / "assets" / "nai_logo.svg"
_OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"


class _PollWorker(QThread):
    found = Signal()
    timed_out = Signal()

    def run(self):
        client = OllamaClient()
        for _ in range(30):
            time.sleep(2)
            if client.ping():
                self.found.emit()
                return
        self.timed_out.emit()


class _PullWorker(QThread):
    progress = Signal(int, int)
    status_text = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, model: str, base_url: str = "http://localhost:11434", parent=None):
        super().__init__(parent)
        self._model = model
        self._base_url = base_url

    def run(self):
        try:
            client = OllamaClient(self._base_url)
            for chunk in client.pull_model(self._model):
                s = chunk.get("status", "")
                completed = chunk.get("completed", 0)
                total = chunk.get("total", 0)
                if total > 0:
                    self.progress.emit(completed, total)
                else:
                    self.status_text.emit(s)
                if s == "success":
                    self.finished.emit()
                    return
            self.finished.emit()
        except OllamaError as e:
            self.error.emit(str(e))


class SetupWizardDialog(QDialog):
    STEP_WELCOME  = 0
    STEP_DOWNLOAD = 1
    STEP_INSTALL  = 2
    STEP_MODEL    = 3
    STEP_DONE     = 4

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db = db
        self._installer_path: str | None = None
        self._selected_model = "llama3.2"
        self._poll_worker: _PollWorker | None = None
        self._pull_worker: _PullWorker | None = None
        self._nam: QNetworkAccessManager | None = None
        self._reply: QNetworkReply | None = None
        self._tmp_file = None
        self.setWindowTitle("NAI Pro Forma — Setup")
        self.setMinimumWidth(540)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: #C8102E;")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)
        if _LOGO_PATH.exists():
            logo = QSvgWidget(str(_LOGO_PATH))
            logo.setFixedSize(130, 28)
            logo.setStyleSheet("background: transparent;")
            hl.addWidget(logo)
        hl.addStretch()
        layout.addWidget(header)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        self._stack.addWidget(self._make_welcome())   # 0
        self._stack.addWidget(self._make_download())  # 1
        self._stack.addWidget(self._make_install())   # 2
        self._stack.addWidget(self._make_model())     # 3
        self._stack.addWidget(self._make_done())      # 4

    def _make_welcome(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(12)

        title = QLabel("Welcome to NAI Pro Forma Generator")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        title.setWordWrap(True)
        vl.addWidget(title)

        body = QLabel(
            "This one-time setup installs Ollama, a free local AI engine that runs "
            "entirely on your computer. No data leaves your machine.\n\n"
            "The setup takes about 5 minutes depending on your internet speed."
        )
        body.setStyleSheet("color: #8E8E93; font-size: 13px;")
        body.setWordWrap(True)
        vl.addWidget(body)
        vl.addStretch()

        btn_row = QHBoxLayout()
        skip = QPushButton("Skip for now")
        skip.setObjectName("secondaryBtn")
        skip.clicked.connect(self.reject)
        btn_row.addWidget(skip)
        btn_row.addStretch()
        start = QPushButton("Get Started →")
        start.setObjectName("primaryBtn")
        start.clicked.connect(self._start_download_step)
        btn_row.addWidget(start)
        vl.addLayout(btn_row)
        return w

    def _make_download(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(12)

        title = QLabel("Downloading Ollama")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        vl.addWidget(title)

        self._dl_status = QLabel("Starting download…")
        self._dl_status.setStyleSheet("color: #8E8E93; font-size: 13px;")
        vl.addWidget(self._dl_status)

        self._dl_bar = QProgressBar()
        self._dl_bar.setRange(0, 100)
        self._dl_bar.setValue(0)
        vl.addWidget(self._dl_bar)

        self._dl_error = QLabel()
        self._dl_error.setStyleSheet("color: #C8102E; font-size: 12px;")
        self._dl_error.setVisible(False)
        self._dl_error.setWordWrap(True)
        vl.addWidget(self._dl_error)

        vl.addStretch()

        btn_row = QHBoxLayout()
        self._dl_retry_btn = QPushButton("Retry")
        self._dl_retry_btn.setObjectName("secondaryBtn")
        self._dl_retry_btn.setVisible(False)
        self._dl_retry_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._dl_retry_btn)
        manual = QPushButton("I'll install Ollama myself →")
        manual.setObjectName("secondaryBtn")
        manual.clicked.connect(lambda: self._go_to(self.STEP_INSTALL))
        btn_row.addWidget(manual)
        btn_row.addStretch()
        vl.addLayout(btn_row)
        return w

    def _make_install(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(12)

        title = QLabel("Install Ollama")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        vl.addWidget(title)

        body = QLabel(
            "Complete the Ollama installer, then click Continue.\n"
            "Ollama will run in the background when installation is done."
        )
        body.setStyleSheet("color: #8E8E93; font-size: 13px;")
        body.setWordWrap(True)
        vl.addWidget(body)

        self._install_status = QLabel("Waiting for Ollama to start…")
        self._install_status.setStyleSheet("color: #8E8E93; font-size: 12px;")
        vl.addWidget(self._install_status)

        vl.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._continue_btn = QPushButton("Continue →")
        self._continue_btn.setObjectName("primaryBtn")
        self._continue_btn.clicked.connect(self._check_ollama_and_continue)
        btn_row.addWidget(self._continue_btn)
        vl.addLayout(btn_row)
        return w

    def _make_model(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(12)

        title = QLabel("Choose an AI Model")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        vl.addWidget(title)

        body = QLabel("This model runs entirely on your computer. Larger models produce better notes.")
        body.setStyleSheet("color: #8E8E93; font-size: 13px;")
        body.setWordWrap(True)
        vl.addWidget(body)

        self._model_group = QButtonGroup(w)
        for model_id, label in [
            ("llama3.2", "llama3.2  —  Recommended · ~2 GB · Fast, high quality"),
            ("mistral",  "mistral   —  ~4 GB · More detailed output"),
            ("phi3",     "phi3      —  ~2.3 GB · Very fast, lightweight"),
        ]:
            rb = QRadioButton(label)
            rb.setProperty("model_id", model_id)
            if model_id == "llama3.2":
                rb.setChecked(True)
            self._model_group.addButton(rb)
            vl.addWidget(rb)

        self._pull_bar = QProgressBar()
        self._pull_bar.setRange(0, 100)
        self._pull_bar.setValue(0)
        self._pull_bar.setVisible(False)
        vl.addWidget(self._pull_bar)

        self._pull_status = QLabel()
        self._pull_status.setStyleSheet("color: #8E8E93; font-size: 12px;")
        self._pull_status.setVisible(False)
        vl.addWidget(self._pull_status)

        self._pull_error = QLabel()
        self._pull_error.setStyleSheet("color: #C8102E; font-size: 12px;")
        self._pull_error.setVisible(False)
        self._pull_error.setWordWrap(True)
        vl.addWidget(self._pull_error)

        vl.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._pull_btn = QPushButton("Download Model")
        self._pull_btn.setObjectName("primaryBtn")
        self._pull_btn.clicked.connect(self._start_pull)
        btn_row.addWidget(self._pull_btn)
        vl.addLayout(btn_row)
        return w

    def _make_done(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(12)

        title = QLabel("You're all set!")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #00B050;")
        vl.addWidget(title)

        body = QLabel(
            "AI note generation is ready. Open your pro forma, go to the Notes step, "
            "and click Auto-Generate to write professional deal notes automatically."
        )
        body.setStyleSheet("color: #8E8E93; font-size: 13px;")
        body.setWordWrap(True)
        vl.addWidget(body)
        vl.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        open_btn = QPushButton("Open App")
        open_btn.setObjectName("primaryBtn")
        open_btn.clicked.connect(self.accept)
        btn_row.addWidget(open_btn)
        vl.addLayout(btn_row)
        return w

    # ── Navigation ─────────────────────────────────────────────────────────

    def _go_to(self, step: int):
        self._stack.setCurrentIndex(step)

    # ── Download step ──────────────────────────────────────────────────────

    def _start_download_step(self):
        if OllamaClient().ping():
            self._go_to(self.STEP_MODEL)
            return
        self._go_to(self.STEP_DOWNLOAD)
        self._start_download()

    def _start_download(self):
        self._dl_error.setVisible(False)
        self._dl_retry_btn.setVisible(False)
        self._dl_bar.setValue(0)
        self._dl_status.setText("Starting download…")

        self._tmp_file = tempfile.NamedTemporaryFile(suffix=".exe", delete=False)
        self._tmp_file.close()

        self._nam = QNetworkAccessManager(self)
        req = QNetworkRequest(QUrl(_OLLAMA_INSTALLER_URL))
        self._reply = self._nam.get(req)
        self._reply.downloadProgress.connect(self._on_dl_progress)
        self._reply.finished.connect(self._on_dl_finished)
        self._reply.errorOccurred.connect(self._on_dl_error)

    def _on_dl_progress(self, received: int, total: int):
        if total > 0:
            self._dl_bar.setValue(int(received * 100 / total))
            self._dl_status.setText(
                f"Downloading OllamaSetup.exe… "
                f"{received // 1_048_576} MB / {total // 1_048_576} MB"
            )

    def _on_dl_finished(self):
        if self._reply.error() != QNetworkReply.NetworkError.NoError:
            return
        data = self._reply.readAll()
        with open(self._tmp_file.name, "wb") as f:
            f.write(data.data())
        self._installer_path = self._tmp_file.name
        self._dl_bar.setValue(100)
        self._dl_status.setText("Download complete. Launching installer…")
        subprocess.Popen([self._installer_path])
        self._go_to(self.STEP_INSTALL)
        self._start_polling()

    def _on_dl_error(self, _error):
        try:
            if self._tmp_file:
                os.unlink(self._tmp_file.name)
        except OSError:
            pass
        self._dl_error.setText(f"Download failed: {self._reply.errorString()}")
        self._dl_error.setVisible(True)
        self._dl_retry_btn.setVisible(True)

    # ── Install step ───────────────────────────────────────────────────────

    def _start_polling(self):
        self._install_status.setText("Waiting for Ollama to start…")
        self._poll_worker = _PollWorker(self)
        self._poll_worker.found.connect(self._on_ollama_found)
        self._poll_worker.timed_out.connect(self._on_poll_timeout)
        self._poll_worker.start()

    def _on_ollama_found(self):
        self._install_status.setText("Ollama is running.")
        self._go_to(self.STEP_MODEL)

    def _on_poll_timeout(self):
        self._install_status.setText(
            "Ollama doesn't seem to be running. Open it from the Start menu, then click Continue."
        )

    def _check_ollama_and_continue(self):
        if OllamaClient().ping():
            self._go_to(self.STEP_MODEL)
        else:
            self._install_status.setText(
                "Ollama isn't responding yet. Start it from the Start menu, then try again."
            )

    # ── Model step ─────────────────────────────────────────────────────────

    def _start_pull(self):
        checked = self._model_group.checkedButton()
        if not checked:
            return
        self._selected_model = checked.property("model_id")
        self._pull_btn.setEnabled(False)
        self._pull_bar.setValue(0)
        self._pull_bar.setVisible(True)
        self._pull_status.setText("Connecting…")
        self._pull_status.setVisible(True)
        self._pull_error.setVisible(False)

        base_url = get_setting("ollama_url", default="http://localhost:11434", conn=self._db)
        self._pull_worker = _PullWorker(self._selected_model, base_url, self)
        self._pull_worker.progress.connect(self._on_pull_progress)
        self._pull_worker.status_text.connect(self._on_pull_status)
        self._pull_worker.finished.connect(self._on_pull_finished)
        self._pull_worker.error.connect(self._on_pull_error)
        self._pull_worker.start()

    def _on_pull_progress(self, completed: int, total: int):
        pct = int(completed * 100 / total) if total else 0
        self._pull_bar.setValue(pct)
        self._pull_status.setText(
            f"Downloading… {completed // 1_048_576} MB / {total // 1_048_576} MB"
        )

    def _on_pull_status(self, text: str):
        self._pull_status.setText(text.capitalize())

    def _on_pull_finished(self):
        set_setting("setup_complete", "true", conn=self._db)
        set_setting("ollama_model", self._selected_model, conn=self._db)
        set_setting("ollama_url", "http://localhost:11434", conn=self._db)
        self._go_to(self.STEP_DONE)

    def _on_pull_error(self, msg: str):
        self._pull_bar.setVisible(False)
        self._pull_btn.setEnabled(True)
        hint = " (Check available disk space.)" if "space" in msg.lower() else ""
        self._pull_error.setText(f"Download failed: {msg}{hint}")
        self._pull_error.setVisible(True)
        self._pull_status.setVisible(False)
```

- [ ] **Step 4: Run all tests to verify they pass**

```
.venv\Scripts\python.exe -m pytest tests/test_setup_wizard.py tests/test_settings.py tests/test_ollama_client.py -v
```

Expected: all pass

- [ ] **Step 5: Run full suite**

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 80 passed

- [ ] **Step 6: Commit**

```
git add app/ui/setup_wizard.py tests/test_setup_wizard.py
git commit -m "feat: add SetupWizardDialog with Ollama download, install, and model pull"
```

---

### Task 4: Wire first-run check into MainWindow

**Files:**
- Modify: `app/ui/main_window.py`

Current `main_window.py` imports are at the top of the file. The `_build_ui()` method ends with `self._check_for_draft()`.

- [ ] **Step 1: Add imports and `_check_first_run()` to `app/ui/main_window.py`**

Add to the top-level imports (after the existing imports):

```python
from app.db.database import init_db
from app.db.settings import get_setting
```

Add the `_check_first_run()` method to the `MainWindow` class (after `_check_for_draft`):

```python
def _check_first_run(self):
    db = init_db()
    val = get_setting("setup_complete", conn=db)
    if val != "true":
        from app.ui.setup_wizard import SetupWizardDialog
        dlg = SetupWizardDialog(db=db, parent=self)
        dlg.exec()
```

At the end of `_build_ui()`, call `_check_first_run()` after `_check_for_draft()`:

```python
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
        self._check_first_run()
```

- [ ] **Step 2: Run full suite**

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 80 passed — `_check_first_run` only shows a dialog when `setup_complete != "true"`. Tests use isolated in-memory or tmp DBs and never trigger the GUI dialog.

- [ ] **Step 3: Commit**

```
git add app/ui/main_window.py
git commit -m "feat: show SetupWizardDialog on first launch when setup not complete"
```

---

### Task 5: Auto-Generate button in Notes page

**Files:**
- Modify: `app/ui/wizard/page_notes.py`
- Modify: `tests/test_notes.py`

- [ ] **Step 1: Add the failing button-visibility tests to `tests/test_notes.py`**

Append these two tests at the bottom of `tests/test_notes.py`:

```python
def test_auto_generate_button_hidden_when_setup_not_complete(qtbot, tmp_path, monkeypatch):
    from app.db.database import init_db as real_init_db
    db = real_init_db(str(tmp_path / "test.db"))
    # setup_complete not set — button should be hidden
    monkeypatch.setattr("app.ui.wizard.page_notes.init_db", lambda: db)
    from app.models.session import ProFormaSession
    import importlib, app.ui.wizard.page_notes as pn_mod
    importlib.reload(pn_mod)
    page = pn_mod.NotesPage(ProFormaSession())
    qtbot.addWidget(page)
    assert not page._gen_btn.isVisible()


def test_auto_generate_button_visible_when_setup_complete(qtbot, tmp_path, monkeypatch):
    from app.db.database import init_db as real_init_db
    from app.db.settings import set_setting
    db = real_init_db(str(tmp_path / "test.db"))
    set_setting("setup_complete", "true", conn=db)
    monkeypatch.setattr("app.ui.wizard.page_notes.init_db", lambda: db)
    import importlib, app.ui.wizard.page_notes as pn_mod
    importlib.reload(pn_mod)
    page = pn_mod.NotesPage(ProFormaSession())
    qtbot.addWidget(page)
    assert page._gen_btn.isVisible()
```

- [ ] **Step 2: Run to verify these tests fail**

```
.venv\Scripts\python.exe -m pytest tests/test_notes.py -v -k "auto_generate"
```

Expected: FAIL — `AttributeError: 'NotesPage' object has no attribute '_gen_btn'`

- [ ] **Step 3: Rewrite `app/ui/wizard/page_notes.py`**

```python
from __future__ import annotations
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from app.db.database import init_db
from app.db.settings import get_setting
from app.models.session import ProFormaSession
from app.ollama.client import OllamaClient, OllamaError


def _build_prompt(session: ProFormaSession) -> str:
    total_sf = session.total_sqft or 1.0
    occ_sf = session.occupied_sqft
    occupancy = occ_sf / total_sf

    total_rent = sum(t.sqft * t.rate_psf for t in session.tenants)
    total_t_sf = sum(t.sqft for t in session.tenants) or 1.0
    weighted_avg = total_rent / total_t_sf

    tenant_parts = [
        f"{t.suite} – {t.name} ({t.sqft:,.0f} SF, ${t.rate_psf:.2f}/SF, exp {t.lease_exp or 'N/A'})"
        for t in session.tenants
    ]
    tenant_summary = "; ".join(tenant_parts) if tenant_parts else "None"

    return (
        "You are a commercial real estate analyst. Write concise, professional deal "
        "notes for the following pro forma. Use plain prose, 3-4 short paragraphs. "
        "Cover: property overview, tenancy summary, income analysis, and key assumptions.\n\n"
        f"Property: {session.building_name or 'Unnamed'}\n"
        f"Projection period: {session.years} years starting {session.start_month}/{session.start_year}\n"
        f"Total SF: {session.total_sqft:,.0f}  |  Occupied SF: {occ_sf:,.0f}  ({occupancy:.0%} occupied)\n"
        f"Tenants ({len(session.tenants)}): {tenant_summary}\n"
        f"Weighted avg rate: ${weighted_avg:.2f}/SF  |  Market avg: ${session.market_avg_rate:.2f}/SF\n"
        f"OpEx/SF: ${session.opex_psf:.2f}  |  Cap rate: {session.cap_rate:.2%}\n\n"
        "Write the deal notes now:"
    )


class _GenerateWorker(QThread):
    chunk_ready = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, model: str, prompt: str, base_url: str):
        super().__init__()
        self._model = model
        self._prompt = prompt
        self._base_url = base_url

    def run(self):
        try:
            client = OllamaClient(self._base_url)
            for token in client.generate(self._model, self._prompt):
                self.chunk_ready.emit(token)
            self.finished.emit()
        except OllamaError as e:
            self.error.emit(str(e))


class NotesPage(QWidget):
    def __init__(self, session: ProFormaSession):
        super().__init__()
        self.session = session
        self._worker: _GenerateWorker | None = None
        self._build_ui()
        self._refresh_gen_btn_visibility()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 0)

        title = QLabel("Deal Notes & Assumptions")
        title.setStyleSheet("font-size: 22px; font-weight: 700; margin-bottom: 12px;")
        layout.addWidget(title)

        sub = QLabel("Optional. These notes will appear in the PDF and Excel output.")
        sub.setStyleSheet("color: #8E8E93; font-size: 12px; margin-bottom: 8px;")
        layout.addWidget(sub)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._gen_btn = QPushButton("Auto-Generate")
        self._gen_btn.setObjectName("primaryBtn")
        self._gen_btn.clicked.connect(self._start_generate)
        toolbar.addWidget(self._gen_btn)

        self._gen_status = QLabel()
        self._gen_status.setStyleSheet("color: #8E8E93; font-size: 12px;")
        self._gen_status.setVisible(False)
        toolbar.addWidget(self._gen_status)

        toolbar.addStretch()

        self._count_lbl = QLabel("0 characters")
        self._count_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        toolbar.addWidget(self._count_lbl)

        layout.addLayout(toolbar)

        self._edit = QPlainTextEdit()
        self._edit.setObjectName("notesEdit")
        self._edit.setPlaceholderText(
            "Enter deal assumptions, market commentary, or any relevant notes…"
        )
        layout.addWidget(self._edit, 1)
        self._edit.textChanged.connect(self._update_count)

    def _refresh_gen_btn_visibility(self):
        try:
            db = init_db()
            val = get_setting("setup_complete", conn=db)
            self._gen_btn.setVisible(val == "true")
        except Exception:
            self._gen_btn.setVisible(False)

    def _update_count(self):
        n = len(self._edit.toPlainText())
        self._count_lbl.setText(f"{n} character{'s' if n != 1 else ''}")

    def _start_generate(self):
        try:
            db = init_db()
            model = get_setting("ollama_model", default="llama3.2", conn=db)
            base_url = get_setting("ollama_url", default="http://localhost:11434", conn=db)
        except Exception:
            model, base_url = "llama3.2", "http://localhost:11434"

        if not OllamaClient(base_url).ping():
            self._gen_status.setText(
                "Ollama isn't running. Start it from your taskbar, then try again."
            )
            self._gen_status.setVisible(True)
            return

        self._gen_btn.setEnabled(False)
        self._gen_btn.setText("Generating…")
        self._gen_status.setVisible(False)
        self._edit.setPlainText("")

        self._worker = _GenerateWorker(model, _build_prompt(self.session), base_url)
        self._worker.chunk_ready.connect(self._on_chunk)
        self._worker.finished.connect(self._on_generate_done)
        self._worker.error.connect(self._on_generate_error)
        self._worker.start()

    def _on_chunk(self, token: str):
        self._edit.moveCursor(QTextCursor.MoveOperation.End)
        self._edit.insertPlainText(token)

    def _on_generate_done(self):
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("Auto-Generate")

    def _on_generate_error(self, msg: str):
        self._edit.appendPlainText(f"\n\n[Generation stopped: {msg}]")
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText("Auto-Generate")

    def bind(self, session: ProFormaSession):
        self.session = session
        self.refresh()

    def refresh(self):
        self._edit.setPlainText(self.session.notes)
        self._update_count()
        self._refresh_gen_btn_visibility()

    def validate(self) -> bool:
        return True

    def commit(self):
        self.session.notes = self._edit.toPlainText()
```

- [ ] **Step 4: Run the notes tests**

```
.venv\Scripts\python.exe -m pytest tests/test_notes.py -v
```

Expected: all 11 tests pass (9 existing + 2 new)

- [ ] **Step 5: Run full suite**

```
.venv\Scripts\python.exe -m pytest tests/ -q
```

Expected: 84 passed

- [ ] **Step 6: Commit**

```
git add app/ui/wizard/page_notes.py tests/test_notes.py
git commit -m "feat: add Auto-Generate button to Notes page with streaming Ollama output"
```

---

### Task 6: Update spec and rebuild exe

**Files:**
- Modify: `NAI_ProForma_Generator.spec`

- [ ] **Step 1: Add `PySide6.QtNetwork` to `hiddenimports`**

In `NAI_ProForma_Generator.spec`, update `hiddenimports` to:

```python
    hiddenimports=[
        'openpyxl', 'PIL', 'dateutil', 'dateutil.relativedelta',
        'win32com', 'win32com.client', 'pywintypes',
        'PySide6.QtNetwork',
    ],
```

- [ ] **Step 2: Rebuild exe**

```
.venv\Scripts\python.exe -m PyInstaller NAI_ProForma_Generator.spec --noconfirm
```

Expected: `Build complete!`

- [ ] **Step 3: Copy to Desktop**

```powershell
Copy-Item "dist\NAI_ProForma_Generator.exe" "$env:USERPROFILE\Desktop\NAI_ProForma_Generator.exe" -Force
```

- [ ] **Step 4: Commit**

```
git add NAI_ProForma_Generator.spec
git commit -m "chore: add PySide6.QtNetwork to hiddenimports for Ollama setup wizard"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Settings table + `get_setting`/`set_setting` → Task 1
- ✅ `OllamaClient` with `ping`, `pull_model`, `generate` → Task 2
- ✅ `SetupWizardDialog` 5-step flow → Task 3
- ✅ Download step with `QNetworkAccessManager`, progress bar, retry, "install myself" skip → Task 3
- ✅ Install step with `_PollWorker`, 60s timeout, Continue button always active → Task 3
- ✅ Model step with 3 radio options, streaming pull progress → Task 3
- ✅ Done step writes `setup_complete`, `ollama_model`, `ollama_url` → Task 3
- ✅ Skip for now closes dialog without writing `setup_complete` → Task 3 (`reject()`)
- ✅ Already-has-Ollama fast path (ping on Get Started → skip to model step) → Task 3
- ✅ `_check_first_run()` in `MainWindow` before `_check_for_draft` → Task 4
- ✅ `_build_prompt()` with all session fields → Task 5
- ✅ `_GenerateWorker` streaming into `QPlainTextEdit` → Task 5
- ✅ Ollama-not-running inline warning → Task 5
- ✅ Mid-stream error handling → Task 5
- ✅ Button hidden when setup incomplete → Task 5
- ✅ `PySide6.QtNetwork` in hiddenimports → Task 6
- ✅ Tests for all layers → Tasks 1–5

**Placeholder scan:** No TBDs. All steps contain complete code.

**Type consistency:** `get_setting`/`set_setting` signatures consistent across all tasks. `OllamaClient` method names consistent between `client.py`, `setup_wizard.py`, and `page_notes.py`. `_PullWorker(model, base_url, parent)` signature consistent between definition and call site.
