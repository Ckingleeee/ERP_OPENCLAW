"""Rules for deciding which LangChain messages may be exposed to the browser."""

from __future__ import annotations

from typing import Any

from agent.middlewares.context_injection import INTERNAL_CONTEXT_MARKER

INTERNAL_CONTEXT_PREFIX = "【系统上下文】\n"
INTERNAL_CONTEXT_END = (
    "（recent_suppliers 和 recent_queries 由系统自动维护，你无需手动更新）"
)


def is_internal_stream_message(message: Any) -> bool:
    """Hide system context and echoed user messages from the assistant stream."""
    message_type = str(getattr(message, "type", "")).lower()
    additional_kwargs = getattr(message, "additional_kwargs", {}) or {}

    return (
        message_type.startswith("system")
        or message_type.startswith("human")
        or INTERNAL_CONTEXT_MARKER in additional_kwargs
    )


def strip_internal_context_prefix(content: str) -> str:
    """Remove leaked legacy context while preserving the assistant answer after it."""
    if not content.startswith(INTERNAL_CONTEXT_PREFIX):
        return content

    _, separator, remainder = content.partition(INTERNAL_CONTEXT_END)
    if not separator:
        return content
    return remainder.lstrip("\r\n")
