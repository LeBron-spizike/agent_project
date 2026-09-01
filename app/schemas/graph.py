"""图状态相关 schema."""

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class GraphState(BaseModel):
    """LangGraph 智能体/工作流的状态定义."""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="会话中的消息"
    )
    long_term_memory: str = Field(default="", description="会话相关的长期记忆")
    knowledge: str = Field(default="", description="本轮检索到的 RAG 知识库上下文")
    knowledge_sources: list[str] = Field(default_factory=list, description="本轮命中的知识库来源文件名")
    profile: str = Field(default="", description="用户求职画像摘要（非空时注入系统提示词）")
    mode: str = Field(default="career", description="人设模式：career/resume/interview")
