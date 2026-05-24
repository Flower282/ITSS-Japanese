from __future__ import annotations

import base64
from typing import Any

from nicegui import ui

from src.core.i18n import _, get_user_language, nav, validate_language_or_default
from src.frontend.api_client import api_post_form
from src.frontend.components.components import (
    action_button,
    conversation_history_view,
    input_composer,
    page_title_block,
    recommendation_chips,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.services.conversation_service import (
    add_message,
    build_tone_context,
    create_conversation,
    load_conversation_history,
    load_translate_context,
    run_analysis,
    search_conversations,
    translate_text,
)
from src.frontend.services.voice_recorder import VOICE_RECORDER_JS
from src.frontend.ui_state import UiState


def _empty_context(lang: str) -> dict[str, Any]:
    return {
        "conversation_name": _("new_conversation_title", lang),
        "messages": [],
        "reply_suggestions": [],
        "partner_text": "",
        "translation_text": "",
        "nuance_analysis": "",
        "intent_analysis": "",
        "culture_explanation": "",
    }


@ui.page("/translate")
@ui.page("/translate/{conversation_id}")
def translation_page(conversation_id: int | None = None) -> None:
    layout_state = UiState()
    lang = validate_language_or_default(get_user_language())

    state: dict[str, Any] = {
        "lang": lang,
        "conversation_id": conversation_id,
        "context": _empty_context(lang),
        "history_items": [],
        "search_history": [],
        "messages": [],
        "selected_tones": [_("tone_polite", lang)],
        "partner_recording": False,
    }

  # UI refs (giữ nguyên khi cập nhật dữ liệu — không rebuild cả trang)
    refs: dict[str, Any] = {}

    def tone_context() -> str:
        return build_tone_context(
            state["context"].get("conversation_name", ""),
            state["selected_tones"],
        )

    def set_loading(visible: bool) -> None:
        if refs.get("loading_box"):
            refs["loading_box"].set_visibility(visible)
        if refs.get("main_content"):
            refs["main_content"].set_visibility(not visible)

    def update_panel_labels() -> None:
        panels = state.get("panels", {})
        if refs.get("lbl_partner"):
            refs["lbl_partner"].set_text(panels.get("partner") or _("no_data", lang))
        if refs.get("lbl_translation"):
            refs["lbl_translation"].set_text(
                panels.get("translation") or _("no_data", lang)
            )
        if refs.get("lbl_meaning"):
            refs["lbl_meaning"].set_text(panels.get("meaning") or _("no_data", lang))

    def sync_panels_from_context() -> None:
        ctx = state["context"]
        state["panels"] = {
            "partner": ctx.get("partner_text") or "",
            "translation": ctx.get("translation_text") or "",
            "meaning": (
                ctx.get("nuance_analysis")
                or ctx.get("intent_analysis")
                or ctx.get("culture_explanation")
                or ""
            ),
            "replies": ctx.get("reply_suggestions") or [],
        }
        update_panel_labels()
        render_replies()

    def render_replies() -> None:
        container = refs.get("replies_container")
        if not container:
            return
        container.clear()
        replies = state.get("panels", {}).get("replies") or []
        with container:
            ui.label(_("suggested_replies_title", lang)).classes(
                "text-sm font-semibold text-slate-700 mb-2"
            )
            if not replies:
                ui.label(_("no_data", lang)).classes("text-xs text-slate-500")
            for reply in replies:
                title = reply.get("title", "")
                desc = reply.get("description", "")
                btn = ui.button(title).props("outline").classes(
                    "w-full text-left rounded-xl mb-2"
                )

                async def pick(r: dict = reply) -> None:
                    inp = refs.get("draft_input")
                    if inp:
                        inp.value = r.get("description") or r.get("title") or ""

                btn.on("click", pick)
                if desc and desc != title:
                    ui.label(desc).classes("text-xs text-slate-500 -mt-1 mb-2")

    def render_history() -> None:
        container = refs.get("history_container")
        if not container:
            return
        container.clear()
        with container:
            conversation_history_view(
                title=_("conv_history_title", lang),
                messages=state["messages"],
                max_height="560px",
            )

    async def ensure_conversation_id() -> int | None:
        if state["conversation_id"]:
            return int(state["conversation_id"])
        created = await create_conversation(_("new_conversation_title", lang))
        state["conversation_id"] = created["id"]
        state["context"]["conversation_name"] = created.get(
            "label", _("new_conversation_title", lang)
        )
        if refs.get("title_name"):
            refs["title_name"].set_text(state["context"]["conversation_name"])
        return state["conversation_id"]

    async def reload_context() -> None:
        conv_id = state.get("conversation_id")
        if not conv_id:
            state["context"] = _empty_context(lang)
            state["messages"] = []
            sync_panels_from_context()
            render_history()
            return
        ctx = await load_translate_context(int(conv_id), lang)
        state["context"] = ctx
        state["messages"] = [
            {
                "id": m["id"],
                "role": m["role"],
                "label": _("you_label", lang)
                if m["role"] == "you"
                else _("listen_label", lang),
                "time": m.get("time", ""),
                "text": m["text"],
                "tags": list(state["selected_tones"]) if m["role"] == "you" else [],
            }
            for m in ctx.get("messages", [])
        ]
        layout_state.selected_history_id = conv_id
        if refs.get("title_name"):
            refs["title_name"].set_text(ctx.get("conversation_name", ""))
        sync_panels_from_context()
        render_history()

    def refresh_sidebar() -> None:
        if layout_state.refresh_sidebar_history:
            layout_state.refresh_sidebar_history()

    async def load_page() -> None:
        set_loading(True)
        try:
            loaded = await load_conversation_history()
            state["history_items"].clear()
            state["history_items"].extend(loaded)
            refresh_sidebar()
            if not state["conversation_id"] and state["history_items"]:
                state["conversation_id"] = state["history_items"][0]["id"]
            await reload_context()
        except Exception as exc:
            ui.notify(f"Lỗi tải dữ liệu: {exc}", type="negative")
        set_loading(False)

    async def handle_new_conversation() -> None:
        try:
            created = await create_conversation(_("new_conversation_title", lang))
            state["conversation_id"] = created["id"]
            state["context"] = _empty_context(lang)
            state["context"]["conversation_name"] = created.get("label", "")
            state["messages"] = []
            state["panels"] = {
                "partner": "",
                "translation": "",
                "meaning": "",
                "replies": [],
            }
            layout_state.selected_history_id = created["id"]
            loaded = await load_conversation_history()
            state["history_items"].clear()
            state["history_items"].extend(loaded)
            refresh_sidebar()
            inp = refs.get("draft_input")
            if inp:
                inp.value = ""
            sync_panels_from_context()
            render_history()
            render_replies()
            ui.notify(_("new_conv_created", lang), type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def handle_save() -> None:
        if not state["messages"]:
            ui.notify(_("empty_input_warn", lang), type="warning")
            return
        try:
            await ensure_conversation_id()
            loaded = await load_conversation_history()
            state["history_items"].clear()
            state["history_items"].extend(loaded)
            refresh_sidebar()
            layout_state.selected_history_id = state["conversation_id"]
            ui.notify(_("save_conv", lang), type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def handle_partner_analyze() -> None:
        if not state["panels"].get("partner", "").strip():
            ui.notify(_("empty_input_warn", lang), type="warning")
            return
        try:
            conv_id = await ensure_conversation_id()
            ui.notify(_("analyzing_content", lang), type="info")
            await run_analysis(conv_id)
            await reload_context()
            ui.notify("Phân tích AI hoàn tất", type="positive")
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def handle_full_analyze() -> None:
        try:
            conv_id = await ensure_conversation_id()
            ui.notify(_("analyzing_content", lang), type="info")
            await run_analysis(conv_id)
            ui.navigate.to(nav(f"/analysis/{conv_id}", lang))
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def append_message(text: str, role: str = "you") -> None:
        conv_id = await ensure_conversation_id()
        saved = await add_message(conv_id, text, role=role)
        state["messages"].append(
            {
                "id": saved["id"],
                "role": role,
                "label": _("you_label", lang)
                if role == "you"
                else _("listen_label", lang),
                "time": saved.get("time", ""),
                "text": text,
                "tags": list(state["selected_tones"]) if role == "you" else [],
            }
        )
        render_history()

    async def handle_translate() -> None:
        inp = refs.get("draft_input")
        if not inp or not (inp.value or "").strip():
            ui.notify(_("empty_input_warn", lang), type="warning")
            return
        text = inp.value.strip()
        try:
            ui.notify("Đang dịch...", type="info")
            result = await translate_text(
                text,
                context=tone_context(),
                direction="vi-to-ja",
            )
            japanese = (result.get("translation") or "").strip()
            if not japanese:
                ui.notify(_("failed_analysis_load", lang), type="warning")
                return
            await append_message(japanese, role="you")
            inp.value = ""
            ui.notify(_("added_to_history", lang), type="positive")
        except Exception as exc:
            ui.notify(f"Dịch thất bại: {exc}", type="negative")

    async def handle_partner_voice() -> None:
        if state["partner_recording"]:
            state["partner_recording"] = False
            if refs.get("voice_status"):
                refs["voice_status"].set_text(_("voice", lang))
            result = await ui.run_javascript(
                "return await stopRecordingToBase64()", timeout=120.0
            )
            if not result or not result.get("ok"):
                ui.notify(
                    (result or {}).get("error", "Ghi âm thất bại"),
                    type="negative",
                )
                return
            try:
                ui.notify("Đang xử lý âm thanh...", type="info")
                audio_bytes = base64.b64decode(result["base64"])
                data = await api_post_form(
                    "/api/v1/translate/audio",
                    {"context": tone_context()},
                    {
                        "audio": (
                            result.get("filename", "record.webm"),
                            audio_bytes,
                            result.get("mimeType", "audio/webm"),
                        )
                    },
                )
                transcript = (data.get("transcript") or "").strip()
                translation = (data.get("translation") or "").strip()
                state["panels"]["partner"] = transcript
                state["panels"]["translation"] = translation
                state["panels"]["meaning"] = ""
                state["context"]["partner_text"] = transcript
                state["context"]["translation_text"] = translation
                update_panel_labels()
                if transcript:
                    await append_message(transcript, role="listen")
                ui.notify(_("added_to_history", lang), type="positive")
            except Exception as exc:
                ui.notify(f"API dịch âm thanh: {exc}", type="negative")
        else:
            init = await ui.run_javascript("return await startRecording()")
            if not init or not init.get("ok"):
                ui.notify(
                    (init or {}).get("error", "Không thể truy cập micro"),
                    type="negative",
                )
                return
            state["partner_recording"] = True
            if refs.get("voice_status"):
                refs["voice_status"].set_text("Đang ghi âm...")

    async def handle_history_select(selected_id: str | int) -> None:
        state["conversation_id"] = int(selected_id)
        layout_state.selected_history_id = int(selected_id)
        set_loading(True)
        try:
            await reload_context()
        except Exception as exc:
            ui.notify(str(exc), type="negative")
        set_loading(False)

    async def handle_search(keyword: str) -> None:
        keyword = (keyword or "").strip()
        if not keyword:
            return
        if keyword not in state["search_history"]:
            state["search_history"] = [keyword, *state["search_history"][:9]]
        try:
            results = await search_conversations(keyword)
            if not results:
                ui.notify(_("no_conv_found", lang), type="warning")
                return
            await handle_history_select(results[0]["id"])
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    async def handle_language_change(new_lang: str) -> None:
        state["lang"] = validate_language_or_default(new_lang)
        state["selected_tones"] = [_("tone_polite", state["lang"])]
        try:
            await reload_context()
        except Exception as exc:
            ui.notify(str(exc), type="negative")

    def title_slot() -> None:
        refs["title_name"] = ui.label(
            state["context"].get("conversation_name", _("new_conversation_title", lang))
        ).classes("text-lg font-semibold text-slate-800")
        ui.label(_("online", lang)).classes("text-sm text-slate-500")
        ui.label(_("ai_supporting", lang)).classes(
            "text-xs text-emerald-600 font-medium"
        )

    ui.run_javascript(VOICE_RECORDER_JS)

    with base_layout(
        active_nav="/translate",
        ui_state=layout_state,
        title_slot=title_slot,
        search_history=state["search_history"],
        on_search=handle_search,
        on_locale_change=handle_language_change,
        on_logo_click=lambda: ui.navigate.to(nav("/", lang)),
        top_bar_actions=[
            {
                "label": _("analyze", lang),
                "icon": "analytics",
                "variant": "primary",
                "on_click": handle_full_analyze,
            },
            {
                "label": _("archive", lang),
                "icon": "archive",
                "variant": "secondary",
                "on_click": handle_save,
            },
        ],
        on_new_conversation=handle_new_conversation,
        on_history_select=handle_history_select,
        history_items=state["history_items"],
    ):
        with ui.column().classes("w-full gap-4"):
            refs["loading_box"] = ui.row().classes("w-full justify-center py-20")
            with refs["loading_box"]:
                ui.spinner(size="lg")

            refs["main_content"] = ui.column().classes("w-full gap-6")
            refs["main_content"].set_visibility(False)

            with refs["main_content"]:
                with ui.row().classes("w-full items-start gap-6"):
                    refs["history_container"] = ui.column().classes(
                        "w-full max-w-[420px] flex-1"
                    )

                    with ui.column().classes("w-full max-w-[420px] flex-1 gap-3"):
                        with ui.row().classes("w-full justify-end items-center gap-2"):
                            refs["voice_status"] = ui.label(_("voice", lang)).classes(
                                "text-xs text-slate-500"
                            )
                            ui.button(icon="mic").props("flat round").on(
                                "click", handle_partner_voice
                            )
                            action_button(
                                label=_("ai_analyze_btn", lang),
                                icon="auto_awesome",
                                variant="secondary",
                                on_click=handle_partner_analyze,
                            )

                        def panel_card(title: str, key: str) -> None:
                            with ui.element("div").classes(
                                "w-full rounded-2xl border border-slate-100 "
                                "bg-white p-4 shadow-sm"
                            ):
                                ui.label(title).classes(
                                    "text-sm font-semibold text-slate-700 mb-2"
                                )
                                refs[key] = ui.label(_("no_data", lang)).classes(
                                    "text-sm text-slate-600 whitespace-pre-wrap"
                                )

                        panel_card(_("what_other_says", lang), "lbl_partner")
                        panel_card(_("translation_vn", lang), "lbl_translation")
                        panel_card(_("real_meaning", lang), "lbl_meaning")

                        refs["replies_container"] = ui.column().classes("w-full")

                    with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                        refs["draft_input"] = input_composer(
                            title=_("what_you_want_say", lang),
                            placeholder=_("input_placeholder", lang),
                            value="",
                        )
                        with ui.element("div").classes(
                            "w-full rounded-2xl border border-slate-100 bg-white p-4"
                        ):
                            ui.label(_("optimize_tone", lang)).classes(
                                "text-sm font-semibold text-slate-700 mb-3"
                            )
                            recommendation_chips(
                                options=[
                                    _("tone_polite", lang),
                                    _("tone_shorter", lang),
                                    _("tone_soft", lang),
                                ],
                                selected=state["selected_tones"],
                                on_change=lambda v: (
                                    state["selected_tones"].clear(),
                                    state["selected_tones"].extend(v),
                                ),
                            )
                            with ui.row().classes("justify-end mt-4 w-full"):
                                action_button(
                                    label=_("translate_optimize", lang),
                                    icon="translate",
                                    variant="primary",
                                    on_click=handle_translate,
                                )

    ui.timer(0.15, load_page, once=True)
