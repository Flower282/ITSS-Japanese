from __future__ import annotations

from nicegui import ui

from src.frontend.components.components import (
    action_button,
    insight_list,
    page_title_block,
    scenario_panel,
    sync_action_bar,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState
from src.core.i18n import _, get_user_language, validate_language_or_default


@ui.page("/culture")
def culture_page() -> None:
    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

    if lang == 'jp':
        handbook_items = [
            {
                "title": "敬語（けいご）",
                "description": "年上や上司への敬意を示す階層的な言語システム。",
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
                "tags": ["直接的な言い方を避ける", "提案する前に聞く"],
                "link_label": "続きを読む",
                "link_href": "#",
            },
        ]
        scenarios = [
            {
                "index": 1,
                "category": "間接的なコミュニケーション",
                "phrase": '相手が言いました: "ちょっと考えさせてください"',
                "meaning": "これは多くの場合、時間が必要なのではなく、丁寧な断り方です。",
                "response": "代替案を準備するか、現在の懸念事項について穏やかに尋ねる。",
                "accent_classes": "border-amber-100 bg-amber-50/70",
            },
            {
                "index": 2,
                "category": "時間管理",
                "phrase": '"なるべく早く" というデッドラインが設定された',
                "meaning": "日本の仕事文化では、これは通常「今すぐ」、最優先事項を意味します。",
                "response": "すぐに取り掛かるか、具体的な完了時間を報告する。",
                "accent_classes": "border-rose-100 bg-rose-50/60",
            },
        ]
    else:
        handbook_items = [
            {
                "title": "Kính ngữ (Keigo)",
                "description": "Hệ thống ngôn ngữ phân cấp, thể hiện sự tôn trọng với người lớn tuổi, cấp trên.",
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
                "tags": ["Tránh nói thẳng", "Lắng nghe trước khi góp ý"],
                "link_label": "Đọc tiếp",
                "link_href": "#",
            },
        ]
        scenarios = [
            {
                "index": 1,
                "category": "GIAO TIẾP GIÁN TIẾP",
                "phrase": 'Đối tác nói: "Chotto kangaesete kudasai" (Để tôi suy nghĩ một chút)',
                "meaning": "Đây thường là cách từ chối lịch sự, không phải thực sự cần thêm thời gian suy nghĩ.",
                "response": "Nên chuẩn bị phương án thay thế hoặc nhẹ nhàng hỏi về các vướng mắc hiện tại.",
                "accent_classes": "border-amber-100 bg-amber-50/70",
            },
            {
                "index": 2,
                "category": "QUẢN LÝ THỜI GIAN",
                "phrase": 'Deadline được đưa ra "narubeku hayaku" (Càng sớm càng tốt)',
                "meaning": "Trong văn hóa làm việc Nhật, đây thường có nghĩa là NGAY LẬP TỨC, ưu tiên cao nhất.",
                "response": "Cần bắt tay vào làm ngay hoặc báo cáo thời gian hoàn thành cụ thể.",
                "accent_classes": "border-rose-100 bg-rose-50/60",
            },
        ]

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    def handle_recommended_lesson() -> None:
        ui.notify(_('opened_lesson', lang), type="info")

    def handle_roadmap() -> None:
        ui.notify(_('showed_roadmap', lang), type="info")

    def handle_sync() -> None:
        ui.notify(_('updated_from_conv', lang), type="positive")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"{_('searching', lang)}: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', lang), type="info")

    with base_layout(
        active_nav="/culture",
        ui_state=layout_state,
        on_new_conversation=handle_new_conversation,
        on_search=handle_search,
        on_locale_click=handle_locale_click,
    ):
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

            with ui.row().classes("items-center gap-2"):
                ui.label(_('new_badge', lang)).classes(
                    "text-[10px] font-semibold px-2 py-0.5 rounded-full "
                    "bg-amber-100 text-amber-700"
                )
                action_button(
                    label=_('recommended_lesson_btn', lang),
                    icon="school",
                    variant="secondary",
                    on_click=handle_recommended_lesson,
                    extra_classes=(
                        "border-amber-200 bg-amber-50 text-amber-700 "
                        "hover:bg-amber-100"
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
                        ui.label(_('ai_culture_assistant', lang)).classes(
                            "text-sm font-semibold text-slate-800"
                        )
                    ui.label(_('ai_culture_insight', lang)).classes(
                        "text-sm text-slate-600 mt-2"
                    )

                    action_button(
                        label=_('view_roadmap', lang),
                        icon="map",
                        variant="secondary",
                        on_click=handle_roadmap,
                        extra_classes="mt-4 bg-white",
                    )

                with ui.column().classes("gap-3"):
                    ui.label(_('comm_handbook', lang)).classes(
                        "text-sm font-semibold text-slate-700"
                    )
                    insight_list(items=handbook_items, max_height="300px")

            with ui.column().classes("flex-1 gap-4"):
                scenario_panel(
                    title=_('real_situation_analysis', lang),
                    scenarios=scenarios,
                    max_height="520px",
                    header_action=lambda: sync_action_bar(
                        label=_('update_from_conv', lang),
                        icon="sync",
                        on_click=handle_sync,
                        variant="secondary",
                    ),
                )
