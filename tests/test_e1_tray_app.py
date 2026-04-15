from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest

from callscribe.app.controller import AppState, MenuSnapshot, create_app


class FakeExecutor:
    def __init__(self) -> None:
        self._queue: list[Callable[[], None]] = []

    def submit(self, fn) -> None:
        self._queue.append(fn)

    def run_all(self) -> None:
        while self._queue:
            self._queue.pop(0)()


class FakeTrayUI:
    def __init__(self) -> None:
        self.run_called = False
        self.stop_called = False
        self.tooltips: list[str] = []
        self.menus: list[MenuSnapshot] = []

    def run(self) -> None:
        self.run_called = True

    def stop(self) -> None:
        self.stop_called = True

    def set_tooltip(self, text: str) -> None:
        self.tooltips.append(text)

    def set_menu(self, snapshot: MenuSnapshot) -> None:
        self.menus.append(snapshot)


@dataclass
class FakeConfigStore:
    output_folder: str | None

    def get_output_folder(self) -> str | None:
        return self.output_folder


class FakeRecordingService:
    def __init__(self) -> None:
        self.start_called = 0
        self.stop_called = 0

    def start(self) -> None:
        self.start_called += 1

    def stop(self) -> None:
        self.stop_called += 1


def test_tray_starts_via_controller_start() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder="C:/tmp"),
        recorder=FakeRecordingService(),
        executor=executor,
    )

    app.start()

    assert tray.run_called is True


def test_missing_output_folder_puts_app_into_needs_setup_and_disables_controls() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder=None),
        recorder=FakeRecordingService(),
        executor=executor,
    )

    assert app.state == AppState.NEEDS_SETUP
    assert tray.menus[-1] == MenuSnapshot(start_enabled=False, stop_enabled=False)


def test_manual_start_stop_updates_state_and_menu_without_blocking_ui_thread() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    recorder = FakeRecordingService()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder="C:/tmp"),
        recorder=recorder,
        executor=executor,
    )

    assert app.state == AppState.IDLE
    assert tray.menus[-1] == MenuSnapshot(start_enabled=True, stop_enabled=False)

    app.handle_start()
    # Must not execute long-running work inline: it should be scheduled.
    assert recorder.start_called == 0
    executor.run_all()

    assert recorder.start_called == 1
    assert app.state == AppState.RECORDING
    assert tray.menus[-1] == MenuSnapshot(start_enabled=False, stop_enabled=True)

    app.handle_stop()
    assert recorder.stop_called == 0
    executor.run_all()

    assert recorder.stop_called == 1
    assert app.state == AppState.IDLE
    assert tray.menus[-1] == MenuSnapshot(start_enabled=True, stop_enabled=False)

