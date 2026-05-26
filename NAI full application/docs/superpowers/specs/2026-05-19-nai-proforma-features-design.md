# NAI Pro Forma Generator — Feature Additions Design

**Goal:** Add four features to the existing PySide6 desktop app: deal templates, deal notes, IRR/NPV return analysis, and one-click email delivery.

**Architecture:** All features extend the existing session model, SQLite database, wizard, dashboard, and PDF/Excel outputs. No new major subsystems; each feature is a targeted addition to existing modules.

**Tech Stack:** PySide6, SQLite (via sqlite3), openpyxl, QPdfWriter, win32com (pywin32), Python stdlib (webbrowser, subprocess, itertools)

---

## Feature 1: Templates

### Data

A new `templates` table in the existing `%APPDATA%/NAI_ProForma/runs.db` SQLite database:

```sql
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_name TEXT NOT NULL,
    building_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    inputs_json TEXT NOT NULL
)
```

New functions in `app/db/database.py`:
- `save_template(name: str, session: ProFormaSession) -> int`
- `list_templates() -> list[dict]` — returns `id, template_name, building_name, created_at`
- `get_template(template_id: int) -> dict | None` — returns `inputs_json`
- `delete_template(template_id: int) -> None`

### UI

The Dashboard (`app/ui/dashboard.py`) gets a `QTabWidget` with two tabs: **Saved Runs** (existing table) and **Templates** (new table). The Templates tab matches the Saved Runs layout with columns: Template Name, Building, Created, and a Delete button per row. Clicking a template row calls `on_edit(session)` with the session reconstructed from `inputs_json` — identical to the existing edit flow.

Each row in the Saved Runs tab gets an additional **"Save as Template"** button. Clicking it shows a `QInputDialog` prompting for a template name (pre-filled with the building name), then calls `save_template`.

### Behaviour

