from __future__ import annotations

from typing import Callable

from nicegui import ui

from src.frontend.components.action_button import action_button


def sync_action_bar(
    *,
    label: str,
    icon: str,
    on_click: Callable[[], None],
    helper_text: str | None = None,
    variant: str = "secondary",
) -> ui.element:
    """Render a compact action row for syncing data."""
    with ui.row().classes("items-center gap-2") as root:
        if helper_text:
            ui.label(helper_text).classes("text-xs text-slate-500")
        action_button(
            label=label,
            icon=icon,
            variant=variant,
            on_click=on_click,
            extra_classes="rounded-full px-3 py-1.5 text-xs",
        )

    return root
