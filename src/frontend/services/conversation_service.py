"""Shared helpers for conversation and analysis API calls."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from src.frontend.api_client import api_get, api_patch_json, api_post_json


async def load_conversation_history(limit: int = 30) -> list[dict[str, Any]]:
    data = await api_get(f"/api/analysis/conversations?limit={limit}")
    if not isinstance(data, list):
        return []
    return [
        {
            "id": item["id"],
            "label": item.get("label", ""),
            "subtitle": item.get("subtitle", ""),
        }
        for item in data
        if isinstance(item, dict) and item.get("id") is not None
    ]


async def load_translate_context(
    conversation_id: int, lang: str = "vn"
) -> dict[str, Any]:
    query = urlencode({"lang": lang})
    return await api_get(
        f"/api/analysis/{conversation_id}/translate-context?{query}"
    )


async def load_dashboard_overview(lang: str = "vn") -> dict[str, Any]:
    query = urlencode({"lang": lang})
    return await api_get(f"/api/analysis/overview?{query}")


async def rename_conversation(conversation_id: int, name: str) -> dict[str, Any]:
    return await api_patch_json(
        f"/api/analysis/conversations/{conversation_id}",
        {"name": name.strip()},
    )


async def create_conversation(name: str = "Hội thoại mới") -> dict[str, Any]:
    import httpx

    from src.frontend.api_client import api_base_url, auth_headers

    query = urlencode({"name": name})
    async with httpx.AsyncClient(base_url=api_base_url(), timeout=60.0) as client:
        response = await client.post(
            f"/api/analysis/conversations?{query}",
            headers=auth_headers(),
        )
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    return response.json()


async def add_message(
    conversation_id: int,
    text: str,
    role: str = "you",
    *,
    translation: str | None = None,
    note: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"text": text, "role": role}
    if translation:
        payload["translation"] = translation
    if note:
        payload["note"] = note
    if tags:
        payload["tags"] = tags
    return await api_post_json(
        f"/api/analysis/{conversation_id}/messages",
        payload,
    )


async def run_analysis(conversation_id: int) -> dict[str, Any]:
    import httpx

    from src.frontend.api_client import api_base_url, auth_headers

    async with httpx.AsyncClient(base_url=api_base_url(), timeout=120.0) as client:
        response = await client.post(
            f"/api/analysis/{conversation_id}/run?replace_existing=true",
            headers=auth_headers(),
        )
    if response.status_code >= 400:
        raise RuntimeError(response.text)
    return response.json()


async def translate_text(
    text: str, context: str = "", direction: str = "ja-to-vi"
) -> dict[str, Any]:
    return await api_post_json(
        "/api/v1/translate",
        {"text": text, "context": context, "direction": direction},
    )


async def search_conversations(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    query = urlencode({"q": keyword, "limit": limit})
    data = await api_get(f"/api/analysis/search?{query}")
    return data if isinstance(data, list) else []


def build_tone_context(conversation_name: str, tones: list[str]) -> str:
    tone_part = ", ".join(tones) if tones else ""
    if tone_part:
        return f"{conversation_name}. Giọng điệu mong muốn: {tone_part}"
    return conversation_name
