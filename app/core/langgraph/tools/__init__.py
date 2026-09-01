"""用于增强语言模型能力的 LangGraph 工具.

工具分为两类：

1. 静态工具（同步，模块导入时即可用）
   - duckduckgo_search：DuckDuckGo 网页搜索
   - calculator：安全四则运算
   - ask_human：中断图流程，向用户请求补充信息

2. MCP 工具（异步，运行时动态从 MCP Server 加载）
   - 百度地图（自建 FastMCP Server）：地理编码、周边检索、路线规划、天气等 5 个工具

使用方式：
    # 在 LangGraph Agent 初始化时调用，获取完整工具列表
    all_tools = await load_all_tools()
"""

from langchain_core.tools.base import BaseTool

from app.core.config import settings

from .ask_human import ask_human
from .calculator import calculator
from .duckduckgo_search import duckduckgo_search_tool
from .knowledge_search import knowledge_search
from .mcp_client import get_langchain_mcp_tools
from .baidu_mcp import get_baidu_mcp_servers

# 静态工具：同步加载，始终可用
static_tools: list[BaseTool] = [duckduckgo_search_tool, calculator, ask_human]

# RAG tool 模式：注册知识库检索工具，由 Agent 按需调用
# （inject 模式不注册，知识每轮自动注入 system prompt，避免同一轮既注入又调用造成重复）
if settings.RAG_ENABLED and settings.RAG_MODE == "tool":
    static_tools.append(knowledge_search)


async def load_all_tools() -> list[BaseTool]:
    """加载全部工具：静态工具 + 所有已配置的 MCP 工具.

    在 LangGraph Agent 的 create_graph() 中调用一次，结果缓存在 Agent 实例上。
    MCP 工具未配置 Key 或连接失败时，自动降级为仅使用静态工具，不影响服务启动。

    返回：
        BaseTool 列表，可直接传给 llm.bind_tools() 和 ToolNode。
    """
    from app.core.logging import logger  # 避免循环导入

    baidu_servers = get_baidu_mcp_servers()

    if not baidu_servers:
        # 未配置 MCP，直接返回静态工具
        logger.info("tools_loaded", static_count=len(static_tools), mcp_count=0)
        return list(static_tools)

    try:
        mcp_tools = await get_langchain_mcp_tools(baidu_servers)
        all_tools = static_tools + mcp_tools
        logger.info(
            "tools_loaded",
            static_count=len(static_tools),
            mcp_count=len(mcp_tools),
            total=len(all_tools),
            mcp_tool_names=[t.name for t in mcp_tools],
        )
        return all_tools
    except Exception as e:
        # MCP 加载失败时降级：仍使用静态工具，不中断 Agent 启动
        logger.warning(
            "mcp_tools_load_failed_fallback_to_static",
            error=str(e),
            static_count=len(static_tools),
        )
        return list(static_tools)
