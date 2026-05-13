from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


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
    def submit(self, fn: Callable[[], None]) -> None: ...


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
        self._last_error_message: str | None = None
        if self._config.get_output_folder() is None:
            self._state = AppState.NEEDS_SETUP

        self._publish_state()

    @property
    def state(self) -> AppState:
        return self._state

    def start(self) -> None:
        self._tray.run()

    def handle_start(self) -> None:
        if self._state not in (AppState.IDLE, AppState.ERROR):
            return
        if self._config.get_output_folder() is None:
            self._state = AppState.NEEDS_SETUP
            self._publish_state()
            return

        self._last_error_message = None
        self._state = AppState.RECORDING
        self._publish_state()

        def do_start() -> None:
            self._recorder.start()

        self._executor.submit(do_start)

    def handle_recording_error(self, message: str) -> None:
        self._last_error_message = message[:400]
        self._state = AppState.ERROR
        self._publish_state()

    def handle_stop(self) -> None:
        if self._state != AppState.RECORDING:
            return

        def do_stop() -> None:
            self._recorder.stop()
            self._last_error_message = None
            self._state = AppState.IDLE
            self._publish_state()

        self._executor.submit(do_stop)

    def handle_quit(self) -> None:
        if self._state == AppState.RECORDING:
            def do_quit_after_stop() -> None:
                self._recorder.stop()
                self._last_error_message = None
                self._state = AppState.IDLE
                self._publish_state()
                self._tray.stop()

            self._executor.submit(do_quit_after_stop)
            return

        self._tray.stop()

    def _menu_snapshot(self) -> MenuSnapshot:
        match self._state:
            case AppState.IDLE:
                return MenuSnapshot(start_enabled=True, stop_enabled=False)
            case AppState.RECORDING:
                return MenuSnapshot(start_enabled=False, stop_enabled=True)
            case AppState.NEEDS_SETUP:
                return MenuSnapshot(start_enabled=False, stop_enabled=False)
            case AppState.ERROR:
                return MenuSnapshot(start_enabled=True, stop_enabled=False)
            case _:
                return MenuSnapshot(start_enabled=False, stop_enabled=False)

    def _publish_state(self) -> None:
        self._tray.set_menu(self._menu_snapshot())
        self._tray.set_tooltip(self._tooltip_text())

    def _tooltip_text(self) -> str:
        match self._state:
            case AppState.IDLE:
                return "Idle"
            case AppState.RECORDING:
                return "Recording"
            case AppState.ERROR:
                if self._last_error_message:
                    short = self._last_error_message.replace("\n", " ")
                    if len(short) > 120:
                        short = short[:117] + "..."
                    return f"Error: {short}"
                return "Error"
            case AppState.NEEDS_SETUP:
                return "Needs_setup"
            case AppState.TRANSCRIBING:
                return "Transcribing"
            case _:
                return str(self._state)


def create_app(
    *,
    tray: TrayUI,
    config_store: ConfigStore,
    recorder: RecordingService,
    executor: Executor,
) -> AppController:
    return AppController(tray=tray, config_store=config_store, recorder=recorder, executor=executor)
