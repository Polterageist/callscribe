from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from callscribe.app.controller import AppState, MenuSnapshot, create_app


class FakeExecutor:
    def __init__(self) -> None:
        self._queue: list[Callable[[], None]] = []
        self.submit_called = 0

    def submit(self, fn: Callable[[], None]) -> None:
        self.submit_called += 1
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

    assert tray.tooltips[-1] == "Idle"

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
    assert tray.menus[-1] == MenuSnapshot(
        start_enabled=False,
        stop_enabled=False,
    )
    assert tray.tooltips[-1] == "Needs_setup"


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

    assert app.state.value == AppState.IDLE.value
    assert tray.menus[-1] == MenuSnapshot(
        start_enabled=True,
        stop_enabled=False,
    )
    assert tray.tooltips[-1] == "Idle"

    app.handle_start()
    # Must not execute long-running work inline: it should be scheduled.
    assert recorder.start_called == 0
    executor.run_all()

    assert recorder.start_called == 1
    assert cast(str, app.state.value) == AppState.RECORDING.value
    assert tray.menus[-1] == MenuSnapshot(
        start_enabled=False,
        stop_enabled=True,
    )
    assert tray.tooltips[-1] == "Recording"

    app.handle_stop()
    assert recorder.stop_called == 0
    executor.run_all()

    assert recorder.stop_called == 1
    assert cast(str, app.state.value) == AppState.IDLE.value
    assert tray.menus[-1] == MenuSnapshot(
        start_enabled=True,
        stop_enabled=False,
    )
    assert tray.tooltips[-1] == "Idle"


def test_quit_stops_tray_in_idle() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder="C:/tmp"),
        recorder=FakeRecordingService(),
        executor=executor,
    )

    app.handle_quit()

    assert tray.stop_called is True


def test_quit_while_recording_schedules_stop_then_stops_tray() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    recorder = FakeRecordingService()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder="C:/tmp"),
        recorder=recorder,
        executor=executor,
    )

    app.handle_start()
    executor.run_all()
    assert app.state == AppState.RECORDING

    app.handle_quit()

    # Stop should be scheduled, not executed inline.
    assert recorder.stop_called == 0
    assert tray.stop_called is False

    executor.run_all()

    assert recorder.stop_called == 1
    assert tray.stop_called is True


def test_double_start_does_not_schedule_duplicate_start() -> None:
    tray = FakeTrayUI()
    executor = FakeExecutor()
    recorder = FakeRecordingService()
    app = create_app(
        tray=tray,
        config_store=FakeConfigStore(output_folder="C:/tmp"),
        recorder=recorder,
        executor=executor,
    )

    app.handle_start()
    app.handle_start()

    # Still non-blocking: recorder not started inline.
    assert recorder.start_called == 0
    # But only one start task should be scheduled.
    assert executor.submit_called == 1

    executor.run_all()
    assert recorder.start_called == 1

