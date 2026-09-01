"""pgvector 知识库向量存储."""

import json
from typing import Any
from typing import Sequence

from sqlalchemy import text
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import logger
from app.services.database import database_service

_EMBEDDING_INDEX_NAME = "knowledge_chunks_embedding_idx"


def _to_pgvector_literal(embedding: Sequence[float]) -> str:
    """把 embedding 列表转为 pgvector 字符串字面量（如 "[0.1,0.2]"）.

    psycopg 不能直接绑定 Python list 为 vector 类型，统一转为字符串后用 ::vector 显式转换。
    """
    return "[" + ",".join(f"{value:.7f}" for value in embedding) + "]"


def ensure_tables() -> None:
    """确保 pgvector 扩展、知识库表和向量索引存在（幂等）.

    注意：embedding 维度在建表时固定；之后修改 RAG_EMBEDDING_DIMS 需要删表重建。
    """
    dims = int(settings.RAG_EMBEDDING_DIMS)
    with Session(database_service.engine) as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS knowledge_files (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL DEFAULT '',
                    md5 TEXT NOT NULL DEFAULT '',
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        session.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    file_id TEXT NOT NULL REFERENCES knowledge_files(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({dims})
                )
                """
            )
        )
        session.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS {_EMBEDDING_INDEX_NAME}
                    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
                """
            )
        )
        session.commit()
    logger.info("rag_vector_store_tables_ready", embedding_dims=dims)


def get_file_record(file_id: str) -> dict[str, Any] | None:
    """按 id 查询已摄取文件记录，未摄取过时返回 None."""
    with Session(database_service.engine) as session:
        row = session.execute(
            text("SELECT id, name, md5, chunk_count, created_at FROM knowledge_files WHERE id = :file_id"),
            {"file_id": file_id},
        ).mappings().first()
        return dict(row) if row else None


def upsert_file_record(file_id: str, name: str, md5: str, chunk_count: int) -> None:
    """新增或更新文件登记记录（摄取完成时调用）."""
    with Session(database_service.engine) as session:
        session.execute(
            text(
                """
                INSERT INTO knowledge_files (id, name, md5, chunk_count)
                VALUES (:id, :name, :md5, :chunk_count)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    md5 = EXCLUDED.md5,
                    chunk_count = EXCLUDED.chunk_count
                """
            ),
            {"id": file_id, "name": name, "md5": md5, "chunk_count": chunk_count},
        )
        session.commit()


def delete_file_record(file_id: str) -> bool:
    """删除文件登记记录，chunks 通过 ON DELETE CASCADE 级联删除；文件不存在返回 False."""
    with Session(database_service.engine) as session:
        result = session.execute(
            text("DELETE FROM knowledge_files WHERE id = :file_id"),
            {"file_id": file_id},
        )
        session.commit()
        return bool(result.rowcount > 0)  # pyright: ignore[reportAttributeAccessIssue]


def list_file_records() -> list[dict[str, Any]]:
    """列出全部已摄取文件记录，按首次摄取时间排序."""
    with Session(database_service.engine) as session:
        rows = session.execute(
            text("SELECT id, name, md5, chunk_count, created_at FROM knowledge_files ORDER BY created_at, id")
        ).mappings().all()
        return [dict(row) for row in rows]


def delete_chunks_by_file(file_id: str) -> int:
    """删除指定文件的全部分块（保留登记记录，供同文件内容变更后重摄前清理）."""
    with Session(database_service.engine) as session:
        result = session.execute(
            text("DELETE FROM knowledge_chunks WHERE file_id = :file_id"),
            {"file_id": file_id},
        )
        session.commit()
        return int(result.rowcount)  # pyright: ignore[reportAttributeAccessIssue]


def insert_chunks(file_id: str, chunks: Sequence[tuple[str, dict[str, Any], Sequence[float]]]) -> None:
    """批量写入分块（content + metadata + embedding）.

    参数：
        chunks: (content, metadata, embedding) 三元组列表。
    """
    if not chunks:
        return
    params = [
        {
            "file_id": file_id,
            "content": content,
            "metadata_json": json.dumps(metadata, ensure_ascii=False),
            "embedding_literal": _to_pgvector_literal(embedding),
        }
        for content, metadata, embedding in chunks
    ]
    with Session(database_service.engine) as session:
        session.execute(
            text(
                """
                INSERT INTO knowledge_chunks (file_id, content, metadata, embedding)
                VALUES (:file_id, :content, CAST(:metadata_json AS JSONB), (:embedding_literal)::vector)
                """
            ),
            params,
        )
        session.commit()


def match_chunks(
    query_embedding: Sequence[float],
    k: int,
    score_threshold: float,
) -> list[dict[str, Any]]:
    """按余弦相似度检索最相关的 k 个分块，按 score 降序返回."""
    embedding_literal = _to_pgvector_literal(query_embedding)
    with Session(database_service.engine) as session:
        rows = session.execute(
            text(
                """
                SELECT c.id, c.file_id, f.name AS source, c.content, c.metadata,
                       1 - (c.embedding <=> (:embedding_literal)::vector) AS score
                FROM knowledge_chunks c
                JOIN knowledge_files f ON f.id = c.file_id
                WHERE (:score_threshold <= 0 OR 1 - (c.embedding <=> (:embedding_literal)::vector) >= :score_threshold)
                ORDER BY c.embedding <=> (:embedding_literal)::vector
                LIMIT :k
                """
            ),
            {"embedding_literal": embedding_literal, "score_threshold": score_threshold, "k": k},
        ).mappings().all()
        return [dict(row) for row in rows]


