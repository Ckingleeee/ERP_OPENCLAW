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
    def test_generic_operations_intent_is_not_memorized(self):
        messages = [HumanMessage(content="补充权益")]
        self.assertIsNone(_is_meaningful_erp_exchange(messages))

    async def test_internal_model_call_is_not_streamed(self):
        model = AsyncMock()
        model.ainvoke.return_value = AIMessage(
            content=(
                '{"providers": [], "query": '
                '"用户表示需要补充权益，但需要补充具体资源"}'
            )
        )

        result = await _extract_entities(model, "补充权益", "请补充资源")

        self.assertEqual(result, {"providers": [], "query": ""})
        config = model.ainvoke.await_args.kwargs["config"]
        self.assertIn(TAG_NOSTREAM, config["tags"])
        self.assertIn(INTERNAL_MEMORY_TAG, config["tags"])

    async def test_concrete_operations_query_is_preserved(self):
        model = AsyncMock()
        model.ainvoke.return_value = AIMessage(
            content=(
                '{"providers": ["星享数字权益"], '
                '"query": "补充1000张视频会员月卡并比较成本"}'
            )
        )

        result = await _extract_entities(
            model,
            "补充1000张视频会员月卡并比较成本",
            "正在分析",
        )

        self.assertEqual(result["providers"], ["星享数字权益"])
        self.assertEqual(result["query"], "补充1000张视频会员月卡并比较成本")

    def test_legacy_vague_query_is_removed_during_merge(self):
        current_lines = [
            "language: zh-CN",
            "",
            "recent_providers: []",
            "recent_queries:",
            "  - 用户表示需要补充权益，但未说明具体资源",
        ]

        merged = _merge_preferences(current_lines, [], "")

        self.assertIn("language: zh-CN", merged)
        self.assertIn("recent_queries: []", merged)
        self.assertNotIn("未说明具体资源", merged)


if __name__ == "__main__":
    unittest.main()
