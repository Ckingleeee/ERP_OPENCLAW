"""Utilities for resilient Server-Sent Events streams."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Any


HEARTBEAT = object()


async def with_heartbeat(
    source: AsyncIterator[Any],
    *,
    interval_seconds: float = 15,
) -> AsyncIterator[Any]:
    """Yield a sentinel while waiting without cancelling the source iterator."""
    iterator = source.__aiter__()
    pending: asyncio.Task | None = None
    try:
        pending = asyncio.create_task(anext(iterator))
        while True:
            done, _ = await asyncio.wait(
                {pending},
                timeout=max(0.001, interval_seconds),
            )
            if not done:
                yield HEARTBEAT
                continue

            try:
                item = pending.result()
            except StopAsyncIteration:
                return
            yield item
            pending = asyncio.create_task(anext(iterator))
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
