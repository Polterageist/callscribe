from __future__ import annotations

from collections.abc import Callable

import pystray  # type: ignore[import-untyped]
from PIL import Image

from callscribe.app.controller import MenuSnapshot, TrayUI
from callscribe.tray.app_icon import default_tray_icon


class PystrayTrayAdapter(TrayUI):
    def __init__(
        self,
        *,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_open_output_folder: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
        icon: Image.Image | None = None,
    ) -> None:
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_open_output_folder = on_open_output_folder
        self._on_settings = on_settings
        self._on_quit = on_quit

        self._snapshot = MenuSnapshot(start_enabled=False, stop_enabled=False)

        self._icon = pystray.Icon(
            "callscribe",
            icon or default_tray_icon(),
            title="Callscribe",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        items = (
            pystray.MenuItem(
                "Start recording",
                lambda: self._on_start(),
                enabled=lambda _item=None: self._snapshot.start_enabled,
            ),
            pystray.MenuItem(
                "Stop recording",
                lambda: self._on_stop(),
                enabled=lambda _item=None: self._snapshot.stop_enabled,
            ),
            pystray.MenuItem("Open output folder", lambda: self._on_open_output_folder()),
            pystray.MenuItem("Settings…", lambda: self._on_settings()),
            pystray.MenuItem("Quit", lambda: self._on_quit()),
        )
        # Real pystray expects `Menu(*items)`. Our tests use a lightweight fake menu
        # that behaves like a tuple; accept both forms.
        try:
            return pystray.Menu(*items)
        except TypeError:
            return pystray.Menu(items)

    def run(self) -> None:
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()

    def set_tooltip(self, text: str) -> None:
        self._icon.title = text
        created = getattr(type(self._icon), "created", None)
        if created is not None:
            try:
                created.title = text
            except Exception:
                pass

    def set_menu(self, snapshot: MenuSnapshot) -> None:
        self._snapshot = snapshot
        # Rebuild menu so enabled callables read latest snapshot.
        self._icon.menu = self._build_menu()
        update_menu = getattr(self._icon, "update_menu", None)
        if callable(update_menu):
            update_menu()

