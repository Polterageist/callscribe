"""Unit tests for loopback + mic stereo mix (pure numpy)."""

from __future__ import annotations

import numpy as np
import pytest

from callscribe.audio.stereo_mix import (
    dup_mono_to_stereo,
    interleaved_stereo_bytes,
    mix_loopback_mic_to_int16_stereo,
    mono_float_from_device,
    stereo_float_from_multichannel,
)


def test_stereo_from_multichannel_keeps_left_right() -> None:
    lb = np.array([[1.0, -1.0], [0.5, 0.25]], dtype=np.float32)
    out = stereo_float_from_multichannel(lb)
    assert out.shape == (2, 2)
    np.testing.assert_array_almost_equal(out[0], [1.0, -1.0])
    np.testing.assert_array_almost_equal(out[1], [0.5, 0.25])


def test_stereo_from_mono_duplicates() -> None:
    lb = np.array([0.3, -0.2], dtype=np.float32)
    out = stereo_float_from_multichannel(lb)
    assert out.shape == (2, 2)
    np.testing.assert_array_almost_equal(out[0], [0.3, 0.3])
    np.testing.assert_array_almost_equal(out[1], [-0.2, -0.2])


def test_mono_float_from_stereo_is_mean() -> None:
    mic = np.array([[1.0, -1.0], [0.4, 0.2]], dtype=np.float32)
    m = mono_float_from_device(mic)
    assert m.shape == (2,)
    np.testing.assert_array_almost_equal(m, [0.0, 0.3])


def test_mix_duplicates_mic_to_both_channels() -> None:
    """Loopback L/R preserved in sum when mic is centered mono (dup to L+R)."""
    lb = np.array([[0.1, -0.1]], dtype=np.float32)
    mic = np.array([[0.2]], dtype=np.float32)
    out = mix_loopback_mic_to_int16_stereo(lb, mic)
    assert out is not None
    assert out.shape == (1, 2)
    # mixed L = 0.1 + 0.2, R = -0.1 + 0.2
    expected_l = int(round((0.1 + 0.2) * 32767))
    expected_r = int(round((-0.1 + 0.2) * 32767))
    assert out[0, 0] == pytest.approx(expected_l, abs=2)
    assert out[0, 1] == pytest.approx(expected_r, abs=2)


def test_interleaved_bytes_order() -> None:
    stereo = np.array([[1000, -2000]], dtype=np.int16)
    b = interleaved_stereo_bytes(stereo)
    assert len(b) == 4
    assert b[0:2] == (1000).to_bytes(2, "little", signed=True)
    assert b[2:4] == (-2000).to_bytes(2, "little", signed=True)


def test_dup_mono_to_stereo() -> None:
    m = np.array([0.5, -0.5], dtype=np.float32)
    st = dup_mono_to_stereo(m)
    assert st.shape == (2, 2)
    np.testing.assert_array_almost_equal(st[:, 0], st[:, 1])
