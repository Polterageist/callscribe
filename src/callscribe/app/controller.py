from __future__ import annotations

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

        self._state: AppState = AppState.IDLE

    @property
    def state(self) -> AppState:
        return self._state

    def start(self) -> None:
        raise NotImplementedError

    def handle_start(self) -> None:
        raise NotImplementedError

    def handle_stop(self) -> None:
        raise NotImplementedError


def create_app(
    *,
    tray: TrayUI,
    config_store: ConfigStore,
    recorder: RecordingService,
    executor: Executor,
) -> AppController:
    return AppController(tray=tray, config_store=config_store, recorder=recorder, executor=executor)

