from __future__ import annotations

from nicegui import ui


def stat_card(
    *,
    label: str,
    value: str,
    icon: str,
    trend: str | None = None,
    accent_classes: str = "bg-blue-50 text-blue-600",
    trend_classes: str = "text-emerald-600",
) -> ui.element:
    with ui.element("div").classes(
        "w-full rounded-xl bg-white p-4 shadow-sm border border-slate-100"
    ) as card:
        with ui.row().classes("w-full items-start justify-between"):
            icon_box = ui.element("div").classes(
                f"h-10 w-10 rounded-xl flex items-center justify-center {accent_classes}"
            )
            with icon_box:
                ui.icon(icon)
            if trend:
                ui.label(trend).classes(f"text-xs font-semibold {trend_classes}")
        ui.label(value).classes("text-2xl font-semibold text-slate-800 mt-4")
        ui.label(label).classes("text-xs text-slate-500")
    return card
