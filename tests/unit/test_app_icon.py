"""Unit tests for tray/window icon helpers."""

from __future__ import annotations

import numpy as np
from PIL import Image

from callscribe.tray.app_icon import invert_rgba_preserving_alpha, rasterize_logo_svg


def test_invert_rgba_preserving_alpha() -> None:
    img = Image.fromarray(
        np.array([[[10, 20, 30, 255], [0, 0, 0, 0]]], dtype=np.uint8),
        mode="RGBA",
    )
    out = invert_rgba_preserving_alpha(img)
    px0 = out.getpixel((0, 0))
    px1 = out.getpixel((1, 0))
    assert px0 == (245, 235, 225, 255)
    assert px1 == (255, 255, 255, 0)


def test_rasterize_logo_svg_minimal() -> None:
    svg = b"""<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
        <rect width="32" height="32" fill="#010203"/>
    </svg>"""
    pil = rasterize_logo_svg(svg, 32)
    assert pil.size == (32, 32)
    assert pil.mode == "RGBA"
    assert pil.getpixel((16, 16))[0:3] == (1, 2, 3)
