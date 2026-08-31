"""Tests for private user-context injection and stream visibility."""

from types import SimpleNamespace
import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.middlewares.context_injection import (
    INTERNAL_CONTEXT_MARKER,
    ContextInjectionMiddleware,
)
from api_view.message_visibility import (
    is_internal_display_message,
    is_internal_stream_message,
    is_user_visible_assistant_message,
    sanitize_legacy_assistant_content,
    strip_internal_context_prefix,
)
from agent.internal_messages import (
    INTERNAL_MEMORY_MODEL_NAME,
    INTERNAL_MEMORY_TAG,
    INTERNAL_MODEL_METADATA_KEY,
)


class ContextInjectionTests(unittest.TestCase):
    def setUp(self):
        self.middleware = ContextInjectionMiddleware()
        self.runtime = SimpleNamespace(
            context=SimpleNamespace(user_id="yyf", username="yyf")
        )

    def test_context_is_marked_and_injected_once(self):
        update = self.middleware.before_agent({"messages": []}, self.runtime)
        message = update["messages"][0]

        self.assertEqual(
            message.additional_kwargs[INTERNAL_CONTEXT_MARKER], "yyf"
        )
        self.assertIsNone(
            self.middleware.before_agent({"messages": [message]}, self.runtime)
        )

    def test_legacy_context_is_not_injected_again(self):
        legacy = SystemMessage(
            content=(
                "【系统上下文】\n"
                "当前用户 user_id: yyf\n"
                "当前用户 username: yyf"
            )
        )

        self.assertIsNone(
            self.middleware.before_agent({"messages": [legacy]}, self.runtime)
        )

    def test_only_assistant_text_is_visible(self):
        internal = SystemMessage(
            content="private",
            additional_kwargs={INTERNAL_CONTEXT_MARKER: "yyf"},
        )

        self.assertTrue(is_internal_stream_message(internal))
        self.assertTrue(is_internal_stream_message(HumanMessage(content="hello")))
        self.assertFalse(is_internal_stream_message(AIMessage(content="answer")))
        self.assertTrue(
            is_internal_stream_message(
                AIMessage(content='{"suppliers": [], "query": "internal"}'),
                {"tags": [INTERNAL_MEMORY_TAG]},
            )
        )
        self.assertTrue(
            is_internal_stream_message(
                AIMessage(content="internal"),
                {INTERNAL_MODEL_METADATA_KEY: INTERNAL_MEMORY_MODEL_NAME},
            )
        )
        self.assertFalse(
            is_user_visible_assistant_message(
                AIMessage(content="I'll inspect the available tools."),
                is_subagent=True,
            )
        )
        self.assertTrue(
            is_user_visible_assistant_message(
                AIMessage(content="权益运营分析已完成。"),
                is_subagent=False,
            )
        )

    def test_legacy_context_is_removed_without_losing_answer(self):
        leaked = (
            "【系统上下文】\n"
            "当前用户 user_id: yyf\n"
            "当前用户 username: yyf\n"
            "用户偏好文件路径: /memories/yyf/preferences.md\n\n"
            "请首先使用 read_file 读取上述偏好文件了解用户偏好。\n"
            "（recent_providers 和 recent_queries 由系统自动维护，你无需手动更新）\n"
            "这是用户真正应该看到的回答。"
        )

        self.assertEqual(
            strip_internal_context_prefix(leaked),
            "这是用户真正应该看到的回答。",
        )
        self.assertEqual(strip_internal_context_prefix("正常回答"), "正常回答")

    def test_legacy_memory_json_is_removed_without_losing_answer(self):
        leaked = (
            "请补充具体权益资源。\n"
            '{"providers": [], "query": '
            '"用户表示需要补充权益，但需要补充具体资源"}'
        )

        self.assertEqual(
            sanitize_legacy_assistant_content(leaked),
            "请补充具体权益资源。",
        )
        self.assertEqual(
            sanitize_legacy_assistant_content(
                '{"code": 200, "message": "正常业务 JSON"}'
            ),
            '{"code": 200, "message": "正常业务 JSON"}',
        )

    def test_child_agent_narration_is_not_a_display_message(self):
        self.assertTrue(
            is_internal_display_message(
                {
                    "role": "assistant",
                    "content": "I'll start by scanning the skills directory.",
                    "source": "d78a8575-995e-a658-b89e-096fcc196448",
                }
            )
        )
        self.assertFalse(
            is_internal_display_message(
                {
                    "role": "assistant",
                    "content": "权益运营分析已完成。",
                    "source": "main",
                }
            )
        )
        self.assertFalse(
            is_internal_display_message(
                {
                    "role": "tool",
                    "text": "tool result",
                    "source": "benefit-operations-analyst",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
