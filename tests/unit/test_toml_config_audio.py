from __future__ import annotations

from pathlib import Path

from callscribe.config.settings import AppSettings
from callscribe.config.store import TomlConfigStore


def test_save_settings_roundtrip_for_audio_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    store = TomlConfigStore(path=path)
    out = tmp_path / "out"
    out.mkdir()

    store.save_settings(
        AppSettings(
            output_folder=str(out),
            loopback_speaker_name="Speakers (Test)",
            microphone_name="Mic (Test)",
        )
    )

    assert store.get_output_folder() == str(out.resolve())
    assert store.get_loopback_speaker_name() == "Speakers (Test)"
    assert store.get_microphone_name() == "Mic (Test)"

    store.save_settings(
        AppSettings(
            output_folder=str(out),
            loopback_speaker_name=None,
            microphone_name=None,
        )
    )
    assert store.get_loopback_speaker_name() is None
    assert store.get_microphone_name() is None
