from __future__ import annotations

from nicegui import ui

from src.frontend.components.components import (
    action_button,
    analysis_panel,
    conversation_history_view,
    input_composer,
    page_title_block,
    recommendation_chips,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState


@ui.page("/translate")
def translation_page() -> None:
    layout_state = UiState()

    messages: list[dict] = [
        {
            "id": 1,
            "role": "listen",
            "label": "NGHE",
            "time": "10:30",
            "text": (
                "Eto, kintou no koto nan desu kedo, mou sukoshi jikan ga hitsuyou kamo"
                " shiremasen."
            ),
            "tags": ["Goi mo", "Xin y kien", "Dang do du"],
        },
        {
            "id": 2,
            "role": "you",
            "label": "BAN NOI",
            "time": "10:31",
            "text": "Dạ, em hiểu. Tanaka-san có thể cho em biết cụ thể hơn được không?",
            "tags": ["Tone: Lich su", "Khang dinh", "De nghi"],
        },
    ]

    suggested_replies = [
        {
            "id": "s1",
            "title": "Hoi can them bao nhieu thoi gian",
            "description": "The hien su lang nghe va de xuat giai phap",
        },
        {
            "id": "s2",
            "title": "Dong y va bao se xem xet dieu chinh",
            "description": "Giam bot ap luc va hop tac",
        },
    ]

    selected_tones: list[str] = ["Lịch sự"]
    draft_input: ui.textarea | None = None

    def handle_new_conversation() -> None:
        if draft_input:
            draft_input.value = ""
        ui.notify("Đã tạo hội thoại mới.", type="positive")

    def handle_save() -> None:
        ui.notify("Đã lưu hội thoại hiện tại.", type="positive")

    def handle_analyze() -> None:
        ui.notify("Đang phân tích nội dung.", type="info")

    def handle_translate() -> None:
        if not draft_input or not draft_input.value:
            ui.notify("Vui lòng nhập nội dung cần dịch.", type="warning")
            return
        messages.append(
            {
                "id": len(messages) + 1,
                "role": "you",
                "label": "BAN NOI",
                "time": "10:32",
                "text": draft_input.value,
                "tags": ["Đã tối ưu", ", ".join(selected_tones) or "Không"],
            }
        )
        render_history.refresh()
        ui.notify("Đã thêm câu trả lời vào lịch sử.", type="positive")

    def handle_select_reply(text: str) -> None:
        if draft_input:
            draft_input.value = text

    @ui.refreshable
    def render_history() -> None:
        conversation_history_view(
            title="LỊCH SỬ HỘI THOẠI",
            messages=messages,
            max_height="560px",
        )

    with base_layout(
        active_nav="/translate",
        ui_state=layout_state,
        title_slot=lambda: page_title_block(
            title="Cuộc hội thoại mới",
            subtitle="Đang trực tuyến",
            status="AI Assistant đang hỗ trợ",
        ),
        top_bar_actions=[
            {
                "label": "Phân tích",
                "icon": "analytics",
                "variant": "primary",
                "on_click": handle_analyze,
            },
            {
                "label": "Lưu trữ",
                "icon": "archive",
                "variant": "secondary",
                "on_click": handle_save,
            },
        ],
        on_new_conversation=handle_new_conversation,
        on_history_select=lambda _: ui.notify("Đã tải lịch sử hội thoại."),
    ):
        with ui.row().classes("w-full items-start gap-6"):
            with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                render_history()

            with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                analysis_panel(
                    title="ĐỐI PHƯƠNG NÓI GÌ?",
                    content=messages[0]["text"],
                    accent_classes="border-amber-200 bg-amber-50",
                    header_action=lambda: action_button(
                        label="Phân tích AI",
                        icon="auto_awesome",
                        variant="secondary",
                        on_click=handle_analyze,
                    ),
                )
                analysis_panel(
                    title="BẢN DỊCH (TIẾNG VIỆT)",
                    content=(
                        "Ah, ve deadline, co le toi can them mot chut thoi gian..."
                    ),
                    accent_classes="border-sky-200 bg-sky-50",
                )
                analysis_panel(
                    title="Ý NGHĨA THỰC TẾ & SẮC THÁI",
                    content=(
                        "Đối tác đang gặp khó khăn và muốn xin gia hạn deadline, "
                        "nhưng ngại nói trực tiếp. Cách nói thể hiện sự ngập ngừng "
                        "và do dự."
                    ),
                    tags=["Gián tiếp", "Khó nói", "Ngại ngùng"],
                    accent_classes="border-violet-200 bg-violet-50",
                )
                analysis_panel(
                    title="GỢI Ý CÁCH TRẢ LỜI (CLICK ĐỂ DÙNG)",
                    actions=[
                        {
                            "title": reply["title"],
                            "description": reply["description"],
                            "on_click": lambda text=reply["title"]: handle_select_reply(
                                text
                            ),
                        }
                        for reply in suggested_replies
                    ],
                )

            with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                draft_input = input_composer(
                    title="BẠN MUỐN NÓI GÌ?",
                    placeholder="Nhập ý bạn muốn nói bằng tiếng Việt...",
                    value="Ah, về deadline, có lẽ tôi cần thêm một chút thời gian...",
                )

                with ui.element("div").classes(
                    "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
                ):
                    ui.label("TỐI ƯU TỔNG GIỌNG").classes(
                        "text-sm font-semibold text-slate-700 mb-3"
                    )
                    recommendation_chips(
                        options=["Lịch sự", "Ngắn gọn hơn", "Mềm mỏng"],
                        selected=selected_tones,
                        on_change=lambda value: selected_tones.clear()
                        or selected_tones.extend(value),
                    )
                    with ui.row().classes("items-center justify-between mt-4"):
                        with ui.row().classes(
                            "items-center gap-2 text-xs text-slate-500"
                        ):
                            ui.icon("mic").classes("text-sm")
                            ui.label("Giọng nói")
                        action_button(
                            label="Dịch & Tối ưu",
                            icon="translate",
                            variant="primary",
                            on_click=handle_translate,
                        )
