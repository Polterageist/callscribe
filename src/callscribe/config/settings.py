from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    """Values persisted from the settings dialog (single TOML write on OK)."""

    output_folder: str
    loopback_speaker_name: str | None
    microphone_name: str | None
