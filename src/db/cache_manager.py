import threading
from typing import Any

# Global in-memory cache dictionary
_memory_cache: dict[str, Any] = {}
_lock = threading.Lock()


def get_cached_conversations_list() -> list[dict[str, Any]] | None:
    with _lock:
        return _memory_cache.get("conversations_list")


def set_cached_conversations_list(conversations: list[dict[str, Any]]) -> None:
    with _lock:
        _memory_cache["conversations_list"] = conversations


def get_cached_translate_context(conversation_id: int, lang: str) -> dict[str, Any] | None:
    with _lock:
        contexts = _memory_cache.get("translate_contexts", {})
        key = f"{conversation_id}_{lang}"
        return contexts.get(key)


def set_cached_translate_context(conversation_id: int, lang: str, data: dict[str, Any]) -> None:
    with _lock:
        if "translate_contexts" not in _memory_cache:
            _memory_cache["translate_contexts"] = {}
        key = f"{conversation_id}_{lang}"
        _memory_cache["translate_contexts"][key] = data


def invalidate_all() -> None:
    with _lock:
        _memory_cache.clear()


def invalidate_conversation(conversation_id: int) -> None:
    with _lock:
        # Invalidate the list
        if "conversations_list" in _memory_cache:
            del _memory_cache["conversations_list"]
            
        # Invalidate all language contexts for this conversation
        if "translate_contexts" in _memory_cache:
            contexts = _memory_cache["translate_contexts"]
            keys_to_delete = [k for k in contexts.keys() if k.startswith(f"{conversation_id}_")]
            for k in keys_to_delete:
                del contexts[k]

