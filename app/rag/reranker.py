"""DashScope gte-rerank 二阶段精排客户端.

DashScope 的 rerank 走原生 text-rerank 端点（非 OpenAI 兼容 /v1），且当前依赖里没有
现成的 langchain DashScope reranker，故以轻量 httpx 客户端实现。
与 embeddings.py 的工厂模式一致：get_reranker() 返回实例，不产生网络 I/O；
Key 缺失 / 未启用 / 接口失败时由 rag_service.search() 捕获并降级为纯向量结果。
"""

import httpx

from app.core.config import settings

# DashScope 原生 text-rerank 端点（非 compatible-mode /v1）
_RERANK_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

# 单次 rerank 超时（秒）
_RERANK_TIMEOUT = 30


def get_reranker() -> "Reranker":
    """构建 DashScope rerank 客户端（不产生网络 I/O，调用发生在检索时）."""
    return Reranker()


class Reranker:
    """调用 DashScope text-rerank 接口给候选分块打分重排."""

    def __init__(self) -> None:
        """从配置读取 Key 与模型名."""
        self.api_key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
        self.model = settings.RAG_RERANK_MODEL

    @property
    def enabled(self) -> bool:
        """是否启用 rerank 精排（开关 + Key 就绪）；未就绪时调用方走纯向量结果."""
        return settings.RAG_RERANK_ENABLED and bool(self.api_key)

    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[int]:
        """对候选文档打分，返回按相关性降序的索引列表（长度 <= top_n）.

        参数：
            query: 用户查询。
            documents: 候选文档文本列表。
            top_n: 精排后保留的条数。

        返回：
            按相关性降序排列的候选索引列表。

        抛出：
            Exception: 网络 / 接口 / 解析错误，由调用方捕获并降级为纯向量结果。
        """
        if not self.enabled:
            raise RuntimeError("rerank not enabled or api key missing")

        payload = {
            "model": self.model,
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": top_n},
        }
        async with httpx.AsyncClient(timeout=_RERANK_TIMEOUT) as client:
            resp = await client.post(
                _RERANK_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # DashScope text-rerank 响应中 output.results 为索引与相关性得分的列表
        results = data.get("output", {}).get("results", [])
        ordered = sorted(results, key=lambda r: float(r.get("relevance_score", 0.0)), reverse=True)
        return [int(r["index"]) for r in ordered]
