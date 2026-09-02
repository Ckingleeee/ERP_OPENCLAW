import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


VALIDATOR_PATH = (
    Path(__file__).parents[2] / "scripts" / "validate-docker-env.py"
)


def load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "docker_env_validator_under_test", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载 Docker 环境校验脚本")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def valid_environment() -> dict[str, str]:
    return {
        "MYSQL_ROOT_PASSWORD": "mysql-root-password",
        "ERP_DB_PASSWORD": "erp-database-password",
        "MONGO_ROOT_PASSWORD": "mongo-root-password",
        "MONGODB_APP_USER": "erp_agent",
        "MONGODB_APP_PASSWORD": "mongo-application-password",
        "ERP_ADMIN_PASSWORD": "erp-admin-password",
        "DEEPSEEK_API_KEY": "deepseek-test-key",
        "DEEPSEEK_BASE_URL": "https://example.com/v1",
        "ALIBABA_API_KEY": "alibaba-test-key",
        "ALIBABA_BASE_URL": "https://example.com/v1",
        "OPEN_SANDBOX_API_KEY": "opensandbox-test-key",
        "OPEN_SANDBOX_DOMAIN": "http://127.0.0.1:18080",
        "AUTH_JWT_SECRET": "a" * 32,
        "HTTP_PORT": "80",
        "AUTH_COOKIE_SECURE": "false",
        "CORS_ALLOWED_ORIGINS": "http://localhost",
    }


class DockerEnvValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = load_validator_module()

    def run_validation(self, values: dict[str, str]) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "".join(f"{key}={value}\n" for key, value in values.items()),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(
                output
            ):
                result = self.validator.validate(env_path)
        return result, output.getvalue()

    def test_xiaobenyang_url_requires_api_key(self):
        values = valid_environment()
        values["ANALYSIS_MCP_URL"] = (
            "https://mcp.xiaobenyang.com/example/mcp"
        )

        result, output = self.run_validation(values)

        self.assertEqual(result, 1)
        self.assertIn("XBY_API_KEY", output)

    def test_xiaobenyang_url_with_api_key_is_valid(self):
        values = valid_environment()
        values.update(
            {
                "ANALYSIS_MCP_URL": "https://mcp.xiaobenyang.com/example/mcp",
                "XBY_API_KEY": "xby-test-key",
            }
        )

        result, output = self.run_validation(values)

        self.assertEqual(result, 0, output)


if __name__ == "__main__":
    unittest.main()
