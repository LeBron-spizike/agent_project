"""RAG 知识库相关 schema."""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """知识库摄取请求."""

    directory: str | None = Field(default=None, description="要摄取的知识目录，缺省使用 RAG_KNOWLEDGE_DIR")


class KnowledgeFileInfo(BaseModel):
    """已摄取知识文件的登记信息."""

    id: str = Field(description="文件在知识目录下的相对路径（posix 风格）")
    name: str = Field(description="文件名")
    md5: str = Field(description="摄取时的内容 MD5")
    chunk_count: int = Field(description="分块数量")
    created_at: datetime = Field(description="首次摄取时间")


class KnowledgeFileList(BaseModel):
    """知识文件列表响应."""

    total: int
    files: list[KnowledgeFileInfo]


class IngestReport(BaseModel):
    """知识库摄取报告."""

    total_files: int = Field(description="扫描到的文件总数")
    ingested_files: list[str] = Field(default_factory=list, description="本次成功摄取的文件")
    skipped_files: list[str] = Field(default_factory=list, description="MD5 未变化而跳过的文件")
    failed_files: list[str] = Field(default_factory=list, description="摄取失败的文件")
    failed_reasons: dict[str, str] = Field(default_factory=dict, description="失败原因（文件 -> 错误信息）")
    total_chunks: int = Field(default=0, description="本次新增分块总数")
