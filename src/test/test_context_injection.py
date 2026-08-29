"""Tests for private user-context injection and stream visibility."""

from types import SimpleNamespace
import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.middlewares.context_injection import (
    INTERNAL_CONTEXT_MARKER,
    ContextInjectionMiddleware,
)
from api_view.message_visibility import (
    is_internal_stream_message,
    strip_internal_context_prefix,
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

    def test_legacy_context_is_removed_without_losing_answer(self):
        leaked = (
            "【系统上下文】\n"
            "当前用户 user_id: yyf\n"
            "当前用户 username: yyf\n"
            "用户偏好文件路径: /memories/yyf/preferences.md\n\n"
            "请首先使用 read_file 读取上述偏好文件了解用户偏好。\n"
            "（recent_suppliers 和 recent_queries 由系统自动维护，你无需手动更新）\n"
            "这是用户真正应该看到的回答。"
        )

        self.assertEqual(
            strip_internal_context_prefix(leaked),
            "这是用户真正应该看到的回答。",
        )
        self.assertEqual(strip_internal_context_prefix("正常回答"), "正常回答")


if __name__ == "__main__":
    unittest.main()
