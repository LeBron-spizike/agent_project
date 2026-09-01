"""聊天相关 schema."""

import re
from typing import (
    List,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.schemas.base import BaseResponse


class Message(BaseModel):
    """聊天接口的消息模型.

    Attributes:
        role: 消息发送方角色。
        content: 消息内容。
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="消息发送方角色")
    # 20000：文件分析会把提取的文件文本（上限 ANALYZE_MAX_CHARS）拼进消息，且分析类回答可能较长
    content: str = Field(..., description="消息内容", min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """校验消息内容.

        参数：
            v: 要校验的内容。

        返回：
            str: 校验后的内容。

        抛出：
            ValueError: 内容包含不允许的模式时抛出。
        """
        # 检查潜在恶意内容
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # 检查空字节
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """聊天接口请求模型.

    Attributes:
        session_id: Chat session ID owned by the authenticated user.
        messages: 会话中的消息列表。
        mode: 人设模式（career=职业顾问 / resume=简历评审 / interview=面试官）。
    """

    session_id: str = Field(..., description="聊天会话 ID")
    messages: List[Message] = Field(
        ...,
        description="会话中的消息列表",
        min_length=1,
    )
    mode: Literal["career", "resume", "interview"] = Field(
        default="career",
        description="人设模式：career=职业顾问（默认）/ resume=简历评审 / interview=面试官",
    )


class ChatResponse(BaseResponse):
    """聊天接口响应模型.

    Attributes:
        messages: 会话中的消息列表。
        knowledge_sources: 本轮回答命中的 RAG 知识库来源文件名（未命中时为空列表）。
    """

    messages: List[Message] = Field(..., description="会话中的消息列表")
    knowledge_sources: List[str] = Field(
        default_factory=list,
        description="本轮回答命中的知识库来源文件名，用于前端展示 RAG 引用来源",
    )


class StreamResponse(BaseResponse):
    """流式聊天接口响应模型.

    Attributes:
        content: 当前分片内容。
        done: Whether the stream is complete.
        knowledge_sources: 本轮回答命中的 RAG 知识库来源文件名（随结束事件返回，
            供前端展示"知识库来源"徽章）。
    """

    content: str = Field(default="", description="当前分片内容")
    done: bool = Field(default=False, description="流式响应是否完成")
    knowledge_sources: List[str] = Field(
        default_factory=list,
        description="本轮回答命中的知识库来源文件名，随流式结束事件返回",
    )


class SessionTitle(BaseModel):
    """会话标题生成的结构化输出 schema."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=60,
    )

    @field_validator("title")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = " ".join(v.split()).strip(" \"'`.,:;!?-")
        if not v:
            raise ValueError("empty title after normalization")
        return v
