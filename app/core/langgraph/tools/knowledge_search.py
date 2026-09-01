"""LangGraph 知识库检索工具（RAG tool 模式）.

借鉴参考项目把 RAG 封装成 @tool 的做法：由 Agent 决策何时检索知识库。
与 inject 模式互斥使用（RAG_MODE 配置），避免同一轮既注入知识又调用工具造成重复。
"""

from langchain_core.tools import tool

from app.rag.rag_service import rag_service


@tool
async def knowledge_search(query: str) -> str:
    """检索就业规划知识库, 返回与查询最相关的知识条目及来源.

    当用户询问简历撰写、面试准备、行业与岗位选择、求职策略、职业路径等知识性问题时使用；
    闲聊、需要用户个人背景的问题无需调用本工具。
    """
    context = await rag_service.format_context(query)
    if not context:
        return "未在知识库中检索到相关内容，请基于自身知识回答并说明该部分信息仅供参考。"
    return context
