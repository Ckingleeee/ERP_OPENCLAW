"""基于阿里云百炼千问模型的联网搜索工具。"""

from langchain_core.tools import tool
from openai import OpenAI

from agent.env_utils import (
    ALIBABA_API_KEY,
    ALIBABA_BASE_URL,
    ALIBABA_SEARCH_MODEL,
)


def _get_client() -> OpenAI:
    """按需创建客户端，避免缺少搜索配置时阻断 Agent 模块导入。"""
    if not ALIBABA_API_KEY:
        raise RuntimeError("未配置 ALIBABA_API_KEY")
    if not ALIBABA_BASE_URL:
        raise RuntimeError("未配置 ALIBABA_BASE_URL")
    return OpenAI(api_key=ALIBABA_API_KEY, base_url=ALIBABA_BASE_URL)


@tool('web_search', parse_docstring=True)
def web_search(query: str) -> str:
    """
    使用千问模型的联网搜索能力进行搜索和摘要。

    适用于：市场行情调研、供应商背景调查、物料价格趋势查询、行业资讯获取等。

    Args:
        query: 需要搜索的内容或者关键字。

    Returns:
        返回搜索之后的结果。
    """
    try:
        response = _get_client().chat.completions.create(
            model=ALIBABA_SEARCH_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是 ERP 采购场景的联网研究助手。基于联网搜索结果回答，"
                        "优先给出最新、可核验的信息；无法确认时明确说明。"
                    ),
                },
                {"role": "user", "content": query},
            ],
            extra_body={
                "enable_search": True,
                "search_options": {"search_strategy": "max"},
            },
        )
        content = response.choices[0].message.content
        return content or "没有搜索到任何内容！"
    except Exception as e:
        print(e)
        return f"搜索失败: {e}"
