from __future__ import annotations

from typing import Callable

from nicegui import ui


def navigation_header(
    *,
    search_placeholder: str,
    user_name: str,
    locale_code: str,
    avatar_url: str | None = None,
    on_search: Callable[[str], None] | None = None,
    on_locale_click: Callable[[], None] | None = None,
    on_logout: Callable[[], None] | None = None,
) -> ui.element:
    with ui.row().classes("w-full items-center justify-between gap-4") as root:
        with ui.element("div").classes("flex-1"):
            search_input = (
                ui.input(placeholder=search_placeholder)
                .props("outlined dense rounded prepend-icon=search")
                .classes("w-full bg-white")
            )
            if on_search:
                search_input.on("update:model-value", lambda e: on_search(e.value))

        with ui.row().classes("items-center gap-3"):
            ui.label(user_name).classes("text-sm text-slate-500")

            if avatar_url:
                ui.image(avatar_url).classes("h-8 w-8 rounded-full object-cover")
            else:
                initials = "".join(
                    [part[0] for part in user_name.split() if part][:2]
                ).upper()
                initials = initials or "?"
                avatar = ui.element("div").classes(
                    "h-8 w-8 rounded-full bg-slate-200 text-xs text-slate-600 flex items-center justify-center"
                )
                with avatar:
                    ui.label(initials)

            badge = ui.element("div").classes(
                "h-8 w-8 rounded-full bg-blue-600 text-xs text-white flex items-center justify-center"
            )
            if on_locale_click:
                badge.on("click", lambda: on_locale_click())
            with badge:
                ui.label(locale_code)

            if on_logout:
                ui.button(icon="logout", on_click=on_logout).props(
                    "flat dense"
                ).classes("text-slate-500")

    return root
