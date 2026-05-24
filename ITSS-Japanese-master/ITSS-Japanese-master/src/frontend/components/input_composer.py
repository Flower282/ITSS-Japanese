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
    """Editable textarea for drafting a reply."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
        textarea = (
            ui.textarea(value=value or "", placeholder=placeholder)
            .props("outlined autogrow clearable")
            .classes("w-full")
            .style("min-height: 9rem")
        )
        if on_change:
            textarea.on("update:model-value", lambda e: on_change(e.value or ""))

    return textarea
