from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from callscribe.app.controller import AppState, MenuSnapshot, create_app
from callscribe.app.recording_service import FileRecordingService
from callscribe.config.settings import AppSettings
from callscribe.config.store import TomlConfigStore


class _FakeExecutor:
    def __init__(self) -> None:
        self._queue: list[Callable[[], None]] = []

    def submit(self, fn: Callable[[], None]) -> None:
        self._queue.append(fn)

    def run_all(self) -> None:
        while self._queue:
            self._queue.pop(0)()


class _FakeTrayUI:
    def __init__(self) -> None:
        self.tooltips: list[str] = []
        self.menus: list[MenuSnapshot] = []

    def run(self) -> None:
        return

    def stop(self) -> None:
        return

    def set_tooltip(self, text: str) -> None:
        self.tooltips.append(text)

    def set_menu(self, snapshot: MenuSnapshot) -> None:
        self.menus.append(snapshot)


def test_recording_error_on_non_windows_sets_error_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    out = tmp_path / "out"
    out.mkdir()
    store = TomlConfigStore(path=tmp_path / "cfg.toml")
    store.save_settings(AppSettings(output_folder=str(out), loopback_speaker_name=None, microphone_name=None))

    tray = _FakeTrayUI()
    executor = _FakeExecutor()
    recorder = FileRecordingService(store)
    app = create_app(tray=tray, config_store=store, recorder=recorder, executor=executor)
    recorder.set_error_handler(app.handle_recording_error)

    app.handle_start()
    executor.run_all()

    assert app.state == AppState.ERROR
    assert tray.menus[-1] == MenuSnapshot(start_enabled=True, stop_enabled=False)
    assert "Windows" in tray.tooltips[-1]
