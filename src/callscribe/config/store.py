from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import tomlkit


def _default_config_path() -> Path:
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / "Callscribe" / "config.toml"


@dataclass
class TomlConfigStore:
    path: Path = _default_config_path()

    def get_output_folder(self) -> str | None:
        doc = self._read()
        value = doc.get("output_folder")
        if not value:
            return None
        return str(value)

    def set_output_folder(self, folder: str) -> None:
        p = Path(folder)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        doc = self._read()
        doc["output_folder"] = str(p)
        self.path.write_text(tomlkit.dumps(doc), encoding="utf-8")

    def _read(self) -> tomlkit.TOMLDocument:
        if not self.path.exists():
            return tomlkit.document()
        try:
            text = self.path.read_text(encoding="utf-8")
            return tomlkit.parse(text)
        except Exception:
            # If config is unreadable, return empty doc (E1: treat as Needs_setup).
            return tomlkit.document()

