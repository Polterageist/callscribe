from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from callscribe.audio.windows_capture import WindowsAudioCapture
from callscribe.config.store import TomlConfigStore
from callscribe.storage.session_paths import create_session_directory, session_audio_wav_path

logger = logging.getLogger(__name__)


class FileRecordingService:
    """Creates a session folder, records stereo WAV (L=loopback, R=mic) until stop."""

    def __init__(
        self,
        config_store: TomlConfigStore,
        *,
        capture_cls: type[WindowsAudioCapture] = WindowsAudioCapture,
    ) -> None:
        self._config = config_store
        self._capture_cls = capture_cls
        self._on_error: Callable[[str], None] | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

    def set_error_handler(self, handler: Callable[[str], None]) -> None:
        self._on_error = handler

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Recording start ignored: already running")
            return
        if self._thread is not None:
            self._thread = None

        out = self._config.get_output_folder()
        if not out:
            self._notify("Output folder is not configured")
            return
        if sys.platform != "win32":
            self._notify("Audio capture is only supported on Windows")
            return

        self._stop_event = threading.Event()
        output_folder = Path(out)
        assert self._stop_event is not None
        session_root = create_session_directory(output_folder)
        wav_path = session_audio_wav_path(session_root)
        logger.info("Session directory: %s", session_root)

        def run() -> None:
            stop_ev = self._stop_event
            assert stop_ev is not None
            try:
                capture = self._capture_cls(
                    wav_path=wav_path,
                    loopback_speaker_name=self._config.get_loopback_speaker_name(),
                    microphone_name=self._config.get_microphone_name(),
                    stop_event=stop_ev,
                )
                capture.run()
            except Exception as e:
                logger.exception("Recording failed")
                self._notify(f"{type(e).__name__}: {e}")

        self._thread = threading.Thread(target=run, name="callscribe-audio-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        logger.info("Stop recording requested")
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=60.0)
            if self._thread.is_alive():
                logger.error("Capture thread did not stop within timeout")
            self._thread = None
        self._stop_event = None

    def _notify(self, message: str) -> None:
        logger.error("%s", message)
        if self._on_error is not None:
            self._on_error(message)
