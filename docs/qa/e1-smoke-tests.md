# QA Test Cases — E1 (Windows tray UI)

This document contains **manual smoke test cases** for Epic **E1** (must stories), based on `docs/tdd-windows-tray-app-v1.md`.

## Scope

- **E1.S1 [must]** Tray presence (app runs in system tray)
- **E1.S2 [must]** State visibility (Idle / Recording / Error / Needs_setup)
- **E1.S3 [must]** Manual Start/Stop from tray

## Preconditions

- OS: **Windows**
- The app can be started (e.g., `poetry run python -m callscribe`).
- Optional: ability to temporarily choose an output folder via **Settings…**.

## TC-E1-001 — App appears in system tray

- **Goal**: Verify the app is available without an open window.
- **Steps**:
  - Start the app.
  - Look at the system tray area (and tray overflow) for the Callscribe icon.
- **Expected**:
  - Callscribe icon is present in the system tray.
  - No main window is required for operation.

## TC-E1-002 — Tray menu contains required items

- **Goal**: Verify minimal tray menu structure.
- **Steps**:
  - Right-click (or open) the tray icon menu.
- **Expected**:
  - Menu contains items:
    - **Start recording**
    - **Stop recording**
    - **Open output folder**
    - **Settings…**
    - **Quit**

## TC-E1-003 — First-run: missing output_folder shows Needs_setup and disables Start/Stop

- **Goal**: Verify first-run UX when `output_folder` is not configured.
- **Setup**:
  - Ensure config has **no** `output_folder` set (fresh run or config reset).
- **Steps**:
  - Start the app.
  - Open tray menu.
  - Inspect tooltip/title for state.
- **Expected**:
  - State is **Needs_setup** (or a clear error state with actionable hint).
  - **Start recording** is disabled.
  - **Stop recording** is disabled.
  - **Settings…** is available as the primary path to fix setup.

## TC-E1-004 — Settings… selects output folder and enables Start

- **Goal**: Verify minimal setup flow via folder picker.
- **Setup**:
  - App is in **Needs_setup**.
- **Steps**:
  - Open tray menu → click **Settings…**.
  - Choose a writable folder.
  - Re-open tray menu.
- **Expected**:
  - `output_folder` is saved and persists across app restart.
  - App transitions to **Idle** state.
  - **Start recording** becomes enabled.
  - **Stop recording** remains disabled.

## TC-E1-005 — Idle state: Start enabled, Stop disabled

- **Goal**: Verify menu enable/disable rules in Idle.
- **Setup**:
  - `output_folder` is configured; app is idle.
- **Steps**:
  - Open tray menu.
  - Inspect enabled state of Start/Stop.
  - Inspect tooltip/title.
- **Expected**:
  - Tooltip shows **Idle**.
  - **Start recording** enabled.
  - **Stop recording** disabled.

## TC-E1-006 — Start recording transitions to Recording; Start disabled, Stop enabled

- **Goal**: Verify manual start from tray.
- **Setup**:
  - App is in **Idle** and ready.
- **Steps**:
  - Open tray menu → click **Start recording**.
  - Re-open menu (if it closes) and inspect enabled state.
  - Inspect tooltip/title.
- **Expected**:
  - State becomes **Recording** (tooltip/title reflects Recording).
  - **Start recording** disabled.
  - **Stop recording** enabled.

## TC-E1-007 — Stop recording transitions to Idle; Start enabled, Stop disabled

- **Goal**: Verify manual stop from tray.
- **Setup**:
  - App is in **Recording**.
- **Steps**:
  - Open tray menu → click **Stop recording**.
  - Re-open menu and inspect enabled state.
  - Inspect tooltip/title.
- **Expected**:
  - State returns to **Idle**.
  - **Start recording** enabled.
  - **Stop recording** disabled.

## TC-E1-008 — Open output folder opens configured folder

- **Goal**: Verify “Open output folder” action.
- **Setup**:
  - `output_folder` configured.
- **Steps**:
  - Open tray menu → click **Open output folder**.
- **Expected**:
  - File Explorer opens at the configured output folder.

## TC-E1-009 — Quit exits the app (tray icon disappears)

- **Goal**: Verify quitting from tray.
- **Steps**:
  - Open tray menu → click **Quit**.
- **Expected**:
  - App process exits.
  - Tray icon disappears.

## TC-E1-010 — Quit while Recording stops recording first (no UI freeze)

- **Goal**: Verify the app does not block UI loop and performs a safe stop sequence on quit.
- **Setup**:
  - Start recording (state **Recording**).
- **Steps**:
  - Click **Quit** while recording.
- **Expected**:
  - App initiates stop (no tray UI freeze).
  - App exits after completing stop sequence (or a bounded timeout with fail-safe behavior).

