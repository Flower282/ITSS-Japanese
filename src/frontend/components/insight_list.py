from __future__ import annotations

from typing import Callable
from nicegui import ui


def insight_list(
    *,
    items: list[dict],
    max_height: str | None = None,
    on_link_click: Callable[[dict], None] | None = None,
) -> ui.element:
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
                with ui.row().classes("items-start gap-3 w-full flex-nowrap mb-2"):
                    icon_box = ui.element("div").classes(
                        "h-12 w-12 rounded-2xl bg-emerald-50 "
                        "flex items-center justify-center flex-shrink-0"
                    )
                    with icon_box:
                        icon = item.get("icon", "menu_book")
                        # If it is an emoji, render as label, else render as ui.icon
                        if len(icon) == 1 or icon in ["🙇", "💬"]:
                            ui.label(icon).classes("text-2xl")
                        else:
                            ui.icon(icon).classes("text-xl text-emerald-600")

                    with ui.column().classes("gap-2 flex-1"):
                        ui.label(item.get("title", "")).classes(
                            "text-sm font-bold text-slate-800"
                        )
                        ui.label(item.get("description", "")).classes(
                            "text-xs text-slate-500 leading-relaxed"
                        )
                        
                        # Render tags list
                        if item.get("tags"):
                            with ui.column().classes("w-full gap-2 mt-1"):
                                for tag in item.get("tags", []):
                                    with ui.row().classes(
                                        "items-center gap-2 rounded-xl bg-slate-50 border border-slate-100/60 px-3 py-2 w-full"
                                    ):
                                        ui.icon("assignment").classes(
                                            "text-xs text-slate-400"
                                        )
                                        ui.label(tag).classes("text-xs text-slate-600 font-medium")

                        link_label = item.get("link_label")
                        if link_label:
                            if on_link_click:
                                ui.link(link_label, "javascript:void(0)").classes(
                                    "text-xs text-blue-600 hover:text-blue-800 transition-colors font-medium mt-1"
                                ).on("click", lambda e, it=item: on_link_click(it))
                            else:
                                ui.link(link_label, item.get("link_href", "#")).classes(
                                    "text-xs text-blue-600 hover:text-blue-800 transition-colors font-medium mt-1"
                                )

    return container
