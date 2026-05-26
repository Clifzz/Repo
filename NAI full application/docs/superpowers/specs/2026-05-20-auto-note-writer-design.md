# Auto Note Writer — Design Spec

**Date:** 2026-05-20  
**Status:** Approved

---

## Goal

Add an AI-powered "Auto-Generate" button to the Notes page that writes professional CRE deal commentary from the live pro forma data, powered by a locally-running Ollama instance. A first-run setup wizard downloads and configures Ollama automatically so the feature works out-of-the-box when the `.exe` is shared.

## Architecture

```
main.py starts
    └─ MainWindow._check_first_run()
           └─ reads settings table in SQLite
                  ├─ setup_complete = false → show SetupWizardDialog (blocks)
                  └─ setup_complete = true  → open dashboard as normal

SetupWizardDialog (5 steps, QDialog)
    Step 1: Welcome
    Step 2: Download OllamaSetup.exe (QNetworkAccessManager + progress bar)
    Step 3: Launch installer, poll localhost:11434 until alive
    Step 4: Pick + pull model (streaming progress bar)
    Step 5: Done — write setup_complete + ollama_model to settings table

Notes page (existing)
    └─ Auto-Generate button (top-right of notes card)
           └─ OllamaClient.generate(prompt)
                  └─ streams response chunks → QThread → QPlainTextEdit
```

## New Files

| File | Responsibility |
|------|---------------|
| `app/ollama/client.py` | Thin HTTP wrapper: `ping()`, `list_models()`, `pull_model()`, `generate()` |
| `app/ollama/__init__.py` | Package marker |
| `app/ui/setup_wizard.py` | 5-step first-run QDialog |
| `app/db/settings.py` | `get_setting()` / `set_setting()` on `settings` table |
| `tests/test_ollama_client.py` | Unit tests for OllamaClient |
| `tests/test_setup_wizard.py` | Tests for first-run detection logic |
| `tests/test_settings.py` | Tests for settings persistence |

## Modified Files

| File | Change |
|------|--------|
| `app/db/database.py` | Add `settings` table migration on `init_db()` |
| `app/ui/main_window.py` | Call `_check_first_run()` after building UI |
| `app/ui/wizard/page_notes.py` | Add Auto-Generate button + streaming display + Ollama status handling |

---

## Setup Wizard — Step Details

### Step 1: Welcome
- NAI logo + heading "Welcome to NAI Pro Forma Generator"
- Body: "This one-time setup installs Ollama, a free local AI engine that runs entirely on your computer. No data leaves your machine."
- Single button: "Get Started" → Step 2
- Small "Skip for now" text link — closes the dialog immediately without writing `setup_complete`; wizard reappears on next launch

### Step 2: Download Ollama
- Auto-detects if Ollama is already running (`ping()` on `localhost:11434`). If yes, skip to Step 4.
- Downloads `https://ollama.com/download/OllamaSetup.exe` to a temp file via `QNetworkAccessManager`
- Shows filename, progress bar (bytes downloaded / total), and download speed
- On network error: inline error message + "Retry" button + "I'll install Ollama myself →" link (skips to Step 3 without downloading)
- Partial downloads deleted on failure

### Step 3: Install
- Launches downloaded installer via `subprocess.Popen([installer_path])`
- Shows spinner + message: "Complete the Ollama installer, then click Continue"
- Polls `GET localhost:11434/api/tags` every 2 seconds
- "Continue" button activates as soon as Ollama responds (or after 60 s timeout with a fallback message: "Ollama doesn't seem to be running. Open it from Start, then click Continue")
- Continue button always available so users can manually trigger re-check

### Step 4: Choose Model
- Three radio options:
  - `llama3.2` — Recommended · ~2 GB · Fast, high quality
  - `mistral` — ~4 GB · More detailed output
  - `phi3` — ~2.3 GB · Very fast, lightweight
- "Download Model" button starts pull via `POST localhost:11434/api/pull` (streaming)
- Progress shown as a progress bar, parsing `{"status":"pulling manifest"}` / `{"completed":N,"total":N}` JSON lines
- On pull error: inline error message + "Retry". If error message contains "space", surface disk space hint.
- Cannot advance until pull reports `{"status":"success"}`

### Step 5: Done
- "You're all set. AI note generation is ready."
- Writes to `settings` table: `setup_complete = "true"`, `ollama_model = <chosen>`, `ollama_url = "http://localhost:11434"`
- "Open App" closes dialog → main window becomes interactive

---

## Settings Table

Schema added in `app/db/database.py` `init_db()`:

