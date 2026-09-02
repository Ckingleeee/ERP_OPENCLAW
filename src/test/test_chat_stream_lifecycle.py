"""Tests for full-lifecycle chat streaming resilience."""
import asyncio
import unittest
from unittest.mock import AsyncMock, patch

try:
    from api_view.api import chat
except ModuleNotFoundError as exc:
    if exc.name != "pymongo":
        raise
    chat = None


class _EmptyAgentGraph:
    async def _stream(self):
        if False:
            yield None

    def astream(self, **kwargs):
        return self._stream()


@unittest.skipIf(chat is None, "pymongo is not installed in this test environment")
class ChatStreamLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_heartbeat_covers_work_before_agent_stream_starts(self):
        async def slow_core(**kwargs):
            await asyncio.sleep(0.03)
            yield chat.create_sse_message({"type": "done", "thread_id": "thread-1"})

        with (
            patch.object(chat, "_stream_chat_response_core", slow_core),
            patch.object(chat, "SSE_HEARTBEAT_INTERVAL_SECONDS", 0.01),
        ):
            received = [
                item
                async for item in chat.stream_chat_response(
                    message="hello",
                    thread_id="thread-1",
                    user_id="user-1",
                )
            ]

        self.assertIn(": keep-alive\n\n", received)
        self.assertIn('"type": "done"', received[-1])

    async def test_user_message_is_saved_before_agent_initialization(self):
        saved_snapshots = []

        async def save_messages(thread_id, messages, user_id=None):
            saved_snapshots.append([dict(message) for message in messages])
            return True

        with (
            patch.object(
                chat.agent_loader,
                "get_display_messages",
                AsyncMock(return_value=[]),
            ),
            patch.object(
                chat.agent_loader,
                "save_display_messages",
                side_effect=save_messages,
            ),
            patch.object(
                chat.agent_loader,
                "get_agent_for_user",
                AsyncMock(return_value=_EmptyAgentGraph()),
            ) as get_agent,
        ):
            events = [
                item
                async for item in chat._stream_chat_response_core(
                    message="persist me",
                    thread_id="thread-2",
                    user_id="user-2",
                )
            ]

        self.assertTrue(get_agent.await_count)
        self.assertGreaterEqual(len(saved_snapshots), 2)
        self.assertEqual(saved_snapshots[0][-1]["role"], "user")
        self.assertEqual(saved_snapshots[0][-1]["content"], "persist me")
        self.assertIn('"type": "done"', events[-1])


if __name__ == "__main__":
    unittest.main()
