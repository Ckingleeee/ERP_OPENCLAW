import asyncio

from fastmcp import Client
from langchain_mcp_adapters.client import MultiServerMCPClient

from mcp_server.server_main import mcp


async def mcp_client():
    """创建内存模式客户端固件"""
    async with Client(mcp) as client:
        # result = await client.call_tool(
        #     "provider_query", {"name": "星享数字权益"}
        # )
        result = await client.call_tool("replenishment_update", {
            "replenishment_id": 1,
            "actual_activation_date": "2026-09-15",
            "replenishment_number": 'BR20260801001',
            "remark": "权益资源生效日期调整"
        })

        print(result)


async def agent_client():
    mcp_server_config = {
        "url": "http://127.0.0.1:8000/mcp",
        "transport": "streamable_http",
    }
    # 创建一个mcp的客户端
    mcp_client = MultiServerMCPClient({
        # "xsct": xsct_mcp_server_config,
        "api": mcp_server_config,
    })
    all_tools = await mcp_client.get_tools(server_name="api")
    print(all_tools)
    # tools = [t for t in all_tools if t.name.startswith(f"{group_name}_")]
    tools = [t for t in all_tools if t.name.startswith("resource_")]
    print(tools)

if __name__ == '__main__':
    asyncio.run(mcp_client())
    # asyncio.run(agent_client())
