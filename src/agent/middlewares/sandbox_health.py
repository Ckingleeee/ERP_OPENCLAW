"""
沙箱健康检查 + 自动恢复中间件。

在 Agent 开始前检查沙箱；工具出现沙箱错误后，在下一次模型调用前再次检查。
短暂不可用时等待服务恢复，持续不可用时才重建沙箱（skills + venv），
并重新上传 AGENTS.md。依赖 SandboxBackendProxy
的热替换能力，重建后其他中间件/工具无需感知变化。

与 SandboxCircuitBreakerMiddleware 配合：
- 本中间件：主动健康检查 → 自动恢复
- SandboxCircuitBreakerMiddleware：恢复后仍失败 → 熔断保护
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from agent.backends.sandbox_proxy import SandboxBackendProxy
from agent.backends.sandbox_resilience import (
    SandboxUnavailableError,
    probe_sandbox_once,
    wait_for_sandbox,
)

logger = logging.getLogger(__name__)


class SandboxHealthMiddleware(AgentMiddleware):
    """沙箱健康守护中间件。

    启动时主动检查；工具返回沙箱传输错误后再次检查：
    - 健康 → 透传
    - 短暂不可用 → 等待服务恢复并复用原沙箱
    - 持续不可用 → 重建沙箱并重新播种 AGENTS.md
    """

    def __init__(
        self,
        *,
        sandbox_backend: SandboxBackendProxy,
        user_id: str,
        agents_md_content: bytes,
        recovery_grace_seconds: float = 35,
    ) -> None:
        super().__init__()
        self._backend = sandbox_backend
        self._user_id = user_id
        self._agents_md = agents_md_content
        self._recovery_grace_seconds = recovery_grace_seconds

    def before_agent(
        self, state: dict[str, Any], runtime: Any
    ) -> Optional[dict[str, Any]]:
        return None

    async def abefore_agent(
        self, state: dict[str, Any], runtime: Any
    ) -> Optional[dict[str, Any]]:
        if await self._check():
            return None

        logger.warning("用户 %s 沙箱无响应，等待 OpenSandbox 恢复...", self._user_id)
        if await self._wait_for_recovery():
            logger.info("用户 %s 沙箱连接已恢复，无需重建", self._user_id)
            return None

        logger.warning("用户 %s 沙箱持续不可用，触发自动重建...", self._user_id)
        await self._recover()
        return None

    async def abefore_model(
        self, state: dict[str, Any], runtime: Any
    ) -> Optional[dict[str, Any]]:
        """Recover between tool and model only after a sandbox transport error."""
        if not self._last_message_has_sandbox_error(state):
            return None
        if await self._wait_for_recovery():
            logger.info("用户 %s 工具故障后沙箱连接已恢复", self._user_id)
            return None
        logger.warning("用户 %s 工具故障后沙箱仍不可用，触发重建", self._user_id)
        await self._recover()
        return None

    async def _check(self) -> bool:
        return await probe_sandbox_once(self._backend)

    async def _wait_for_recovery(self) -> bool:
        return await wait_for_sandbox(
            self._backend,
            timeout_seconds=self._recovery_grace_seconds,
        )

    @staticmethod
    def _last_message_has_sandbox_error(state: dict[str, Any]) -> bool:
        messages = state.get("messages", [])
        if not messages or not isinstance(messages[-1], ToolMessage):
            return False
        content = getattr(messages[-1], "content", "")
        if not isinstance(content, str):
            return False
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            return False
        return str(payload.get("error_code", "")).startswith("SANDBOX_")

    async def _recover(self) -> None:
        from agent.backends.sandbox_manager import recreate_user_sandbox

        try:
            await recreate_user_sandbox(self._user_id)
            responses = await asyncio.to_thread(
                self._backend.upload_files,
                [("/AGENTS.md", self._agents_md)],
            )
        except Exception as exc:
            raise SandboxUnavailableError(str(exc)) from exc

        failures = [response for response in responses if response.error]
        if failures:
            raise SandboxUnavailableError(
                f"AGENTS.md restore failed: {failures[0].error}"
            )
        logger.info("用户 %s 沙箱自动恢复完成", self._user_id)
