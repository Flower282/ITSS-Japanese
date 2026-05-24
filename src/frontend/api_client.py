"""HTTP client for calling backend APIs from NiceGUI pages."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from src.core.config import settings
from src.frontend import state

DEFAULT_TIMEOUT = 90.0


def api_base_url() -> str:
    return getattr(settings, "APP_BASE_URL", "http://127.0.0.1:8000")


def auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = state.get_token()
    if token:
        headers["Authorization"] = token
    return headers


async def api_get(path: str, *, timeout: float = DEFAULT_TIMEOUT) -> Any:
    async with httpx.AsyncClient(
        base_url=api_base_url(), timeout=timeout
    ) as client:
        response = await client.get(path, headers=auth_headers())

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_extract_error(response),
        )
    return response.json()


async def api_post_json(
    path: str, payload: dict[str, Any], *, timeout: float = DEFAULT_TIMEOUT
) -> Any:
    async with httpx.AsyncClient(
        base_url=api_base_url(), timeout=timeout
    ) as client:
        response = await client.post(
            path, json=payload, headers=auth_headers()
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_extract_error(response),
        )
    return response.json()


async def api_post_form(
    path: str, data: dict[str, str], files: dict[str, Any], *, timeout: float = 120.0
) -> Any:
    async with httpx.AsyncClient(
        base_url=api_base_url(), timeout=timeout
    ) as client:
        response = await client.post(
            path, data=data, files=files, headers=auth_headers()
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_extract_error(response),
        )
    return response.json()


async def api_put_json(
    path: str, payload: dict[str, Any], *, timeout: float = DEFAULT_TIMEOUT
) -> Any:
    async with httpx.AsyncClient(
        base_url=api_base_url(), timeout=timeout
    ) as client:
        response = await client.put(
            path, json=payload, headers=auth_headers()
        )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_extract_error(response),
        )
    return response.json()


async def api_delete(path: str, *, timeout: float = DEFAULT_TIMEOUT) -> Any:
    async with httpx.AsyncClient(
        base_url=api_base_url(), timeout=timeout
    ) as client:
        response = await client.delete(path, headers=auth_headers())

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=_extract_error(response),
        )
    return response.json()


def _extract_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, list):
                return "; ".join(str(item) for item in detail)
            if detail:
                return str(detail)
    except Exception:
        pass
    return response.text or f"HTTP {response.status_code}"
