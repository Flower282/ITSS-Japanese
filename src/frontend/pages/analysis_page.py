from __future__ import annotations

from nicegui import ui

from src.frontend.components.components import (
    action_button,
    checklist_panel,
    page_title_block,
    stats_cards_row,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState


@ui.page("/analysis")
def analysis_page() -> None:
    layout_state = UiState()

    metrics = [
        {
            "title": "THỜI LƯỢNG",
            "value": "45",
            "subtitle": "Phút tương tác",
            "accent_classes": "border-blue-100 bg-blue-50",
            "value_classes": "text-blue-600",
        },
        {
            "title": "ĐỘ HIỂU",
            "value": "87%",
            "subtitle": "Truyền đạt chính xác",
            "accent_classes": "border-emerald-100 bg-emerald-50",
            "value_classes": "text-emerald-600",
        },
        {
            "title": "CẢM XÚC CHUNG",
            "value": "Tốt",
            "subtitle": "Tích cực & Xây dựng",
            "accent_classes": "border-purple-100 bg-purple-50",
            "value_classes": "text-purple-600",
        },
    ]

    perception_gaps = [
        {
            "title": "Deadline dự án",
            "severity": "CAO",
            "severity_classes": "bg-rose-500 text-white",
            "left_title": "VN QUAN ĐIỂM VIỆT NAM",
            "left_text": "Hiểu là deadline có thể linh hoạt",
            "right_title": "JP QUAN ĐIỂM NHẬT BẢN",
            "right_text": "Deadline là tuyệt đối cần tuân thủ",
            "recommendation": "Cần xác nhận lại deadline cụ thể và cam kết rõ ràng",
        },
        {
            "title": "Cách nhận phản hồi",
            "severity": "TRUNG BÌNH",
            "severity_classes": "bg-amber-500 text-white",
            "left_title": "VN QUAN ĐIỂM VIỆT NAM",
            "left_text": "Ưu tiên lời nhắc nhẹ và linh hoạt",
            "right_title": "JP QUAN ĐIỂM NHẬT BẢN",
            "right_text": "Ưu tiên phản hồi rõ ràng và đúng hạn",
            "recommendation": "Nên đưa cam kết thời gian phản hồi cụ thể",
        },
    ]

    decisions = [
        "Gia hạn deadline đến ngày 15/4",
        "Tăng cường họp hàng ngày vào 9:00 AM",
        "Phân công Sato-san hỗ trợ phần UI",
    ]

    action_items = [
        "Bạn: Gửi báo cáo tiến độ trước 5 PM hôm nay",
        "Tanaka-san: Xác nhận phạm vi yêu cầu mới",
        "Cả nhóm: Chốt lại timeline trong buổi họp ngày mai",
    ]

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    def handle_export() -> None:
        ui.notify("Đã xuất báo cáo PDF.", type="positive")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"Đang tìm: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify("Đã chuyển ngôn ngữ hiển thị.", type="info")

    with base_layout(
        active_nav="/analysis",
        ui_state=layout_state,
        on_new_conversation=handle_new_conversation,
        on_search=handle_search,
        on_locale_click=handle_locale_click,
    ):
        with ui.row().classes("w-full items-center justify-between"):
            page_title_block(
                title="Phân tích hội thoại",
                subtitle="Cuộc họp với Tanaka-san - 10/04/2026",
            )
            action_button(
                label="Xuất báo cáo PDF",
                icon="download",
                variant="primary",
                on_click=handle_export,
            )

        stats_cards_row(cards=metrics)

        with ui.element("div").classes(
            "w-full rounded-2xl border border-slate-100 bg-white p-5 shadow-sm"
        ):
            with ui.row().classes("items-start gap-3"):
                icon_box = ui.element("div").classes(
                    "h-10 w-10 rounded-full bg-blue-600 text-white flex items-center justify-center"
                )
                with icon_box:
                    ui.icon("psychology")
                with ui.column().classes("gap-1"):
                    ui.label("Nhận xét tổng quan từ AI").classes(
                        "text-sm font-semibold text-slate-800"
                    )
                    ui.label(
                        "Cuộc họp diễn ra tích cực với mức độ hiểu biết lẫn nhau là 87%. "
                        "Tuy nhiên, có một số điểm cần lưu ý về sự khác biệt trong nhận thức "
                        "về deadline và cách giao tiếp. Khuyến nghị tăng cường xác nhận rõ "
                        "các cam kết và sử dụng ngôn ngữ lịch sự, gián tiếp hơn khi giao tiếp "
                        "với đồng nghiệp Nhật Bản."
                    ).classes("text-sm text-slate-600")

        with ui.row().classes("w-full items-start gap-6"):
            with ui.column().classes("flex-1 gap-4"):
                ui.label("Điểm lệch nhận thức").classes(
                    "text-sm font-semibold text-slate-700"
                )

                for gap in perception_gaps:
                    with ui.element("div").classes(
                        "w-full rounded-2xl border border-rose-100 bg-rose-50/60 p-4"
                    ):
                        with ui.row().classes("items-start justify-between"):
                            ui.label(gap["title"]).classes(
                                "text-sm font-semibold text-slate-800"
                            )
                            ui.label(gap["severity"]).classes(
                                f"text-[10px] font-semibold px-2 py-0.5 rounded-full "
                                f"{gap['severity_classes']}"
                            )

                        with ui.row().classes("gap-3 mt-3"):
                            with ui.element("div").classes(
                                "flex-1 rounded-xl border border-slate-100 bg-white p-3"
                            ):
                                ui.label(gap["left_title"]).classes(
                                    "text-[11px] text-slate-400 font-semibold"
                                )
                                ui.label(gap["left_text"]).classes(
                                    "text-sm text-slate-600 mt-1"
                                )

                            with ui.element("div").classes(
                                "flex-1 rounded-xl border border-slate-100 bg-white p-3"
                            ):
                                ui.label(gap["right_title"]).classes(
                                    "text-[11px] text-slate-400 font-semibold"
                                )
                                ui.label(gap["right_text"]).classes(
                                    "text-sm text-slate-600 mt-1"
                                )

                        with ui.element("div").classes(
                            "mt-3 rounded-xl border border-blue-100 bg-blue-50 p-3"
                        ):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("tips_and_updates").classes(
                                    "text-blue-600 text-sm"
                                )
                                ui.label("KHUYẾN NGHỊ AI").classes(
                                    "text-[11px] font-semibold text-blue-600"
                                )
                            ui.label(gap["recommendation"]).classes(
                                "text-sm text-slate-600 mt-1"
                            )

            with ui.column().classes("w-full max-w-[360px] gap-4"):
                checklist_panel(
                    title="Tóm tắt nội dung",
                    items=decisions,
                )
                checklist_panel(
                    title="Action items",
                    items=action_items,
                    icon_classes="text-blue-600",
                )
