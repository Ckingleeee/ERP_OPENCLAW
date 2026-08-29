"""Tests for the Qwen-backed web search tool."""

from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import Mock, patch

from agent.tools import web_search
from agent.tools import web_search as exported_web_search


web_search_module = importlib.import_module("agent.tools.web_search")


class QwenWebSearchTests(unittest.TestCase):
    def test_tool_is_exported_under_existing_name(self):
        self.assertIs(exported_web_search, web_search)
        self.assertEqual(web_search.name, "web_search")

    @patch("agent.tools.web_search._get_client")
    def test_search_enables_qwen_network_search(self, get_client):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="联网搜索结果"))]
        )
        client = Mock()
        client.chat.completions.create.return_value = completion
        get_client.return_value = client

        result = web_search.invoke({"query": "汽车零部件最新行情"})

        self.assertEqual(result, "联网搜索结果")
        call = client.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], web_search_module.ALIBABA_SEARCH_MODEL)
        self.assertTrue(call["extra_body"]["enable_search"])
        self.assertEqual(
            call["extra_body"]["search_options"]["search_strategy"], "max"
        )

    def test_missing_api_key_has_clear_error(self):
        with (
            patch.object(web_search_module, "ALIBABA_API_KEY", None),
            self.assertRaisesRegex(RuntimeError, "ALIBABA_API_KEY"),
        ):
            web_search_module._get_client()


if __name__ == "__main__":
    unittest.main()
