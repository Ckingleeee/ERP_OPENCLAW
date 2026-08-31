from fastmcp import FastMCP, Context

# 分组名称
GROUP_NAME = "provider"


def register_provider_tools(mcp: FastMCP):
    """注册权益服务商分组的所有工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_query")
    async def query_providers(name: str, ctx: Context) -> list:
        """
        按名称模糊搜索信用卡权益或营销资源服务商。

        Args:
            name: 权益服务商名称（模糊查询），必填
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        try:
            response = await http_client.get(
                "/providers/search", params={"name": name}
            )
            response.raise_for_status()
            result = response.json()
            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]
            return result.get("data", [])
        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']
