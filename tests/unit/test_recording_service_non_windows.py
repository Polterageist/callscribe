from __future__ import annotations

import sys
from pathlib import Path

import pytest

from callscribe.app.recording_service import FileRecordingService
from callscribe.config.settings import AppSettings
from callscribe.config.store import TomlConfigStore


def test_start_on_non_windows_notifies_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    out = tmp_path / "sessions"
    out.mkdir()
    cfg = tmp_path / "c.toml"
    store = TomlConfigStore(path=cfg)
    store.save_settings(AppSettings(output_folder=str(out), loopback_speaker_name=None, microphone_name=None))

    rec = FileRecordingService(store)
    errors: list[str] = []
    rec.set_error_handler(errors.append)
    rec.start()
    assert len(errors) == 1
    assert "Windows" in errors[0]
