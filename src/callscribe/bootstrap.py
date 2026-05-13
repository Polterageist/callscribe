from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from callscribe.single_instance import ensure_single_instance

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BootConfig:
    test_mode: bool
    log_to_stream: bool
    test_run_for_ms: int
    log_console_enabled: bool

    @staticmethod
    def from_env(env: dict[str, str] | None = None) -> BootConfig:
        e = os.environ if env is None else env
        test_mode = e.get("CALLSCRIBE_TEST_MODE") == "1"
        log_to_stream = e.get("CALLSCRIBE_LOG_STDOUT") == "1"
        test_run_for_ms = int(e.get("CALLSCRIBE_TEST_RUN_FOR_MS", "2500"))
        log_console_enabled = e.get("CALLSCRIBE_LOG_CONSOLE", "1") != "0"
        return BootConfig(
            test_mode=test_mode,
            log_to_stream=log_to_stream,
            test_run_for_ms=test_run_for_ms,
            log_console_enabled=log_console_enabled,
        )


def default_log_dir() -> Path:
    # Cross-platform, but respects Windows roaming profile when available.
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Callscribe" / "logs"
    return Path.home() / ".callscribe" / "logs"


def configure_logging(config: BootConfig) -> None:
    """File: DEBUG + verbose format. Console: lighter (INFO + short format) when enabled."""
    log_dir = default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    app_logger = logging.getLogger("callscribe")
    app_logger.handlers.clear()
    app_logger.setLevel(logging.DEBUG)
    app_logger.propagate = False

    file_handler = logging.FileHandler(
        log_dir / "callscribe.log",
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s")
    )
    app_logger.addHandler(file_handler)

    console_on = False
    if config.test_mode:
        console_on = config.log_to_stream
    else:
        console_on = config.log_console_enabled

    if console_on:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        if config.test_mode:
            stream_handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            stream_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        app_logger.addHandler(stream_handler)

    for noisy in ("PIL", "urllib3", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.basicConfig(handlers=[], force=True)


def ensure_primary_instance(
    app_id: str,
    *,
    on_activate: Callable[[], None],
) -> bool:
    return ensure_single_instance(app_id, on_activate=on_activate) is not None
