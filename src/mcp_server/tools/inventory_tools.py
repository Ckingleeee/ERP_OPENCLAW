from fastmcp import FastMCP, Context

GROUP_NAME = "quota"


def register_quota_tools(mcp: FastMCP):
    """注册权益资源配额管理分组的所有工具。"""

    @mcp.tool(name=f"{GROUP_NAME}_warning")
    async def list_quota_warnings(ctx: Context) -> list:
        """
        查询权益与营销资源的配额预警列表。
        返回所有当前配额低于安全阈值的资源及其服务商详情。

        无需传参。
        """
        http_client = ctx.request_context.lifespan_context.get("http_client")

        try:
            response = await http_client.get("/quotas/warning")
            response.raise_for_status()
            result = response.json()

            if result.get("code") != 200:
                return [f"API error: code={result.get('code')}"]

            return result.get("data", [])
        except Exception as e:
            return [f'没有查询到任何信息，而且报错: {e}']
