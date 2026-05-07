from __future__ import annotations

from typing import Callable

from nicegui import ui


ACTIVE_CLASSES = "bg-blue-600 text-white shadow-sm"
INACTIVE_CLASSES = "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"


def recommendation_chips(
    *,
    options: list[str],
    selected: list[str],
    on_change: Callable[[list[str]], None] | None = None,
) -> ui.element:
    """Render selectable tone chips with multi-select behavior."""
    selected_set = set(selected)
    buttons: dict[str, ui.element] = {}

    def set_state(option: str, is_active: bool) -> None:
        button = buttons[option]
        if is_active:
            button.classes(add=ACTIVE_CLASSES, remove=INACTIVE_CLASSES)
        else:
            button.classes(add=INACTIVE_CLASSES, remove=ACTIVE_CLASSES)

    def toggle_option(option: str) -> None:
        if option in selected_set:
            selected_set.remove(option)
        else:
            selected_set.add(option)
        set_state(option, option in selected_set)
        if on_change:
            on_change(sorted(selected_set))

    with ui.row().classes("flex-wrap gap-2") as root:
        for option in options:
            button = ui.element("button").classes(
                "rounded-full px-3 py-1 text-xs font-semibold transition"
            )
            button.on("click", lambda o=option: toggle_option(o))
            with button:
                ui.label(option)
            buttons[option] = button
            set_state(option, option in selected_set)

    return root
