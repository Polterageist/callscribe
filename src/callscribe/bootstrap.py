from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from callscribe.single_instance import ensure_single_instance

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootConfig:
    test_mode: bool
    log_to_stream: bool
    test_run_for_ms: int

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> BootConfig:
        e = os.environ if env is None else env
        test_mode = e.get("CALLSCRIBE_TEST_MODE") == "1"
        log_to_stream = e.get("CALLSCRIBE_LOG_STDOUT") == "1"
        test_run_for_ms = int(e.get("CALLSCRIBE_TEST_RUN_FOR_MS", "2500"))
        return BootConfig(
            test_mode=test_mode,
            log_to_stream=log_to_stream,
            test_run_for_ms=test_run_for_ms,
        )


def default_log_dir() -> Path:
    # Cross-platform, but respects Windows roaming profile when available.
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Callscribe" / "logs"
    return Path.home() / ".callscribe" / "logs"


def configure_logging(config: BootConfig) -> None:
    log_dir = default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(
        log_dir / "callscribe.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )

    handlers: list[logging.Handler] = [file_handler]
    if config.log_to_stream:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(
            logging.Formatter(
                "%(message)s"
                if config.test_mode
                else "%(levelname)s %(name)s: %(message)s"
            )
        )
        handlers.append(stream_handler)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        force=True,
    )


def ensure_primary_instance(
    app_id: str,
    *,
    on_activate: Callable[[], None],
) -> bool:
    return ensure_single_instance(app_id, on_activate=on_activate) is not None