```sql
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

`app/db/settings.py` API:
```python
def get_setting(key: str, default: str | None = None, conn=None) -> str | None
def set_setting(key: str, value: str, conn=None) -> None
```

Keys used:
- `setup_complete` — `"true"` or absent
- `ollama_model` — e.g. `"llama3.2"`
- `ollama_url` — e.g. `"http://localhost:11434"`

---

## OllamaClient API (`app/ollama/client.py`)

```python
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434")
    def ping(self) -> bool                          # GET /api/tags, returns True if 200
    def list_models(self) -> list[str]              # GET /api/tags → model names
    def pull_model(self, model: str) -> Iterator[dict]   # POST /api/pull, streams JSON lines
    def generate(self, model: str, prompt: str) -> Iterator[str]  # POST /api/generate, streams response tokens
```

All methods raise `OllamaError(message)` on connection failure or non-200 response.  
`generate()` uses `stream=True`, reads newline-delimited JSON, yields `chunk["response"]` strings.

---

## Notes Page — Auto-Generate UI

**Layout change:** A toolbar row is added above the `QPlainTextEdit`:
```
[ Auto-Generate ]                    [ character count ]
[         QPlainTextEdit (notes)                      ]
```

**Button states:**
- Hidden if `setup_complete` is not `"true"` in settings
- Enabled: normal primary button style
- Generating: text → "Generating…", disabled, spinner `QLabel` shown inline
- Done: re-enabled, spinner hidden

**Streaming flow:**
1. Build prompt from session (see Prompt Design below)
2. Clear existing notes text
3. Dispatch `GenerateWorker(QThread)` with `OllamaClient` + prompt
4. Worker emits `chunk_ready(str)` → main thread appends to `QPlainTextEdit`
5. Worker emits `finished()` → re-enable button
6. Worker emits `error(str)` → append `"\n\n[Generation stopped: {error}]"`, re-enable button

**Ollama not reachable at generate-time:**  
Inline warning replaces spinner: "Ollama isn't running. Start it from your taskbar, then try again." No re-download needed.

---

## Prompt Design

```
You are a commercial real estate analyst. Write concise, professional deal
notes for the following pro forma. Use plain prose, 3-4 short paragraphs.
Cover: property overview, tenancy summary, income analysis, and key assumptions.

Property: {building_name}
Projection period: {years} years starting {start_month}/{start_year}
Total SF: {total_sqft:,}  |  Occupied SF: {occupied_sqft:,}  ({occupancy:.0%} occupied)
Tenants ({n}): {tenant_summary}
  e.g. "Suite 100 – Acme Corp (2,400 SF, $28.50/SF, exp 06-2027), ..."
Weighted avg rate: ${weighted_avg_rate:.2f}/SF  |  Market avg: ${market_avg_rate:.2f}/SF
OpEx/SF: ${opex_psf:.2f}  |  OpEx growth: {opex_growth:.1%}
Cap rate: {cap_rate:.2%}{irr_line}

Write the deal notes now:
```

`{irr_line}` is omitted if no IRR data is available. If IRR data exists:  
`\nIRR: {irr:.2%}  |  NPV: ${npv:,.0f}  |  Exit value: ${exit_value:,.0f}`

---

## First-Run Detection Flow (`MainWindow._check_first_run`)

```python
def _check_first_run(self):
    db = init_db()
    val = get_setting("setup_complete", conn=db)
    if val != "true":
        dlg = SetupWizardDialog(db=db, parent=self)
        dlg.exec()
```

Called at the end of `_build_ui()`, before `_check_for_draft()`. `MainWindow` opens its own short-lived DB connection for this check — the `DashboardView` manages its own connection separately.

---

## Error Handling Summary

| Scenario | Behaviour |
|----------|-----------|
| Download fails | Inline error + Retry + "install myself" skip link |
| Ollama doesn't start in 60 s | Timeout message, Continue button stays available |
| Model pull fails | Inline error + Retry + disk space hint if relevant |
| Ollama stopped after setup | Inline warning in notes page, no re-download |
| Generation error mid-stream | Partial text kept, error appended, button re-enabled |
| Already has Ollama on first run | Steps 2 & 3 auto-skipped, goes straight to model picker |

---

## Testing

- `test_settings.py` — get/set round-trip, missing key returns default, multiple keys independent
- `test_ollama_client.py` — `ping()` returns False on connection refused; `generate()` yields tokens from mocked streaming response; `OllamaError` raised on non-200
- `test_setup_wizard.py` — `_check_first_run()` does not show dialog when `setup_complete = "true"`; shows dialog when key absent
- Notes page tests — Auto-Generate button hidden when setup incomplete; visible when complete (widget-level check)
