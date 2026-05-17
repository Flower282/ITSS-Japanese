from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from typing import Any
from urllib.parse import urlencode

import httpx
from nicegui import ui

from src.frontend.components.components import action_button
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState
from src.core.i18n import _, get_user_language, validate_language_or_default


API_BASE_URL = "/api"


def clean_display_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = unicodedata.normalize("NFC", text)

    text = "".join(
        char
        for char in text
        if char == "\n"
        or char == "\t"
        or not unicodedata.category(char).startswith("C")
    )

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def safe_list_text(items: list[Any]) -> list[str]:
    cleaned_items: list[str] = []

    for item in items:
        text = clean_display_text(item)

        if text:
            cleaned_items.append(text)

    return cleaned_items


def empty_analysis_payload() -> dict[str, Any]:
    return {
        "id": None,
        "meeting_title": "Chưa có phân tích hội thoại",
        "meeting_date": "",
        "duration_minutes": None,
        "understanding_score": 0,
        "overall_sentiment": "N/A",
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
        "ai_overall_feedback": "Chưa có dữ liệu phân tích trong database.",
        "perception_gaps": [],
        "decisions": [],
        "action_items": [],
        "ai_log_count": 0,
    }


def normalize_metric(metric: dict[str, Any]) -> dict[str, Any]:
    title = clean_display_text(metric.get("title", ""))
    value = clean_display_text(metric.get("value", ""))
    subtitle = clean_display_text(metric.get("subtitle", ""))

    if title == "THỜI LƯỢNG":
        return {
            "title": title,
            "value": value,
            "subtitle": subtitle or "Phút tương tác",
            "accent_classes": "border-blue-100 bg-blue-50",
            "value_classes": "text-blue-600",
        }

    if title == "ĐỘ HIỂU":
        return {
            "title": title,
            "value": value,
            "subtitle": subtitle or "Truyền đạt chính xác",
            "accent_classes": "border-emerald-100 bg-emerald-50",
            "value_classes": "text-emerald-600",
        }

    return {
        "title": title or "CẢM XÚC CHUNG",
        "value": value or "N/A",
        "subtitle": subtitle or "Tích cực & Xây dựng",
        "accent_classes": "border-purple-100 bg-purple-50",
        "value_classes": "text-purple-600",
    }


def normalize_gap(gap: dict[str, Any]) -> dict[str, Any]:
    severity = clean_display_text(gap.get("severity", "THẤP")).upper()

    if severity == "CAO":
        severity_classes = "bg-rose-500 text-white"
        card_classes = "w-full rounded-2xl border border-rose-100 bg-rose-50/60 p-4"
    elif severity == "TRUNG BÌNH":
        severity_classes = "bg-amber-500 text-white"
        card_classes = "w-full rounded-2xl border border-amber-100 bg-amber-50/60 p-4"
    else:
        severity_classes = "bg-emerald-500 text-white"
        card_classes = "w-full rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4"

    return {
        "title": clean_display_text(gap.get("title", "Vấn đề chưa đặt tên")),
        "severity": severity,
        "severity_classes": gap.get("severity_classes") or severity_classes,
        "card_classes": gap.get("card_classes") or card_classes,
        "left_title": clean_display_text(gap.get("left_title", "Quan điểm Việt Nam")),
        "left_text": clean_display_text(gap.get("left_text", "")),
        "right_title": clean_display_text(gap.get("right_title", "Quan điểm Nhật Bản")),
        "right_text": clean_display_text(gap.get("right_text", "")),
        "recommendation": clean_display_text(gap.get("recommendation", "")),
    }


def normalize_analysis_payload(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id"),
        "meeting_title": clean_display_text(
            data.get("meeting_title") or "Cuộc hội thoại chưa đặt tên"
        ),
        "meeting_date": clean_display_text(data.get("meeting_date") or ""),
        "duration_minutes": data.get("duration_minutes"),
        "understanding_score": data.get("understanding_score") or 0,
        "overall_sentiment": clean_display_text(data.get("overall_sentiment") or "N/A"),
        "metrics": [
            normalize_metric(metric)
            for metric in (data.get("metrics") or [])
            if isinstance(metric, dict)
        ],
        "ai_overall_feedback": clean_display_text(
            data.get("ai_overall_feedback") or ""
        ),
        "perception_gaps": [
            normalize_gap(gap)
            for gap in (data.get("perception_gaps") or [])
            if isinstance(gap, dict)
        ],
        "decisions": safe_list_text(data.get("decisions") or []),
        "action_items": safe_list_text(data.get("action_items") or []),
        "ai_log_count": data.get("ai_log_count") or 0,
    }


