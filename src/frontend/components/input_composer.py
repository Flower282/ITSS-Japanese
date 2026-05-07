from __future__ import annotations

from typing import Callable

from nicegui import ui


def input_composer(
    *,
    title: str,
    placeholder: str,
    value: str = "",
    on_change: Callable[[str], None] | None = None,
) -> ui.textarea:
    """Render the response input area and return the textarea element."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
        textarea = ui.textarea(value=value, placeholder=placeholder).classes(
            "w-full h-36 rounded-xl border border-slate-200 bg-white p-3 text-sm"
        )
        if on_change:
            textarea.on("update:model-value", lambda e: on_change(e.value))
        with ui.row().classes("items-center justify-between mt-3 text-xs text-slate-500"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("mic").classes("text-sm")
                ui.label("Giong noi")
            ui.label("Nhap de phan tich nhanh")

    return textarea
