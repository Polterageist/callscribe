from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from callscribe.bootstrap import BootConfig, configure_logging


def _reset_callscribe_logger() -> None:
    log = logging.getLogger("callscribe")
    log.handlers.clear()
    log.setLevel(logging.NOTSET)
    log.propagate = True


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
    yield
    _reset_callscribe_logger()


def test_configure_logging_file_and_console_handlers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("callscribe.bootstrap.default_log_dir", lambda: tmp_path)

    configure_logging(
        BootConfig(
            test_mode=False,
            log_to_stream=False,
            test_run_for_ms=0,
            log_console_enabled=True,
        )
    )

    log = logging.getLogger("callscribe")
    assert len(log.handlers) == 2
    kinds = {type(h).__name__ for h in log.handlers}
    assert "FileHandler" in kinds
    assert "StreamHandler" in kinds


def test_configure_logging_test_mode_console_only_when_stdout_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("callscribe.bootstrap.default_log_dir", lambda: tmp_path)

    configure_logging(
        BootConfig(
            test_mode=True,
            log_to_stream=True,
            test_run_for_ms=0,
            log_console_enabled=False,
        )
    )

    log = logging.getLogger("callscribe")
    assert len(log.handlers) == 2