async def fetch_json_from_api(url: str) -> Any:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:
        response = await client.get(url, headers={"Accept": "application/json"})

    if response.status_code == 404:
        raise RuntimeError("Backend không tìm thấy dữ liệu phân tích.")

    if response.status_code >= 400:
        detail = response.text

        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("detail") or detail)
        except Exception:
            pass

        raise RuntimeError(detail)

    return response.json()

    if not result or not result.get("ok"):
        detail = "Không gọi được API backend."

        if result and isinstance(result.get("data"), dict):
            detail = result["data"].get("detail") or detail

        raise RuntimeError(detail)

    return result.get("data")


async def load_analysis_from_api(analysis_id: int | None = None) -> dict[str, Any]:
    try:
        if analysis_id is None:
            data = await fetch_json_from_api(f"{API_BASE_URL}/analysis/latest/ensure")
        else:
            data = await fetch_json_from_api(f"{API_BASE_URL}/analysis/{analysis_id}/ensure")

        if not isinstance(data, dict):
            raise RuntimeError("API không trả về JSON object hợp lệ.")

        return normalize_analysis_payload(data)

    except Exception as e:
        print(f"Cannot load analysis from API: {e}")
        ui.notify(f"Không tải được dữ liệu phân tích: {e}", type="negative")
        return empty_analysis_payload()


async def search_first_analysis_from_api(keyword: str) -> dict[str, Any] | None:
    keyword = keyword.strip()

    if not keyword:
        return None

    try:
        data = await fetch_json_from_api(
            f"{API_BASE_URL}/analysis/search?{urlencode({'q': keyword, 'limit': 1})}"
        )

        if not isinstance(data, list) or not data:
            return None

        if not isinstance(data[0], dict):
            return None

        return normalize_analysis_payload(data[0])

        result = await ui.run_javascript(
            f"""
            const params = new URLSearchParams();
            params.set("q", {json.dumps(keyword)});
            params.set("limit", "1");

            return fetch("{API_BASE_URL}/analysis/search?" + params.toString(), {{
                method: "GET",
                headers: {{
                    "Accept": "application/json"
                }}
            }})
            .then(async response => {{
                const text = await response.text();

                let data = null;
                try {{
                    data = text ? JSON.parse(text) : null;
                }} catch (error) {{
                    data = [];
                }}

                return {{
                    ok: response.ok,
                    status: response.status,
                    data: data
                }};
            }})
            .catch(error => {{
                return {{
                    ok: false,
                    status: 0,
                    data: []
                }};
            }});
            """,
            respond=True,
            timeout=30,
        )

        if not result or not result.get("ok"):
            return None

        data = result.get("data")

        if not isinstance(data, list) or not data:
            return None

        if not isinstance(data[0], dict):
            return None

        return normalize_analysis_payload(data[0])

    except Exception as e:
        print(f"Cannot search analysis from API: {e}")
        ui.notify(f"Lỗi tìm kiếm phân tích: {e}", type="negative")
        return None


def add_analysis_css() -> None:
    ui.add_head_html(
        """
        <style>
            body, input, textarea, select, button {
                font-family: "Segoe UI", "Arial", "Tahoma", "Verdana", sans-serif;
                text-rendering: optimizeLegibility;
                -webkit-font-smoothing: antialiased;
            }

            .analysis-text {
                font-family: "Segoe UI", "Arial", "Tahoma", "Verdana", sans-serif;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: normal;
                line-height: 1.55;
                letter-spacing: normal;
            }

            .analysis-card {
                border-radius: 18px;
                border: 1px solid #e2e8f0;
                background: white;
                box-shadow: 0 8px 20px rgba(15, 23, 42, 0.045);
            }

            .analysis-metric-value {
                white-space: nowrap !important;
                overflow-wrap: normal !important;
                word-break: keep-all !important;
            }

            .analysis-metric-copy {
                overflow-wrap: normal !important;
                word-break: normal !important;
            }

            .analysis-metric-value-long {
                font-size: 1.55rem !important;
                line-height: 1 !important;
            }

            .analysis-metric-copy-compact {
                overflow-wrap: normal !important;
                word-break: normal !important;
                font-size: 0.9rem !important;
            }
        </style>
        """
    )


