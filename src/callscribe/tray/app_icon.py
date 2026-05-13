"""Load ``logo.svg`` for tray / Tk; invert for dark Windows shell (light taskbar = unchanged)."""

from __future__ import annotations

import io
import logging
import sys
from importlib import resources
from typing import Any, cast

from PIL import Image, ImageDraw, ImageOps

logger = logging.getLogger(__name__)

_TRAY_ICON_SIZE = 128


def default_tray_icon() -> Image.Image:
    """Minimal placeholder if SVG raster fails."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(0, 0, 0, 255))
    d.text((26, 18), "C", fill=(255, 255, 255, 255))
    return img


def windows_shell_prefers_dark_icons() -> bool:
    """True when Windows shell is in dark mode (taskbar dark → use light/inverted tray art)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        try:
            value, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
            return int(value) == 0
        finally:
            key.Close()
    except OSError:
        return False


def invert_rgba_preserving_alpha(img: Image.Image) -> Image.Image:
    """Invert RGB channels; keep alpha (for dark-on-light logo on dark taskbar)."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    inv = ImageOps.invert(rgb)
    r2, g2, b2 = inv.split()
    return Image.merge("RGBA", (r2, g2, b2, a))


def _logo_svg_bytes() -> bytes:
    return resources.files("callscribe.resources").joinpath("logo.svg").read_bytes()


def rasterize_logo_svg(svg_bytes: bytes, size: int) -> Image.Image:
    import cairosvg

    png = cairosvg.svg2png(bytestring=svg_bytes, output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def load_tray_icon_pil(*, size: int = _TRAY_ICON_SIZE) -> Image.Image:
    """Rasterize bundled logo for ``pystray``; invert on dark Windows shell."""
    try:
        raw = rasterize_logo_svg(_logo_svg_bytes(), size)
    except Exception as e:
        logger.warning("Could not rasterize logo.svg, using placeholder: %s", e)
        return default_tray_icon()
    if windows_shell_prefers_dark_icons():
        raw = invert_rgba_preserving_alpha(raw)
    return raw


def apply_tk_window_icon(window: object, *, size: int = 64) -> None:
    """Set window/taskbar decoration icon from logo (Tk ``iconphoto``)."""
    try:
        from PIL import ImageTk  # noqa: PLC0415
    except ImportError:
        return

    try:
        inner = max(256, size * 4)
        raw = rasterize_logo_svg(_logo_svg_bytes(), inner)
        if windows_shell_prefers_dark_icons():
            raw = invert_rgba_preserving_alpha(raw)
        pil = raw.resize((size, size), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil)
    except Exception as e:
        logger.debug("Tk window icon skipped: %s", e)
        return

    w = cast(Any, window)
    try:
        w.iconphoto(True, photo)
    except Exception as e:
        logger.debug("iconphoto failed: %s", e)
        return
    w._callscribe_icon_photo = photo
