from __future__ import annotations

import logging
import sys
import threading
import wave
from pathlib import Path
from typing import Any

from callscribe.audio.stereo_mix import interleaved_stereo_bytes, mix_loopback_mic_to_int16_stereo

logger = logging.getLogger(__name__)

_SAMPLERATE = 48_000
_BLOCKSIZE = 2048


def _loopback_inputs() -> list[Any]:
    import soundcard as sc

    return [m for m in sc.all_microphones(include_loopback=True) if m.isloopback]


def _resolve_loopback_microphone(name: str | None) -> Any:
    """WASAPI loopback is exposed as a ``Microphone`` with ``isloopback=True``, not ``Speaker.recorder()``."""
    import soundcard as sc

    devices = _loopback_inputs()
    if not devices:
        raise RuntimeError("No WASAPI loopback endpoints found (empty loopback device list)")
    if not name:
        default_sp = sc.default_speaker()
        for m in devices:
            if m.name == default_sp.name:
                logger.debug("Using default loopback for speaker: %s", m.name)
                return m
        logger.debug("Using first loopback device: %s", devices[0].name)
        return devices[0]
    for m in devices:
        if m.name == name:
            logger.debug("Resolved loopback device: %s", m.name)
            return m
    for m in devices:
        if name in m.name:
            logger.debug("Resolved loopback device (substring): %s", m.name)
            return m
    raise ValueError(f"Loopback device not found: {name!r}")


def _resolve_microphone(name: str | None) -> Any:
    import soundcard as sc

    if not name:
        mic = sc.default_microphone()
        logger.debug("Using default microphone: %s", mic.name)
        return mic
    for mic in sc.all_microphones(include_loopback=False):
        if mic.name == name:
            logger.debug("Resolved microphone: %s", mic.name)
            return mic
    try:
        return sc.get_microphone(name, include_loopback=False)
    except Exception as e:
        raise ValueError(f"Microphone not found: {name!r}") from e


class WindowsAudioCapture:
    """WASAPI loopback (``Microphone`` with ``isloopback``) + mic → stereo int16 WAV.

    Loopback keeps L/R from the device (first two channels if multi-channel).
    Microphone is mixed in mono then duplicated to both channels.
    """

    def __init__(
        self,
        *,
        wav_path: Path,
        loopback_speaker_name: str | None,
        microphone_name: str | None,
        stop_event: threading.Event,
    ) -> None:
        self._wav_path = wav_path
        self._loopback_name = loopback_speaker_name
        self._mic_name = microphone_name
        self._stop_event = stop_event

    def run(self) -> None:
        if sys.platform != "win32":
            raise OSError("Windows-only audio capture")
        logger.info("Starting capture to %s", self._wav_path)
        loopback = _resolve_loopback_microphone(self._loopback_name)
        microphone = _resolve_microphone(self._mic_name)

        with wave.open(str(self._wav_path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(_SAMPLERATE)
            with loopback.recorder(samplerate=_SAMPLERATE) as sys_rec, microphone.recorder(
                samplerate=_SAMPLERATE
            ) as mic_rec:
                while not self._stop_event.is_set():
                    sys_block = sys_rec.record(numframes=_BLOCKSIZE)
                    mic_block = mic_rec.record(numframes=_BLOCKSIZE)
                    stereo_i16 = mix_loopback_mic_to_int16_stereo(sys_block, mic_block)
                    if stereo_i16 is None:
                        continue
                    n = stereo_i16.shape[0]
                    wf.writeframes(interleaved_stereo_bytes(stereo_i16))
                    logger.debug("Wrote %s stereo frames", n)
        logger.info("Capture finalized: %s", self._wav_path)
