from __future__ import annotations

from callscribe.app.controller import MenuSnapshot, TrayUI


class NullTray(TrayUI):
    def run(self) -> None:
        return

    def stop(self) -> None:
        return

    def set_tooltip(self, text: str) -> None:
        return

    def set_menu(self, snapshot: MenuSnapshot) -> None:
        return

