from __future__ import annotations

import json
from typing import Any

from nicegui import ui
from sqlmodel import Session, select

from src.db.session import engine
from src.frontend.components.components import (
    action_button,
    checklist_panel,
    page_title_block,
    stats_cards_row,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState
from src.models.analysis_models import ConversationAnalysis


def empty_analysis_payload() -> dict[str, Any]:
    return {
        "id": None,
        "meeting_title": "Chưa có phân tích hội thoại",
        "meeting_date": "",
        "metrics": [
            {
                "title": "THỜI LƯỢNG",
                "value": "0",
                "subtitle": "Phút tương tác",
                "accent_classes": "border-blue-100 bg-blue-50",
                "value_classes": "text-blue-600",
            },
            {
                "title": "ĐỘ HIỂU",
                "value": "0%",
                "subtitle": "Chưa có dữ liệu",
                "accent_classes": "border-emerald-100 bg-emerald-50",
                "value_classes": "text-emerald-600",
            },
            {
                "title": "CẢM XÚC CHUNG",
                "value": "N/A",
                "subtitle": "Chưa có dữ liệu",
                "accent_classes": "border-purple-100 bg-purple-50",
                "value_classes": "text-purple-600",
            },
        ],
        "ai_overall_feedback": "Chưa có dữ liệu phân tích. Hãy tạo hoặc phân tích một hội thoại trước.",
        "perception_gaps": [],
        "decisions": [],
        "action_items": [],
    }


def normalize_gap(gap: dict[str, Any]) -> dict[str, Any]:
    severity = gap.get("severity", "THẤP")

    if severity == "CAO":
        default_severity_classes = "bg-rose-500 text-white"
        default_card_classes = "w-full rounded-2xl border border-rose-100 bg-rose-50/60 p-4"
    elif severity == "TRUNG BÌNH":
        default_severity_classes = "bg-amber-500 text-white"
        default_card_classes = "w-full rounded-2xl border border-amber-100 bg-amber-50/60 p-4"
    else:
        default_severity_classes = "bg-emerald-500 text-white"
        default_card_classes = "w-full rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4"

    return {
        "title": gap.get("title", "Vấn đề chưa đặt tên"),
        "severity": severity,
        "severity_classes": gap.get("severity_classes") or default_severity_classes,
        "card_classes": gap.get("card_classes") or default_card_classes,
        "left_title": gap.get("left_title", "VN QUAN ĐIỂM VIỆT NAM"),
        "left_text": gap.get("left_text") or gap.get("vn_view", ""),
        "right_title": gap.get("right_title", "JP QUAN ĐIỂM NHẬT BẢN"),
        "right_text": gap.get("right_text") or gap.get("jp_view", ""),
        "recommendation": gap.get("recommendation", ""),
    }


def analysis_to_search_text(row: ConversationAnalysis) -> str:
    payload = {
        "meeting_title": row.meeting_title,
        "meeting_date": row.meeting_date,
        "duration_minutes": row.duration_minutes,
        "transcript": row.transcript,
        "understanding_score": row.understanding_score,
        "overall_sentiment": row.overall_sentiment,
        "ai_overall_feedback": row.ai_overall_feedback,
        "metrics": row.metrics,
        "perception_gaps": row.perception_gaps,
        "decisions": row.decisions,
        "action_items": row.action_items,
    }

    return json.dumps(payload, ensure_ascii=False).lower()


def find_first_analysis_by_keyword(keyword: str) -> ConversationAnalysis | None:
    keyword = keyword.strip().lower()

    if not keyword:
        return None

    with Session(engine) as session:
        statement = (
            select(ConversationAnalysis)
            .order_by(ConversationAnalysis.created_at.desc())
            .limit(200)
        )
        rows = session.exec(statement).all()

        for row in rows:
            if keyword in analysis_to_search_text(row):
                return row

    return None


def row_to_payload(row: ConversationAnalysis) -> dict[str, Any]:
    return {
        "id": row.id,
        "meeting_title": row.meeting_title,
        "meeting_date": row.meeting_date or "",
        "metrics": row.metrics or [],
        "ai_overall_feedback": row.ai_overall_feedback,
        "perception_gaps": [
            normalize_gap(gap) for gap in (row.perception_gaps or [])
        ],
        "decisions": row.decisions or [],
        "action_items": row.action_items or [],
    }


def load_analysis(analysis_id: int | None = None) -> dict[str, Any]:
    try:
        with Session(engine) as session:
            if analysis_id is not None:
                row = session.get(ConversationAnalysis, analysis_id)

                if not row:
                    return empty_analysis_payload()

                return row_to_payload(row)

            statement = (
                select(ConversationAnalysis)
                .order_by(ConversationAnalysis.created_at.desc())
                .limit(1)
            )
            row = session.exec(statement).first()

            if not row:
                return empty_analysis_payload()

            return row_to_payload(row)

    except Exception as e:
        print(f"Cannot load analysis: {e}")
        return empty_analysis_payload()


def render_analysis_page(analysis_id: int | None = None) -> None:
    layout_state = UiState()
    data = load_analysis(analysis_id)

    current_id = data.get("id")
    metrics = data["metrics"]
    perception_gaps = data["perception_gaps"]
    decisions = data["decisions"] or [
        "Chưa phát hiện quyết định chính nào trong hội thoại."
    ]
    action_items = data["action_items"] or ["Chưa có action items."]
    ai_overall_feedback = data["ai_overall_feedback"]

    meeting_title = data["meeting_title"]
    meeting_date = data.get("meeting_date") or ""
    subtitle = f"{meeting_title} - {meeting_date}" if meeting_date else meeting_title

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    def handle_export() -> None:
        if not current_id:
            ui.notify("Chưa có dữ liệu phân tích để xuất PDF.", type="warning")
            return

        ui.notify("Đang tạo báo cáo PDF...", type="info")
        ui.run_javascript(
            f'window.open("/api/analysis/{current_id}/export-pdf", "_blank")'
        )

    def handle_search(value: str) -> None:
        keyword = value.strip()

        if not keyword:
            return

        row = find_first_analysis_by_keyword(keyword)

        if not row or row.id is None:
            ui.notify("Không tìm thấy kết quả phù hợp", type="warning")
            return

        ui.notify(f"Tìm thấy: {row.meeting_title}", type="positive")
        ui.navigate.to(f"/analysis/{row.id}")

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
                subtitle=subtitle,
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
                    ui.label(ai_overall_feedback).classes("text-sm text-slate-600")

        with ui.row().classes("w-full items-start gap-6"):
            with ui.column().classes("flex-1 gap-4"):
                ui.label("Điểm lệch nhận thức").classes(
                    "text-sm font-semibold text-slate-700"
                )

                if not perception_gaps:
                    with ui.element("div").classes(
                        "w-full rounded-2xl border border-slate-100 bg-white p-4"
                    ):
                        ui.label("Chưa phát hiện điểm lệch nhận thức nào.").classes(
                            "text-sm text-slate-500"
                        )

                for gap in perception_gaps:
                    with ui.element("div").classes(
                        gap.get(
                            "card_classes",
                            "w-full rounded-2xl border border-slate-100 bg-white p-4",
                        )
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


@ui.page("/analysis")
def analysis_page() -> None:
    render_analysis_page()


@ui.page("/analysis/{analysis_id}")
def analysis_detail_page(analysis_id: int) -> None:
    render_analysis_page(analysis_id)
