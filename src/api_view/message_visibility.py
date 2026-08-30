"""Rules for deciding which LangChain messages may be exposed to the browser."""

from __future__ import annotations

import json
from typing import Any

from agent.internal_messages import (
    INTERNAL_CONTEXT_MARKER,
    INTERNAL_MEMORY_MODEL_NAME,
    INTERNAL_MEMORY_TAG,
    INTERNAL_MODEL_METADATA_KEY,
)

INTERNAL_CONTEXT_PREFIX = "【系统上下文】\n"
INTERNAL_CONTEXT_END = (
    "（recent_suppliers 和 recent_queries 由系统自动维护，你无需手动更新）"
)


def is_internal_display_message(message: dict[str, Any]) -> bool:
    """Identify legacy child-agent narration stored as a browser message."""
    source = str(message.get("source") or "").strip()
    return (
        message.get("role") == "assistant"
        and bool(source)
        and source != "main"
    )


def is_internal_stream_message(
    message: Any, metadata: dict[str, Any] | None = None
) -> bool:
    """Hide system context and echoed user messages from the assistant stream."""
    message_type = str(getattr(message, "type", "")).lower()
    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}
    metadata = metadata or {}
    tags = metadata.get("tags") or []

    return (
        message_type.startswith("system")
        or message_type.startswith("human")
        or INTERNAL_CONTEXT_MARKER in additional_kwargs
        or INTERNAL_MEMORY_TAG in tags
        or metadata.get(INTERNAL_MODEL_METADATA_KEY) == INTERNAL_MEMORY_MODEL_NAME
    )


def is_user_visible_assistant_message(
    message: Any,
    metadata: dict[str, Any] | None = None,
    *,
    is_subagent: bool = False,
) -> bool:
    """Allow only main-agent assistant messages into the browser text stream."""
    return not is_subagent and not is_internal_stream_message(message, metadata)


def strip_internal_context_prefix(content: str) -> str:
    """Remove leaked legacy context while preserving the assistant answer after it."""
    if not content.startswith(INTERNAL_CONTEXT_PREFIX):
        return content

    _, separator, remainder = content.partition(INTERNAL_CONTEXT_END)
    if not separator:
        return content
    return remainder.lstrip("\r\n")


def strip_internal_memory_payload(content: str) -> str:
    """Remove a legacy memory-extraction JSON object appended to an answer."""
    trimmed = content.rstrip()
    start = trimmed.rfind("{")
    if start < 0:
        return content

    candidate = trimmed[start:]
    try:
        payload = json.loads(candidate)
    except (json.JSONDecodeError, TypeError):
        return content

    if (
        not isinstance(payload, dict)
        or set(payload) != {"suppliers", "query"}
        or not isinstance(payload.get("suppliers"), list)
        or not isinstance(payload.get("query"), str)
    ):
        return content
    return trimmed[:start].rstrip()


def sanitize_legacy_assistant_content(content: str) -> str:
    """Remove known internal payloads stored before stream filtering was fixed."""
    content = strip_internal_context_prefix(content)
    return strip_internal_memory_payload(content)
