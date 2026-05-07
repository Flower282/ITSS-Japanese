from __future__ import annotations

from nicegui import ui


def conversation_history_view(
    *,
    title: str,
    messages: list[dict],
    max_height: str | None = None,
) -> ui.element:
    """Render a scrollable conversation history view."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
        scroll = ui.column().classes("gap-3 overflow-y-auto pr-1")
        if max_height:
            scroll.style(f"max-height: {max_height};")

        with scroll:
            for message in messages:
                role = message.get("role")
                card_classes = (
                    "border-amber-200 bg-amber-50"
                    if role == "listen"
                    else "border-sky-200 bg-sky-50"
                )
                with ui.element("div").classes(
                    f"rounded-xl border p-3 {card_classes}"
                ):
                    with ui.row().classes(
                        "items-center justify-between text-[11px] uppercase text-slate-500"
                    ):
                        ui.label(message.get("label", ""))
                        ui.label(message.get("time", ""))
                    ui.label(message.get("text", "")).classes("text-sm text-slate-700")
                    with ui.row().classes("flex-wrap gap-2 mt-2"):
                        for tag in message.get("tags", []):
                            ui.label(tag).classes(
                                "text-[10px] font-semibold px-2 py-0.5 rounded-full "
                                "bg-white text-slate-500"
                            )

    return container
