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


@ui.page("/culture")
def culture_page() -> None:
    layout_state = UiState()

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
            "phrase": "Đối tác nói: \"Chotto kangaesete kudasai\" (Để tôi suy nghĩ một chút)",
            "meaning": "Đây thường là cách từ chối lịch sự, không phải thực sự cần thêm thời gian suy nghĩ.",
            "response": "Nên chuẩn bị phương án thay thế hoặc nhẹ nhàng hỏi về các vướng mắc hiện tại.",
            "accent_classes": "border-amber-100 bg-amber-50/70",
        },
        {
            "index": 2,
            "category": "QUẢN LÝ THỜI GIAN",
            "phrase": "Deadline được đưa ra \"narubeku hayaku\" (Càng sớm càng tốt)",
            "meaning": "Trong văn hóa làm việc Nhật, đây thường có nghĩa là NGAY LẬP TỨC, ưu tiên cao nhất.",
            "response": "Cần bắt tay vào làm ngay hoặc báo cáo thời gian hoàn thành cụ thể.",
            "accent_classes": "border-rose-100 bg-rose-50/60",
        },
    ]

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    def handle_recommended_lesson() -> None:
        ui.notify("Đã mở bài học gợi ý.", type="info")

    def handle_roadmap() -> None:
        ui.notify("Đã hiển thị lộ trình học tập.", type="info")

    def handle_sync() -> None:
        ui.notify("Đã cập nhật từ hội thoại gần nhất.", type="positive")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"Đang tìm: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify("Đã chuyển ngôn ngữ hiển thị.", type="info")

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
                    title="Giải thích văn hóa",
                    subtitle="Nâng cao sự thấu hiểu văn hóa Nhật Bản (日本の文化理解)",
                )

            with ui.row().classes("items-center gap-2"):
                ui.label("Mới").classes(
                    "text-[10px] font-semibold px-2 py-0.5 rounded-full "
                    "bg-amber-100 text-amber-700"
                )
                action_button(
                    label="Bài học: Kỹ năng đọc không khí (空気を読む)",
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
                        ui.label("Trợ lý Văn hóa AI").classes(
                            "text-sm font-semibold text-slate-800"
                        )
                    ui.label(
                        "Qua phân tích lịch sử hội thoại, bạn có xu hướng sử dụng ngôn ngữ Nhật "
                        "qua trang trọng so với mục đích thân thiện trong môi trường IT startup."
                    ).classes("text-sm text-slate-600 mt-2")

                    action_button(
                        label="Xem lộ trình gợi ý",
                        icon="map",
                        variant="secondary",
                        on_click=handle_roadmap,
                        extra_classes="mt-4 bg-white",
                    )

                with ui.column().classes("gap-3"):
                    ui.label("Cẩm nang giao tiếp").classes(
                        "text-sm font-semibold text-slate-700"
                    )
                    insight_list(items=handbook_items, max_height="300px")

            with ui.column().classes("flex-1 gap-4"):
                scenario_panel(
                    title="Phân tích tình huống thực tế",
                    scenarios=scenarios,
                    max_height="520px",
                    header_action=lambda: sync_action_bar(
                        label="Cập nhật từ hội thoại của bạn",
                        icon="sync",
                        on_click=handle_sync,
                        variant="secondary",
                    ),
                )
