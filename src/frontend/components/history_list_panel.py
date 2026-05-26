from __future__ import annotations

from typing import Callable

from nicegui import ui


def history_list_panel(
    *,
    title: str | None,
    items: list[dict],
    on_select: Callable[[str | int], None] | None = None,
    selected_id: str | int | None = None,
    on_refresh: Callable[[], None] | None = None,
) -> ui.element:
    """Render the history list panel with selectable items."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        if title:
            with ui.row().classes("items-center justify-between mb-3"):
                ui.label(title).classes("text-xs text-slate-400 tracking-wide")
                refresh_btn = ui.button(icon="refresh").props(
                    "flat round dense"
                ).classes("text-slate-400")
                if on_refresh:
                    refresh_btn.on("click", on_refresh)

        ui.add_head_html(
            """
            <style>
                .history-scrollbar {
                    scrollbar-width: thin;
                    scrollbar-color: #cbd5e1 transparent;
                }
                .history-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .history-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .history-scrollbar::-webkit-scrollbar-thumb {
                    background: #cbd5e1;
                    border-radius: 4px;
                }
                .history-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #94a3b8;
                }
            </style>
            """
        )
        with ui.column().classes("w-full gap-3 overflow-y-auto history-scrollbar pr-1").style("max-height: 320px;"):
            if not items:
                ui.label("Chưa có hội thoại.").classes("text-xs text-slate-400")
            for item in items:
                is_active = item.get("id") == selected_id
                button = ui.element("button").classes(
                    "w-full text-left rounded-xl border px-3 py-2 transition "
                    + (
                        "border-blue-200 bg-blue-50"
                        if is_active
                        else "border-slate-100 hover:bg-slate-50"
                    )
                )
                if on_select:
                    button.on("click", lambda i=item: on_select(i["id"]))
                with button:
                    ui.label(item.get("label", "")).classes(
                        "text-sm font-semibold text-slate-700"
                    )
                    ui.label(item.get("subtitle", "")).classes(
                        "text-xs text-slate-400"
                    )

    return container
