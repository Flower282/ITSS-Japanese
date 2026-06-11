import json
import os
import threading
from pathlib import Path
from typing import Any

CACHE_FILE = Path(__file__).parent / "cache_conversations.json"
_lock = threading.Lock()


def _load_cache() -> dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict[str, Any]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")


def get_cached_conversations_list() -> list[dict[str, Any]] | None:
    with _lock:
        cache = _load_cache()
        return cache.get("conversations_list")


def set_cached_conversations_list(conversations: list[dict[str, Any]]) -> None:
    with _lock:
        cache = _load_cache()
        cache["conversations_list"] = conversations
        _save_cache(cache)


def get_cached_translate_context(conversation_id: int, lang: str) -> dict[str, Any] | None:
    with _lock:
        cache = _load_cache()
        contexts = cache.get("translate_contexts", {})
        key = f"{conversation_id}_{lang}"
        return contexts.get(key)


def set_cached_translate_context(conversation_id: int, lang: str, data: dict[str, Any]) -> None:
    with _lock:
        cache = _load_cache()
        if "translate_contexts" not in cache:
            cache["translate_contexts"] = {}
        key = f"{conversation_id}_{lang}"
        cache["translate_contexts"][key] = data
        _save_cache(cache)


def invalidate_all() -> None:
    with _lock:
        if CACHE_FILE.exists():
            try:
                os.remove(CACHE_FILE)
            except Exception:
                pass


def invalidate_conversation(conversation_id: int) -> None:
    with _lock:
        cache = _load_cache()
        # Invalidate the list
        if "conversations_list" in cache:
            del cache["conversations_list"]
        # Invalidate all language contexts for this conversation
        contexts = cache.get("translate_contexts", {})
        keys_to_delete = [k for k in contexts.keys() if k.startswith(f"{conversation_id}_")]
        for k in keys_to_delete:
            del contexts[k]
        cache["translate_contexts"] = contexts
        _save_cache(cache)