def render_text(text: Any, classes: str = ""):
    return ui.label(clean_display_text(text)).classes(
        f"analysis-text {classes}"
    )


def render_metric_card(metric: dict[str, Any]) -> None:
    is_sentiment_metric = metric.get("title") == "CẢM XÚC CHUNG"
    value = clean_display_text(metric.get("value", ""))
    is_long_sentiment = is_sentiment_metric and len(value) > 6
    value_width_class = "w-[116px]" if is_long_sentiment else (
        "w-[128px]" if is_sentiment_metric else "w-[96px]"
    )
    value_size_class = "analysis-metric-value-long" if is_long_sentiment else (
        "text-3xl" if is_sentiment_metric and len(value) > 3 else "text-4xl"
    )
    copy_class = (
        "analysis-metric-copy analysis-metric-copy-compact"
        if is_sentiment_metric
        else "analysis-metric-copy"
    )

    with ui.element("div").classes(
        f"flex-1 min-w-[250px] h-[112px] overflow-hidden rounded-2xl border px-5 py-4 "
        f"{metric.get('accent_classes') or 'border-slate-100 bg-slate-50'}"
    ):
        with ui.row().classes("h-full flex-nowrap items-center gap-4"):
            render_text(
                value,
                f"analysis-metric-value {value_width_class} shrink-0 {value_size_class} font-bold leading-none "
                f"{metric.get('value_classes') or 'text-slate-800'}",
            )

            copy_column_classes = (
                "min-w-0 flex-1 gap-0.5 pl-3"
                if is_long_sentiment
                else "min-w-0 flex-1 gap-0.5"
            )
            with ui.column().classes(copy_column_classes):
                ui.label(metric.get("title", "")).classes(
                    "text-[11px] font-bold uppercase tracking-wide text-slate-500"
                )
                render_text(
                    metric.get("subtitle", ""),
                    f"{copy_class} text-sm font-semibold text-slate-700 leading-snug",
                )


def render_feedback_card(ai_overall_feedback: str, lang: str = 'vn') -> None:
    with ui.element("div").classes("analysis-card w-full px-6 py-5"):
        with ui.row().classes("w-full flex-nowrap items-start gap-5"):
            with ui.element("div").classes(
                "h-11 w-11 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0"
            ):
                ui.icon("psychology").classes("text-lg")

            with ui.column().classes("gap-1.5 flex-1 min-w-0"):
                ui.label(_('ai_overall_feedback_label', lang)).classes(
                    "text-lg font-bold text-slate-800"
                )
                render_text(
                    ai_overall_feedback,
                    "text-sm font-medium text-slate-600",
                )


