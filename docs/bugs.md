# Bugs

## Epic E1 — App lifecycle & single-instance

### E1-B1 — Double launch starts two instances

- **Symptom**: starting Callscribe twice results in **two running instances** (two tray icons / two processes).
- **Expected**: single-instance behavior; the second launch should focus/activate the existing instance or exit with a clear message.
- **Notes**: likely requires a single-instance lock (mutex / lockfile + IPC/activation).
- **Automation**: regression covered by `tests/integration/test_app_startup.py`.
- **Status**: fixed (single-instance guard + activation on second launch).

## Epic E2 — Settings UI & dialogs (Tk / pystray integration)

### E2-B1 — Folder picker window becomes unresponsive

- **Symptom**: the **directory selection window opens**, but afterwards **none of its controls work**, including close (X).
- **Expected**: folder picker should be interactive and closable; after selection/cancel, the app should return to tray normally.
- **Observed logs**: tray callback sometimes crashes with `_tkinter.TclError: Разрушительный сбой` when opening Settings (folder picker).
- **Notes**: likely caused by how the dialog is created or the GUI event loop/threading interaction (calling Tk dialogs from pystray win32 message handler thread/context).
- **Mitigation (2026-05)**: Settings dialog runs on a **dedicated single-worker** `ThreadPoolExecutor` via `run_in_executor`, so `wait_window` no longer blocks the asyncio loop; **Open output folder** uses `asyncio.to_thread` for `os.startfile` / `xdg-open`.
- **Status**: can not reproduce (original); tray threading mitigated as above

### Repro logs (Settings… → foldepicker)

```text
An error occurred when calling message handler
Traceback (most recent call last):
  File \"...pystray\\_win32.py\", line 412, in _dispatcher
  ...
  File \"D:\\workspace\\projects\\soft\\callscribe\\src\\callscribe\\__main__.py\", line 34, in _pick_folder
    folder = filedialog.askdirectory(title=\"Callscribe — Select output folder\")
  File \"...\\tkinter\\commondialog.py\", line 45, in show
    s = master.tk.call(self.command, *master._options(self.options))
_tkinter.TclError: Разрушительный сбой
```

### E2-B2 — Settings… window does not open

- **Symptom**: choosing **Settings…** from the tray menu does **nothing** (no window, no clear error in the user-visible surface).
- **Expected**: the combined settings dialog (output folder, loopback, microphone) opens and is interactive.
- **Notes**: may still be Tk / pystray / thread-affinity on Windows despite running the dialog off the asyncio loop (`run_in_executor` + dedicated Tk worker). Track here; fix in branch `feature/e3-audio-capture` (no separate GitHub issue for now).
- **Status**: open

## Epic E3 — Recording quality and runtime

### E3-B1 — Sound stutters or cuts out while recording

- **Symptom**: during an active recording session, **audio breaks up** or **drops** (subjectively: stutter, gaps, or glitching).
- **Expected**: continuous capture matching what the user hears on loopback + mic mix.
- **Notes**: might be **CPU / scheduling / buffer sizing** rather than a bug in the WAV writer itself; profile capture thread, block size, and concurrent work (logging, future STT) on the same machine.
- **Status**: open

