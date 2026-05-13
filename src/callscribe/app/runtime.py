from __future__ import annotations

import asyncio
import atexit
import logging
import os
import sys
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from callscribe.app.controller import AppController, Executor, RecordingService, TrayUI, create_app
from callscribe.app.recording_service import FileRecordingService
from callscribe.bootstrap import BootConfig
from callscribe.config.settings import AppSettings
from callscribe.config.store import TomlConfigStore
from callscribe.tray.app_icon import load_tray_icon_pil
from callscribe.tray.null_tray import NullTray
from callscribe.tray.pystray_tray import PystrayTrayAdapter

logger = logging.getLogger(__name__)

_settings_tk_executor_singleton: ThreadPoolExecutor | None = None


def _get_settings_tk_executor() -> ThreadPoolExecutor:
    """Single worker so all Tk runs on one thread (pystray posts from Win32 thread)."""
    global _settings_tk_executor_singleton
    if _settings_tk_executor_singleton is None:
        ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix="callscribe-settings-tk")

        def _shutdown() -> None:
            ex.shutdown(wait=False, cancel_futures=True)

        atexit.register(_shutdown)
        _settings_tk_executor_singleton = ex
    return _settings_tk_executor_singleton


class SettingsDialogFn(Protocol):
    def __call__(self) -> AppSettings | None: ...


@dataclass(frozen=True)
class _Callbacks:
    on_start: Callable[[], None]
    on_stop: Callable[[], None]
    on_open_output_folder: Callable[[], None]
    on_settings: Callable[[], None]
    on_quit: Callable[[], None]


class TrayAppRuntime:
    def __init__(
        self,
        *,
        boot_config: BootConfig,
        config_store: TomlConfigStore,
        executor: Executor,
        recorder: RecordingService,
        open_settings: SettingsDialogFn,
    ) -> None:
        self._boot = boot_config
        self._config_store = config_store
        self._executor = executor
        self._recorder = recorder
        self._open_settings = open_settings

        self._loop: asyncio.AbstractEventLoop | None = None
        self._controller: AppController | None = None
        self._tray: TrayUI | None = None

    @property
    def tray(self) -> TrayUI:
        assert self._tray is not None
        return self._tray

    @property
    def controller(self) -> AppController:
        assert self._controller is not None
        return self._controller

    def _bind_recorder_errors(self) -> None:
        if isinstance(self._recorder, FileRecordingService):
            assert self._controller is not None
            self._recorder.set_error_handler(self._controller.handle_recording_error)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()

        callbacks = _Callbacks(
            on_start=self._sync(self._on_start),
            on_stop=self._sync(self._on_stop),
            on_open_output_folder=self._sync(self._on_open_output_folder),
            on_settings=self._sync(self._on_settings),
            on_quit=self._sync(self._on_quit),
        )

        self._tray = self._create_tray(callbacks)
        self._controller = create_app(
            tray=self._tray,
            config_store=self._config_store,
            recorder=self._recorder,
            executor=self._executor,
        )
        self._bind_recorder_errors()

        if self._boot.test_mode:
            self._controller.start()
            logger.info("CALLSCRIBE_READY pid=%s", os.getpid())
            for handler in logging.getLogger("callscribe").handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
            sys.stdout.flush()
            await asyncio.sleep(max(0, self._boot.test_run_for_ms) / 1000.0)
            return

        # `pystray` is blocking; run it off the event loop.
        await asyncio.to_thread(self._controller.start)

    def _create_tray(self, callbacks: _Callbacks) -> TrayUI:
        if self._boot.test_mode:
            return NullTray()
        return PystrayTrayAdapter(
            on_start=callbacks.on_start,
            on_stop=callbacks.on_stop,
            on_open_output_folder=callbacks.on_open_output_folder,
            on_settings=callbacks.on_settings,
            on_quit=callbacks.on_quit,
            icon=load_tray_icon_pil(),
        )

    def _sync(self, fn: Callable[[], Coroutine[object, object, None]]) -> Callable[[], None]:
        def wrapper() -> None:
            loop = self._loop
            if loop is None:
                return
            loop.call_soon_threadsafe(self._schedule, fn())

        return wrapper

    def _schedule(self, coro: Coroutine[object, object, None]) -> None:
        asyncio.create_task(coro)

    async def _on_start(self) -> None:
        self.controller.handle_start()

    async def _on_stop(self) -> None:
        self.controller.handle_stop()

    async def _on_open_output_folder(self) -> None:
        folder = self._config_store.get_output_folder()
        if not folder:
            return

        def _open_folder() -> None:
            if sys.platform == "win32":
                os.startfile(folder)
                return
            import subprocess

            subprocess.run(["xdg-open", folder], check=False)

        await asyncio.to_thread(_open_folder)

    async def _on_settings(self) -> None:
        if self._boot.test_mode:
            return
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(_get_settings_tk_executor(), self._open_settings)
        if not result:
            return

        self._config_store.save_settings(result)

        self._controller = create_app(
            tray=self.tray,
            config_store=self._config_store,
            recorder=self._recorder,
            executor=self._executor,
        )
        self._bind_recorder_errors()

    async def _on_quit(self) -> None:
        self.controller.handle_quit()
