import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_NAME = "mcp_client_config_under_test"
MODULE_PATH = Path(__file__).parents[1] / "agent" / "tools" / "mcp_client.py"


def load_mcp_client_module():
    sys.modules.pop(MODULE_NAME, None)
    adapter_package = types.ModuleType("langchain_mcp_adapters")
    adapter_package.__path__ = []
    client_module = types.ModuleType("langchain_mcp_adapters.client")
    client_module.MultiServerMCPClient = object
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 MCP 客户端配置模块")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {
            "langchain_mcp_adapters": adapter_package,
            "langchain_mcp_adapters.client": client_module,
            MODULE_NAME: module,
        },
    ):
        spec.loader.exec_module(module)
    return module


class MCPClientConfigTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop(MODULE_NAME, None)

    def test_xby_api_key_is_sent_as_http_header(self):
        with patch.dict(
            os.environ,
            {
                "ANALYSIS_MCP_URL": "https://mcp.xiaobenyang.com/example/mcp",
                "XBY_API_KEY": "test-secret-key",
            },
            clear=False,
        ):
            module = load_mcp_client_module()

        headers = module.MCP_SERVER_CONFIG["analysis"].get("headers", {})
        self.assertIn("XBY-APIKEY", headers)
        self.assertTrue(
            headers["XBY-APIKEY"] == "test-secret-key",
            "XBY-APIKEY 请求头未使用测试环境变量",
        )

    def test_empty_xby_api_key_does_not_send_empty_header(self):
        with patch.dict(
            os.environ,
            {
                "ANALYSIS_MCP_URL": "https://example.com/mcp",
                "XBY_API_KEY": "",
            },
            clear=False,
        ):
            module = load_mcp_client_module()

        self.assertFalse(
            "headers" in module.MCP_SERVER_CONFIG["analysis"],
            "未配置密钥时不应发送空的认证请求头",
        )

    def test_xiaobenyang_endpoint_without_key_is_not_exposed_to_agent(self):
        with patch.dict(
            os.environ,
            {
                "ANALYSIS_MCP_URL": "https://mcp.xiaobenyang.com/example/mcp",
                "XBY_API_KEY": "",
            },
            clear=False,
        ):
            module = load_mcp_client_module()

        self.assertNotIn("analysis", module.MCP_SERVER_CONFIG)

    def test_xby_api_key_is_not_sent_to_other_hosts(self):
        with patch.dict(
            os.environ,
            {
                "ANALYSIS_MCP_URL": "https://example.com/mcp",
                "XBY_API_KEY": "test-secret-key",
            },
            clear=False,
        ):
            module = load_mcp_client_module()

        self.assertFalse(
            "headers" in module.MCP_SERVER_CONFIG["analysis"],
            "XBY_API_KEY 不得发送给非小笨羊域名",
        )


if __name__ == "__main__":
    unittest.main()
