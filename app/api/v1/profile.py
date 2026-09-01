"""用户求职画像 API 接口.

提供求职画像的读取与更新。更新后把画像摘要写入 mem0 长期记忆，
使后续对话既能通过 system prompt 结构化注入画像，也能按语义检索到画像信息。
"""

from fastapi import (
    APIRouter,
    Depends,
    Request,
)

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.user import User
from app.schemas.profile import UserProfile
from app.services.database import database_service
from app.services.memory import memory_service

router = APIRouter()


@router.get("/me/profile", response_model=UserProfile)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["profile"][0])
async def get_profile(
    request: Request,
    user: User = Depends(get_current_user),
) -> UserProfile:
    """获取当前用户的求职画像（未填写时返回空字段）."""
    profile = await database_service.get_user_profile(user.id)
    return UserProfile(**(profile or {}))


@router.put("/me/profile", response_model=UserProfile)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["profile"][0])
async def update_profile(
    request: Request,
    profile_data: UserProfile,
    user: User = Depends(get_current_user),
) -> UserProfile:
    """保存当前用户的求职画像，并写入 mem0 长期记忆供语义检索."""
    await database_service.update_user_profile(user.id, profile_data.model_dump())

    # 记忆通道：画像摘要作为 system 消息写入 mem0，后续对话按语义检索到
    summary = profile_data.to_summary()
    if summary:
        try:
            await memory_service.add(
                str(user.id),
                [{"role": "system", "content": f"用户的求职画像：{summary}"}],
                metadata={"source": "profile"},
            )
            logger.info("user_profile_memory_written", user_id=user.id)
        except Exception as e:
            # 记忆写入失败不影响画像保存
            logger.warning("user_profile_memory_write_failed", user_id=user.id, error=str(e))

    logger.info("user_profile_updated", user_id=user.id, has_content=bool(summary))
    return profile_data
