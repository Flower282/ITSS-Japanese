"""Language switcher navbar component."""

from nicegui import ui
from typing import Callable
from src.core.i18n import _, get_language_options


def create_language_navbar(
    current_lang: str,
    on_language_change: Callable[[str], None]
) -> None:
    """
    Create a navbar with language switcher.
    
    Args:
        current_lang: Current language code ('vn' or 'jp')
        on_language_change: Callback when language is selected
    """
    with ui.row().props('class="w-full q-pa-md q-mb-lg" style="background-color: #f5f5f5; border-radius: 8px;"'):
        # Logo/Brand
        ui.label('MyApp').props('class="text-h5 text-weight-bold"')
        ui.space()
        
        # Language switcher
        with ui.row().props('class="items-center q-gutter-md"'):
            ui.label(_('language_label', current_lang)).props('class="text-body2"')
            
            ui.select(
                value=current_lang,
                options=get_language_options(current_lang),
                on_change=lambda value: on_language_change(value)
            ).props('outlined dense')
