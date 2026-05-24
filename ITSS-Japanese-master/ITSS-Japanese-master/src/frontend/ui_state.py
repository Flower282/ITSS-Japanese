from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class UiState:
    """Shared UI state for layout-level interactions."""

    search_query: str = ""
    selected_history_id: str | int | None = None
    locale_code: str = "vn"
    history_items: list[dict[str, Any]] = field(default_factory=list)
    refresh_sidebar_history: Callable[[], None] | None = None
