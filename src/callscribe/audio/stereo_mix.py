"""WASAPI loopback + mic stereo mix (pure numpy, unit-tested)."""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray


def stereo_float_from_multichannel(block: np.ndarray) -> NDArray[np.float32]:
    """Map device block to stereo float (n, 2) in range roughly -1..1.

    - (n,) or (n, 1): duplicate to both channels (mono → stereo).
    - (n, c) with c >= 2: use first two channels as L/R (true stereo).
    """
    x = np.asarray(block, dtype=np.float32)
    if x.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    if x.ndim == 1:
        return np.column_stack((x, x))
    if x.shape[1] == 1:
        m = x[:, 0]
        return np.column_stack((m, m))
    return np.column_stack((x[:, 0], x[:, 1]))


def mono_float_from_device(block: np.ndarray) -> NDArray[np.float32]:
    """Single channel float (n,) for mixing; multi-channel mean to mono."""
    x = np.asarray(block, dtype=np.float32)
    if x.size == 0:
        return np.zeros(0, dtype=np.float32)
    if x.ndim == 1:
        return x
    return np.asarray(x.mean(axis=-1), dtype=np.float32)


def dup_mono_to_stereo(mono: NDArray[np.float32]) -> NDArray[np.float32]:
    """(n,) → (n, 2) with identical L/R."""
    if mono.size == 0:
        return np.zeros((0, 2), dtype=np.float32)
    return np.column_stack((mono, mono))


def mix_loopback_mic_to_int16_stereo(
    loopback_block: np.ndarray,
    mic_block: np.ndarray,
) -> NDArray[np.int16] | None:
    """Sum loopback stereo and duplicated mic; clip to int16.

    Returns None when there are no frames.
    """
    sys_st = stereo_float_from_multichannel(loopback_block)
    mic_m = mono_float_from_device(mic_block)
    mic_st = dup_mono_to_stereo(mic_m)
    n = min(sys_st.shape[0], mic_st.shape[0])
    if n == 0:
        return None
    sys_st = sys_st[:n]
    mic_st = mic_st[:n]
    mixed = sys_st + mic_st
    return cast(
        NDArray[np.int16],
        np.clip(mixed * 32_767.0, -32_767.0, 32_767.0).astype(np.int16),
    )


def interleaved_stereo_bytes(stereo_int16: NDArray[np.int16]) -> bytes:
    """WAV interleaved L,R,L,R… from shape (n, 2)."""
    return np.ascontiguousarray(stereo_int16).tobytes()
