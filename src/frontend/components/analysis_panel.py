from __future__ import annotations

from typing import Callable

from nicegui import ui


def analysis_panel(
    *,
    title: str,
    content: str | list[str] | None = None,
    tags: list[str] | None = None,
    actions: list[dict] | None = None,
    accent_classes: str = "border-slate-100 bg-white",
    header_action: Callable[[], None] | None = None,
) -> ui.element:
    """Render an analysis card with optional tags and actions."""
    container = ui.element("div").classes(
        f"w-full rounded-2xl border p-4 shadow-sm {accent_classes}"
    )

    with container:
        with ui.row().classes("items-center justify-between mb-3"):
            ui.label(title).classes("text-sm font-semibold text-slate-700")
            if header_action:
                header_action()

        if isinstance(content, list):
            with ui.column().classes("gap-1"):
                for line in content:
                    ui.label(f"• {line}").classes("text-sm text-slate-600")
        elif content:
            ui.label(content).classes("text-sm text-slate-600")

        if tags:
            with ui.row().classes("flex-wrap gap-2 mt-3"):
                for tag in tags:
                    ui.label(tag).classes(
                        "text-[10px] font-semibold px-2 py-0.5 rounded-full "
                        "bg-white border border-slate-200 text-slate-600"
                    )

        if actions:
            with ui.column().classes("gap-2 mt-3"):
                for action in actions:
                    button = ui.element("button").classes(
                        "w-full text-left rounded-xl border border-slate-200 "
                        "bg-white px-3 py-3 shadow-sm hover:bg-slate-50"
                    )
                    if action.get("on_click"):
                        button.on("click", lambda a=action: a["on_click"]())
                    with button:
                        ui.label(action.get("title", "")).classes(
                            "text-sm font-semibold text-slate-700"
                        )
                        ui.label(action.get("description", "")).classes(
                            "text-xs text-slate-500"
                        )

    return container
