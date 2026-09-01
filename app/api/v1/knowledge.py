"""知识库管理 API 接口.

提供 RAG 知识库的摄取、上传、文件列表与下架能力。
所有接口均需登录（get_current_user）并带限流装饰器。
"""

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.rag.document_loader import SUPPORTED_EXTENSIONS
from app.rag.rag_service import rag_service
from app.schemas.rag import (
    IngestReport,
    IngestRequest,
    KnowledgeFileList,
)

router = APIRouter()


@router.post("/ingest", response_model=IngestReport)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["knowledge"][0])
async def ingest_knowledge(
    request: Request,
    ingest_request: IngestRequest,
    user: User = Depends(get_current_user),
) -> IngestReport:
    """触发知识目录增量摄取（MD5 未变化的文件自动跳过）.

    参数：
        request: FastAPI 请求对象，用于限流。
        ingest_request: 摄取请求，directory 缺省时使用 RAG_KNOWLEDGE_DIR。
        user: 从登录 token 解析出的当前用户。

    返回：
        IngestReport: 摄取报告（成功/跳过/失败文件与分块数）。
    """
    try:
        logger.info("knowledge_ingest_request_received", user_id=user.id, directory=ingest_request.directory)
        report = await rag_service.ingest_directory(ingest_request.directory)
        logger.info(
            "knowledge_ingest_request_completed",
            user_id=user.id,
            ingested=len(report.ingested_files),
            failed=len(report.failed_files),
        )
        return report
    except Exception as e:
        logger.exception("knowledge_ingest_request_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=IngestReport)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["knowledge"][0])
async def upload_knowledge(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> IngestReport:
    """上传知识文档到知识目录并触发摄取（MD5 未变化自动跳过）.

    参数：
        request: FastAPI 请求对象，用于限流。
        file: 上传的知识文档，支持 MD / TXT / PDF / DOCX。
        user: 从登录 token 解析出的当前用户。

    返回：
        IngestReport: 摄取报告（成功/跳过/失败文件与分块数）。
    """
    filename = file.filename or "未命名文件"
    try:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=422, detail="仅支持 MD / TXT / PDF / DOCX 文件")

        data = await file.read()
        if not data:
            raise HTTPException(status_code=422, detail="文件为空")

        knowledge_dir = Path(settings.RAG_KNOWLEDGE_DIR)
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        # 防止路径穿越：只保留文件名，落盘到知识目录根下
        dest = knowledge_dir / Path(filename).name
        dest.write_bytes(data)

        report = await rag_service.ingest_directory(knowledge_dir)
        logger.info(
            "knowledge_upload_request_completed",
            user_id=user.id,
            filename=filename,
            ingested=len(report.ingested_files),
            failed=len(report.failed_files),
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("knowledge_upload_request_failed", user_id=user.id, filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=KnowledgeFileList)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["knowledge"][0])
async def list_knowledge_files(
    request: Request,
    user: User = Depends(get_current_user),
) -> KnowledgeFileList:
    """列出已摄取的知识文件."""
    try:
        return await rag_service.list_files()
    except Exception as e:
        logger.exception("knowledge_files_list_failed", user_id=user.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id:path}")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["knowledge"][0])
async def delete_knowledge_file(
    request: Request,
    file_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """下架知识文件（删除登记记录与全部分块）.

    参数：
        file_id: 文件在知识目录下的相对路径（posix 风格），支持子目录。
    """
    try:
        deleted = await rag_service.delete_file(file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        return {"message": "Knowledge file deleted successfully", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("knowledge_file_delete_failed", user_id=user.id, file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
