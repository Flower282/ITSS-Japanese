from __future__ import annotations

from nicegui import ui


def page_title_block(
    *,
    title: str,
    subtitle: str | None = None,
    status: str | None = None,
    status_classes: str = "bg-blue-50 text-blue-600",
) -> ui.element:
    """Render a title block with optional subtitle and status badge."""
    with ui.column().classes("gap-1") as root:
        ui.label(title).classes("text-lg font-semibold text-slate-900")
        with ui.row().classes("items-center gap-2"):
            if subtitle:
                ui.label(subtitle).classes("text-xs text-slate-500")
            if status:
                ui.label(status).classes(
                    f"text-[10px] font-semibold px-2 py-1 rounded-full {status_classes}"
                )
    return root
