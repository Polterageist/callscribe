from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from tkinter import Button, Label, StringVar, Tk, Toplevel, filedialog
from tkinter.ttk import Combobox

from callscribe.config.settings import AppSettings
from callscribe.platform.windows_audio_devices import DEFAULT_DEVICE_LABEL
from callscribe.tray.app_icon import apply_tk_window_icon

logger = logging.getLogger(__name__)

_tk_root: Tk | None = None


def _root() -> Tk:
    global _tk_root
    if _tk_root is None:
        _tk_root = Tk()
        _tk_root.withdraw()
        try:
            _tk_root.attributes("-topmost", False)
        except Exception:
            pass
    return _tk_root


def _merge_options(device_names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = [DEFAULT_DEVICE_LABEL]
    for n in device_names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def show_settings_dialog(
    *,
    output_folder: str | None,
    loopback_speaker_name: str | None,
    microphone_name: str | None,
    list_loopback_speakers: Callable[[], list[str]],
    list_microphones: Callable[[], list[str]],
) -> AppSettings | None:
    """Modal settings window; returns saved settings or None if cancelled."""
    root = _root()
    result: list[AppSettings | None] = [None]

    win = Toplevel(root)
    win.title("Callscribe — Settings")
    win.transient(root)
    apply_tk_window_icon(root, size=64)
    apply_tk_window_icon(win, size=64)
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass

    folder_var = StringVar(value=output_folder or "")
    lb_names = _merge_options(list_loopback_speakers())
    mic_names = _merge_options(list_microphones())

    lb_var = StringVar(
        value=(
            loopback_speaker_name
            if loopback_speaker_name and loopback_speaker_name in lb_names
            else DEFAULT_DEVICE_LABEL
        )
    )
    if loopback_speaker_name and loopback_speaker_name not in lb_names:
        lb_names = [DEFAULT_DEVICE_LABEL, loopback_speaker_name, *lb_names[1:]]

    mic_var = StringVar(
        value=(
            microphone_name if microphone_name and microphone_name in mic_names else DEFAULT_DEVICE_LABEL
        )
    )
    if microphone_name and microphone_name not in mic_names:
        mic_names = [DEFAULT_DEVICE_LABEL, microphone_name, *mic_names[1:]]

    Label(win, text="Output folder").grid(row=0, column=0, sticky="w", padx=8, pady=4)
    folder_entry = Label(win, textvariable=folder_var, anchor="w", width=48, relief="sunken")
    folder_entry.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

    def browse_folder() -> None:
        initial = folder_var.get() or None
        picked = filedialog.askdirectory(
            parent=win,
            title="Callscribe — Select output folder",
            initialdir=initial,
        )
        if picked:
            folder_var.set(picked)

    Button(win, text="Browse…", command=browse_folder).grid(row=0, column=2, padx=4, pady=4)

    Label(win, text="Loopback (system audio)").grid(row=1, column=0, sticky="w", padx=8, pady=4)
    lb_combo = Combobox(win, textvariable=lb_var, values=lb_names, state="readonly", width=45)
    lb_combo.grid(row=1, column=1, columnspan=2, padx=4, pady=4, sticky="ew")

    Label(win, text="Microphone").grid(row=2, column=0, sticky="w", padx=8, pady=4)
    mic_combo = Combobox(win, textvariable=mic_var, values=mic_names, state="readonly", width=45)
    mic_combo.grid(row=2, column=1, columnspan=2, padx=4, pady=4, sticky="ew")

    win.columnconfigure(1, weight=1)

    def on_ok() -> None:
        folder = folder_var.get().strip()
        if not folder:
            logger.warning("Settings OK ignored: empty output folder")
            return
        p = Path(folder)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Cannot create output folder: %s", e)
            return

        lb = lb_var.get()
        mic = mic_var.get()
        saved = AppSettings(
            output_folder=str(p.resolve()),
            loopback_speaker_name=None if lb == DEFAULT_DEVICE_LABEL else lb,
            microphone_name=None if mic == DEFAULT_DEVICE_LABEL else mic,
        )
        result[0] = saved
        logger.info("Settings dialog OK (output=%s)", saved.output_folder)
        win.destroy()

    def on_cancel() -> None:
        logger.debug("Settings dialog cancelled")
        win.destroy()

    btn_row = 3
    Button(win, text="OK", command=on_ok).grid(row=btn_row, column=1, sticky="e", padx=4, pady=8)
    Button(win, text="Cancel", command=on_cancel).grid(row=btn_row, column=2, sticky="w", padx=4, pady=8)

    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", on_cancel)
    root.wait_window(win)
    return result[0]
