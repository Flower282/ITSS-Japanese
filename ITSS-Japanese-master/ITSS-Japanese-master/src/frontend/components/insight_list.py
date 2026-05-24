from __future__ import annotations

from nicegui import ui


def insight_list(*, items: list[dict], max_height: str | None = None) -> ui.element:
    """Render a list of cultural handbook entries with optional details."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        content = ui.column().classes("gap-3")
        if max_height:
            content.style(f"max-height: {max_height}; overflow-y: auto;")

        with content:
            for item in items:
                with ui.row().classes("items-start gap-3"):
                    icon_box = ui.element("div").classes(
                        "h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 "
                        "flex items-center justify-center"
                    )
                    with icon_box:
                        ui.icon(item.get("icon", "menu_book"))

                    with ui.column().classes("gap-1"):
                        ui.label(item.get("title", "")).classes(
                            "text-sm font-semibold text-slate-800"
                        )
                        ui.label(item.get("description", "")).classes(
                            "text-xs text-slate-500"
                        )
                        for tag in item.get("tags", []):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("check_circle").classes(
                                    "text-[10px] text-emerald-500"
                                )
                                ui.label(tag).classes("text-xs text-slate-500")
                        link_label = item.get("link_label")
                        if link_label:
                            ui.link(link_label, item.get("link_href", "#")).classes(
                                "text-xs text-blue-600"
                            )

    return container
