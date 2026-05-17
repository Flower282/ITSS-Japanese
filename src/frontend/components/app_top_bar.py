from __future__ import annotations

from typing import Callable, Union

from nicegui import ui

from src.frontend.components.action_button import action_button


def app_top_bar(
    *,
    search_placeholder: str,
    user_name: str,
    user_subtitle: str | None = None,
    locale_code: str,
    title_slot: Callable[[], None] | None = None,
    on_search: Callable[[str], None] | None = None,
    on_locale_click: Callable[[], None] | None = None,
    actions: list[dict] | None = None,
    search_history: list[str] | None = None,
    logo_src: str | None = None,
    on_logo_click: Callable[[], None] | None = None,
    language_options: Union[list[str], dict[str, str]] | None = None,
    active_language: str | None = None,
    on_language_change: Callable[[str], None] | None = None,
    primary_action_label: str | None = None,
    on_primary_action: Callable[[], None] | None = None,
) -> ui.element:
    """Render the top bar with search, title, locale, and actions."""
    with ui.row().classes(
        "w-full items-center justify-between gap-6 rounded-2xl border "
        "border-slate-100 bg-white/90 p-4 shadow-sm backdrop-blur"
    ) as root:
        with ui.row().classes("flex-1 items-center gap-4"):
            if logo_src:
                logo = ui.image(logo_src).classes("h-8 w-8 rounded-lg")
                if on_logo_click:
                    logo.on("click", lambda: on_logo_click())

            with ui.element("div").classes("flex-1 max-w-md"):
                search_input = (
                    ui.input(placeholder=search_placeholder)
                    .props("outlined dense rounded prepend-icon=search")
                    .classes("w-full bg-white")
                )
                if search_history:
                    search_input.props("list=search-history")
                    with ui.element("datalist").props("id=search-history"):
                        for item in search_history:
                            ui.element("option").props(f"value={item}")
                if on_search:
                    search_input.on(
                        "keydown.enter",
                        lambda: on_search(search_input.value or ""),
                    )
                    search_input.props("append-icon=search")
                    search_input.on(
                        "click:append",
                        lambda: on_search(search_input.value or ""),
                    )
            if title_slot:
                title_slot()

        with ui.row().classes("items-center gap-3"):
            if primary_action_label:
                action_button(
                    label=primary_action_label,
                    icon="add",
                    variant="primary",
                    on_click=on_primary_action,
                )

            for action in actions or []:
                action_button(
                    label=action.get("label", ""),
                    icon=action.get("icon"),
                    variant=action.get("variant", "secondary"),
                    on_click=action.get("on_click"),
                )

            with ui.element("div").classes(
                "flex items-center gap-3 rounded-xl border border-slate-200 "
                "bg-white px-3 py-2"
            ):
                ui.icon("person").classes("text-blue-600")
                with ui.column().classes("gap-0"):
                    ui.label(user_name).classes("text-xs font-semibold text-slate-700")
                    if user_subtitle:
                        ui.label(user_subtitle).classes("text-[11px] text-slate-400")
                if language_options:
                    selector = ui.select(
                        options=language_options,
                        value=active_language or locale_code,
                        on_change=lambda e: on_language_change(e.value) if on_language_change else None,
                    ).classes("text-xs")
                    selector.props("dense outlined")
                else:
                    badge = ui.element("div").classes(
                        "h-8 w-8 rounded-full bg-blue-600 text-white "
                        "text-xs font-semibold flex items-center justify-center"
                    )
                    if on_locale_click:
                        badge.on("click", lambda: on_locale_click())
                    with badge:
                        ui.label(locale_code)

    return root
