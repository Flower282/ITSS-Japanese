from __future__ import annotations

from nicegui import ui


def analysis_row(
    *,
    icon: str,
    title: str,
    description: str,
    link_label: str,
    status_label: str,
    status_classes: str,
) -> ui.element:
    with ui.element("div").classes(
        "w-full rounded-xl border border-slate-100 bg-white p-4 shadow-sm"
    ) as row:
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.row().classes("items-start gap-3"):
                icon_box = ui.element("div").classes(
                    "h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center"
                )
                with icon_box:
                    ui.icon(icon).classes("text-slate-500")

                with ui.column().classes("gap-1"):
                    ui.label(title).classes("text-sm font-semibold text-slate-800")
                    ui.label(description).classes("text-xs text-slate-500 max-w-xl")
                    ui.link(link_label, "#").classes("text-xs text-blue-600")

            ui.label(status_label).classes(
                f"text-xs font-semibold px-2 py-1 rounded-full {status_classes}"
            )
    return row
