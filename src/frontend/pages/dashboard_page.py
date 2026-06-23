from __future__ import annotations

from nicegui import app, ui

from src.core.i18n import _, get_user_language, nav, validate_language_or_default
from src.frontend import state
from src.frontend.components.components import analysis_row, stat_card
from src.frontend.layouts.layout import base_layout
from src.frontend.services.conversation_service import (
    load_conversation_history,
    load_dashboard_overview,
)
from src.frontend.ui_state import UiState


@ui.page("/")
def dashboard_page() -> None:
    layout_state = UiState()
    lang = validate_language_or_default(get_user_language())

    page_state: dict = {
        "overview": None,
        "history_items": [],
        "loading": True,
    }

    def handle_logout() -> None:
        state.clear_auth()
        app.storage.user.clear()
        ui.navigate.to("/login")

    with ui.dialog() as logout_dialog, ui.card().classes("min-w-[320px]"):
        ui.label(_('logout_confirm', lang)).classes(
            "text-sm font-medium text-slate-700"
        )
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(_('cancel', lang), on_click=logout_dialog.close).props("outline")
            ui.button(_('logout', lang), on_click=handle_logout).props("color=negative")

    async def handle_search(value: str) -> None:
        if value.strip():
            ui.navigate.to(nav(f"/analysis?search={value.strip()}", lang))

    @ui.refreshable
    def content() -> None:
        overview = page_state.get("overview") or {}
        insights = overview.get("insights") or []

        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(_('overview', lang)).classes(
                    "text-2xl font-semibold text-slate-800"
                )
                ui.label(_('overview_subtitle', lang)).classes(
                    "text-sm text-slate-500"
                )
            ui.button(_('lang_btn', lang), icon="language").props(
                "outline"
            ).classes("rounded-xl text-slate-600")

        if page_state["loading"]:
            with ui.row().classes("w-full justify-center py-16"):
                ui.spinner(size="lg")
            return

        with ui.grid().classes(
            "w-full gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
        ):
            stat_card(
                label=_('total_conversations', lang),
                value=str(overview.get("total_conversations", 0)),
                icon="chat_bubble",
                trend=f"+{_('this_week', lang)}",
                accent_classes="bg-blue-50 text-blue-600",
            )
            stat_card(
                label=_('ai_accuracy', lang),
                value=f"{overview.get('understanding_score', 0)}%",
                icon="auto_awesome",
                trend=f"+{_('this_week', lang)}",
                accent_classes="bg-purple-50 text-purple-600",
            )
            stat_card(
                label=_('suggestions_to_review', lang),
                value=str(overview.get("suggestions_count", 0)),
                icon="lightbulb",
                trend=_('need_review', lang),
                accent_classes="bg-amber-50 text-amber-600",
                trend_classes="text-amber-600",
            )
            stat_card(
                label=_('interaction_time', lang),
                value=str(overview.get("interaction_time", "0h")),
                icon="schedule",
                trend=_('this_month', lang),
                accent_classes="bg-emerald-50 text-emerald-600",
                trend_classes="text-emerald-600",
            )

        with ui.element("div").classes(
            "w-full rounded-xl bg-white p-4 shadow-sm border border-slate-100"
        ):
            with ui.row().classes("items-center justify-between"):
                ui.label(_('ai_analysis_title', lang)).classes(
                    "text-sm font-semibold text-slate-800"
                )
                latest_id = overview.get("latest_analysis_id")
                report_href = (
                    nav(f"/analysis/{latest_id}", lang) if latest_id else nav("/analysis", lang)
                )
                ui.link(_('view_full_report', lang), report_href).classes(
                    "text-xs text-blue-600"
                )

            with ui.column().classes("mt-4 gap-3"):
                if not insights:
                    ui.label(_('no_analysis_feedback', lang)).classes(
                        "text-sm text-slate-500"
                    )
                for item in insights:
                    analysis_row(
                        icon=item.get("icon", "auto_awesome"),
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        link_label=item.get("link_label", _('view_details', lang)),
                        status_label=item.get("status_label", ""),
                        status_classes=item.get(
                            "status_classes", "bg-slate-50 text-slate-600"
                        ),
                        link_href=report_href,
                    )

    async def load_page_data() -> None:
        cache_key = f"dashboard_data_{lang}"
        cached = app.storage.user.get(cache_key)
        if cached:
            page_state["history_items"] = cached.get("history_items", [])
            page_state["overview"] = cached.get("overview", {})
            page_state["loading"] = False
            content.refresh()
        else:
            page_state["loading"] = True
            content.refresh()

        try:
            page_state["history_items"] = await load_conversation_history()
            page_state["overview"] = await load_dashboard_overview(lang)
            app.storage.user[cache_key] = {
                "history_items": page_state["history_items"],
                "overview": page_state["overview"],
            }
        except Exception as exc:
            ui.notify(f"{_('failed_analysis_load', lang)}: {exc}", type="negative")
            page_state["overview"] = {
                "total_conversations": 0,
                "understanding_score": 0,
                "suggestions_count": 0,
                "interaction_time": "0h",
                "latest_analysis_id": None,
                "insights": [],
            }
        page_state["loading"] = False
        shell.refresh()

    @ui.refreshable
    def shell() -> None:
        with base_layout(
            active_nav="/",
            ui_state=layout_state,
            history_items=page_state.get("history_items", []),
            on_history_select=lambda cid: ui.navigate.to(
                nav(f"/translate/{cid}", lang)
            ),
            top_bar_actions=[
                {
                    "label": _('logout', lang),
                    "icon": "logout",
                    "variant": "secondary",
                    "on_click": logout_dialog.open,
                }
            ],
            on_search=handle_search,
            on_new_conversation=lambda: ui.navigate.to(nav("/translate", lang)),
        ):
            content()

    shell()
    ui.timer(0.1, load_page_data, once=True)
