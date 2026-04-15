from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol, runtime_checkable


class AppState(str, Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    ERROR = "error"
    NEEDS_SETUP = "needs_setup"


@dataclass(frozen=True)
class MenuSnapshot:
    start_enabled: bool
    stop_enabled: bool


@runtime_checkable
class Executor(Protocol):
    def submit(self, fn) -> None: ...


@runtime_checkable
class TrayUI(Protocol):
    def run(self) -> None: ...

    def stop(self) -> None: ...

    def set_tooltip(self, text: str) -> None: ...

    def set_menu(self, snapshot: MenuSnapshot) -> None: ...


@runtime_checkable
class ConfigStore(Protocol):
    def get_output_folder(self) -> str | None: ...


@runtime_checkable
class RecordingService(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...


class AppController:
    def __init__(
        self,
        *,
        tray: TrayUI,
        config_store: ConfigStore,
        recorder: RecordingService,
        executor: Executor,
    ) -> None:
        self._tray = tray
        self._config = config_store
        self._recorder = recorder
        self._executor = executor

        self._state = AppState.IDLE
        if self._config.get_output_folder() is None:
            self._state = AppState.NEEDS_SETUP

        self._publish_state()

    @property
    def state(self) -> AppState:
        return self._state

    def start(self) -> None:
        self._tray.run()

    def handle_start(self) -> None:
        if self._state != AppState.IDLE:
            return
        if self._config.get_output_folder() is None:
            self._state = AppState.NEEDS_SETUP
            self._publish_state()
            return

        def do_start() -> None:
            self._recorder.start()
            self._state = AppState.RECORDING
            self._publish_state()

        self._executor.submit(do_start)

    def handle_stop(self) -> None:
        if self._state != AppState.RECORDING:
            return

        def do_stop() -> None:
            self._recorder.stop()
            self._state = AppState.IDLE
            self._publish_state()

        self._executor.submit(do_stop)

    def _menu_snapshot(self) -> MenuSnapshot:
        match self._state:
            case AppState.IDLE:
                return MenuSnapshot(start_enabled=True, stop_enabled=False)
            case AppState.RECORDING:
                return MenuSnapshot(start_enabled=False, stop_enabled=True)
            case AppState.NEEDS_SETUP:
                return MenuSnapshot(start_enabled=False, stop_enabled=False)
            case _:
                # Conservative defaults for states not covered by E1 tests yet.
                return MenuSnapshot(start_enabled=False, stop_enabled=False)

    def _publish_state(self) -> None:
        self._tray.set_menu(self._menu_snapshot())


def create_app(
    *,
    tray: TrayUI,
    config_store: ConfigStore,
    recorder: RecordingService,
    executor: Executor,
) -> AppController:
    return AppController(tray=tray, config_store=config_store, recorder=recorder, executor=executor)

