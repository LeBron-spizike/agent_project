"""RAG 知识库的 Embedding 客户端构建.

复用项目已有的 DashScope 兼容模式配置（与 mem0 长期记忆一致的 text-embedding-v4），
通过 langchain-openai 的 OpenAIEmbeddings 走 OpenAI 兼容接口。
"""

from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr

from app.core.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    """构建 DashScope 兼容模式的 Embedding 客户端.

    - 配置了 DASHSCOPE_API_KEY 时走 DashScope 兼容模式（与 mem0 长期记忆同一模型 text-embedding-v4）
    - check_embedding_ctx_length=False：跳过 tiktoken 分词（DashScope 模型 token 体系与 OpenAI 不同，
      且离线容器可能缺少 tiktoken 缓存，参考 app/utils/graph.py 的离线兜底教训）
    """
    api_key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
    return OpenAIEmbeddings(
        model=settings.RAG_EMBEDDING_MODEL,
        dimensions=settings.RAG_EMBEDDING_DIMS,
        api_key=SecretStr(api_key) if api_key else None,
        base_url=settings.DASHSCOPE_BASE_URL if settings.DASHSCOPE_API_KEY else None,
        check_embedding_ctx_length=False,
    )
