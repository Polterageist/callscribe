# Bugs

## Double launch starts two instances

- **Symptom**: starting Callscribe twice results in **two running instances** (two tray icons / two processes).
- **Expected**: single-instance behavior; the second launch should focus/activate the existing instance or exit with a clear message.
- **Notes**: likely requires a single-instance lock (mutex / lockfile + IPC/activation).

## Folder picker window becomes unresponsive

- **Symptom**: the **directory selection window opens**, but afterwards **none of its controls work**, including close (X).
- **Expected**: folder picker should be interactive and closable; after selection/cancel, the app should return to tray normally.
- **Observed logs**: tray callback sometimes crashes with `_tkinter.TclError: Разрушительный сбой` when opening Settings (folder picker).
- **Notes**: likely caused by how the dialog is created or the GUI event loop/threading interaction (calling Tk dialogs from pystray win32 message handler thread/context).

### Repro logs (Settings… → folder picker)

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

