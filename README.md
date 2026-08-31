# 卡营智控——信用卡权益与营销资源智能运营工作台

面向信用卡营销运营场景，支持权益服务商、营销资源、配额预警和资源补充历史的自然语言查询与分析，并通过人工审批执行资源补充单写操作。项目由 Vue 前端、Agent Web API、Python 业务 API、MCP、MySQL、MongoDB 和 OpenSandbox 组成。

## Ubuntu 一键部署

```bash
git clone <repository-url> /opt/erp_openclaw
cd /opt/erp_openclaw
cp .env.docker.example .env
# 填写 .env 中的数据库密码、登录密码、JWT 密钥和模型 API Key
chmod 600 .env
sudo bash ./scripts/deploy.sh
```

脚本会安装缺失的 Docker/Compose、部署宿主机 OpenSandbox、构建并启动全部 Compose 服务、配置开机启动并执行健康检查。浏览器访问 `http://<server-ip>/`。

部署后的日常管理：

```bash
erpctl status
erpctl health
erpctl restart
erpctl logs agent-web
```

完整配置、国内镜像源、OpenSandbox 网络边界和现有数据迁移步骤见 [DOCKER_DEPLOY.md](./DOCKER_DEPLOY.md)。

> 不要对已有数据执行 `docker compose down -v`，`-v` 会删除 MySQL 和 MongoDB 持久卷。

## 本地开发

建议把 Python 虚拟环境建在仓库外，避免生成 `.venv/`、`*.egg-info/` 或 `uv.lock`：

```powershell
cd D:\workspace\ERP_OPENCLAW
py -3.12 -m venv ..\erp_openclaw_venv
..\erp_openclaw_venv\Scripts\Activate.ps1
python -m pip install -r requirements-linux.txt -r requirements-erp.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

复制 `.env.example` 为 `.env` 并填写本地配置后，分别启动业务 API、MCP 和 Agent Web：

```powershell
python -m uvicorn erp_backend.main:app --host 127.0.0.1 --port 8080 --reload
python -m mcp_server.server_main
python -m uvicorn api_view.web_app:app --host 127.0.0.1 --port 8888 --reload
```

前端运行 `npm install`、`npm run dev`。业务 API 的数据库初始化、接口和请求示例见 [ERP_BACKEND.md](./ERP_BACKEND.md)。

<details>
<summary>历史 LangGraph 模板说明</summary>

# New LangGraph Project

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

This template demonstrates a simple application implemented using [LangGraph](https://github.com/langchain-ai/langgraph), designed for showing how to get started with [LangGraph Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/#langgraph-server) and using [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/), a visual debugging IDE.

<div align="center">
  <img src="./static/studio_ui.png" alt="Graph view in LangGraph studio UI" width="75%" />
</div>

The core logic defined in `src/agent/graph.py`, showcases an single-step application that responds with a fixed string and the configuration provided.

You can extend this graph to orchestrate more complex agentic workflows that can be visualized and debugged in LangGraph Studio.

## Getting Started

1. Install dependencies, along with the [LangGraph CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/), which will be used to run the server.

```bash
cd path/to/your/app
pip install -e . "langgraph-cli[inmem]"
```

2. (Optional) Customize the code and project as needed. Create a `.env` file if you need to use secrets.

```bash
cp .env .env
```

If you want to enable LangSmith tracing, add your LangSmith API key to the `.env` file.

```text
# .env
LANGSMITH_API_KEY=lsv2...
```

3. Start the LangGraph Server.

```shell
langgraph dev
```

For more information on getting started with LangGraph Server, [see here](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/).

## How to customize

1. **Define runtime context**: Modify the `Context` class in the `graph.py` file to expose the arguments you want to configure per assistant. For example, in a chatbot application you may want to define a dynamic system prompt or LLM to use. For more information on runtime context in LangGraph, [see here](https://langchain-ai.github.io/langgraph/agents/context/?h=context#static-runtime-context).

2. **Extend the graph**: The core logic of the application is defined in [graph.py](./src/agent/graph.py). You can modify this file to add new nodes, edges, or change the flow of information.

## Development

While iterating on your graph in LangGraph Studio, you can edit past state and rerun your app from previous states to debug specific nodes. Local changes will be automatically applied via hot reload.

Follow-up requests extend the same thread. You can create an entirely new thread, clearing previous history, using the `+` button in the top right.

For more advanced features and examples, refer to the [LangGraph documentation](https://langchain-ai.github.io/langgraph/). These resources can help you adapt this template for your specific use case and build more sophisticated conversational agents.

LangGraph Studio also integrates with [LangSmith](https://smith.langchain.com/) for more in-depth tracing and collaboration with teammates, allowing you to analyze and optimize your chatbot's performance.

</details>
