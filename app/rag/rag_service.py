"""RAG 知识库编排服务：检索、上下文组装、摄取与文件管理.

借鉴参考项目 rag/rag_service.py 的"检索 → 上下文组装"思路，但不做独立的 LCEL 总结链——
主体框架保持本项目的 LangGraph Agent：检索结果通过 system prompt 的 {knowledge} 占位符注入
（inject 模式），或作为 knowledge_search 工具结果返回（tool 模式），由主 Agent 统一合成回答。
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import logger
from app.rag.document_loader import (
    compute_file_md5,
    list_knowledge_files,
    load_documents,
    split_documents,
)
from app.rag.embeddings import get_embeddings
from app.rag.reranker import get_reranker
from app.rag.vector_store import (
    delete_chunks_by_file,
    delete_file_record,
    ensure_tables,
    get_file_record,
    insert_chunks,
    list_file_records,
    match_chunks,
    upsert_file_record,
)
from app.schemas.rag import (
    IngestReport,
    KnowledgeFileInfo,
    KnowledgeFileList,
)


@dataclass
class RetrievedChunk:
    """单条检索结果."""

    content: str
    source: str
    score: float
    file_id: str
    section: str = ""


class RagService:
    """RAG 知识库服务（单例：rag_service）."""

    def __init__(self):
        """初始化 Embedding 与 Rerank 客户端（不产生网络 I/O，网络调用发生在检索/摄取时）."""
        self.embeddings = get_embeddings()
        self.reranker = get_reranker()

    @property
    def inject_mode_enabled(self) -> bool:
        """Inject 模式下每轮检索并注入 {knowledge} 占位符."""
        return settings.RAG_ENABLED and settings.RAG_MODE == "inject"

    async def initialize(self) -> None:
        """确保 pgvector 表和索引存在（应用启动时调用一次）."""
        ensure_tables()
        logger.info("rag_service_initialized")

    async def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        """向量检索知识库，返回按相似度降序的分块（开启 rerank 时经 gte-rerank 精排）.

        失败时降级返回空列表，不阻断对话（与 memory_service.search 同模式）。
        """
        if not settings.RAG_ENABLED:
            return []
        try:
            query_embedding = await self.embeddings.aembed_query(query)
            # rerank 开启时先向量粗召回更大候选窗口，精排后再裁剪回最终 k
            final_k = k if k is not None else settings.RAG_TOP_K
            fetch_k = settings.RAG_RERANK_CANDIDATES if self.reranker.enabled else final_k
            rows = match_chunks(
                query_embedding,
                fetch_k,
                settings.RAG_SCORE_THRESHOLD,
            )
            chunks = [
                RetrievedChunk(
                    content=str(row["content"]),
                    source=str(row["source"]),
                    score=float(row["score"]),
                    file_id=str(row["file_id"]),
                    section=str(row["metadata"].get("section", "")) if isinstance(row["metadata"], dict) else "",
                )
                for row in rows
            ]
            if self.reranker.enabled:
                chunks = await self._rerank(query, chunks, final_k)
            logger.info(
                "knowledge_search_completed",
                chunk_count=len(chunks),
                query_length=len(query),
                rerank=self.reranker.enabled,
            )
            return chunks
        except Exception as e:
            logger.error("knowledge_search_failed", error=str(e))
            return []

    async def _rerank(self, query: str, chunks: list[RetrievedChunk], k: int) -> list[RetrievedChunk]:
        """用 gte-rerank 对候选分块精排并裁剪到最终 k.

        rerank 失败时降级为原向量结果（裁剪到 k），不阻断检索。
        """
        if not chunks:
            return chunks
        try:
            documents = [chunk.content for chunk in chunks]
            ordered = await self.reranker.rerank(query, documents, k)
            reranked = [chunks[i] for i in ordered]
            logger.info(
                "knowledge_rerank_completed",
                candidates=len(chunks),
                kept=len(reranked),
                model=self.reranker.model,
            )
            return reranked
        except Exception as e:
            logger.warning("knowledge_rerank_failed_fallback_vector", error=str(e))
            return chunks[:k]

    async def format_context(self, query: str, k: int | None = None) -> str:
        """检索并组装为知识上下文文本；无命中时返回空字符串."""
        context, _ = await self.format_context_with_sources(query, k)
        return context

    async def format_context_with_sources(self, query: str, k: int | None = None) -> tuple[str, list[str]]:
        """检索并组装上下文文本，同时返回去重后的来源标签列表.

        返回：
            (格式化的知识上下文, 来源标签列表)；无命中时返回 ("", [])。
            来源标签为"文件名 · 章节标题"（md 文档带标题信息），供对话展示"知识库来源"使用。
        """
        chunks = await self.search(query, k)
        if not chunks:
            return "", []
        context = "\n\n".join(
            f"【参考资料{i}】（来源：{self._source_label(chunk)}）\n{chunk.content}"
            for i, chunk in enumerate(chunks, start=1)
        )
        sources: list[str] = []
        for chunk in chunks:
            label = self._source_label(chunk)
            if label not in sources:
                sources.append(label)
        return context, sources

    @staticmethod
    def _source_label(chunk: RetrievedChunk) -> str:
        """来源展示标签：md 文档带章节标题（"文件名 · 章节"），其余为文件名."""
        return f"{chunk.source} · {chunk.section}" if chunk.section else chunk.source

    async def ingest_directory(self, directory: str | Path | None = None, force: bool = False) -> IngestReport:
        """摄取知识目录下全部支持的文档（.md/.txt/.pdf），MD5 未变化的自动跳过.

        参数：
            directory: 知识目录，缺省使用 RAG_KNOWLEDGE_DIR。
            force: True 时忽略 MD5 强制重新分块摄取（分块逻辑变更后使用）。
        """
        root = Path(directory) if directory else Path(settings.RAG_KNOWLEDGE_DIR)
        files = list_knowledge_files(root)
        report = IngestReport(total_files=len(files))
        logger.info(
            "knowledge_ingest_started",
            root=str(root),
            total_files=report.total_files,
            force=force,
        )

        for file_path in files:
            file_id = PurePosixPath(file_path.relative_to(root)).as_posix()
            try:
                status, chunk_count = await self.ingest_file(file_path, root, force=force)
                if status == "ingested":
                    report.ingested_files.append(file_id)
                    report.total_chunks += chunk_count
                else:
                    report.skipped_files.append(file_id)
            except Exception as e:
                logger.exception("knowledge_file_ingest_failed", file_id=file_id, error=str(e))
                report.failed_files.append(file_id)
                report.failed_reasons[file_id] = str(e)

        logger.info(
            "knowledge_ingest_completed",
            total_files=report.total_files,
            ingested=len(report.ingested_files),
            skipped=len(report.skipped_files),
            failed=len(report.failed_files),
            total_chunks=report.total_chunks,
        )
        return report

    async def ingest_file(self, file_path: Path, root_dir: Path, force: bool = False) -> tuple[str, int]:
        """摄取单个文档：MD5 去重 → 分块 → 向量化 → 写库.

        返回：
            ("ingested", 分块数) 或 ("skipped", 0)；失败抛出异常由调用方处理。

        抛出：
            Exception: Embedding 或数据库写入失败时抛出，保证失败文件进入报告而非静默丢失。
        """
        file_id = PurePosixPath(file_path.relative_to(root_dir)).as_posix()
        md5 = compute_file_md5(file_path)

        record = get_file_record(file_id)
        if not force and record and record["md5"] == md5:
            logger.debug("knowledge_file_skipped_unchanged", file_id=file_id)
            return "skipped", 0

        documents = load_documents(file_path)
        if not documents:
            logger.warning("knowledge_file_empty_skipped", file_id=file_id)
            return "skipped", 0

        chunks = split_documents(documents)
        if not chunks:
            logger.warning("knowledge_file_no_chunks_skipped", file_id=file_id)
            return "skipped", 0

        # 批量向量化，控制单次请求大小
        contents = [chunk.page_content for chunk in chunks]
        embeddings: list[list[float]] = []
        for start in range(0, len(contents), settings.RAG_INGEST_BATCH_SIZE):
            batch = contents[start : start + settings.RAG_INGEST_BATCH_SIZE]
            embeddings.extend(await self._embed_with_retry(batch))

        # 先更新登记行（chunks 表外键引用它，首次摄取必须先有登记行），
        # 再删旧块、插新块；中途失败时 md5 不匹配会驱动下次摄取自动重摄
        upsert_file_record(file_id, file_path.name, md5, len(chunks))
        delete_chunks_by_file(file_id)
        insert_chunks(
            file_id,
            [
                (chunk.page_content, {**chunk.metadata, "chunk_index": index}, embedding)
                for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            ],
        )

        logger.info("knowledge_file_ingested", file_id=file_id, chunk_count=len(chunks))
        return "ingested", len(chunks)

    async def delete_file(self, file_id: str) -> bool:
        """下架知识文件：删除登记记录与分块，并尽力删除知识目录下的源文件.

        返回：
            bool: 登记记录存在并删除成功时返回 True（源文件删除失败仅告警，不影响）。
        """
        deleted = delete_file_record(file_id)
        if not deleted:
            return False
        # 上传写入的源文件一并删除，避免下次摄取"复活"已下架的文件
        try:
            source = Path(settings.RAG_KNOWLEDGE_DIR) / PurePosixPath(file_id)
            if source.is_file():
                source.unlink()
                logger.info("knowledge_source_file_deleted", file_id=file_id)
        except Exception as e:
            logger.warning("knowledge_source_file_delete_failed", file_id=file_id, error=str(e))
        logger.info("knowledge_file_deleted", file_id=file_id)
        return True

    async def list_files(self) -> KnowledgeFileList:
        """列出已摄取的知识文件."""
        rows = list_file_records()
        files = [
            KnowledgeFileInfo(
                id=str(row["id"]),
                name=str(row["name"]),
                md5=str(row["md5"]),
                chunk_count=int(row["chunk_count"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
        return KnowledgeFileList(total=len(files), files=files)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，瞬时失败按指数退避重试."""
        return await self.embeddings.aembed_documents(texts)


rag_service = RagService()
