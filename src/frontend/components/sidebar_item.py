from __future__ import annotations

from typing import Callable

from nicegui import ui


def sidebar_item(
    *,
    label: str,
    icon: str,
    active: bool = False,
    on_click: Callable[[], None] | None = None,
) -> ui.element:
    base = (
        "w-full flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition "
        "hover:bg-blue-50"
    )
    active_classes = " bg-blue-50 text-blue-700 font-semibold"
    inactive_classes = " text-slate-600"
    classes = base + (active_classes if active else inactive_classes)

    button = ui.element("button").classes(classes)
    if on_click:
        button.on("click", lambda: on_click())
    with button:
        ui.icon(icon).classes("text-lg")
        ui.label(label)
    return button
