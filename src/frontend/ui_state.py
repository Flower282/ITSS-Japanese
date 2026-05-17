from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UiState:
    """Shared UI state for layout-level interactions."""

    search_query: str = ""
    selected_history_id: str | int | None = None
    locale_code: str = "vn"
