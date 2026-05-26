# NAI Pro Forma Generator — UI Modernisation Design

**Goal:** Overhaul the visual design of the existing PySide6 desktop app to an Apple-inspired aesthetic: clean, minimal, generous whitespace, refined typography, no dark chrome.

**Architecture:** All visual changes are contained to `app/ui/styles.qss` (palette and component rules), `app/ui/main_window.py` (sidebar → top bar), `app/ui/dashboard.py` (segmented control tabs, table refinement), and `app/ui/wizard/wizard.py` (dot progress indicator, nav bar). Individual wizard pages get minor spacing tweaks only. No data model, database, or logic changes.

**Tech Stack:** PySide6 QSS, Python widget layout code

---

## Design Principles

- **White and near-white everywhere.** No dark surfaces except the NAI red accent.
- **Depth from shadow, not border.** Cards use `box-shadow` equivalents; hard 1px borders are replaced by subtle separators (`#E5E5EA`).
- **Content is the design.** No decorative elements, no gradients, no icons beyond what already exists.
- **Red is intentional.** NAI red (`#C8102E`) appears only on the primary action button, active/focus states, and the danger variant. Secondary buttons are light gray with dark text.
- **Consistent radius.** `12px` on cards and modals, `10px` on buttons and inputs, `8px` on small controls.

---

## Color System

| Token | Value | Usage |
|---|---|---|
| `bg-grouped` | `#F2F2F7` | App background, alternating table rows, secondary button fill |
| `bg-surface` | `#FFFFFF` | Cards, top bar, table, wizard pages |
| `label-primary` | `#1C1C1E` | Body text, button text, table cell text |
| `label-secondary` | `#8E8E93` | Captions, table column headers, step label |
| `label-tertiary` | `#AEAEB2` | Empty state messages, placeholders |
| `separator` | `#E5E5EA` | Dividers, card borders, input borders |
| `accent` | `#C8102E` | Primary button, focus ring, danger text |
| `accent-hover` | `#A00C24` | Primary button hover |
| `accent-light` | `#FFF1F2` | Selected table row, danger button fill |
| `fill-control` | `#F2F2F7` | Input backgrounds, secondary button, segmented control track |

---

## Typography

Font stack: `"SF Pro Display", "Segoe UI", system-ui, sans-serif`
Base size: `14px` (up from 13px)

| Role | Size | Weight | Color |
|---|---|---|---|
| Page title | `22px` | 700 | `#1C1C1E` |
| Section header | `17px` | 600 | `#1C1C1E` |
| Body | `14px` | 400 | `#1C1C1E` |
| Caption / label | `11px` | 500 | `#8E8E93` |
| Button | `14px` | 600 | — |

---

## Component System

### Buttons

| Variant | Background | Text | Border | Radius | Padding |
|---|---|---|---|---|---|
| `primaryBtn` | `#C8102E` | `#FFFFFF` | none | `10px` | `10px 24px` |
| `secondaryBtn` | `#F2F2F7` | `#1C1C1E` | none | `10px` | `10px 24px` |
| `dangerBtn` | `#FFF1F2` | `#C8102E` | `1px solid #C8102E` | `10px` | `8px 16px` |
| `tableBtn` | `#F2F2F7` | `#1C1C1E` | none | `6px` | `4px 12px` |

### Form Inputs (QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QDateEdit)

- Background: `#F2F2F7`
- Border: none (no border at rest)
- Border-radius: `10px`
- Padding: `8px 12px`
- Focus: `2px solid #C8102E` ring (via `border: 2px solid #C8102E`)
- Invalid: `#FFF1F2` background, `2px solid #C8102E` border

### Cards (`#card` object name)

