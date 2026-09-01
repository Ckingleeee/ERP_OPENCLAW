"""Tests for SSE heartbeats around slow agent output."""
import asyncio
import unittest

from api_view.sse import HEARTBEAT, with_heartbeat


class SSEHeartbeatTests(unittest.IsolatedAsyncioTestCase):
    async def test_heartbeat_does_not_cancel_slow_source(self):
        async def source():
            await asyncio.sleep(0.03)
            yield {"type": "done"}

        received = []
        async for item in with_heartbeat(source(), interval_seconds=0.01):
            received.append(item)

        self.assertIn(HEARTBEAT, received)
        self.assertEqual(received[-1], {"type": "done"})

    async def test_fast_source_does_not_emit_heartbeat(self):
        async def source():
            yield 1
            yield 2

        received = [
            item async for item in with_heartbeat(source(), interval_seconds=0.1)
        ]
        self.assertEqual(received, [1, 2])


if __name__ == "__main__":
    unittest.main()
