"""OpenSandbox failure classification and health-check helpers."""
from __future__ import annotations

import asyncio
from time import monotonic
from typing import Any


PROBE_MARKER = "sandbox-ready"

_UNAVAILABLE_MARKERS = (
    "connection refused",
    "connectionrefusederror",
    "failed to establish a new connection",
    "all connection attempts failed",
    "name or service not known",
    "temporary failure in name resolution",
    "nodename nor servname provided",
)

_UNCERTAIN_MARKERS = (
    "incomplete chunked read",
    "peer closed connection",
    "server disconnected",
    "remoteprotocolerror",
    "connection reset by peer",
)


class SandboxServiceError(RuntimeError):
    """Base class for failures communicating with OpenSandbox."""

    code = "SANDBOX_ERROR"
    user_message = "分析沙箱暂时不可用，请稍后重试。"
    retryable = False
    execution_uncertain = False

    def __init__(self, detail: str = "") -> None:
        super().__init__(self.user_message)
        self.detail = detail[:1000]


class SandboxUnavailableError(SandboxServiceError):
    """The request did not reach OpenSandbox and may be retried safely."""

    code = "SANDBOX_UNAVAILABLE"
    user_message = "分析沙箱正在恢复连接，请稍后重试本次请求。"
    retryable = True


class SandboxExecutionUncertainError(SandboxServiceError):
    """The connection broke after dispatch, so command completion is unknown."""

    code = "SANDBOX_EXECUTION_UNCERTAIN"
    user_message = (
        "分析沙箱在执行过程中断开，命令结果暂时无法确认。"
        "为避免重复操作，系统没有自动重放该命令，请先核对结果后再继续。"
    )
    execution_uncertain = True


def exception_chain_text(exc: BaseException) -> str:
    """Return exception types and messages from the complete cause chain."""
    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(f"{type(current).__name__}: {current}")
        current = current.__cause__ or current.__context__
    return " | ".join(parts)


def classify_sandbox_exception(exc: BaseException) -> SandboxServiceError | None:
    """Convert known OpenSandbox transport failures to stable domain errors."""
    if isinstance(exc, SandboxServiceError):
        return exc

    detail = exception_chain_text(exc)
    lowered = detail.lower()
    # A broken response can mean the command was accepted. Never replay it blindly.
    if any(marker in lowered for marker in _UNCERTAIN_MARKERS):
        return SandboxExecutionUncertainError(detail)
    if any(marker in lowered for marker in _UNAVAILABLE_MARKERS):
        return SandboxUnavailableError(detail)
    if "network connectivity error" in lowered:
        return SandboxExecutionUncertainError(detail)
    return None


def is_successful_probe(response: Any, marker: str = PROBE_MARKER) -> bool:
    """Validate both the command exit code and its expected output marker."""
    if response is None or getattr(response, "exit_code", None) != 0:
        return False
    return marker in str(getattr(response, "output", ""))


async def probe_sandbox_once(backend: Any) -> bool:
    """Run one non-mutating sandbox health probe."""
    try:
        fast_probe = getattr(backend, "health_check", None)
        if callable(fast_probe):
            response = await asyncio.to_thread(fast_probe)
        else:
            response = await asyncio.to_thread(
                backend.execute,
                f"printf {PROBE_MARKER}",
                timeout=10,
            )
    except Exception:
        return False
    return is_successful_probe(response)


async def wait_for_sandbox(
    backend: Any,
    *,
    timeout_seconds: float = 35,
    poll_seconds: float = 2,
) -> bool:
    """Wait through a short OpenSandbox restart window before rebuilding state."""
    deadline = monotonic() + max(0, timeout_seconds)
    while True:
        if await probe_sandbox_once(backend):
            return True
        remaining = deadline - monotonic()
        if remaining <= 0:
            return False
        await asyncio.sleep(min(max(0.05, poll_seconds), remaining))
