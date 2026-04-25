from __future__ import annotations

import logging
import os
import threading
import time
from typing import Callable

from tkinter import Tk
from tkinter import filedialog

from callscribe.app.controller import AppController, Executor, RecordingService, TrayUI, create_app
from callscribe.bootstrap import BootConfig, configure_logging, ensure_primary_instance
from callscribe.config.store import TomlConfigStore
from callscribe.tray.pystray_tray import PystrayTrayAdapter

logger = logging.getLogger(__name__)


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


class _TestTray(TrayUI):
    def run(self) -> None:
        return

    def stop(self) -> None:
        return

    def set_tooltip(self, text: str) -> None:
        return

    def set_menu(self, snapshot) -> None:  # type: ignore[override]
        return


def _create_tray(
    config: BootConfig,
    *,
    on_start: Callable[[], None],
    on_stop: Callable[[], None],
    on_open_output_folder: Callable[[], None],
    on_settings: Callable[[], None],
    on_quit: Callable[[], None],
) -> TrayUI:
    if config.test_mode:
        return _TestTray()
    return PystrayTrayAdapter(
        on_start=on_start,
        on_stop=on_stop,
        on_open_output_folder=on_open_output_folder,
        on_settings=on_settings,
        on_quit=on_quit,
    )


def main() -> None:
    config = BootConfig.from_env()
    configure_logging(config)

    def on_activate() -> None:
        logger.info("CALLSCRIBE_ACTIVATED")

    if not ensure_primary_instance("callscribe", on_activate=on_activate):
        logger.info("CALLSCRIBE_ALREADY_RUNNING")
        return

    config_store = TomlConfigStore()
    executor = ThreadExecutor()
    recorder = NoopRecordingService()

    controller_holder: dict[str, AppController] = {}

    def on_start() -> None:
        controller_holder["c"].handle_start()

    def on_stop() -> None:
        controller_holder["c"].handle_stop()

    def on_open_output_folder() -> None:
        folder = config_store.get_output_folder()
        if folder:
            os.startfile(folder)  # type: ignore[attr-defined]

    def on_settings() -> None:
        if config.test_mode:
            return
        folder = _pick_folder()
        if not folder:
            return
        config_store.set_output_folder(folder)
        # Re-evaluate by recreating controller state in-place (E1 minimal).
        controller_holder["c"] = create_app(
            tray=tray,
            config_store=config_store,
            recorder=recorder,
            executor=executor,
        )

    def on_quit() -> None:
        controller_holder["c"].handle_quit()

    tray = _create_tray(
        config,
        on_start=on_start,
        on_stop=on_stop,
        on_open_output_folder=on_open_output_folder,
        on_settings=on_settings,
        on_quit=on_quit,
    )

    controller_holder["c"] = create_app(
        tray=tray,
        config_store=config_store,
        recorder=recorder,
        executor=executor,
    )

    controller_holder["c"].start()
    logger.info("CALLSCRIBE_READY pid=%s", os.getpid())
    if config.test_mode:
        time.sleep(max(0, config.test_run_for_ms) / 1000.0)
        return


if __name__ == "__main__":
    main()

