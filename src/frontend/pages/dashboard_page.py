from nicegui import app, ui

from src.frontend import state
from src.frontend.components.analysis_row import analysis_row
from src.frontend.components.navigation_header import navigation_header
from src.frontend.components.sidebar_item import sidebar_item
from src.frontend.components.stat_card import stat_card


@ui.page("/")
def dashboard_page() -> None:
    profile = state.get_profile() or {}
    user_name = profile.get("name") or profile.get("email") or "Người dùng"
    avatar_url = profile.get("picture")

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
            ui.button("Đăng xuất", on_click=handle_logout).props(
                "color=negative"
            )

    with ui.row().classes("w-full min-h-screen bg-slate-50"):
        with ui.column().classes(
            "w-72 shrink-0 bg-white border-r border-slate-100 p-4 gap-6"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.image("images/logoitsss.png").classes(
                    "h-9 w-9 rounded-lg shadow-sm"
                )
                ui.label("TrueTalk").classes("text-lg font-semibold text-blue-700")

            ui.button(
                "Hội thoại mới",
                icon="add",
            ).props("unelevated").classes(
                "w-full rounded-xl bg-blue-600 text-white"
            )

            with ui.column().classes("gap-2"):
                ui.label("TÍNH NĂNG CHÍNH").classes(
                    "text-xs text-slate-400 tracking-wide"
                )
                sidebar_item(label="Tổng quan", icon="grid_view", active=True)
                sidebar_item(label="Dịch hội thoại", icon="translate")
                sidebar_item(label="Phân tích hội thoại", icon="analytics")
                sidebar_item(label="Giải thích văn hóa", icon="menu_book")

            with ui.column().classes("gap-3"):
                with ui.row().classes("items-center justify-between"):
                    ui.label("LỊCH SỬ").classes(
                        "text-xs text-slate-400 tracking-wide"
                    )
                    ui.icon("refresh").classes("text-slate-300 text-sm")

                with ui.column().classes("gap-2 text-sm text-slate-600"):
                    ui.label("Tanaka-san").classes("font-semibold")
                    ui.label("10/04/2026 - Dự án mới").classes("text-xs text-slate-400")

                with ui.column().classes("gap-2 text-sm text-slate-600"):
                    ui.label("Yamada-san").classes("font-semibold")
                    ui.label("09/04/2026 - Báo cáo tuần").classes("text-xs text-slate-400")

        with ui.column().classes("flex-1 p-6 gap-6"):
            navigation_header(
                search_placeholder="Tìm kiếm hội thoại, phân tích, văn hóa...",
                user_name=user_name,
                avatar_url=avatar_url,
                locale_code="VN",
                on_logout=logout_dialog.open,
            )

            with ui.row().classes("w-full items-start justify-between gap-4"):
                with ui.column().classes("gap-1"):
                    ui.label("Tổng quan").classes(
                        "text-2xl font-semibold text-slate-800"
                    )
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
                    ui.link("Xem toàn bộ báo cáo", "#").classes(
                        "text-xs text-blue-600"
                    )

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