def render_gap_card(gap: dict[str, Any], lang: str = 'vn') -> None:
    with ui.element("div").classes(gap["card_classes"]):
        with ui.row().classes("items-center justify-between gap-3 w-full"):
            render_text(
                gap["title"],
                "text-base font-bold text-slate-800",
            )
            ui.label(gap["severity"]).classes(
                f"text-[11px] font-bold px-3 py-1 rounded-full "
                f"{gap['severity_classes']}"
            )

        with ui.row().classes("gap-3 mt-3 w-full"):
            with ui.element("div").classes(
                "flex-1 min-w-0 rounded-xl border border-slate-100 bg-white px-4 py-3"
            ):
                ui.label(gap["left_title"]).classes(
                    "text-[10px] font-bold uppercase tracking-wide text-slate-400"
                )
                render_text(
                    gap["left_text"],
                    "text-sm font-semibold text-slate-700 mt-2",
                )

            with ui.element("div").classes(
                "flex-1 min-w-0 rounded-xl border border-slate-100 bg-white px-4 py-3"
            ):
                ui.label(gap["right_title"]).classes(
                    "text-[10px] font-bold uppercase tracking-wide text-slate-400"
                )
                render_text(
                    gap["right_text"],
                    "text-sm font-semibold text-slate-700 mt-2",
                )

        with ui.element("div").classes(
            "mt-3 rounded-xl border border-blue-100 bg-white px-4 py-3"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("tips_and_updates").classes("text-blue-600 text-sm")
                ui.label(_('ai_recommendation', lang)).classes(
                    "text-[10px] font-bold uppercase tracking-wide text-blue-600"
                )

            render_text(
                gap["recommendation"],
                "text-sm font-semibold text-slate-700 mt-2",
            )


def render_check_item(text: str) -> None:
    with ui.row().classes("items-start gap-3 w-full"):
        ui.icon("check_circle").classes("text-emerald-500 text-lg mt-0.5")
        render_text(text, "text-sm font-semibold text-slate-700 flex-1")


def render_summary_panel(title: str, items: list[str], icon: str) -> None:
    with ui.element("div").classes("analysis-card w-full px-5 py-4"):
        with ui.row().classes("items-center gap-3 border-b border-slate-100 pb-3"):
            ui.icon(icon).classes("text-blue-500 text-lg")
            ui.label(title).classes("text-lg font-bold text-slate-800")

        with ui.column().classes("gap-3 pt-4 w-full"):
            for item in items:
                render_check_item(item)


def render_analysis_page(analysis_id: int | None = None) -> None:
    add_analysis_css()

    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

    state: dict[str, Any] = {
        "data": empty_analysis_payload(),
        "loading": True,
        "search_query": "",
        "search_results": [],
    }

    async def load_data() -> None:
        state["loading"] = True
        dashboard.refresh()

        state["data"] = await load_analysis_from_api(analysis_id)
        state["loading"] = False
        dashboard.refresh()

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    async def handle_search(value: str) -> None:
        keyword = value.strip()
        state["search_query"] = keyword

        if not keyword:
            state["search_results"] = []
            dashboard.refresh()
            return

        try:
            results = await fetch_json_from_api(
                f"{API_BASE_URL}/analysis/search?{urlencode({'q': keyword, 'limit': 8})}"
            )
        except Exception as e:
            print(f"Cannot search analysis from API: {e}")
            state["search_results"] = []
            dashboard.refresh()
            return

        if not isinstance(results, list):
            state["search_results"] = []
            dashboard.refresh()
            return

        state["search_results"] = [
            normalize_analysis_payload(item)
            for item in results
            if isinstance(item, dict)
        ]
        dashboard.refresh()
        return

        result = await search_first_analysis_from_api(value)

        if not result or result.get("id") is None:
            ui.notify("Không tìm thấy kết quả phù hợp", type="warning")
            return

        ui.notify(f"Tìm thấy: {result.get('meeting_title')}", type="positive")
        ui.navigate.to(f"/analysis/{result['id']}")

    def open_analysis_result(result: dict[str, Any]) -> None:
        analysis_id = result.get("id")

        if analysis_id is None:
            return

        ui.notify(f"Tìm thấy: {result.get('meeting_title')}", type="positive")
        ui.navigate.to(f"/analysis/{analysis_id}")

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', lang), type="info")

    @ui.refreshable
    def dashboard() -> None:
        data = state["data"]

        current_id = data.get("id")
        meeting_title = data["meeting_title"]
        meeting_date = data.get("meeting_date") or ""
        metrics = data["metrics"]
        ai_overall_feedback = data["ai_overall_feedback"]
        perception_gaps = data["perception_gaps"]
        search_query = state.get("search_query", "")
        search_results = state.get("search_results", [])

        decisions = data["decisions"] or [
            "Chưa phát hiện quyết định chính nào trong hội thoại."
        ]
        action_items = data["action_items"] or ["Chưa có action items."]

        subtitle = f"{meeting_title} - {meeting_date}" if meeting_date else meeting_title

        def handle_export() -> None:
            if not current_id:
                ui.notify(_('no_data_export', lang), type="warning")
                return

            ui.notify(_('generating_pdf', lang), type="info")
            ui.run_javascript(
                f'window.open("{API_BASE_URL}/analysis/{current_id}/export-pdf", "_blank")'
            )

        with ui.column().classes("w-full max-w-[1180px] mx-auto gap-5"):
            with ui.row().classes("w-full items-start justify-between gap-4"):
                with ui.column().classes("gap-0.5"):
                    ui.label(_('conversation_analysis', lang)).classes(
                        "text-2xl font-bold text-slate-900 leading-tight"
                    )
                    render_text(
                        subtitle,
                        "text-sm font-semibold text-slate-500",
                    )

                action_button(
                    label=_('export_pdf', lang),
                    icon="download",
                    variant="primary",
                    on_click=handle_export,
                )

            with ui.row().classes("hidden"):
                search_box = (
                    ui.input(
                        placeholder="Tìm hội thoại cũ trong database...",
                        value=search_query,
                    )
                    .props("outlined dense rounded prepend-icon=search clearable")
                    .classes("flex-1 bg-white")
                )
                search_box.on(
                    "keydown.enter",
                    lambda: asyncio.create_task(handle_search(search_box.value or "")),
                )
                action_button(
                    label="Tìm kiếm",
                    icon="search",
                    variant="secondary",
                    on_click=lambda: asyncio.create_task(
                        handle_search(search_box.value or "")
                    ),
                )

            if search_query:
                with ui.element("div").classes("analysis-card w-full px-5 py-4"):
                    with ui.row().classes("items-center justify-between gap-3"):
                        ui.label(f"{_('search_results_label', lang)}: {search_query}").classes(
                            "text-base font-bold text-slate-800"
                        )
                        ui.label(f"{len(search_results)} {_('results_count', lang)}").classes(
                            "text-xs font-semibold text-slate-500"
                        )

                    if not search_results:
                        render_text(
                            _('no_conv_found', lang),
                            "text-sm text-slate-500 mt-3",
                        )

                    for result in search_results:
                        with ui.row().classes(
                            "w-full items-center justify-between gap-4 rounded-xl border border-slate-100 px-4 py-3 mt-3 hover:bg-slate-50"
                        ):
                            with ui.column().classes("gap-1 min-w-0"):
                                render_text(
                                    result.get("meeting_title", ""),
                                    "text-sm font-bold text-slate-800",
                                )
                                render_text(
                                    result.get("ai_overall_feedback", ""),
                                    "text-xs text-slate-500",
                                )

                            action_button(
                                label=_('open_analysis', lang),
                                icon="open_in_new",
                                variant="secondary",
                                on_click=lambda r=result: open_analysis_result(r),
                            )

            if state["loading"]:
                with ui.element("div").classes(
                    "analysis-card w-full px-6 py-10 text-center"
                ):
                    ui.spinner(size="lg")
                    ui.label(_('loading_data', lang)).classes(
                        "mt-3 text-sm font-semibold text-slate-500"
                    )
                return

            with ui.row().classes("w-full items-stretch gap-4"):
                for metric in metrics:
                    render_metric_card(metric)

            render_feedback_card(ai_overall_feedback, lang)

            with ui.row().classes("w-full gap-6 items-start"):
                with ui.column().classes("flex-[1.08] gap-4 min-w-0"):
                    with ui.row().classes(
                        "items-center gap-3 border-b border-slate-200 pb-3"
                    ):
                        ui.icon("warning_amber").classes("text-orange-500 text-xl")
                        ui.label(_('perception_gaps_label', lang)).classes(
                            "text-lg font-bold text-slate-800"
                        )

                    if not perception_gaps:
                        with ui.element("div").classes(
                            "analysis-card w-full px-5 py-4"
                        ):
                            render_text(
                                _('no_gaps', lang),
                                "text-sm text-slate-500",
                            )

                    for gap in perception_gaps:
                        render_gap_card(gap, lang)

                with ui.column().classes("flex-[0.92] gap-4 min-w-0"):
                    with ui.row().classes(
                        "items-center gap-3 border-b border-slate-200 pb-3"
                    ):
                        ui.icon("article").classes("text-blue-500 text-xl")
                        ui.label(_('content_summary', lang)).classes(
                            "text-lg font-bold text-slate-800"
                        )

                    render_summary_panel(
                        title=_('main_decisions', lang),
                        items=decisions,
                        icon="check_circle",
                    )

                    render_summary_panel(
                        title=_('action_items_label', lang),
                        items=action_items,
                        icon="task_alt",
                    )

    with base_layout(
        active_nav="/analysis",
        ui_state=layout_state,
        on_new_conversation=handle_new_conversation,
        on_search=handle_search,
        on_locale_click=handle_locale_click,
    ):
        dashboard()

    ui.timer(0.2, load_data, once=True)


@ui.page("/analysis")
def analysis_page() -> None:
    render_analysis_page()


@ui.page("/analysis/{analysis_id}")
def analysis_detail_page(analysis_id: int) -> None:
    render_analysis_page(analysis_id)
