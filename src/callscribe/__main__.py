from __future__ import annotations

import os
import threading
from typing import Callable

from tkinter import Tk
from tkinter import filedialog

from callscribe.app.controller import AppController, Executor, RecordingService, create_app
from callscribe.config.store import TomlConfigStore
from callscribe.tray.pystray_tray import PystrayTrayAdapter


class ThreadExecutor(Executor):
    def submit(self, fn: Callable[[], None]) -> None:
        t = threading.Thread(target=fn, daemon=True)
        t.start()


class NoopRecordingService(RecordingService):
    def start(self) -> None:
        return

    def stop(self) -> None:
        return


def _pick_folder() -> str | None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        folder = filedialog.askdirectory(title="Callscribe — Select output folder")
        return folder or None
    finally:
        root.destroy()


def main() -> None:
    config = TomlConfigStore()
    executor = ThreadExecutor()
    recorder = NoopRecordingService()

    controller_holder: dict[str, AppController] = {}

    def on_start() -> None:
        controller_holder["c"].handle_start()

    def on_stop() -> None:
        controller_holder["c"].handle_stop()

    def on_open_output_folder() -> None:
        folder = config.get_output_folder()
        if folder:
            os.startfile(folder)  # type: ignore[attr-defined]

    def on_settings() -> None:
        folder = _pick_folder()
        if not folder:
            return
        config.set_output_folder(folder)
        # Re-evaluate by recreating controller state in-place (E1 minimal).
        controller_holder["c"] = create_app(
            tray=tray,
            config_store=config,
            recorder=recorder,
            executor=executor,
        )

    def on_quit() -> None:
        controller_holder["c"].handle_quit()

    tray = PystrayTrayAdapter(
        on_start=on_start,
        on_stop=on_stop,
        on_open_output_folder=on_open_output_folder,
        on_settings=on_settings,
        on_quit=on_quit,
    )

    controller_holder["c"] = create_app(
        tray=tray,
        config_store=config,
        recorder=recorder,
        executor=executor,
    )

    controller_holder["c"].start()


if __name__ == "__main__":
    main()

