from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from tkinter import Tk, filedialog

from callscribe.app.controller import Executor, RecordingService
from callscribe.app.runtime import TrayAppRuntime
from callscribe.bootstrap import BootConfig, configure_logging, ensure_primary_instance
from callscribe.config.store import TomlConfigStore

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

def main() -> None:
    boot_config = BootConfig.from_env()
    configure_logging(boot_config)

    def on_activate() -> None:
        logger.info("CALLSCRIBE_ACTIVATED")

    if not ensure_primary_instance("callscribe", on_activate=on_activate):
        logger.info("CALLSCRIBE_ALREADY_RUNNING")
        return

    runtime = TrayAppRuntime(
        boot_config=boot_config,
        config_store=TomlConfigStore(),
        executor=ThreadExecutor(),
        recorder=NoopRecordingService(),
        pick_folder=_pick_folder,
    )
    asyncio.run(runtime.run())


if __name__ == "__main__":
    main()

