from __future__ import annotations

from pathlib import Path

from callscribe.storage.session_paths import create_session_directory, session_audio_wav_path


def test_create_session_directory_and_audio_path(tmp_path: Path) -> None:
    root = tmp_path / "vault"
    root.mkdir()
    session = create_session_directory(root)
    assert session.is_dir()
    assert session.parent.name.count("-") == 2  # YYYY-MM-DD
    wav = session_audio_wav_path(session)
    assert wav.name == "audio.wav"
    assert wav.parent == session
