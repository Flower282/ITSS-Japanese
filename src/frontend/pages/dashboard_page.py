from __future__ import annotations

from nicegui import app, ui

from src.frontend import state
from src.frontend.components.components import analysis_row, stat_card
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState


@ui.page("/")
def dashboard_page() -> None:
    layout_state = UiState()

    def handle_logout() -> None:
        state.clear_auth()
        app.storage.user.clear()
        ui.navigate.to("/login")

    with ui.dialog() as logout_dialog, ui.card().classes("min-w-[320px]"):
        ui.label("Bạn có chắc muốn đăng xuất?").classes(
            "text-sm font-medium text-slate-700"
        )
        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Hủy", on_click=logout_dialog.close).props("outline")
            ui.button("Đăng xuất", on_click=handle_logout).props("color=negative")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"Đang tìm: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify("Đã chuyển ngôn ngữ hiển thị.", type="info")

    with base_layout(
        active_nav="/",
        ui_state=layout_state,
        top_bar_actions=[
            {
                "label": "Đăng xuất",
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
                ui.label("Tổng quan").classes("text-2xl font-semibold text-slate-800")
                ui.label(
                    "Xem các phân tích mới và cải thiện kỹ năng giao tiếp của bạn"
                ).classes("text-sm text-slate-500")
            ui.button("Ngôn ngữ: Tiếng Việt", icon="language").props(
                "outline"
            ).classes("rounded-xl text-slate-600")

        with ui.grid().classes(
            "w-full gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4"
        ):
            stat_card(
                label="Tổng số hội thoại",
                value="24",
                icon="chat_bubble",
                trend="+3 tuần này",
                accent_classes="bg-blue-50 text-blue-600",
            )
            stat_card(
                label="Độ chính xác AI",
                value="94%",
                icon="auto_awesome",
                trend="+2% tuần này",
                accent_classes="bg-purple-50 text-purple-600",
            )
            stat_card(
                label="Gợi ý cần xem",
                value="3",
                icon="lightbulb",
                trend="Cần xem lại",
                accent_classes="bg-amber-50 text-amber-600",
                trend_classes="text-amber-600",
            )
            stat_card(
                label="Thời gian tương tác",
                value="12h",
                icon="schedule",
                trend="Trong tháng này",
                accent_classes="bg-emerald-50 text-emerald-600",
                trend_classes="text-emerald-600",
            )

        with ui.element("div").classes(
            "w-full rounded-xl bg-white p-4 shadow-sm border border-slate-100"
        ):
            with ui.row().classes("items-center justify-between"):
                ui.label("Phân tích & Đề xuất AI").classes(
                    "text-sm font-semibold text-slate-800"
                )
                ui.link("Xem toàn bộ báo cáo", "#").classes("text-xs text-blue-600")

            with ui.column().classes("mt-4 gap-3"):
                analysis_row(
                    icon="report_problem",
                    title="Lạm dụng từ xin lỗi",
                    description=(
                        "Bạn có xu hướng nói 'Sumimasen' nhiều hơn mức cần thiết. "
                        "Trong ngữ cảnh dự án hôm qua, bạn có thể dùng 'Arigatou gozaimasu'."
                    ),
                    link_label="Xem chi tiết",
                    status_label="-15% tự tin",
                    status_classes="bg-rose-50 text-rose-600",
                )
                analysis_row(
                    icon="auto_fix_high",
                    title="Cải thiện kính ngữ",
                    description=(
                        "Phân tích từ hội thoại với Tanaka-san cho thấy bạn dùng Keigo "
                        "(kính ngữ) chính xác 92%. Rất tốt!"
                    ),
                    link_label="Xem báo cáo",
                    status_label="+5% so với tuần trước",
                    status_classes="bg-emerald-50 text-emerald-600",
                )
                analysis_row(
                    icon="people_alt",
                    title="Khoảng cách giao tiếp",
                    description=(
                        "AI phát hiện cách nói chuyện của bạn với Yamada-san hơi quá trang trọng "
                        "so với mối quan hệ hiện tại."
                    ),
                    link_label="Tìm hiểu",
                    status_label="Gợi ý thay đổi",
                    status_classes="bg-blue-50 text-blue-600",
                )
