"""后端 HTTP 辅助：封装后端 API 的请求与错误解析."""

import json

import requests

API_BASE = "http://127.0.0.1:8000"


class ChatStreamError(Exception):
    """流式聊天返回 HTTP 错误时抛出的异常（携带后端可读的 detail）."""


def check_health() -> tuple[bool, object]:
    """探测后端健康状态，返回 (是否正常, 响应体)."""
    try:
        res = requests.get(f"{API_BASE}/health", timeout=5)
        return res.ok, res.json()
    except Exception as e:  # noqa: BLE001
        return False, {"error": str(e)}


def register(email: str, password: str, username: str) -> tuple[int, object]:
    """注册新用户，返回 (状态码, 响应体)."""
    payload = {"email": email, "password": password, "username": username}
    res = requests.post(
        f"{API_BASE}/api/v1/auth/register",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    return res.status_code, res.json()


def login(email: str, password: str) -> tuple[int, object]:
    """登录，返回 (状态码, 响应体)."""
    data = {"email": email, "password": password, "grant_type": "password"}
    res = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=15,
    )
    return res.status_code, res.json()


def create_session(token: str) -> tuple[int, object]:
    """为当前用户创建新会话，返回 (状态码, 响应体)."""
    res = requests.post(
        f"{API_BASE}/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return res.status_code, res.json()


def get_sessions(token: str) -> tuple[int, object]:
    """获取当前用户的所有会话，返回 (状态码, 响应体)."""
    res = requests.get(
        f"{API_BASE}/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return res.status_code, res.json()


def delete_session(token: str, session_id: str) -> tuple[int, object]:
    """删除指定会话，返回 (状态码, 响应体)."""
    res = requests.delete(
        f"{API_BASE}/api/v1/auth/session/{session_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return res.status_code, res.json()


def rename_session(token: str, session_id: str, name: str) -> tuple[int, object]:
    """重命名指定会话，返回 (状态码, 响应体)."""
    # 后端该接口用 Form 字段接收 name（非 JSON body）
    res = requests.patch(
        f"{API_BASE}/api/v1/auth/session/{session_id}/name",
        headers={"Authorization": f"Bearer {token}"},
        data={"name": name},
        timeout=15,
    )
    return res.status_code, res.json()


def load_history(token: str, session_id: str) -> tuple[int, object]:
    """加载指定会话的历史消息，返回 (状态码, 响应体)."""
    res = requests.get(
        f"{API_BASE}/api/v1/chatbot/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"session_id": session_id},
        timeout=30,
    )
    return res.status_code, res.json()


def stream_chat(token: str, session_id: str, user_content: str, mode: str = "career") -> tuple:
    """流式发送一条聊天消息（SSE），逐事件产出 (content, done, knowledge_sources).

    参数：
        token: 用户访问令牌。
        session_id: 聊天会话 ID。
        user_content: 用户消息内容。
        mode: 人设模式（career/resume/interview）。

    产出：
        (content, done, knowledge_sources)：当前分片内容、是否结束、本轮命中的知识库来源。

    抛出：
        ChatStreamError: 后端返回非 200 时抛出，携带可读错误信息。
        requests.RequestException: 网络层异常由调用方捕获展示。
    """
    payload = {
        "session_id": session_id,
        "messages": [{"role": "user", "content": user_content}],
        "mode": mode,
    }
    with requests.post(
        f"{API_BASE}/api/v1/chatbot/chat/stream",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        stream=True,
        # (连接, 单次读) 超时：流式响应允许 token 间有较长停顿，只要数据持续流动就不会超时
        timeout=(10, 300),
    ) as res:
        if res.status_code != 200:
            try:
                detail = extract_error(res.json())
            except Exception:  # noqa: BLE001
                detail = res.text[:300]
            raise ChatStreamError(detail)
        for line in res.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            event = json.loads(line[len("data: "):])
            yield (
                event.get("content", ""),
                event.get("done", False),
                event.get("knowledge_sources", []) or [],
            )


def analyze_file(token: str, session_id: str, file, question: str, mode: str = "career") -> tuple[int, object]:
    """上传文件让助手分析（PDF/TXT/MD/DOCX），返回 (状态码, 响应体).

    参数：
        file: Streamlit UploadedFile，含 name/getvalue()/type 属性。
        question: 用户对文件的问题。
        mode: 人设模式（简历诊断请传 resume）。
    """
    res = requests.post(
        f"{API_BASE}/api/v1/chatbot/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"session_id": session_id, "question": question, "mode": mode},
        files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")},
        timeout=180,
    )
    return res.status_code, res.json()


def get_profile(token: str) -> tuple[int, object]:
    """获取当前用户求职画像，返回 (状态码, 响应体)."""
    res = requests.get(
        f"{API_BASE}/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return res.status_code, res.json()


def update_profile(token: str, profile: dict) -> tuple[int, object]:
    """保存当前用户求职画像，返回 (状态码, 响应体)."""
    res = requests.put(
        f"{API_BASE}/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=profile,
        timeout=15,
    )
    return res.status_code, res.json()


def get_knowledge_files(token: str) -> tuple[int, object]:
    """获取知识库文件列表，返回 (状态码, 响应体)."""
    res = requests.get(
        f"{API_BASE}/api/v1/knowledge/files",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return res.status_code, res.json()


def ingest_knowledge(token: str) -> tuple[int, object]:
    """触发知识目录增量摄取，返回 (状态码, 响应体)."""
    res = requests.post(
        f"{API_BASE}/api/v1/knowledge/ingest",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={},
        timeout=180,
    )
    return res.status_code, res.json()


def upload_knowledge(token: str, file) -> tuple[int, object]:
    """上传知识文档并触发摄取，返回 (状态码, 响应体)."""
    res = requests.post(
        f"{API_BASE}/api/v1/knowledge/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")},
        timeout=180,
    )
    return res.status_code, res.json()


def delete_knowledge(token: str, file_id: str) -> tuple[int, object]:
    """删除知识文件，返回 (状态码, 响应体)."""
    res = requests.delete(
        f"{API_BASE}/api/v1/knowledge/files/{file_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    return res.status_code, res.json()


def extract_error(data: object) -> str:
    """把后端错误响应转成一句人能看懂的话。"""
    if not isinstance(data, dict):
        return str(data)[:300]
    detail = data.get("detail", data.get("message", ""))
    if isinstance(detail, list):  # pydantic 校验错误
        parts = []
        for item in detail:
            loc = ".".join(str(x) for x in item.get("loc", []) if x != "body")
            msg = item.get("msg", "")
            parts.append(f"{loc}: {msg}" if loc else str(msg))
        return "；".join(parts) if parts else str(detail)[:300]
    if isinstance(detail, str) and detail:
        return detail
    return str(data)[:300]