- Templates are immutable once saved. To update a template: open it, modify in wizard, save as template again (with same or new name).
- Duplicate template names are allowed (user's responsibility).
- Templates are not affected by deleting a saved run.

---

## Feature 2: Deal Notes

### Data

`ProFormaSession` gains one new field:

```python
notes: str = ""
```

`to_json` and `from_json` are updated to include `notes`. Existing saved runs without `notes` in their JSON will default to `""` on load (handled by `from_json`'s `d.pop("notes", "")` pattern).

### UI

A new **Notes** wizard step is added between Tenants and Review. File: `app/ui/wizard/page_notes.py`.

The page contains:
- A title label: "Deal Notes & Assumptions"
- A `QPlainTextEdit` (multi-line, no character limit enforced, but a live character count label shown below)
- `validate()` always returns `True` (blank is fine)
- `commit()` writes `self._edit.toPlainText()` to `session.notes`
- `bind(session)` and `refresh()` load `session.notes` into the text editor

Wizard step order: Building (0) → Tenants (1) → Notes (2) → Review (3).

### Output

**PDF (`app/excel/pdf_writer.py`):** A "Deal Notes & Assumptions" section is appended after Cap Rate Sensitivity if `session.notes` is non-empty. The text is rendered in a `<pre>`-style block preserving line breaks.

**Excel (`app/excel/writer.py`):** A new `Notes` sheet is added to every workbook. If `session.notes` is empty the sheet contains a placeholder row ("No notes entered"). Column A, row 1 is the header; row 2 onwards contains the notes text wrapped across rows.

---

## Feature 3: IRR / NPV Return Analysis

### Data

Three new fields on `ProFormaSession` (all optional, serialized via `to_json`/`from_json`):

```python
purchase_price: float = 0.0      # 0.0 = "use Y1 value"
exit_cap_rate: float = 0.0       # 0.0 = "use session cap_rate"
discount_rate: float = 0.08      # default 8%
```

### Calculation

New function `calculate_irr_npv(session, result) -> dict` in `app/logic/calculator.py`:

- `effective_purchase = purchase_price if purchase_price > 0 else result["values"][0]`
- `effective_exit_cap = exit_cap_rate if exit_cap_rate > 0 else session.cap_rate`
- `exit_value = result["nois"][-1] / effective_exit_cap`
- Cash flows: `[-effective_purchase] + result["nois"][:-1] + [result["nois"][-1] + exit_value]`
- IRR: Newton's method iteration (max 1000 steps, tolerance 1e-7), returns `None` if non-convergent
- NPV: `sum(cf / (1 + discount_rate)**t for t, cf in enumerate(cash_flows))`

Returns: `{"irr": float | None, "npv": float, "exit_value": float, "effective_purchase": float}`

### UI

The Review page (`app/ui/wizard/page_review.py`) gets a `QGroupBox` labeled "Return Analysis (optional)" below the Y1 metrics, containing three `QDoubleSpinBox` inputs:
- Purchase Price ($) — auto-filled from Y1 value when `refresh()` is called, editable
- Exit Cap Rate (%) — auto-filled from `session.cap_rate`, editable
- Discount Rate (%) — defaults to 8%, editable

Below the inputs, two read-only labels show the computed IRR (%) and NPV ($), updated live as inputs change (via `valueChanged` signals). If IRR does not converge, shows "IRR: N/A".

`commit()` writes the three inputs back to `session` before saving/generating.

### Output

**PDF:** A "Return Analysis" section is added after Cap Rate Sensitivity showing Purchase Price, Exit Cap Rate, Exit Value, IRR, and NPV.

**Excel:** The Inputs sheet gets a "Return Analysis" block with the same five values.

---

## Feature 4: Email Pro Forma

### UI

After a successful generation, an **"Email Pro Forma"** button appears on the Review page (alongside the existing file path row). Clicking it opens a small `QDialog` with two buttons: **Open in Outlook** and **Open in Gmail**.

### Outlook Path

Uses `win32com.client` (from `pywin32` package):

```python
import win32com.client
outlook = win32com.client.Dispatch("Outlook.Application")
mail = outlook.CreateItem(0)
mail.Subject = f"Pro Forma — {session.building_name}"
mail.Attachments.Add(pdf_path)
mail.Display()
```

If `win32com` import fails or COM dispatch raises, shows a `QMessageBox.warning` with "Outlook not found or not installed."

### Gmail Path

```python
import webbrowser, urllib.parse
subject = urllib.parse.quote(f"Pro Forma — {session.building_name}")
webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&su={subject}")
```

Copies `pdf_path` to the system clipboard (`QGuiApplication.clipboard().setText(pdf_path)`), then shows a `QMessageBox.information`: *"Gmail opened in your browser. Your PDF path has been copied to the clipboard — click the paperclip icon in Gmail to attach it."*

### Dependencies

`pywin32` added to the project's dependencies. Added to `hiddenimports` in `NAI_ProForma_Generator.spec`:

```python
hiddenimports=['openpyxl', 'dateutil', 'dateutil.relativedelta', 'win32com', 'win32com.client', 'pywintypes'],
```

The email button is only enabled after a successful generation (i.e., `pdf_path` is set). If PDF export was skipped, the Outlook and Gmail buttons show a warning that no PDF is available.

---

## Error Handling

- **Templates:** DB errors surface as `QMessageBox.critical`. Corrupt `inputs_json` in a template is caught in `from_json` and shows a warning; the template row remains deletable.
- **Notes:** No validation. Notes persisted as plain text — no HTML injection risk (rendered in `QPlainTextEdit`, escaped before insertion into HTML for PDF).
- **IRR:** Non-convergence returns `None`, shown as "N/A" in UI and PDF. Division-by-zero in exit value (zero exit cap rate) is guarded.
- **Email:** Both paths wrapped in try/except with user-facing error dialogs. Email button disabled if `pdf_path` is not set.

---

## Testing

- `tests/test_templates.py` — save, list, get, delete; duplicate names; load session from template
- `tests/test_notes.py` — session serialization round-trip with notes; PDF/Excel output contains notes text
- `tests/test_irr_npv.py` — known cash flows with known IRR; NPV at 0% discount = sum of cash flows; non-convergence returns None
- `tests/test_email.py` — mock win32com and webbrowser; verify correct subject, attachment path, clipboard content
