"""前端状态与会话流程：session_state 初始化、会话切换、消息发送与回复."""

from datetime import datetime

import streamlit as st

from api import (
    ChatStreamError,
    analyze_file,
    create_session,
    extract_error,
    get_sessions,
    load_history,
    rename_session,
    stream_chat,
)

_UI_STATE_VERSION = 2


def init_state() -> None:
    """初始化 st.session_state 默认值（已存在则不覆盖）."""
    defaults = {
        "token": "",
        "session_id": "",
        "logged_in": False,
        "messages": [],
        "sessions": [],
        "sidebar_collapsed": False,
        "pending_reply": False,
        "email": "user@example.com",
        "username": "orson",
        # 当前视图：chat=问答页 / profile=求职画像 / knowledge=知识库管理
        "active_view": "chat",
        # 当前人设模式：career=职业顾问 / resume=简历评审 / interview=面试官
        "mode": "career",
        # 正在重命名的会话 ID 与行内输入值（为空表示未处于重命名状态）
        "renaming_session": "",
        "rename_value": "",
        # 文件上传控件 key 的版本号：发送后 +1 即让控件以新 key 重建（值自动清空）。
        # 新 Streamlit 不允许直接给控件赋值清空，只能用"换 key 重建"方式重置。
        "_uploader_epoch": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # 打开的旧标签页热更新到新版界面时，清除旧侧边栏状态，避免布局状态冲突。
    if st.session_state.get("_ui_state_version") != _UI_STATE_VERSION:
        st.session_state.sidebar_collapsed = False
        st.session_state._ui_state_version = _UI_STATE_VERSION


def toggle_sidebar() -> None:
    """切换侧边栏折叠状态；作为按钮 on_click 回调执行."""
    st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed


def refresh_sessions() -> tuple[bool, object]:
    """从后端刷新会话列表到 session_state."""
    status, data = get_sessions(st.session_state.token)
    if status == 200:
        st.session_state.sessions = data
        return True, data
    return False, data


def switch_session(session_id: str) -> tuple[bool, object]:
    """切换到指定会话并加载其历史消息."""
    status, data = load_history(st.session_state.token, session_id)
    if status == 200:
        st.session_state.session_id = session_id
        st.session_state.messages = data.get("messages", [])
        st.session_state.pending_reply = False
        # 切换会话时退出可能残留的重命名编辑态
        st.session_state.renaming_session = ""
        return True, data
    return False, data


def enter_chat() -> None:
    """登录/注册后：优先复用最近会话，没有则新建，让用户直接进入聊天."""
    try:
        ok, sessions = get_sessions(st.session_state.token)
        if ok and sessions:
            st.session_state.sessions = sessions
            latest = sessions[-1]  # 后端按 created_at 升序，末尾为最近会话
            if switch_session(latest["session_id"])[0]:
                return
        status, data = create_session(st.session_state.token)
        if status == 200:
            st.session_state.session_id = data.get("session_id", "")
            st.session_state.messages = []
            refresh_sessions()
    except Exception:  # noqa: BLE001
        st.session_state.session_id = ""
        st.session_state.messages = []


def group_sessions(sessions: list[dict]) -> tuple[list[dict], list[dict]]:
    """按创建时间分组：今天 / 更早（各组内新→旧）。"""
    today, earlier = [], []
    now = datetime.now().date()
    for s in sessions:
        created = s.get("created_at")
        date = None
        if created:
            try:
                date = datetime.fromisoformat(str(created).replace("Z", "+00:00")).date()
            except ValueError:
                date = None
        (today if date == now else earlier).append(s)
    today.reverse()
    earlier.reverse()
    return today, earlier


def get_session_label(session: dict) -> str:
    """返回会话标题，未命名时回退为"新聊天"."""
    name = session.get("name") or "新聊天"
    return name


def process_prompt(user_input: str, file=None) -> None:
    """把用户消息写入状态并立即重渲染.

    重渲染后快捷提问按钮随之消失；实际的后端调用由 handle_pending_reply
    在消息流下方以全宽"思考中"气泡完成，避免回答只占局部区域。
    attached file 不为 None 时本轮走文件分析接口。
    """
    display_content = user_input
    if file is not None:
        display_content = f"📎 请分析我上传的文件《{file.name}》\n{user_input}"
    st.session_state.messages.append({"role": "user", "content": display_content})
    st.session_state.pending_question = user_input
    st.session_state.pending_file = file
    st.session_state.pending_reply = True
    st.rerun()


def _latest_assistant_content(data: object) -> str:
    """从一次性接口的响应里取最后一条 assistant 文本."""
    response_messages = data.get("messages", []) if isinstance(data, dict) else []
    for msg in reversed(response_messages):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def _stream_assistant(question: str, sources_holder: dict):
    """把后端 SSE 事件流转成 st.write_stream 可消费的文本流，并捕获知识库来源.

    参数：
        question: 用户问题。
        sources_holder: {"sources": [...]} 可变容器，收到结束事件时写入本轮来源，
            供 st.write_stream 返回后读取。
    """
    for content, done, sources in stream_chat(
        st.session_state.token,
        st.session_state.session_id,
        question,
        mode=st.session_state.get("mode", "career"),
    ):
        if sources:
            sources_holder["sources"] = sources
        if content:
            yield content
        if done:
            return


def handle_pending_reply() -> None:
    """渲染待回复消息的思考气泡并调用后端生成回复.

    普通提问走 SSE 流式接口（st.write_stream 打字机渲染）；文件分析无流式接口，仍走一次性 analyze。
    """
    file = st.session_state.pop("pending_file", None)
    question = st.session_state.pop(
        "pending_question", st.session_state.messages[-1]["content"]
    )
    sources_holder: dict = {"sources": []}
    failure: str | None = None

    with st.chat_message("assistant", avatar="🧭"):
        if file is not None:
            with st.spinner("分析文件中，请稍候..."):
                status, data = analyze_file(
                    st.session_state.token,
                    st.session_state.session_id,
                    file,
                    question,
                    mode=st.session_state.get("mode", "career"),
                )
            if status == 200:
                assistant_content = _latest_assistant_content(data)
                knowledge_sources = data.get("knowledge_sources", []) or []
            else:
                failure = f"请求失败：{extract_error(data)}"
        else:
            try:
                assistant_content = st.write_stream(
                    _stream_assistant(question, sources_holder)
                )
                knowledge_sources = sources_holder["sources"]
            except ChatStreamError as e:
                failure = f"请求失败：{e}"
            except Exception as e:  # noqa: BLE001
                failure = f"流式请求异常：{e}"

    # 发送后推进上传控件的 key 版本，让控件以空值重建（等价于清空已选文件）
    st.session_state._uploader_epoch += 1
    st.session_state.pending_reply = False

    if failure:
        st.error(failure)
        return

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": assistant_content,
            # 本轮命中的 RAG 知识库来源，气泡下方渲染"知识库来源"徽章
            "knowledge_sources": knowledge_sources,
        }
    )
    # 会话首条消息触发后端自动命名，刷新侧边栏标题
    refresh_sessions()
    st.rerun()


def start_rename(session_id: str) -> None:
    """进入重命名态：记录会话 ID 并预填当前标题（作为按钮 on_click 回调执行）."""
    st.session_state.renaming_session = session_id
    st.session_state.rename_value = ""
    for session in st.session_state.sessions:
        if session.get("session_id") == session_id:
            st.session_state.rename_value = get_session_label(session)
            break


def commit_rename() -> None:
    """保存重命名：调用后端接口并刷新侧边栏（作为按钮 on_click 回调执行）."""
    session_id = st.session_state.get("renaming_session", "")
    new_name = (st.session_state.get("rename_value") or "").strip()
    st.session_state.renaming_session = ""
    if not session_id or not new_name:
        return
    status, data = rename_session(st.session_state.token, session_id, new_name)
    if status == 200:
        refresh_sessions()
        st.rerun()
    else:
        st.error(f"重命名失败：{extract_error(data)}")


def cancel_rename() -> None:
    """取消重命名：退出重命名编辑态（作为按钮 on_click 回调执行）."""
    st.session_state.renaming_session = ""
    st.session_state.rename_value = ""
