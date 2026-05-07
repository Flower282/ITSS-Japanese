from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from nicegui import ui

from src.frontend import state
from src.frontend.components.action_button import action_button
from src.frontend.components.app_top_bar import app_top_bar
from src.frontend.components.history_list_panel import history_list_panel
from src.frontend.components.side_nav_menu import side_nav_menu
from src.frontend.ui_state import UiState


def build_nav_items(active_route: str) -> list[dict]:
    """Build the default navigation items with an active route."""
    items = [
        {
            "label": "Tong quan",
            "icon": "grid_view",
            "route": "/",
        },
        {
            "label": "Dich hoi thoai",
            "icon": "translate",
            "route": "/translate",
        },
        {
            "label": "Phan tich hoi thoai",
            "icon": "analytics",
            "route": "/analysis",
        },
        {
            "label": "Giai thich van hoa",
            "icon": "menu_book",
            "route": "/culture",
        },
    ]
    for item in items:
        item["active"] = item["route"] == active_route
    return items


def default_history_items() -> list[dict]:
    """Default history list for the sidebar."""
    return [
        {
            "id": "tanaka",
            "label": "Tanaka-san",
            "subtitle": "10/04/2026 - Du an moi",
        },
        {
            "id": "yamada",
            "label": "Yamada-san",
            "subtitle": "09/04/2026 - Bao cao tuan",
        },
    ]


def render_background() -> None:
    """Render the shared gradient background and accent glows."""
    ui.element("div").style(
        "position: fixed; inset: 0; background: linear-gradient(135deg, #F7FAFF, "
        "#F3F7FF 45%, #F0F6FF); z-index: -1;"
    )
    ui.element("div").style(
        "position: fixed; top: -6rem; right: 2rem; width: 18rem; height: 18rem; "
        "background: #DCE7FF; filter: blur(80px); opacity: 0.7; z-index: -1;"
    )
    ui.element("div").style(
        "position: fixed; bottom: 2rem; left: 10rem; width: 16rem; height: 16rem; "
        "background: #FFE7C2; filter: blur(80px); opacity: 0.5; z-index: -1;"
    )


@contextmanager
def base_layout(
    *,
    active_nav: str,
    ui_state: UiState,
    title_slot: Callable[[], None] | None = None,
    top_bar_actions: list[dict] | None = None,
    on_search: Callable[[str], None] | None = None,
    on_locale_click: Callable[[], None] | None = None,
    on_locale_change: Callable[[str], None] | None = None,
    on_new_conversation: Callable[[], None] | None = None,
    on_history_select: Callable[[str | int], None] | None = None,
    history_items: list[dict] | None = None,
    search_placeholder: str = "Tim kiem hoi thoai, phan tich, van hoa...",
    search_history: list[str] | None = None,
    user_subtitle: str | None = "Nguoi Viet Nam",
) -> Iterator[None]:
    """Shared layout with background, sidebar, and header."""
    if not state.get_auth():
        ui.navigate.to("/login")
        return

    profile = state.get_profile() or {}
    user_name = profile.get("name") or profile.get("email") or "Người dùng"

    ui.add_head_html(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
          .tt-body { font-family: 'Space Grotesk', 'Segoe UI', sans-serif; }
        </style>
        """
    )

    nav_items = build_nav_items(active_nav)
    history_items = history_items or default_history_items()
    search_history = search_history or ["deadline", "bao cao", "lich su"]
    if ui_state.selected_history_id is None and history_items:
        ui_state.selected_history_id = history_items[0]["id"]

    def handle_search(value: str) -> None:
        ui_state.search_query = value
        if on_search:
            on_search(value)

    def handle_locale_change(value: str) -> None:
        ui_state.locale_code = value
        if on_locale_change:
            on_locale_change(value)

    def handle_history_select(history_id: str | int) -> None:
        ui_state.selected_history_id = history_id
        if on_history_select:
            on_history_select(history_id)

    def handle_new_conversation() -> None:
        if on_new_conversation:
            on_new_conversation()
        else:
            ui.navigate.to("/translate")

    with ui.element("div").classes("min-h-screen w-full tt-body"):
        render_background()

        with ui.row().classes("w-full min-h-screen"):
            with ui.column().classes(
                "w-72 shrink-0 bg-white border-r border-slate-100 p-4 gap-6"
            ):
                with ui.row().classes("items-center gap-2"):
                    ui.image("images/logoitsss.png").classes(
                        "h-9 w-9 rounded-lg shadow-sm"
                    )
                    ui.label("TrueTalk").classes("text-lg font-semibold text-blue-700")

                action_button(
                    label="Hoi thoai moi",
                    icon="add",
                    on_click=handle_new_conversation,
                ).classes("w-full")

                with ui.column().classes("gap-2"):
                    ui.label("TINH NANG CHINH").classes(
                        "text-xs text-slate-400 tracking-wide"
                    )
                    side_nav_menu(
                        items=nav_items,
                        on_navigate=lambda route: ui.navigate.to(route),
                    )

                history_list_panel(
                    title="LICH SU",
                    items=history_items,
                    selected_id=ui_state.selected_history_id,
                    on_select=handle_history_select,
                )

            with ui.column().classes("flex-1 p-6 gap-6"):
                app_top_bar(
                    search_placeholder=search_placeholder,
                    search_history=search_history,
                    user_name=user_name,
                    user_subtitle=user_subtitle,
                    locale_code=ui_state.locale_code,
                    language_options=["VN", "JP"],
                    active_language=ui_state.locale_code,
                    on_language_change=handle_locale_change,
                    title_slot=title_slot,
                    on_search=handle_search,
                    on_locale_click=on_locale_click,
                    actions=top_bar_actions,
                )
                yield
