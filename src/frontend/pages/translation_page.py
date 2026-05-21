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
from src.core.i18n import _, get_user_language, validate_language_or_default


@ui.page("/translate")
def translation_page() -> None:
    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

    messages: list[dict] = [
        {
            "id": 1,
            "role": "listen",
            "label": _('listen_label', lang),
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
            "label": _('you_label', lang),
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

    selected_tones: list[str] = [_('tone_polite', lang)]
    draft_input: ui.textarea | None = None

    def handle_new_conversation() -> None:
        if draft_input:
            draft_input.value = ""
        ui.notify(_('new_conv_created', lang), type="positive")

    def handle_save() -> None:
        ui.notify(_('save_conv', lang), type="positive")

    def handle_analyze() -> None:
        ui.notify(_('analyzing_content', lang), type="info")

    def handle_translate() -> None:
        if not draft_input or not draft_input.value:
            ui.notify(_('empty_input_warn', lang), type="warning")
            return
        messages.append(
            {
                "id": len(messages) + 1,
                "role": "you",
                "label": _('you_label', lang),
                "time": "10:32",
                "text": draft_input.value,
                "tags": [_('tone_polite', lang), ", ".join(selected_tones) or ""],
            }
        )
        render_history.refresh()
        ui.notify(_('added_to_history', lang), type="positive")

    def handle_select_reply(text: str) -> None:
        if draft_input:
            draft_input.value = text

    @ui.refreshable
    def render_history() -> None:
        conversation_history_view(
            title=_('conv_history_title', lang),
            messages=messages,
            max_height="560px",
        )

    with base_layout(
        active_nav="/translate",
        ui_state=layout_state,
        title_slot=lambda: page_title_block(
            title=_('new_conversation_title', lang),
            subtitle=_('online', lang),
            status=_('ai_supporting', lang),
        ),
        top_bar_actions=[
            {
                "label": _('analyze', lang),
                "icon": "analytics",
                "variant": "primary",
                "on_click": handle_analyze,
            },
            {
                "label": _('archive', lang),
                "icon": "archive",
                "variant": "secondary",
                "on_click": handle_save,
            },
        ],
        on_new_conversation=handle_new_conversation,
        on_history_select=lambda _h: ui.notify(_('loaded_history', lang)),
    ):
        with ui.row().classes("w-full items-start gap-6"):
            with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                render_history()

            with ui.column().classes("w-full max-w-[420px] flex-1 gap-4"):
                analysis_panel(
                    title=_('what_other_says', lang),
                    content=messages[0]["text"],
                    accent_classes="border-amber-200 bg-amber-50",
                    header_action=lambda: action_button(
                        label=_('ai_analyze_btn', lang),
                        icon="auto_awesome",
                        variant="secondary",
                        on_click=handle_analyze,
                    ),
                )
                analysis_panel(
                    title=_('translation_vn', lang),
                    content=(
                        "Ah, ve deadline, co le toi can them mot chut thoi gian..."
                    ),
                    accent_classes="border-sky-200 bg-sky-50",
                )
                analysis_panel(
                    title=_('real_meaning', lang),
                    content=(
                        "Đối tác đang gặp khó khăn và muốn xin gia hạn deadline, "
                        "nhưng ngại nói trực tiếp. Cách nói thể hiện sự ngập ngừng "
                        "và do dự."
                    ),
                    tags=["Gián tiếp", "Khó nói", "Ngại ngùng"],
                    accent_classes="border-violet-200 bg-violet-50",
                )
                analysis_panel(
                    title=_('suggested_replies_title', lang),
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
                    title=_('what_you_want_say', lang),
                    placeholder=_('input_placeholder', lang),
                    value="Ah, về deadline, có lẽ tôi cần thêm một chút thời gian...",
                )

                with ui.element("div").classes(
                    "w-full rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
                ):
                    ui.label(_('optimize_tone', lang)).classes(
                        "text-sm font-semibold text-slate-700 mb-3"
                    )
                    recommendation_chips(
                        options=[
                            _('tone_polite', lang),
                            _('tone_shorter', lang),
                            _('tone_soft', lang),
                        ],
                        selected=selected_tones,
                        on_change=lambda value: selected_tones.clear()
                        or selected_tones.extend(value),
                    )
                    with ui.row().classes("items-center justify-between mt-4"):
                        with ui.row().classes(
                            "items-center gap-2 text-xs text-slate-500"
                        ):
                            ui.icon("mic").classes("text-sm")
                            ui.label(_('voice', lang))
                        action_button(
                            label=_('translate_optimize', lang),
                            icon="translate",
                            variant="primary",
                            on_click=handle_translate,
                        )
