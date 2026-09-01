"""智能体 prompt 加载模块."""

import os
from datetime import datetime
from typing import Optional

from app.core.config import settings

_PROMPTS_DIR = os.path.dirname(__file__)

# 模块加载时读取模板一次，避免每次请求都进行文件 I/O
# mode -> 模板文件：career=职业顾问（默认）、resume=简历评审、interview=面试官
_TEMPLATES: dict[str, str] = {}
for _mode, _file in (("career", "system.md"), ("resume", "system.resume.md"), ("interview", "system.interview.md")):
    with open(os.path.join(_PROMPTS_DIR, _file), "r") as _f:
        _TEMPLATES[_mode] = _f.read()

with open(os.path.join(_PROMPTS_DIR, "session_title.md"), "r") as _f:
    SESSION_TITLE_PROMPT = _f.read()


def load_system_prompt(username: Optional[str] = None, mode: str = "career", **kwargs):
    """从缓存模板加载系统 prompt.

    参数：
        username: 用户展示名称。
        mode: 人设模式（career=职业顾问 / resume=简历评审 / interview=面试官）。
        **kwargs: 模板占位符（long_term_memory / knowledge / profile 等）。

    返回：
        str: 渲染完成的系统 prompt。
    """
    user_context = f"# 用户\n你正在和 {username} 对话。\n" if username else ""
    # 未注入的占位符给空串默认值，保证模板可正常渲染
    kwargs.setdefault("knowledge", "")
    kwargs.setdefault("profile", "")
    template = _TEMPLATES.get(mode, _TEMPLATES["career"])
    return template.format(
        agent_name=settings.PROJECT_NAME + " Agent",
        current_date_and_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_context=user_context,
        **kwargs,
    )