- Background: `#FFFFFF`
- Border: `1px solid #E5E5EA`
- Border-radius: `12px`
- No box-shadow in QSS (PySide6 doesn't support it; the border+white-on-gray achieves equivalent depth)

### QGroupBox

- Border: `1px solid #E5E5EA`
- Border-radius: `10px`
- Title: `11px`, `500` weight, `#8E8E93`, uppercase

### Tables (QTableWidget)

- Background: `#FFFFFF`
- Gridline color: `#F0F0F0`
- Header background: `#F9F9F9`
- Header text: `11px`, `500` weight, `#8E8E93`
- Header border: none (bottom `1px solid #E5E5EA` only)
- Row height: implied by padding — `8px` vertical cell padding
- Alternating row: `#F9F9F9` (very subtle)
- Selected item: `#FFF1F2` background, `#1C1C1E` text
- Hover: handled via selection only (QSS has no hover for table items)

### Segmented Control (Dashboard tabs)

Implemented as a `QTabWidget` with custom QSS:
- Tab bar background: `#F2F2F7`, `border-radius: 10px`, `padding: 3px`
- Active tab: `#FFFFFF` background, `border-radius: 8px`, `1px solid #E5E5EA`
- Inactive tab: transparent background, `#8E8E93` text
- Active tab text: `#1C1C1E`, `font-weight: 600`

---

## Navigation: Top Bar (replaces sidebar)

**Remove:** `app/ui/main_window.py` `_make_sidebar()` and the `#sidebar` widget entirely. Remove the `QHBoxLayout` root layout that placed sidebar + stack side by side.

**Add:** A `QWidget` top bar (`objectName: "topBar"`) above the `QStackedWidget`:

```
┌─────────────────────────────────────────────────────────┐
│  [NAI logo SVG 140×30]  Pro Forma Generator    [+ New]  │  56px tall
└─────────────────────────────────────────────────────────┘
```

- Background: `#FFFFFF`
- Bottom border: `1px solid #E5E5EA`
- Left: `QSvgWidget` of `assets/nai_logo.svg` at 140×30, then a `QLabel("Pro Forma Generator")` in `#8E8E93`, `14px`
- Right: `"+ New Pro Forma"` `primaryBtn`
- The top bar is **always visible** — on both Dashboard and Wizard views

**Main layout** changes from `QHBoxLayout` (sidebar | stack) to `QVBoxLayout` (topBar / stack).

**`_set_active` and `_nav_btn` helpers are deleted** — no longer needed.

**`show_dashboard` and `show_wizard`** keep their logic but drop the `_set_active` calls.

---

## Dashboard Changes (`app/ui/dashboard.py`)

### Stats bar
Remove the separate stats bar `QWidget`. Move the count label ("3 pro formas saved") to a `QLabel` directly above the tab widget, in `#8E8E93` at `12px`. Update it inside `_refresh_runs`.

### Tab widget styling
The `QTabWidget` picks up the new segmented-control QSS automatically from `styles.qss`. No Python changes needed beyond the stats label move.

### Table headers
The `QHeaderView::section` rule in QSS changes from dark (`#4A4A4A` background, white text) to light (`#F9F9F9` background, `#8E8E93` text, `11px`, `500` weight).

### Action buttons
`tableBtn` object name kept. QSS changes from dark gray to `#F2F2F7` background with `#1C1C1E` text. The "Delete" / `dangerBtn` changes from outline-red to filled light-red background.

---

## Wizard Changes (`app/ui/wizard/wizard.py`)

### Progress indicator (replaces step label)
Remove `self._step_lbl` (`QLabel`, objectName `stepLabel`).

Add a `_DotIndicator(QWidget)` inner class in `wizard.py`:

```python
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
        from PySide6.QtGui import QPainter, QColor, QBrush
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(self._count):
            color = QColor("#C8102E") if i == self._active else QColor("#E5E5EA")
            p.setBrush(QBrush(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(i * 18 + 4, 4, 10, 10)
        p.end()
```

`self._dots = _DotIndicator(4)` is added to the nav bar in place of `self._step_lbl`.
`_update_nav()` calls `self._dots.set_step(idx)` instead of setting label text.

### Nav bar
- Remove the `QFrame` separator line — replaced by `border-top: 1px solid #E5E5EA` on the nav bar's QWidget
- Nav bar background: `#FFFFFF` (currently inherits gray)
- Back button: change `objectName` to `"ghostBtn"` — text-only, no background, `#8E8E93` text (looks like a link). Text stays "Cancel" / "Back".
- Next button: stays `primaryBtn`, text stays "Next" / "Generate Pro Forma"

New QSS rule for `ghostBtn`:
```qss
QPushButton#ghostBtn { background: transparent; color: #8E8E93; border: none; padding: 10px 16px; font-size: 14px; }
QPushButton#ghostBtn:hover { color: #1C1C1E; }
```

---

## Wizard Page Tweaks (minor, no structural changes)

These changes are purely cosmetic and happen via QSS + small inline style overrides:

**All pages:**
- Page `setContentsMargins(32, 28, 32, 0)` — increase from `24, 24, 24, 0` for more breathing room
- Section heading labels: add `text-transform: uppercase` equivalent by setting font size to `11px`, weight `500`, color `#8E8E93` (requires Python-side font/color changes since QSS uppercase isn't supported in Qt)

**`page_building.py`:**
- `setContentsMargins(32, 28, 32, 0)` — increase from `(24, 24, 24, 0)`
- The scrollable form card keeps its `#card` objectName
- Form row spacing: increase to `16px` via `layout.setSpacing(16)` where currently `14`

**`page_tenants.py`:**
- `setContentsMargins(32, 28, 32, 0)` — increase from `(24, 24, 24, 0)`

**`page_notes.py`:**
- `setContentsMargins(32, 28, 32, 0)` — increase from `(24, 24, 24, 0)`
- `self._edit.setObjectName("notesEdit")` — add this call after constructing the `QPlainTextEdit`; enables the QSS rule: `#F2F2F7` background, `10px` radius, no border at rest, `2px solid #C8102E` on focus

**`page_review.py`:**
- The two info cards (Building / Tenants) get `padding: 20px` (up from 16px)
- IRR `QGroupBox` picks up the new group box QSS automatically

---

## Files Modified

| File | Change |
|---|---|
| `app/ui/styles.qss` | Complete rewrite — new color system, all component rules |
| `app/ui/main_window.py` | Remove sidebar, add top bar, change root layout to QVBoxLayout |
| `app/ui/dashboard.py` | Remove stats bar widget, add inline count label above tabs |
| `app/ui/wizard/wizard.py` | Replace step label with `_DotIndicator`, update nav bar styling |
| `app/ui/wizard/page_building.py` | Increase margins to `32, 28` |
| `app/ui/wizard/page_tenants.py` | Increase margins to `32, 28` |
| `app/ui/wizard/page_notes.py` | Add `objectName("notesEdit")` to `QPlainTextEdit` |
| `app/ui/wizard/page_review.py` | Increase card padding to `20px` |

---

## What Does NOT Change

- No data model, database, or logic changes
- No layout restructuring within wizard pages (field order, groupings, etc.)
- No new features or interactions
- No changes to PDF or Excel output styling
- No changes to `assets/` (logo files stay the same)
- All existing `objectName` values are preserved except `stepLabel` (removed) and `secondaryBtn` on the Back button (changed to `ghostBtn`)

---

## Testing

Visual confirmation only — run the app after each task and verify the view looks correct. No automated tests are needed for pure style changes. Existing 70-test suite must continue to pass.
