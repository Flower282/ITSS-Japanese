from __future__ import annotations

from nicegui import ui


def stats_cards_row(*, cards: list[dict], layout: str = "row") -> ui.element:
    """Render a row or grid of compact KPI cards."""
    container = ui.row() if layout == "row" else ui.grid()
    container.classes("w-full gap-4")

    with container:
        for card in cards:
            accent_classes = card.get("accent_classes", "border-slate-100 bg-white")
            value_classes = card.get("value_classes", "text-slate-800")
            with ui.element("div").classes(
                f"flex-1 rounded-xl border p-4 {accent_classes}"
            ):
                ui.label(card.get("title", "")).classes(
                    "text-[11px] uppercase tracking-wide text-slate-500"
                )
                ui.label(card.get("value", "")).classes(
                    f"text-2xl font-semibold {value_classes}"
                )
                subtitle = card.get("subtitle")
                if subtitle:
                    ui.label(subtitle).classes("text-xs text-slate-500")

    return container
