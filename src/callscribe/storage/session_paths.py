from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path


def create_session_directory(output_folder: Path) -> Path:
    """Create YYYY-MM-DD/YYYYMMDD-HHMMSS-<8 hex>/ under output_folder and return the session root."""
    now = datetime.now(UTC)
    date_dir = output_folder / now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%d-%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    session_root = date_dir / f"{stamp}-{short_id}"
    session_root.mkdir(parents=True, exist_ok=True)
    return session_root


def session_audio_wav_path(session_root: Path) -> Path:
    return session_root / "audio.wav"
