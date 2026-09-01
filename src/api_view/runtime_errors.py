"""Stable, user-safe error contracts for the streaming chat API."""
from __future__ import annotations

from dataclasses import dataclass

from agent.backends.sandbox_resilience import (
    SandboxExecutionUncertainError,
    SandboxServiceError,
    SandboxUnavailableError,
    exception_chain_text,
)


@dataclass(frozen=True)
class RuntimeErrorInfo:
    code: str
    message: str
    retryable: bool


def classify_runtime_error(exc: BaseException) -> RuntimeErrorInfo:
    """Map implementation exceptions to a stable public error contract."""
    if isinstance(exc, SandboxExecutionUncertainError):
        return RuntimeErrorInfo(exc.code, exc.user_message, exc.retryable)
    if isinstance(exc, SandboxUnavailableError):
        return RuntimeErrorInfo(exc.code, exc.user_message, exc.retryable)
    if isinstance(exc, SandboxServiceError):
        return RuntimeErrorInfo(exc.code, exc.user_message, exc.retryable)

    detail = exception_chain_text(exc).lower()
    if "opensandbox" in detail or "sandboxinternalexception" in detail:
        uncertain = any(marker in detail for marker in (
            "incomplete chunked read",
            "peer closed connection",
            "remoteprotocolerror",
            "connection reset",
        ))
        if uncertain:
            error = SandboxExecutionUncertainError(detail)
        else:
            error = SandboxUnavailableError(detail)
        return RuntimeErrorInfo(error.code, error.user_message, error.retryable)

    if "timeout" in detail or "timed out" in detail:
        return RuntimeErrorInfo(
            "UPSTREAM_TIMEOUT",
            "上游服务响应超时，请稍后重试。",
            True,
        )

    if any(marker in detail for marker in (
        "network error",
        "connecterror",
        "connectionerror",
        "connection refused",
        "server disconnected",
        "remoteprotocolerror",
    )):
        return RuntimeErrorInfo(
            "UPSTREAM_UNAVAILABLE",
            "上游服务连接暂时中断，请稍后重试。",
            True,
        )

    return RuntimeErrorInfo(
        "INTERNAL_ERROR",
        "系统处理请求时发生异常，请稍后重试；若持续出现，请联系管理员。",
        False,
    )
