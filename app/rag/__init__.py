"""RAG 知识库模块.

借鉴参考项目的 rag/ 分层结构（向量库 / 检索编排 / 评测），存储层复用项目现有的
PostgreSQL + pgvector（与 mem0 长期记忆同库），Embedding 复用 DashScope text-embedding-v4。

模块组成：
    embeddings.py       Embedding 客户端构建（DashScope 兼容模式）
    vector_store.py     pgvector 表管理、写入与相似度检索（原生 SQL）
    document_loader.py  知识文档加载、中文分块与文件 MD5
    rag_service.py      编排层：检索 / 上下文组装 / 摄取 / 文件管理
    ingest.py           命令行摄取入口：uv run python -m app.rag.ingest
"""

from app.rag.rag_service import rag_service

__all__ = ["rag_service"]
