from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.frontend.components.sidebar_item import sidebar_item


def side_nav_menu(
    *,
    items: list[dict],
    on_navigate: Callable[[str], None] | None = None,
    footer_actions: list[dict] | None = None,
) -> ui.element:
    """Render a side navigation list with active states."""
    with ui.column().classes("gap-2") as root:
        for item in items:
            route = item.get("route")
            sidebar_item(
                label=item.get("label", ""),
                icon=item.get("icon", ""),
                active=item.get("active", False),
                on_click=(
                    (lambda r=route: on_navigate(r))
                    if on_navigate and route
                    else None
                ),
            )

        if footer_actions:
            ui.separator().classes("my-2")
            for action in footer_actions:
                button = ui.element("button").classes(
                    "w-full flex items-center gap-3 rounded-xl px-3 py-2 "
                    "text-sm text-slate-600 hover:bg-blue-50"
                )        
                if action.get("on_click"):
                    button.on("click", lambda a=action: a["on_click"]())
                with button:
                    icon = action.get("icon")
                    if icon:
                        ui.icon(icon).classes("text-lg")
                    ui.label(action.get("label", ""))

    return root
