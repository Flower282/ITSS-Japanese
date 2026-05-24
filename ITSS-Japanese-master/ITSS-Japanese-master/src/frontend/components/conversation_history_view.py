from __future__ import annotations

from nicegui import ui


def conversation_history_view(
    *,
    title: str,
    messages: list[dict],
    max_height: str | None = None,
) -> ui.element:
    """Scrollable chat history with optional translation and insight blocks."""
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
        scroll = ui.column().classes("gap-3 overflow-y-auto pr-1 w-full")
        if max_height:
            scroll.style(f"max-height: {max_height};")

        with scroll:
            if not messages:
                ui.label("Chưa có tin nhắn trong hội thoại này.").classes(
                    "text-xs text-slate-500"
                )
            for message in messages:
                role = message.get("role", "you")
                is_listen = role == "listen"
                card_classes = (
                    "border-amber-200 bg-amber-50"
                    if is_listen
                    else "border-sky-200 bg-sky-50"
                )
                with ui.element("div").classes(
                    f"rounded-xl border p-3 w-full {card_classes}"
                ):
                    with ui.row().classes(
                        "items-center justify-between text-[11px] uppercase "
                        "text-slate-500 w-full"
                    ):
                        ui.label(message.get("label", ""))
                        ui.label(message.get("time", ""))

                    ui.label(message.get("text", "")).classes(
                        "text-sm text-slate-800 mt-1 whitespace-pre-wrap"
                    )

                    translation = message.get("translation")
                    if translation:
                        ui.label(translation).classes(
                            "text-sm text-slate-600 mt-2 whitespace-pre-wrap"
                        )

                    note = message.get("note")
                    if note:
                        note_classes = (
                            "border-amber-300 bg-amber-100/80 text-amber-900"
                            if is_listen
                            else "border-emerald-300 bg-emerald-50 text-emerald-900"
                        )
                        with ui.element("div").classes(
                            f"mt-2 rounded-lg border px-3 py-2 text-xs "
                            f"{note_classes}"
                        ):
                            ui.label(note).classes("whitespace-pre-wrap")

                    tags = [t for t in (message.get("tags") or []) if t]
                    if tags:
                        with ui.row().classes("flex-wrap gap-2 mt-2"):
                            for tag in tags:
                                ui.label(tag).classes(
                                    "text-[10px] font-semibold px-2 py-0.5 "
                                    "rounded-full bg-white text-slate-600"
                                )

    return container
