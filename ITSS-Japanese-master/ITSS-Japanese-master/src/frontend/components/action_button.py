from __future__ import annotations

from typing import Callable

from nicegui import ui


VARIANT_CLASSES = {
    "primary": "bg-blue-600 text-white shadow-sm hover:bg-blue-700",
    "secondary": "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50",
    "ghost": "text-slate-600 hover:bg-slate-100",
}

VARIANT_PROPS = {
    "primary": "unelevated",
    "secondary": "outline",
    "ghost": "flat",
}


def action_button(
    *,
    label: str,
    icon: str | None = None,
    variant: str = "primary",
    on_click: Callable[[], None] | None = None,
    disabled: bool = False,
    extra_classes: str = "",
) -> ui.button:
    """Render a styled action button for the TrueTalk UI."""
    button = ui.button(label, on_click=on_click, icon=icon)
    button.props(VARIANT_PROPS.get(variant, "unelevated"))
    button.classes(
        "rounded-xl px-4 py-2 text-sm font-semibold gap-2 "
        + VARIANT_CLASSES.get(variant, VARIANT_CLASSES["primary"])
    )
    if extra_classes:
        button.classes(extra_classes)
    if disabled:
        button.disable()
        button.classes("opacity-60 cursor-not-allowed")
    return button
