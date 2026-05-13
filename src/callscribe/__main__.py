from __future__ import annotations

import asyncio
import logging
import os
import threading
from collections.abc import Callable

from callscribe.app.controller import Executor
from callscribe.app.recording_service import FileRecordingService
from callscribe.app.runtime import TrayAppRuntime
from callscribe.bootstrap import BootConfig, configure_logging, ensure_primary_instance
from callscribe.config.settings import AppSettings
from callscribe.config.store import TomlConfigStore
from callscribe.platform.windows_audio_devices import list_loopback_speaker_names, list_microphone_names
from callscribe.ui.settings_dialog import show_settings_dialog

logger = logging.getLogger("callscribe")


class ThreadExecutor(Executor):
    def submit(self, fn: Callable[[], None]) -> None:
        t = threading.Thread(target=fn, daemon=True)
        t.start()


def main() -> None:
    boot_config = BootConfig.from_env()
    configure_logging(boot_config)

    def on_activate() -> None:
        logger.info("CALLSCRIBE_ACTIVATED")

    instance_id = os.environ.get("CALLSCRIBE_INSTANCE_ID", "callscribe")
    if not ensure_primary_instance(instance_id, on_activate=on_activate):
        logger.info("CALLSCRIBE_ALREADY_RUNNING")
        return

    config_store = TomlConfigStore()
    recorder = FileRecordingService(config_store)

    def open_settings() -> AppSettings | None:
        return show_settings_dialog(
            output_folder=config_store.get_output_folder(),
            loopback_speaker_name=config_store.get_loopback_speaker_name(),
            microphone_name=config_store.get_microphone_name(),
            list_loopback_speakers=list_loopback_speaker_names,
            list_microphones=list_microphone_names,
        )

    runtime = TrayAppRuntime(
        boot_config=boot_config,
        config_store=config_store,
        executor=ThreadExecutor(),
        recorder=recorder,
        open_settings=open_settings,
    )
    asyncio.run(runtime.run())


if __name__ == "__main__":
    main()
