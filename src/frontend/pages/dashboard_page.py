from __future__ import annotations

from nicegui import app, ui

from src.frontend import state
from src.frontend.components.components import analysis_row, stat_card
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState
from src.core.i18n import _, get_user_language, validate_language_or_default


@ui.page("/")
def dashboard_page() -> None:
    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

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

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"{_('searching', lang)}: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', lang), type="info")

    with base_layout(
        active_nav="/",
        ui_state=layout_state,
        top_bar_actions=[
            {
                "label": _('logout', lang),
                "icon": "logout",
                "variant": "secondary",
                "on_click": logout_dialog.open,
            }
        ],
        on_search=handle_search,
        on_locale_click=handle_locale_click,
    ):
        with ui.row().classes("w-full items-start justify-between gap-4"):
            with ui.column().classes("gap-1"):
                ui.label(_('overview', lang)).classes("text-2xl font-semibold text-slate-800")
                ui.label(_('overview_subtitle', lang)).classes("text-sm text-slate-500")
            ui.button(_('lang_btn', lang), icon="language").props(
                "outline"
            ).classes("rounded-xl text-slate-600")

        with ui.grid().classes(
            "w-full gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
        ):
            stat_card(
                label=_('total_conversations', lang),
                value="24",
                icon="chat_bubble",
                trend=f"+3 {_('this_week', lang)}",
                accent_classes="bg-blue-50 text-blue-600",
            )
            stat_card(
                label=_('ai_accuracy', lang),
                value="94%",
                icon="auto_awesome",
                trend=f"+2% {_('this_week', lang)}",
                accent_classes="bg-purple-50 text-purple-600",
            )
            stat_card(
                label=_('suggestions_to_review', lang),
                value="3",
                icon="lightbulb",
                trend=_('need_review', lang),
                accent_classes="bg-amber-50 text-amber-600",
                trend_classes="text-amber-600",
            )
            stat_card(
                label=_('interaction_time', lang),
                value="12h",
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
                ui.link(_('view_full_report', lang), "#").classes("text-xs text-blue-600")

            with ui.column().classes("mt-4 gap-3"):
                analysis_row(
                    icon="report_problem",
                    title=_('overuse_sorry_title', lang),
                    description=_('overuse_sorry_desc', lang),
                    link_label=_('view_details', lang),
                    status_label=_('confidence_down', lang),
                    status_classes="bg-rose-50 text-rose-600",
                )
                analysis_row(
                    icon="auto_fix_high",
                    title=_('improve_keigo_title', lang),
                    description=_('improve_keigo_desc', lang),
                    link_label=_('view_report', lang),
                    status_label=_('accuracy_up', lang),
                    status_classes="bg-emerald-50 text-emerald-600",
                )
                analysis_row(
                    icon="people_alt",
                    title=_('comm_distance_title', lang),
                    description=_('comm_distance_desc', lang),
                    link_label=_('learn_more', lang),
                    status_label=_('suggest_change', lang),
                    status_classes="bg-blue-50 text-blue-600",
                )
