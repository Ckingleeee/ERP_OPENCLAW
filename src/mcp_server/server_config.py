import os

# Python ERP 后端 API 地址。保留旧变量名以兼容现有导入。
ERP_API_BASE_URL = os.getenv("ERP_API_BASE_URL", "http://localhost:8080/api")
JAVA_API_BASE_URL = ERP_API_BASE_URL

# MCP 服务监听配置
MCP_HOST = "127.0.0.1"
MCP_PORT = 8000
MCP_PATH = "/mcp"
