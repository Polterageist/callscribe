from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest

from callscribe.app.controller import MenuSnapshot


@dataclass
class CreatedIcon:
    name: str
    title: str
    icon: Any
    menu: Any


class FakeMenuItem:
    def __init__(
        self,
        text: str,
        action: Callable[[], None],
        enabled: Callable[[], bool] | bool = True,
    ) -> None:
        self.text = text
        self.action = action
        self.enabled = enabled


class FakeMenu(tuple):
    pass


class FakeIcon:
    created: CreatedIcon | None = None

    def __init__(self, name: str, icon: Any, title: str, menu: Any) -> None:
        FakeIcon.created = CreatedIcon(
            name=name,
            title=title,
            icon=icon,
            menu=menu,
        )
        self.title = title
        self.menu = menu
        self.run_called = False
        self.stop_called = False

    def run(self) -> None:
        self.run_called = True

    def stop(self) -> None:
        self.stop_called = True

    def update_menu(self) -> None:
        # In real pystray this refreshes menu enable states
        return


def test_adapter_builds_menu_and_updates_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: monkeypatch pystray primitives inside our adapter module
    import callscribe.tray.pystray_tray as mod

    monkeypatch.setattr(
        mod,
        "pystray",
        type(
            "Pystray",
            (),
            {
                "Icon": FakeIcon,
                "Menu": FakeMenu,
                "MenuItem": FakeMenuItem,
            },
        ),
    )

    clicks: list[str] = []

    def on_start() -> None:
        clicks.append("start")

    def on_stop() -> None:
        clicks.append("stop")

    def on_open_output() -> None:
        clicks.append("open")

    def on_settings() -> None:
        clicks.append("settings")

    def on_quit() -> None:
        clicks.append("quit")

    adapter = mod.PystrayTrayAdapter(
        on_start=on_start,
        on_stop=on_stop,
        on_open_output_folder=on_open_output,
        on_settings=on_settings,
        on_quit=on_quit,
    )

    # Initial: IDLE-like menu snapshot
    adapter.set_menu(MenuSnapshot(start_enabled=True, stop_enabled=False))
    created = FakeIcon.created
    assert created is not None

    labels = [item.text for item in created.menu]
    assert labels == [
        "Start recording",
        "Stop recording",
        "Open output folder",
        "Settings…",
        "Quit",
    ]

    # Enabled flags should reflect snapshot via callables
    start_item = created.menu[0]
    stop_item = created.menu[1]
    assert callable(start_item.enabled)
    assert callable(stop_item.enabled)
    assert start_item.enabled() is True
    assert stop_item.enabled() is False

    # Update to Recording-like snapshot
    adapter.set_menu(MenuSnapshot(start_enabled=False, stop_enabled=True))
    assert start_item.enabled() is False
    assert stop_item.enabled() is True

    # Actions are wired
    created.menu[0].action()
    created.menu[3].action()
    created.menu[4].action()
    assert clicks == ["start", "settings", "quit"]


def test_adapter_sets_tooltip_and_run_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    import callscribe.tray.pystray_tray as mod

    monkeypatch.setattr(
        mod,
        "pystray",
        type(
            "Pystray",
            (),
            {
                "Icon": FakeIcon,
                "Menu": FakeMenu,
                "MenuItem": FakeMenuItem,
            },
        ),
    )

    adapter = mod.PystrayTrayAdapter(
        on_start=lambda: None,
        on_stop=lambda: None,
        on_open_output_folder=lambda: None,
        on_settings=lambda: None,
        on_quit=lambda: None,
    )

    adapter.set_tooltip("Idle")
    assert FakeIcon.created is not None
    assert FakeIcon.created.title == "Idle"

    adapter.run()
    assert adapter._icon.run_called is True  # type: ignore[attr-defined]

    adapter.stop()
    assert adapter._icon.stop_called is True  # type: ignore[attr-defined]

