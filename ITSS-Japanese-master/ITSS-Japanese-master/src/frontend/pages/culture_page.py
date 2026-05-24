from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode

from nicegui import ui

from src.core.i18n import _, get_user_language, nav, validate_language_or_default
from src.frontend.api_client import api_get
from src.frontend.components.components import (
    action_button,
    insight_list,
    page_title_block,
    scenario_panel,
    sync_action_bar,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.services.conversation_service import (
    load_conversation_history,
    load_translate_context,
)
from src.frontend.ui_state import UiState


def _default_handbook(lang: str) -> list[dict]:
    if lang == "jp":
        return [
            {
                "title": "敬語（けいご）",
                "description": "年上や上司への敬意を示す階層的な言語システム。",
                "tags": ["です・ます", "尊敬語", "謙譲語"],
                "link_label": "続きを読む",
                "link_href": nav("/analysis", lang),
            }
        ]
    return [
        {
            "title": "Kính ngữ (Keigo)",
            "description": "Hệ thống ngôn ngữ phân cấp, thể hiện sự tôn trọng với người lớn tuổi, cấp trên.",
            "tags": ["てす・ます", "尊敬語", "謙譲語"],
            "link_label": "Đọc tiếp",
            "link_href": nav("/analysis", lang),
        }
    ]


def _gaps_to_scenarios(gaps: list[dict], lang: str) -> list[dict]:
    scenarios = []
    for index, gap in enumerate(gaps[:6], start=1):
        scenarios.append(
            {
                "index": index,
                "category": gap.get("title", "AI"),
                "phrase": gap.get("left_text", "")[:120],
                "meaning": gap.get("right_text", "")[:200],
                "response": gap.get("recommendation", "")[:200],
                "accent_classes": "border-amber-100 bg-amber-50/70",
            }
        )
    return scenarios or _default_scenarios(lang)


def _default_scenarios(lang: str) -> list[dict]:
    if lang == "jp":
        return [
            {
                "index": 1,
                "category": "間接的なコミュニケーション",
                "phrase": "Chotto kangaesete kudasai",
                "meaning": "丁寧な断り方であることが多い。",
                "response": "代替案を準備する。",
                "accent_classes": "border-amber-100 bg-amber-50/70",
            }
        ]
    return [
        {
            "index": 1,
            "category": "GIAO TIẾP GIÁN TIẾP",
            "phrase": 'Đối tác: "Chotto kangaesete kudasai"',
            "meaning": "Đây thường là cách từ chối lịch sự.",
            "response": "Chuẩn bị phương án thay thế.",
            "accent_classes": "border-amber-100 bg-amber-50/70",
        }
    ]


@ui.page("/culture")
def culture_page() -> None:
    layout_state = UiState()
    lang = validate_language_or_default(get_user_language())

    page_state: dict[str, Any] = {
        "handbook_items": _default_handbook(lang),
        "scenarios": _default_scenarios(lang),
        "culture_insight": _("ai_culture_insight", lang),
        "history_items": [],
        "loading": True,
    }

    async def load_culture_data() -> None:
        page_state["loading"] = True
        shell.refresh()
        try:
            page_state["history_items"] = await load_conversation_history()
            query = urlencode({"lang": lang})
            data = await api_get(f"/api/analysis/latest/ensure?{query}", timeout=90.0)
            culture_text = ""
            conv_id = data.get("id")
            if conv_id:
                ctx = await load_translate_context(conv_id, lang)
                culture_text = str(ctx.get("culture_explanation") or "")

            gaps = data.get("perception_gaps") or []
            if culture_text:
                page_state["culture_insight"] = culture_text
                page_state["handbook_items"] = [
                    {
                        "title": _("culture_explain_title", lang),
                        "description": culture_text[:280],
                        "tags": [data.get("overall_sentiment", "AI")],
                        "link_label": _("view_report", lang),
                        "link_href": nav(
                            f"/analysis/{data.get('id')}" if data.get("id") else "/analysis",
                            lang,
                        ),
                    },
                    *_default_handbook(lang),
                ]
            page_state["scenarios"] = _gaps_to_scenarios(gaps, lang)
        except Exception as exc:
            ui.notify(str(exc), type="warning")
        page_state["loading"] = False
        shell.refresh()

    async def handle_sync() -> None:
        await load_culture_data()
        ui.notify(_("updated_from_conv", lang), type="positive")

    @ui.refreshable
    def shell() -> None:
        with base_layout(
            active_nav="/culture",
            ui_state=layout_state,
            history_items=page_state.get("history_items", []),
            on_history_select=lambda cid: ui.navigate.to(nav(f"/translate/{cid}", lang)),
            on_new_conversation=lambda: ui.navigate.to(nav("/translate", lang)),
            on_search=lambda value: ui.navigate.to(nav("/analysis", lang))
            if (value or "").strip()
            else None,
        ):
            if page_state["loading"]:
                with ui.row().classes("w-full justify-center py-20"):
                    ui.spinner(size="lg")
                return

            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-3"):
                    icon_box = ui.element("div").classes(
                        "h-10 w-10 rounded-full bg-amber-100 text-amber-600 "
                        "flex items-center justify-center"
                    )
                    with icon_box:
                        ui.icon("public")
                    page_title_block(
                        title=_("culture_explain_title", lang),
                        subtitle=_("culture_subtitle", lang),
                    )
                action_button(
                    label=_("recommended_lesson_btn", lang),
                    icon="school",
                    variant="secondary",
                    on_click=lambda: ui.navigate.to(nav("/analysis", lang)),
                    extra_classes=(
                        "border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100"
                    ),
                )

            with ui.row().classes("w-full items-start gap-6"):
                with ui.column().classes("w-full max-w-[360px] gap-4"):
                    with ui.element("div").classes(
                        "w-full rounded-2xl border border-blue-100 bg-blue-50/60 p-4 shadow-sm"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            icon_box = ui.element("div").classes(
                                "h-9 w-9 rounded-xl bg-white text-blue-600 "
                                "flex items-center justify-center"
                            )
                            with icon_box:
                                ui.icon("psychology")
                            ui.label(_("ai_culture_assistant", lang)).classes(
                                "text-sm font-semibold text-slate-800"
                            )
                        ui.label(page_state["culture_insight"]).classes(
                            "text-sm text-slate-600 mt-2"
                        )
                        action_button(
                            label=_("view_roadmap", lang),
                            icon="map",
                            variant="secondary",
                            on_click=lambda: ui.navigate.to(nav("/analysis", lang)),
                            extra_classes="mt-4 bg-white",
                        )

                    with ui.column().classes("gap-3"):
                        ui.label(_("comm_handbook", lang)).classes(
                            "text-sm font-semibold text-slate-700"
                        )
                        insight_list(
                            items=page_state["handbook_items"], max_height="300px"
                        )

                with ui.column().classes("flex-1 gap-4"):
                    scenario_panel(
                        title=_("real_situation_analysis", lang),
                        scenarios=page_state["scenarios"],
                        max_height="520px",
                        header_action=lambda: sync_action_bar(
                            label=_("update_from_conv", lang),
                            icon="sync",
                            on_click=lambda: asyncio.create_task(handle_sync()),
                            variant="secondary",
                        ),
                    )

    shell()
    ui.timer(0.1, load_culture_data, once=True)
