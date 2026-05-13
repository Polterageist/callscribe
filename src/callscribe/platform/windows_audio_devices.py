from __future__ import annotations

import logging
import sys
from collections.abc import Callable

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_LABEL = "(Default)"

ListNamesFn = Callable[[], list[str]]


def _names_windows_loopback_devices() -> list[str]:
    import soundcard as sc

    names = [m.name for m in sc.all_microphones(include_loopback=True) if m.isloopback]
    logger.debug("Enumerated %s WASAPI loopback devices", len(names))
    return names


def _names_windows_microphones() -> list[str]:
    import soundcard as sc

    names = [m.name for m in sc.all_microphones(include_loopback=False)]
    logger.debug("Enumerated %s microphones", len(names))
    return names


def _names_stub() -> list[str]:
    return [DEFAULT_DEVICE_LABEL]


def list_loopback_speaker_names() -> list[str]:
    """Loopback capture endpoints (Windows: soundcard virtual mics with ``isloopback``).

    Stored in config as ``loopback_speaker_name`` for backward compatibility; values are device names.
    """
    if sys.platform != "win32":
        return _names_stub()
    try:
        return _names_windows_loopback_devices()
    except Exception:
        logger.exception("Failed to enumerate loopback devices; returning stub list")
        return _names_stub()


def list_microphone_names() -> list[str]:
    if sys.platform != "win32":
        return _names_stub()
    try:
        return _names_windows_microphones()
    except Exception:
        logger.exception("Failed to enumerate microphones; returning stub list")
        return _names_stub()
