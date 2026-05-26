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
from src.db.session import get_db_context
from src.repositories.cultural_assistant_repo import (
    get_marked_messages_with_analysis,
    get_culture_assistant_insight,
    get_user_learning_roadmap,
)


@ui.page("/culture")
def culture_page() -> None:
    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

    page_state: dict[str, Any] = {
        "handbook_items": [],
        "scenarios": [],
        "culture_insight": "",
        "history_items": [],
        "loading": True,
    }

    roadmap_loading = True
    roadmap_text = ""

    @ui.refreshable
    def render_roadmap_content() -> None:
        nonlocal roadmap_loading, roadmap_text
        if roadmap_loading:
            with ui.column().classes("w-full items-center justify-center py-16 gap-4"):
                ui.spinner(size="xl", color="primary", thickness=4)
                ui.label("Đang phân tích hội thoại và lập lộ trình học tập...").classes("text-slate-500 text-sm animate-pulse font-medium")
        else:
            if not roadmap_text:
                ui.label("Không thể tạo lộ trình học tập lúc này.").classes("text-rose-500 py-6 text-center w-full font-medium")
                return

            with ui.column().classes("w-full gap-4 max-h-[450px] overflow-y-auto pr-2"):
                ui.markdown(roadmap_text).classes(
                    "text-sm text-slate-700 leading-relaxed markdown-body "
                    "prose prose-slate max-w-full"
                )

    with ui.dialog().classes("rounded-2xl") as roadmap_dialog, ui.card().classes(
        "w-[650px] max-w-full p-6 rounded-2xl border border-slate-100 shadow-2xl bg-white overflow-hidden"
    ):
        with ui.row().classes("w-full items-center justify-between mb-4 border-b border-slate-100 pb-2"):
            with ui.row().classes("items-center gap-2.5"):
                icon_box = ui.element("div").classes(
                    "h-10 w-10 rounded-xl bg-blue-50 text-blue-600 "
                    "flex items-center justify-center flex-shrink-0"
                )
                with icon_box:
                    ui.icon("auto_awesome", color="primary").classes("text-xl")
                ui.label("Lộ trình Học tập Gợi ý (User #4)").classes("text-base font-bold text-slate-800")
            ui.button(icon="close", on_click=roadmap_dialog.close).props('flat round').classes(
                "text-slate-400 hover:text-slate-600"
            )
        
        render_roadmap_content()

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    async def handle_roadmap() -> None:
        nonlocal roadmap_loading, roadmap_text
        roadmap_dialog.open()
        roadmap_loading = True
        render_roadmap_content.refresh()
        
        def fetch():
            with get_db_context() as db:
                return get_user_learning_roadmap(db, user_id=4)
                
        try:
            roadmap_text = await asyncio.to_thread(fetch)
        except Exception as e:
            print(f"Error fetching roadmap: {e}")
            roadmap_text = "Không thể tải được lộ trình học tập do lỗi hệ thống."
            
        roadmap_loading = False
        render_roadmap_content.refresh()

    async def load_culture_data() -> None:
        page_state["loading"] = True
        shell.refresh()
        try:
            page_state["history_items"] = await load_conversation_history()
            
            def fetch_db():
                with get_db_context() as db:
                    scenarios_data = get_marked_messages_with_analysis(db)
                    insight_text = get_culture_assistant_insight(db, lang)
                    return scenarios_data, insight_text

            marked_scenarios_data, ai_insight_text = await asyncio.to_thread(fetch_db)
            
            if lang == 'jp':
                handbook_items = [
                    {
                        "title": "敬語（けいご）",
                        "description": "年上や上司への敬意を示す階層的な言語システム。",
                        "icon": "🙇",
                        "tags": [
                            "です・ます（基本的な丁寧さ）",
                            "尊敬語（相手を高める）",
                            "謙譲語（自分を下げる）",
                        ],
                        "link_label": "続きを読む",
                        "link_href": "#",
                    },
                    {
                        "title": "返答スタイル",
                        "description": "ビジネスのやり取りで返答のペースを尊重し、面目を保つ。",
                        "icon": "💬",
                        "tags": ["直接的な言い方を避ける", "提案する前に聞く"],
                        "link_label": "続きを読む",
                        "link_href": nav("/analysis", lang),
                    }
                ]
                scenarios = []
                num_scenarios = max(2, len(marked_scenarios_data))
                for i in range(num_scenarios):
                    idx = i + 1
                    has_data = i < len(marked_scenarios_data)
                    
                    phrase_val = marked_scenarios_data[i]["phrase"] if has_data else None
                    meaning_val = marked_scenarios_data[i]["meaning"] if has_data else None
                    response_val = marked_scenarios_data[i]["response"] if has_data else None
                    category_val = marked_scenarios_data[i]["category"] if has_data else None

                    if has_data and category_val == "QUẢN LÝ THỜI GIAN":
                        category = "時間管理"
                        accent_classes = "border-rose-100 bg-rose-50/60"
                    elif has_data and category_val == "GIAO TIẾP GIÁN TIẾP":
                        category = "間接的なコミュニケーション"
                        accent_classes = "border-amber-100 bg-amber-50/70"
                    else:
                        if idx == 1:
                            category = "間接的なコミュニケーション"
                            accent_classes = "border-amber-100 bg-amber-50/70"
                        else:
                            category = "時間管理"
                            accent_classes = "border-rose-100 bg-rose-50/60"

                    phrase = phrase_val
                    if not phrase:
                        if idx == 1:
                            phrase = '相手が言いました: "ちょっと考えさせてください"'
                        else:
                            phrase = '"なるべく早く" というデッドラインが設定された'

                    meaning = meaning_val
                    if not meaning:
                        if idx == 1:
                            meaning = "これは多くの場合、時間が必要なのではなく、丁寧な断り方です。"
                        else:
                            meaning = "日本の仕事文化では、これは通常「今すぐ」、最優先事項を意味します。"
                            
                    response = response_val
                    if not response:
                        if idx == 1:
                            response = "代替案を準備するか、現在の懸念事項について穏やかに尋ねる。"
                        else:
                            response = "すぐに取り掛かるか、具体的な完了時間を報告する。"

                    scenarios.append({
                        "index": idx,
                        "category": category,
                        "phrase": phrase,
                        "meaning": meaning,
                        "response": response,
                        "accent_classes": accent_classes,
                    })
            else:
                handbook_items = [
                    {
                        "title": "Kính ngữ (Keigo)",
                        "description": "Hệ thống ngôn ngữ phân cấp, thể hiện sự tôn trọng với người lớn tuổi, cấp trên.",
                        "icon": "🙇",
                        "tags": [
                            "てす・ます (Lịch sự cơ bản)",
                            "尊敬語 (Tôn kính ngữ)",
                            "謙譲語 (Khiêm nhường ngữ)",
                        ],
                        "link_label": "Đọc tiếp",
                        "link_href": "#",
                    },
                    {
                        "title": "Phong cách phản hồi",
                        "description": "Tôn trọng nhịp độ phản hồi và giữ thể diện trong trao đổi công việc.",
                        "icon": "💬",
                        "tags": ["Tránh nói thẳng", "Lắng nghe trước khi góp ý"],
                        "link_label": "Đọc tiếp",
                        "link_href": "#",
                    },
                ]
                scenarios = []
                num_scenarios = max(2, len(marked_scenarios_data))
                for i in range(num_scenarios):
                    idx = i + 1
                    has_data = i < len(marked_scenarios_data)
                    
                    phrase_val = marked_scenarios_data[i]["phrase"] if has_data else None
                    meaning_val = marked_scenarios_data[i]["meaning"] if has_data else None
                    response_val = marked_scenarios_data[i]["response"] if has_data else None
                    category_val = marked_scenarios_data[i]["category"] if has_data else None

                    if has_data and category_val == "QUẢN LÝ THỜI GIAN":
                        category = "QUẢN LÝ THỜI GIAN"
                        accent_classes = "border-rose-100 bg-rose-50/60"
                    elif has_data and category_val == "GIAO TIẾP GIÁN TIẾP":
                        category = "GIAO TIẾP GIÁN TIẾP"
                        accent_classes = "border-amber-100 bg-amber-50/70"
                    else:
                        if idx == 1:
                            category = "GIAO TIẾP GIÁN TIẾP"
                            accent_classes = "border-amber-100 bg-amber-50/70"
                        else:
                            category = "QUẢN LÝ THỜI GIAN"
                            accent_classes = "border-rose-100 bg-rose-50/60"

                    phrase = phrase_val
                    if not phrase:
                        if idx == 1:
                            phrase = 'Đối tác nói: "Chotto kangaesete kudasai" (Để tôi suy nghĩ một chút)'
                        else:
                            phrase = 'Deadline được đưa ra "narubeku hayaku" (Càng sớm càng tốt)'

                    meaning = meaning_val
                    if not meaning:
                        if idx == 1:
                            meaning = "Đây thường là cách từ chối lịch sự, không phải thực sự cần thêm thời gian suy nghĩ."
                        else:
                            meaning = "Trong văn hóa làm việc Nhật, đây thường có nghĩa là NGAY LẬP TỨC, ưu tiên cao nhất."
                            
                    response = response_val
                    if not response:
                        if idx == 1:
                            response = "Nên chuẩn bị phương án thay thế hoặc nhẹ nhàng hỏi về các vướng mắc hiện tại."
                        else:
                            response = "Cần bắt tay vào làm ngay hoặc báo cáo thời gian hoàn thành cụ thể."

                    scenarios.append({
                        "index": idx,
                        "category": category,
                        "phrase": phrase,
                        "meaning": meaning,
                        "response": response,
                        "accent_classes": accent_classes,
                    })

            page_state["culture_insight"] = ai_insight_text or _('ai_culture_insight', lang)
            page_state["handbook_items"] = handbook_items
            page_state["scenarios"] = scenarios
        except Exception as exc:
            print(f"Error loading culture data: {exc}")
            page_state["culture_insight"] = _('ai_culture_insight', lang)
            page_state["handbook_items"] = []
            page_state["scenarios"] = []
        page_state["loading"] = False
        shell.refresh()

    async def handle_sync() -> None:
        await load_culture_data()
        ui.notify(_('updated_from_conv', lang), type="positive")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"{_('searching', lang)}: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', lang), type="info")

    @ui.refreshable
    def shell() -> None:
        with base_layout(
            active_nav="/culture",
            ui_state=layout_state,
            history_items=page_state.get("history_items", []),
            on_history_select=lambda cid: ui.navigate.to(nav(f"/translate/{cid}", lang)),
            on_new_conversation=handle_new_conversation,
            on_search=handle_search,
            on_locale_click=handle_locale_click,
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
                        title=_('culture_explain_title', lang),
                        subtitle=_('culture_subtitle', lang),
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
                            ui.label(_('ai_culture_assistant', lang)).classes(
                                "text-sm font-semibold text-slate-800"
                            )
                        with ui.element("div").classes("max-h-[110px] overflow-y-auto mt-2 pr-1"):
                            ui.label(page_state["culture_insight"]).classes(
                                "text-sm text-slate-600"
                            )
                        action_button(
                            label=_("view_roadmap", lang),
                            icon="map",
                            variant="secondary",
                            on_click=handle_roadmap,
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
                            on_click=handle_sync,
                            variant="secondary",
                        ),
                    )

    shell()
    ui.timer(0.1, load_culture_data, once=True)
