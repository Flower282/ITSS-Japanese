from __future__ import annotations

from typing import Callable

from nicegui import ui


def scenario_panel(
    *,
    title: str,
    scenarios: list[dict],
    max_height: str | None = None,
    header_action: Callable[[], None] | None = None,
) -> ui.element:
    """Render the scenario analysis panel with scrollable cases."""
    ui.add_head_html(
        """
        <style>
            .custom-scrollbar {
                scrollbar-width: thin;
                scrollbar-color: #cbd5e1 transparent;
            }
            .custom-scrollbar::-webkit-scrollbar {
                width: 6px;
            }
            .custom-scrollbar::-webkit-scrollbar-track {
                background: transparent;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb {
                background: #cbd5e1;
                border-radius: 999px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                background: #94a3b8;
            }
        </style>
        """
    )
    container = ui.element("div").classes(
        "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
    )

    with container:
        with ui.row().classes("items-center justify-between mb-4"):
            ui.label(title).classes("text-sm font-semibold text-slate-700")
            if header_action:
                header_action()

        scroll = ui.column().classes("gap-4 overflow-y-auto pr-2 custom-scrollbar")
        if max_height:
            scroll.style(f"max-height: {max_height};")

        with scroll:
            for scenario in scenarios:
                accent_classes = scenario.get(
                    "accent_classes", "border-amber-100 bg-amber-50/70"
                )
                with ui.element("div").classes(
                    f"rounded-2xl border p-4 {accent_classes}"
                ):
                    with ui.row().classes("items-start gap-3"):
                        badge = ui.element("div").classes(
                            "h-7 w-7 rounded-full bg-white text-slate-600 "
                            "flex items-center justify-center text-xs font-semibold"
                        )
                        with badge:
                            ui.label(str(scenario.get("index", "")))

                        with ui.column().classes("gap-1"):
                            ui.label(scenario.get("category", "")).classes(
                                "text-[11px] uppercase tracking-wide text-slate-500"
                            )
                            ui.label(scenario.get("phrase", "")).classes(
                                "text-sm font-semibold text-slate-800"
                            )

                    with ui.row().classes("gap-3 mt-3"):
                        with ui.element("div").classes(
                            "flex-1 rounded-xl border border-slate-100 bg-white p-3"
                        ):
                            with ui.row().classes("items-center gap-2 mb-2"):
                                ui.icon("info").classes("text-blue-500 text-sm")
                                ui.label("Ý NGHĨA THỰC TẾ").classes(
                                    "text-[11px] font-semibold text-blue-600"
                                )
                            ui.label(scenario.get("meaning", "")).classes(
                                "text-sm text-slate-600"
                            )

                        with ui.element("div").classes(
                            "flex-1 rounded-xl border border-slate-100 bg-white p-3"
                        ):
                            with ui.row().classes("items-center gap-2 mb-2"):
                                ui.icon("done_all").classes("text-emerald-500 text-sm")
                                ui.label("CÁCH ỨNG PHÓ").classes(
                                    "text-[11px] font-semibold text-emerald-600"
                                )
                            ui.label(scenario.get("response", "")).classes(
                                "text-sm text-slate-600"
                            )

    return container
