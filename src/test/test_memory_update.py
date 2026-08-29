"""Tests for private and meaningful automatic memory updates."""

import unittest
from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.constants import TAG_NOSTREAM

from agent.internal_messages import INTERNAL_MEMORY_TAG
from agent.middlewares.memory_update import (
    _extract_entities,
    _is_meaningful_erp_exchange,
    _merge_preferences,
)


class MemoryUpdateTests(unittest.IsolatedAsyncioTestCase):
    def test_generic_procurement_intent_is_not_memorized(self):
        messages = [HumanMessage(content="我需要采购")]
        self.assertIsNone(_is_meaningful_erp_exchange(messages))

    async def test_internal_model_call_is_not_streamed(self):
        model = AsyncMock()
        model.ainvoke.return_value = AIMessage(
            content=(
                '{"suppliers": [], "query": '
                '"用户表示需要采购，但未说明具体物料或需求"}'
            )
        )

        result = await _extract_entities(model, "我需要采购", "请补充物料")

        self.assertEqual(result, {"suppliers": [], "query": ""})
        config = model.ainvoke.await_args.kwargs["config"]
        self.assertIn(TAG_NOSTREAM, config["tags"])
        self.assertIn(INTERNAL_MEMORY_TAG, config["tags"])

    async def test_concrete_procurement_query_is_preserved(self):
        model = AsyncMock()
        model.ainvoke.return_value = AIMessage(
            content=(
                '{"suppliers": ["博世"], '
                '"query": "采购100个博世火花塞并比较报价"}'
            )
        )

        result = await _extract_entities(
            model,
            "采购100个博世火花塞并比较报价",
            "正在分析",
        )

        self.assertEqual(result["suppliers"], ["博世"])
        self.assertEqual(result["query"], "采购100个博世火花塞并比较报价")

    def test_legacy_vague_query_is_removed_during_merge(self):
        current_lines = [
            "language: zh-CN",
            "",
            "recent_suppliers: []",
            "recent_queries:",
            "  - 用户表示需要采购，但未说明具体物料或需求",
        ]

        merged = _merge_preferences(current_lines, [], "")

        self.assertIn("language: zh-CN", merged)
        self.assertIn("recent_queries: []", merged)
        self.assertNotIn("未说明具体物料", merged)


if __name__ == "__main__":
    unittest.main()
