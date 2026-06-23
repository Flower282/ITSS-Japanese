from __future__ import annotations

import asyncio
import re
import unicodedata
from typing import Any
from urllib.parse import urlencode

from nicegui import ui, app

from src.frontend.api_client import api_get
from src.frontend.components.components import action_button
from src.frontend.services.conversation_service import (
    load_conversation_history,
    load_translate_context,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.ui_state import UiState
from src.core.i18n import _, get_user_language, validate_language_or_default, nav


API_BASE_URL = "/api"

LANGUAGE_OPTIONS = {
    "vn": "Tiếng Việt",
    "jp": "日本語",
}


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


def empty_analysis_payload(lang: str = "vn") -> dict[str, Any]:
    return {
        "id": None,
        "meeting_title": _("no_analysis_data_title", lang),
        "meeting_date": "",
        "duration_minutes": None,
        "understanding_score": 0,
        "overall_sentiment": "N/A",
        "metrics": [
            {
                "title": _("duration_metric_title", lang),
                "value": "0",
                "subtitle": _("duration_metric_subtitle", lang),
                "accent_classes": "border-blue-100 bg-blue-50",
                "value_classes": "text-blue-600",
            },
            {
                "title": _("understanding_metric_title", lang),
                "value": "0%",
                "subtitle": _("no_data", lang),
                "accent_classes": "border-emerald-100 bg-emerald-50",
                "value_classes": "text-emerald-600",
            },
            {
                "title": _("sentiment_metric_title", lang),
                "value": "N/A",
                "subtitle": _("no_data", lang),
                "accent_classes": "border-purple-100 bg-purple-50",
                "value_classes": "text-purple-600",
            },
        ],
        "ai_overall_feedback": _("no_analysis_feedback", lang),
        "perception_gaps": [],
        "decisions": [],
        "action_items": [],
        "ai_log_count": 0,
    }


def normalize_metric(metric: dict[str, Any], lang: str) -> dict[str, Any]:
    title = clean_display_text(metric.get("title", ""))
    value = clean_display_text(metric.get("value", ""))
    subtitle = clean_display_text(metric.get("subtitle", ""))
    accent_classes = metric.get("accent_classes")
    value_classes = metric.get("value_classes")

    DURATION_TITLES = {"THỜI LƯỢNG", "時間"}
    UNDERSTANDING_TITLES = {"ĐỘ HIỂU", "理解度", "理解"}

    if title in DURATION_TITLES:
        return {
            "title": title,
            "value": value,
            "subtitle": subtitle or _("duration_metric_subtitle", lang),
            "accent_classes": accent_classes or "border-blue-100 bg-blue-50",
            "value_classes": value_classes or "text-blue-600",
        }

    if title in UNDERSTANDING_TITLES:
        return {
            "title": title,
            "value": value,
            "subtitle": subtitle or _("understanding_metric_subtitle", lang),
            "accent_classes": accent_classes or "border-emerald-100 bg-emerald-50",
            "value_classes": value_classes or "text-emerald-600",
        }

    return {
        "title": title or _("sentiment_metric_title", lang),
        "value": value or "N/A",
        "subtitle": subtitle or _("sentiment_metric_subtitle", lang),
        "accent_classes": accent_classes or "border-purple-100 bg-purple-50",
        "value_classes": value_classes or "text-purple-600",
    }


def normalize_gap(gap: dict[str, Any], lang: str) -> dict[str, Any]:
    raw_severity = clean_display_text(gap.get("severity", "THẤP"))

    # Support Vietnamese and Japanese severity labels. Map display value to
    # internal keys for class selection, but keep the original text for display.
    SEVERITY_MAP = {
        "CAO": "CAO",
        "高": "CAO",
        "TRUNG BÌNH": "TRUNG BÌNH",
        "中": "TRUNG BÌNH",
        "THẤP": "THẤP",
        "低": "THẤP",
    }

    norm_key = SEVERITY_MAP.get(raw_severity.upper(), SEVERITY_MAP.get(raw_severity, "THẤP"))

    if norm_key == "CAO":
        severity_classes = "bg-rose-500 text-white"
        card_classes = "w-full rounded-2xl border border-rose-100 bg-rose-50/60 p-4"
    elif norm_key == "TRUNG BÌNH":
        severity_classes = "bg-amber-500 text-white"
        card_classes = "w-full rounded-2xl border border-amber-100 bg-amber-50/60 p-4"
    else:
        severity_classes = "bg-emerald-500 text-white"
        card_classes = "w-full rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4"

    return {
        "title": clean_display_text(gap.get("title", _("untitled_issue", lang))),
        "severity": raw_severity,
        "severity_classes": gap.get("severity_classes") or severity_classes,
        "card_classes": gap.get("card_classes") or card_classes,
        "left_title": clean_display_text(
            gap.get("left_title", _("vietnamese_perspective", lang))
        ),
        "left_text": clean_display_text(gap.get("left_text", "")),
        "right_title": clean_display_text(
            gap.get("right_title", _("japanese_perspective", lang))
        ),
        "right_text": clean_display_text(gap.get("right_text", "")),
        "recommendation": clean_display_text(gap.get("recommendation", "")),
    }


def normalize_analysis_payload(data: dict[str, Any], lang: str) -> dict[str, Any]:
    duration_mins = data.get("duration_minutes")
    if duration_mins is not None:
        try:
            val_num = float(duration_mins)
            duration_val = f"{int(val_num)}" if val_num % 1 == 0 else f"{val_num}"
        except (ValueError, TypeError):
            duration_val = str(duration_mins)
    else:
        duration_val = "0"

    raw_metrics = data.get("metrics") or []
    normalized_metrics = []
    for metric in raw_metrics:
        if isinstance(metric, dict):
            norm_m = normalize_metric(metric, lang)
            if norm_m.get("title") in {"THỜI LƯỢNG", "時間"}:
                norm_m["value"] = duration_val
            normalized_metrics.append(norm_m)

    return {
        "id": data.get("id"),
        "meeting_title": clean_display_text(
            data.get("meeting_title") or _("untitled_conversation", lang)
        ),
        "meeting_date": clean_display_text(data.get("meeting_date") or ""),
        "duration_minutes": duration_mins,
        "understanding_score": data.get("understanding_score") or 0,
        "overall_sentiment": clean_display_text(data.get("overall_sentiment") or "N/A"),
        "metrics": normalized_metrics,
        "ai_overall_feedback": clean_display_text(
            data.get("ai_overall_feedback") or ""
        ),
        "perception_gaps": [
            normalize_gap(gap, lang)
            for gap in (data.get("perception_gaps") or [])
            if isinstance(gap, dict)
        ],
        "decisions": safe_list_text(data.get("decisions") or []),
        "action_items": safe_list_text(data.get("action_items") or []),
        "ai_log_count": data.get("ai_log_count") or 0,
    }


async def fetch_json_from_api(url: str) -> Any:
    try:
        return await api_get(url, timeout=60.0)
    except Exception as exc:
        detail = str(getattr(exc, "detail", None) or exc)
        if "404" in detail or "not found" in detail.lower():
            raise RuntimeError("analysis_not_found") from exc
        raise RuntimeError(detail) from exc


async def load_analysis_from_api(
    analysis_id: int | None = None,
    lang: str = "vn",
) -> dict[str, Any]:
    try:
        query = urlencode({"lang": lang})

        if analysis_id is None:
            data = await fetch_json_from_api(
                f"{API_BASE_URL}/analysis/latest/ensure?{query}"
            )
        else:
            data = await fetch_json_from_api(
                f"{API_BASE_URL}/analysis/{analysis_id}/ensure?{query}"
            )

        if not isinstance(data, dict):
            raise RuntimeError("invalid_analysis_response")

        conversation_id = data.get("id")
        if conversation_id is not None:
            try:
                context = await load_translate_context(conversation_id, lang)
                messages = context.get("messages") or []
                num_messages = len(messages)
                data["duration_minutes"] = num_messages * 1.5
            except Exception as e:
                print(f"Cannot load translate context for message count: {e}")

        return normalize_analysis_payload(data, lang)

    except Exception as e:
        print(f"Cannot load analysis from API: {e}")
        detail = str(e)
        if detail == "analysis_not_found":
            detail = _("backend_analysis_not_found", lang)
        elif detail == "invalid_analysis_response":
            detail = _("invalid_analysis_response", lang)
        ui.notify(f"{_('failed_analysis_load', lang)}: {detail}", type="negative")
        return empty_analysis_payload(lang)


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

            .analysis-search-dropdown {
                scrollbar-width: thin;
                scrollbar-color: #cbd5e1 transparent;
            }

            .analysis-search-dropdown::-webkit-scrollbar {
                width: 6px;
            }

            .analysis-search-dropdown::-webkit-scrollbar-track {
                background: transparent;
            }

            .analysis-search-dropdown::-webkit-scrollbar-thumb {
                background: #cbd5e1;
                border-radius: 999px;
            }

            .analysis-search-dropdown::-webkit-scrollbar-thumb:hover {
                background: #94a3b8;
            }
        </style>
        """
    )


def jp_weight(lang: str, default: str, jp: str) -> str:
    return jp if lang == "jp" else default


def render_text(text: Any, classes: str = ""):
    return ui.label(clean_display_text(text)).classes(
        f"analysis-text {classes}"
    )


def render_metric_card(metric: dict[str, Any], lang: str) -> None:
    SENTIMENT_TITLES = {"CẢM XÚC CHUNG", "全体の感情", "感情"}
    is_sentiment_metric = metric.get("title") in SENTIMENT_TITLES
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
                f"analysis-metric-value {value_width_class} shrink-0 {value_size_class} "
                f"{jp_weight(lang, 'font-bold', 'font-semibold')} leading-none "
                f"{metric.get('value_classes') or 'text-slate-800'}",
            )

            copy_column_classes = (
                "min-w-0 flex-1 gap-0.5 pl-3"
                if is_long_sentiment
                else "min-w-0 flex-1 gap-0.5"
            )
            with ui.column().classes(copy_column_classes):
                ui.label(metric.get("title", "")).classes(
                    f"text-[11px] {jp_weight(lang, 'font-bold', 'font-semibold')} uppercase tracking-wide text-slate-500"
                )
                render_text(
                    metric.get("subtitle", ""),
                    f"{copy_class} text-sm {jp_weight(lang, 'font-semibold', 'font-medium')} text-slate-700 leading-snug",
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
                    f"text-lg {jp_weight(lang, 'font-bold', 'font-semibold')} text-slate-800"
                )
                render_text(
                    ai_overall_feedback,
                    f"text-sm {jp_weight(lang, 'font-medium', 'font-normal')} text-slate-600",
                )


def render_gap_card(gap: dict[str, Any], lang: str = 'vn') -> None:
    with ui.element("div").classes(gap["card_classes"]):
        with ui.row().classes("items-center justify-between gap-3 w-full"):
            render_text(
                gap["title"],
                f"text-base {jp_weight(lang, 'font-bold', 'font-semibold')} text-slate-800",
            )
            ui.label(gap["severity"]).classes(
                f"text-[11px] {jp_weight(lang, 'font-bold', 'font-semibold')} px-3 py-1 rounded-full "
                f"{gap['severity_classes']}"
            )

        with ui.row().classes("gap-3 mt-3 w-full"):
            with ui.element("div").classes(
                "flex-1 min-w-0 rounded-xl border border-slate-100 bg-white px-4 py-3"
            ):
                ui.label(gap["left_title"]).classes(
                    f"text-[10px] {jp_weight(lang, 'font-bold', 'font-semibold')} uppercase tracking-wide text-slate-400"
                )
                render_text(
                    gap["left_text"],
                    f"text-sm {jp_weight(lang, 'font-semibold', 'font-medium')} text-slate-700 mt-2",
                )

            with ui.element("div").classes(
                "flex-1 min-w-0 rounded-xl border border-slate-100 bg-white px-4 py-3"
            ):
                ui.label(gap["right_title"]).classes(
                    f"text-[10px] {jp_weight(lang, 'font-bold', 'font-semibold')} uppercase tracking-wide text-slate-400"
                )
                render_text(
                    gap["right_text"],
                    f"text-sm {jp_weight(lang, 'font-semibold', 'font-medium')} text-slate-700 mt-2",
                )

        with ui.element("div").classes(
            "mt-3 rounded-xl border border-blue-100 bg-white px-4 py-3"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.icon("tips_and_updates").classes("text-blue-600 text-sm")
                ui.label(_('ai_recommendation', lang)).classes(
                    f"text-[10px] {jp_weight(lang, 'font-bold', 'font-semibold')} uppercase tracking-wide text-blue-600"
                )

            render_text(
                gap["recommendation"],
                f"text-sm {jp_weight(lang, 'font-semibold', 'font-medium')} text-slate-700 mt-2",
            )


def render_check_item(text: str, lang: str) -> None:
    with ui.row().classes("items-start gap-3 w-full"):
        ui.icon("check_circle").classes("text-emerald-500 text-lg mt-0.5")
        render_text(
            text,
            f"text-sm {jp_weight(lang, 'font-semibold', 'font-medium')} text-slate-700 flex-1",
        )


def render_summary_panel(title: str, items: list[str], icon: str, lang: str) -> None:
    with ui.element("div").classes("analysis-card w-full px-5 py-4"):
        with ui.row().classes("items-center gap-3 border-b border-slate-100 pb-3"):
            ui.icon(icon).classes("text-blue-500 text-lg")
            ui.label(title).classes(
                f"text-lg {jp_weight(lang, 'font-bold', 'font-semibold')} text-slate-800"
            )

        with ui.column().classes("gap-3 pt-4 w-full"):
            for item in items:
                render_check_item(item, lang)


def render_analysis_page(analysis_id: int | None = None) -> None:
    add_analysis_css()

    layout_state = UiState()

    initial_lang = validate_language_or_default(get_user_language())

    state: dict[str, Any] = {
        "lang": initial_lang,
        "data": empty_analysis_payload(initial_lang),
        "active_analysis_id": analysis_id,
        "history_items": [],
        "loading": True,
        "search_query": "",
        "search_results": [],
        "synced_latest_route": analysis_id is not None,
    }

    async def load_data() -> None:
        active_id = state.get("active_analysis_id")
        cache_key = f"analysis_{active_id}_{state['lang']}" if active_id else f"analysis_latest_{state['lang']}"
        cached_data = app.storage.user.get(cache_key)

        if cached_data:
            state["data"] = cached_data
            state["loading"] = False
            page_shell.refresh()
        else:
            state["loading"] = True
            page_shell.refresh()

        try:
            state["history_items"] = await load_conversation_history()
        except Exception:
            state["history_items"] = []

        fetched_data = await load_analysis_from_api(
            active_id,
            state["lang"],
        )
        state["data"] = fetched_data

        current_id = fetched_data.get("id")
        if current_id:
            app.storage.user[f"analysis_{current_id}_{state['lang']}"] = fetched_data
            if not active_id:
                app.storage.user[f"analysis_latest_{state['lang']}"] = fetched_data

        state["active_analysis_id"] = current_id
        layout_state.selected_history_id = current_id
        if current_id and not any(
            h.get("id") == current_id for h in state["history_items"]
        ):
            state["history_items"].insert(
                0,
                {
                    "id": current_id,
                    "label": state["data"].get("meeting_title", ""),
                    "subtitle": state["data"].get("meeting_date", ""),
                },
            )
        state["loading"] = False
        page_shell.refresh()

        if (
            analysis_id is None
            and current_id is not None
            and not state.get("synced_latest_route")
        ):
            state["synced_latest_route"] = True
            ui.navigate.to(nav(f"/analysis/{current_id}", state["lang"]))

    def handle_new_conversation() -> None:
        ui.navigate.to(nav("/translate", state["lang"]))

    async def handle_search(value: str) -> None:
        keyword = value.strip()
        state["search_query"] = keyword

        if not keyword:
            state["search_results"] = []
            page_shell.refresh()
            return

        try:
            results = await fetch_json_from_api(
                f"{API_BASE_URL}/analysis/search?{urlencode({'q': keyword, 'limit': 10})}"
            )
        except Exception as e:
            if state.get("search_query") != keyword:
                return
            print(f"Cannot search analysis from API: {e}")
            state["search_results"] = []
            page_shell.refresh()
            return

        if state.get("search_query") != keyword:
            return

        if not isinstance(results, list):
            state["search_results"] = []
            page_shell.refresh()
            return

        state["search_results"] = [
            normalize_analysis_payload(item, state["lang"])
            for item in results
            if isinstance(item, dict)
        ]
        page_shell.refresh()

    def open_analysis_result(result: dict[str, Any]) -> None:
        analysis_id = result.get("id")

        if analysis_id is None:
            return

        state["active_analysis_id"] = analysis_id
        layout_state.selected_history_id = analysis_id
        ui.notify(f"{_('found_label', state['lang'])}: {result.get('meeting_title')}", type="positive")
        ui.navigate.to(nav(f"/analysis/{analysis_id}", state["lang"]))

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', state["lang"]), type="info")

    @ui.refreshable
    def page_shell() -> None:
        with base_layout(
            active_nav="/analysis",
            ui_state=layout_state,
            on_new_conversation=handle_new_conversation,
            on_history_select=lambda selected_id: ui.navigate.to(
                nav(f"/analysis/{selected_id}", state["lang"])
            ),
            history_items=state.get("history_items", []),
            on_search=handle_search,
            on_locale_click=handle_locale_click,
            on_locale_change=lambda value: asyncio.create_task(handle_language_change(value)),
        ):
            dashboard()

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
            _('no_decisions', state["lang"])
        ]
        action_items = data["action_items"] or [_('no_action_items', state["lang"])]

        subtitle = f"{meeting_title} - {meeting_date}" if meeting_date else meeting_title

        def handle_export() -> None:
            if not current_id:
                ui.notify(_('no_data_export', state["lang"]), type="warning")
                return

            ui.notify(_('generating_pdf', state["lang"]), type="info")
            query = urlencode({"lang": state["lang"]})
            ui.run_javascript(
                f'window.open("{API_BASE_URL}/analysis/{current_id}/export-pdf?{query}", "_blank")'
            )

        async def handle_refresh() -> None:
            if not current_id:
                ui.notify("Không có dữ liệu để cập nhật", type="warning")
                return
            ui.notify("Đang cập nhật phân tích, vui lòng chờ...", type="info")
            try:
                from src.frontend.services.conversation_service import run_analysis
                await run_analysis(current_id)
                ui.notify("Đã cập nhật phân tích thành công", type="positive")
                
                # Clear client-side cache
                cache_key = f"analysis_{current_id}_{state['lang']}"
                if cache_key in app.storage.user:
                    del app.storage.user[cache_key]
                
                await load_data()
            except Exception as e:
                ui.notify(f"Lỗi khi cập nhật: {e}", type="negative")

        with ui.column().classes("w-full max-w-[1180px] mx-auto gap-5"):
            if search_query:
                with ui.element("div").classes(
                    "analysis-search-dropdown -mt-1 ml-1 w-[94%] max-w-[470px] max-h-72 overflow-y-auto "
                    "rounded-2xl border border-slate-100 bg-white/95 shadow-lg shadow-slate-200/60"
                ):
                    if not search_results:
                        render_text(
                            _('no_conv_found', state["lang"]),
                            "px-4 py-2 text-[13px] font-normal tracking-[0.015em] text-slate-500",
                        )

                    for result in search_results:
                        row = ui.row().classes(
                            "w-full cursor-pointer flex-nowrap items-center gap-2.5 border-b border-slate-100/70 "
                            "px-4 py-2 last:border-b-0 hover:bg-slate-50/90"
                        )
                        row.on("click", lambda r=result: open_analysis_result(r))
                        with row:
                            ui.icon("forum").classes("text-slate-400 text-[12px] shrink-0")
                            ui.label(
                                clean_display_text(result.get("meeting_title", ""))
                            ).classes(
                                "flex-1 min-w-0 truncate whitespace-nowrap overflow-hidden "
                                "text-[13px] font-normal leading-relaxed tracking-[0.015em] text-slate-600"
                            )

            with ui.row().classes("w-full items-start justify-between gap-4"):
                with ui.column().classes("gap-0.5"):
                    ui.label(_('conversation_analysis', state["lang"])).classes(
                        f"text-2xl {jp_weight(state['lang'], 'font-bold', 'font-semibold')} text-slate-900 leading-tight"
                    )
                    render_text(
                        subtitle,
                        f"text-sm {jp_weight(state['lang'], 'font-semibold', 'font-medium')} text-slate-500",
                    )

                with ui.row().classes("gap-2"):
                    action_button(
                        label="CẬP NHẬT",
                        icon="sync",
                        on_click=lambda: asyncio.create_task(handle_refresh()),
                    )
                    action_button(
                        label=_('export_pdf', state["lang"]),
                        icon="download",
                        variant="primary",
                        on_click=handle_export,
                    )

            with ui.row().classes("hidden"):
                search_box = (
                    ui.input(
                        placeholder=_('search_old_conv', state["lang"]),
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
                    label=_('search', state["lang"]),
                    icon="search",
                    variant="secondary",
                    on_click=lambda: asyncio.create_task(
                        handle_search(search_box.value or "")
                    ),
                )

            if state["loading"]:
                with ui.element("div").classes(
                    "analysis-card w-full px-6 py-10 text-center"
                ):
                    ui.spinner(size="lg")
                    ui.label(_('loading_data', state["lang"])).classes(
                        f"mt-3 text-sm {jp_weight(state['lang'], 'font-semibold', 'font-medium')} text-slate-500"
                    )
                return

            with ui.row().classes("w-full items-stretch gap-4"):
                for metric in metrics:
                    render_metric_card(metric, state["lang"])

            render_feedback_card(ai_overall_feedback, state["lang"])

            with ui.row().classes("w-full gap-6 items-start"):
                with ui.column().classes("flex-[1.08] gap-4 min-w-0"):
                    with ui.row().classes(
                        "items-center gap-3 border-b border-slate-200 pb-3"
                    ):
                        ui.icon("warning_amber").classes("text-orange-500 text-xl")
                        ui.label(_('perception_gaps_label', state["lang"])).classes(
                            f"text-lg {jp_weight(state['lang'], 'font-bold', 'font-semibold')} text-slate-800"
                        )

                    if not perception_gaps:
                        with ui.element("div").classes(
                            "analysis-card w-full px-5 py-4"
                        ):
                            render_text(
                                _('no_gaps', state["lang"]),
                                "text-sm text-slate-500",
                            )

                    for gap in perception_gaps:
                        render_gap_card(gap, state["lang"])

                with ui.column().classes("flex-[0.92] gap-4 min-w-0"):
                    with ui.row().classes(
                        "items-center gap-3 border-b border-slate-200 pb-3"
                    ):
                        ui.icon("article").classes("text-blue-500 text-xl")
                        ui.label(_('content_summary', state["lang"])).classes(
                            f"text-lg {jp_weight(state['lang'], 'font-bold', 'font-semibold')} text-slate-800"
                        )

                    render_summary_panel(
                        title=_('main_decisions', state["lang"]),
                        items=decisions,
                        icon="check_circle",
                        lang=state["lang"],
                    )

                    render_summary_panel(
                        title=_('action_items_label', state["lang"]),
                        items=action_items,
                        icon="task_alt",
                        lang=state["lang"],
                    )

    async def handle_language_change(new_lang: str) -> None:
        normalized = validate_language_or_default(new_lang)
        if normalized == state["lang"]:
            return

        state["lang"] = normalized
        state["data"] = empty_analysis_payload(normalized)
        page_shell.refresh()
        await load_data()
        if state.get("search_query"):
            await handle_search(state.get("search_query"))

    page_shell()

    ui.timer(0.2, load_data, once=True)


@ui.page("/analysis")
def analysis_page() -> None:
    render_analysis_page()


@ui.page("/analysis/{analysis_id}")
def analysis_detail_page(analysis_id: int) -> None:
    render_analysis_page(analysis_id)
