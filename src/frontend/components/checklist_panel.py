from __future__ import annotations

from nicegui import ui


def checklist_panel(
    *,
    title: str,
    items: list[str],
    accent_classes: str = "border-slate-100 bg-white",
    icon: str = "task_alt",
    icon_classes: str = "text-emerald-500",
) -> ui.element:
    """Render a checklist style panel for summaries and action items."""
    container = ui.element("div").classes(
        f"w-full rounded-2xl border p-4 shadow-sm {accent_classes}"
    )

    with container:
        ui.label(title).classes("text-sm font-semibold text-slate-700 mb-3")
        with ui.column().classes("gap-2"):
            for item in items:
                with ui.row().classes("items-start gap-2"):
                    ui.icon(icon).classes(f"text-sm {icon_classes}")
                    ui.label(item).classes("text-sm text-slate-600")

    return container
