from __future__ import annotations

import base64
from typing import Any

import asyncio

from nicegui import context, ui

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
    mark_message,
    rename_conversation,
    run_analysis,
    search_conversations,
    translate_text,
)
from src.frontend.services.voice_recorder import VOICE_RECORDER_JS
from src.frontend.ui_state import UiState


def _message_from_api(m: dict[str, Any], lang: str) -> dict[str, Any]:
    role = m.get("role", "you")
    return {
        "id": m.get("id"),
        "role": role,
        "label": _("you_label", lang) if role == "you" else _("listen_label", lang),
        "time": m.get("time", ""),
        "text": m.get("text", ""),
        "translation": m.get("translation"),
        "note": m.get("note"),
        "tags": m.get("tags") or [],
        "is_marked": int(m.get("is_marked") or 0),
    }


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
        "you_recording": False,
    }

  # UI refs (giữ nguyên khi cập nhật dữ liệu — không rebuild cả trang)
    refs: dict[str, Any] = {}
    client = context.client

    def toast(message: str, *, type: str = "info") -> None:
        with client:
            ui.notify(message, type=type)

    def tone_context() -> str:
        return build_tone_context(
            state["context"].get("conversation_name", ""),
            state["selected_tones"],
        )

    def set_loading(visible: bool, hide_content: bool = True) -> None:
        with client:
            if refs.get("loading_box"):
                refs["loading_box"].set_visibility(visible if hide_content else False)
            if refs.get("main_content"):
                if hide_content:
                    refs["main_content"].set_visibility(not visible)
                    refs["main_content"].style("opacity: 1.0; pointer-events: auto;")
                else:
                    refs["main_content"].set_visibility(True)
                    if visible:
                        refs["main_content"].style("opacity: 0.5; pointer-events: none;")
                    else:
                        refs["main_content"].style("opacity: 1.0; pointer-events: auto;")

    def update_panel_labels() -> None:
        panels = state.get("panels", {})
        with client:
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
        with client:
            container.clear()
        replies = state.get("panels", {}).get("replies") or []
        with client, container:
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

    async def handle_mark_message(message_id: int) -> None:
        try:
            result = await mark_message(message_id)
            marked_id = int(result.get("id", message_id))
            for item in state["messages"]:
                if item.get("id") == marked_id:
                    item["is_marked"] = int(result.get("is_marked", 1))
                    break
            render_history()
            toast("Đã đánh dấu tin nhắn", type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")

    def render_history() -> None:
        container = refs.get("history_container")
        if not container:
            return
        with client:
            container.clear()
        with client, container:
            conversation_history_view(
                title=_("conv_history_title", lang),
                messages=state["messages"],
                max_height="560px",
                on_mark=handle_mark_message,
                lang=lang,
            )

    async def ensure_conversation_id() -> int | None:
        if state["conversation_id"]:
            return int(state["conversation_id"])
        created = await create_conversation(_("new_conversation_title", lang))
        state["conversation_id"] = created["id"]
        state["context"]["conversation_name"] = created.get(
            "label", _("new_conversation_title", lang)
        )
        set_title_value(state["context"]["conversation_name"])
        return state["conversation_id"]

    async def reload_context() -> None:
        conv_id = state.get("conversation_id")
        if not conv_id:
            state["context"] = _empty_context(lang)
            state["messages"] = []
            sync_panels_from_context()
            render_history()
            refresh_sidebar()
            return
        ctx = await load_translate_context(int(conv_id), lang)
        state["context"] = ctx
        state["messages"] = [
            _message_from_api(m, lang) for m in ctx.get("messages", [])
        ]
        layout_state.selected_history_id = conv_id
        set_title_value(ctx.get("conversation_name", ""))
        sync_panels_from_context()
        render_history()
        refresh_sidebar()

    def refresh_sidebar() -> None:
        with client:
            if layout_state.refresh_sidebar_history:
                layout_state.refresh_sidebar_history()

    async def sync_history_from_db() -> list[dict[str, Any]]:
        loaded = await load_conversation_history()
        state["history_items"].clear()
        state["history_items"].extend(loaded)
        layout_state.history_items.clear()
        layout_state.history_items.extend(loaded)
        refresh_sidebar()
        return loaded

    def set_title_value(name: str) -> None:
        state["context"]["conversation_name"] = name
        with client:
            if refs.get("title_input"):
                refs["title_input"].value = name

    def update_history_item_label(conv_id: int, label: str) -> None:
        for items in (state["history_items"], layout_state.history_items):
            for item in items:
                if item.get("id") == conv_id:
                    item["label"] = label
        refresh_sidebar()

    async def handle_rename_conversation() -> None:
        conv_id = state.get("conversation_id")
        title_input = refs.get("title_input")
        if not conv_id or not title_input:
            return
        new_name = (title_input.value or "").strip()
        if not new_name:
            toast(_("empty_input_warn", lang), type="warning")
            set_title_value(state["context"].get("conversation_name", ""))
            return
        if new_name == state["context"].get("conversation_name"):
            return
        try:
            updated = await rename_conversation(int(conv_id), new_name)
            label = updated.get("label", new_name)
            set_title_value(label)
            update_history_item_label(int(conv_id), label)
            toast("Đã đổi tên hội thoại", type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")
            set_title_value(state["context"].get("conversation_name", ""))

    async def handle_refresh_history() -> None:
        try:
            await sync_history_from_db()
            toast("Đã cập nhật danh sách hội thoại", type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")

    async def load_page() -> None:
        set_loading(True)
        try:
            await sync_history_from_db()
            if state["conversation_id"]:
                layout_state.selected_history_id = int(state["conversation_id"])
            elif state["history_items"]:
                state["conversation_id"] = state["history_items"][0]["id"]
                layout_state.selected_history_id = state["conversation_id"]
            await reload_context()
        except Exception as exc:
            toast(f"Lỗi tải dữ liệu: {exc}", type="negative")
        set_loading(False)

    async def handle_new_conversation() -> None:
        try:
            created = await create_conversation(_("new_conversation_title", lang))
            conv_id = int(created["id"])
            state["conversation_id"] = conv_id
            state["context"] = _empty_context(lang)
            state["context"]["conversation_name"] = created.get("label", "")
            state["messages"] = []
            state["panels"] = {
                "partner": "",
                "translation": "",
                "meaning": "",
                "replies": [],
            }
            layout_state.selected_history_id = conv_id
            await sync_history_from_db()
            set_title_value(state["context"]["conversation_name"])
            with client:
                inp = refs.get("draft_input")
                if inp:
                    inp.value = ""
            sync_panels_from_context()
            render_history()
            render_replies()
            toast(_("new_conv_created", lang), type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")

    async def handle_save() -> None:
        if not state["messages"]:
            toast(_("empty_input_warn", lang), type="warning")
            return
        try:
            conv_id = await ensure_conversation_id()
            if conv_id is not None:
                layout_state.selected_history_id = conv_id
            await sync_history_from_db()
            toast(_("save_conv", lang), type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")

    async def handle_partner_analyze() -> None:
        if not state["panels"].get("partner", "").strip():
            toast(_("empty_input_warn", lang), type="warning")
            return
        try:
            conv_id = await ensure_conversation_id()
            toast(_("analyzing_content", lang), type="info")
            await run_analysis(conv_id)
            await reload_context()
            toast("Phân tích AI hoàn tất", type="positive")
        except Exception as exc:
            toast(str(exc), type="negative")

    async def handle_full_analyze() -> None:
        try:
            conv_id = await ensure_conversation_id()
            toast(_("analyzing_content", lang), type="info")
            await run_analysis(conv_id)
            with client:
                ui.navigate.to(nav(f"/analysis/{conv_id}", lang))
        except Exception as exc:
            toast(str(exc), type="negative")

    async def append_message(
        text: str,
        role: str = "you",
        *,
        translation: str | None = None,
        note: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        conv_id = await ensure_conversation_id()
        saved = await add_message(
            conv_id,
            text,
            role=role,
            translation=translation,
            note=note,
            tags=tags,
        )
        state["messages"].append(_message_from_api(saved, lang))
        render_history()

    async def handle_translate() -> None:
        inp = refs.get("draft_input")
        if not inp or not (inp.value or "").strip():
            toast(_("empty_input_warn", lang), type="warning")
            return
        vietnamese = inp.value.strip()
        tones = list(state["selected_tones"])
        try:
            toast("Đang dịch...", type="info")
            result = await translate_text(
                vietnamese,
                context=tone_context(),
                direction="vi-to-ja",
            )
            japanese = (result.get("translation") or "").strip()
            if not japanese:
                toast(_("failed_analysis_load", lang), type="warning")
                return
            tone_note = (
                f"{_('optimize_tone', lang)}: {', '.join(tones)}"
                if tones
                else None
            )
            await append_message(
                japanese,
                role="you",
                translation=vietnamese,
                note=tone_note,
                tags=tones,
            )
            # Reload from API so "meaning/nuance" panel always follows backend output.
            await reload_context()
            state["panels"]["partner"] = japanese
            state["panels"]["translation"] = vietnamese
            update_panel_labels()
            with client:
                inp.value = ""
            warning = result.get("warning")
            if warning:
                toast(str(warning), type="warning")
            toast(_("added_to_history", lang), type="positive")
        except Exception as exc:
            toast(f"Dịch thất bại: {exc}", type="negative")

    async def handle_you_voice() -> None:
        if state["lang"] != "jp":
            return

        if state["you_recording"]:
            state["you_recording"] = False
            result = await ui.run_javascript(
                "return await stopRecordingToBase64()",
                timeout=120.0,
            )
            if not result or not result.get("ok"):
                toast((result or {}).get("error", "Ghi âm thất bại"), type="negative")
                return

            try:
                toast("Đang xử lý giọng nói tiếng Nhật...", type="info")
                audio_bytes = base64.b64decode(result["base64"])
                data = await api_post_form(
                    "/api/v1/translate/audio",
                    {"context": tone_context(), "direction": "ja-to-vi"},
                    {
                        "audio": (
                            result.get("filename", "record.webm"),
                            audio_bytes,
                            result.get("mimeType", "audio/webm"),
                        )
                    },
                )
                japanese_raw = (data.get("transcript") or "").strip()
                if not japanese_raw:
                    toast("Không nhận diện được tiếng Nhật từ audio", type="warning")
                    return

                simplified = await translate_text(
                    japanese_raw,
                    context=tone_context(),
                    direction="ja-to-ja-simple",
                )
                japanese_n45 = (simplified.get("translation") or "").strip() or japanese_raw
                with client:
                    inp = refs.get("draft_input")
                    if inp:
                        inp.value = japanese_n45
                warning = simplified.get("warning")
                if warning:
                    toast(str(warning), type="warning")
                toast("Đã đưa câu tiếng Nhật N4/N5 vào ô nhập", type="positive")
            except Exception as exc:
                toast(f"Ghi âm tiếng Nhật thất bại: {exc}", type="negative")
        else:
            init = await ui.run_javascript("return await startRecording()")
            if not init or not init.get("ok"):
                toast((init or {}).get("error", "Không thể truy cập micro"), type="negative")
                return
            state["you_recording"] = True
            toast("Đang ghi âm tiếng Nhật cho phần Bạn muốn nói gì...", type="info")

    async def handle_partner_voice() -> None:
        if state["partner_recording"]:
            state["partner_recording"] = False
            with client:
                if refs.get("voice_status"):
                    refs["voice_status"].set_text(_("voice", lang))
            result = await ui.run_javascript(
                "return await stopRecordingToBase64()", timeout=120.0
            )
            if not result or not result.get("ok"):
                toast(
                    (result or {}).get("error", "Ghi âm thất bại"),
                    type="negative",
                )
                return
            try:
                toast("Đang xử lý âm thanh...", type="info")
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
                    await append_message(
                        transcript,
                        role="listen",
                        translation=translation or None,
                    )
                toast(_("added_to_history", lang), type="positive")
            except Exception as exc:
                toast(f"API dịch âm thanh: {exc}", type="negative")
        else:
            init = await ui.run_javascript("return await startRecording()")
            if not init or not init.get("ok"):
                toast(
                    (init or {}).get("error", "Không thể truy cập micro"),
                    type="negative",
                )
                return
            state["partner_recording"] = True
            with client:
                if refs.get("voice_status"):
                    refs["voice_status"].set_text("Đang ghi âm...")

    async def handle_history_select(selected_id: str | int) -> None:
        state["conversation_id"] = int(selected_id)
        layout_state.selected_history_id = int(selected_id)
        set_loading(True, hide_content=False)
        try:
            await reload_context()
        except Exception as exc:
            toast(str(exc), type="negative")
        set_loading(False, hide_content=False)

    async def handle_search(keyword: str) -> None:
        keyword = (keyword or "").strip()
        if not keyword:
            return
        if keyword not in state["search_history"]:
            state["search_history"] = [keyword, *state["search_history"][:9]]
        try:
            results = await search_conversations(keyword)
            if not results:
                toast(_("no_conv_found", lang), type="warning")
                return
            await handle_history_select(results[0]["id"])
        except Exception as exc:
            toast(str(exc), type="negative")

    async def handle_language_change(new_lang: str) -> None:
        target_lang = validate_language_or_default(new_lang)
        conv_id = state.get("conversation_id")
        target_path = f"/translate/{conv_id}" if conv_id else "/translate"
        with client:
            ui.navigate.to(nav(target_path, target_lang))

    def title_slot() -> None:
        with ui.row().classes("items-center gap-2 w-full"):
            refs["title_input"] = (
                ui.input(
                    value=state["context"].get(
                        "conversation_name", _("new_conversation_title", lang)
                    ),
                    placeholder=_("new_conversation_title", lang),
                )
                .props("dense borderless")
                .classes(
                    "text-lg font-semibold text-slate-800 flex-grow min-w-0"
                )
            )
            ui.icon("edit").classes("text-slate-400 text-base shrink-0")
        refs["title_input"].on("keydown.enter", handle_rename_conversation)
        refs["title_input"].on("blur", handle_rename_conversation)
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
        on_locale_change=lambda value: asyncio.create_task(handle_language_change(value)),
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
        on_history_refresh=handle_refresh_history,
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
                        if lang == "jp":
                            with ui.row().classes("w-full justify-end"):
                                ui.button(icon="mic").props("flat round").on(
                                    "click",
                                    handle_you_voice,
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
