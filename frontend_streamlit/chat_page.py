"""登录后的问答页面：侧边栏、顶栏、消息流、欢迎屏."""

import streamlit as st

from api import (
    create_session,
    delete_session,
)
from state import (
    cancel_rename,
    commit_rename,
    get_session_label,
    group_sessions,
    handle_pending_reply,
    process_prompt,
    refresh_sessions,
    start_rename,
    switch_session,
    toggle_sidebar,
)
from styles import inject_styles


def render_sidebar() -> None:
    """ChatGPT 风格左侧会话栏：会话列表独立滚动，用户区固定底部."""
    with st.sidebar:
        # 会话列表区（新聊天 + 历史分组）：占满剩余高度并独立滚动
        with st.container(key="session_list"):
            if st.button("＋ 新聊天", type="primary", use_container_width=True, key="new_chat"):
                status, data = create_session(st.session_state.token)
                if status == 200:
                    st.session_state.session_id = data.get("session_id", "")
                    st.session_state.messages = []
                    st.session_state.pending_reply = False
                    refresh_sessions()
                    st.rerun()
                else:
                    st.error("会话创建失败")

            today_sessions, earlier_sessions = group_sessions(st.session_state.sessions)

            if not st.session_state.sessions:
                st.caption("暂无历史会话，点击上方「新聊天」开始。")
            else:
                if today_sessions:
                    st.markdown('<p class="hist-group">今天</p>', unsafe_allow_html=True)
                    _render_session_list(today_sessions)
                if earlier_sessions:
                    st.markdown('<p class="hist-group">更早</p>', unsafe_allow_html=True)
                    _render_session_list(earlier_sessions)

        # 工具区：完善求职画像 / 知识库管理（固定在会话列表下方、用户区上方）
        with st.container(key="sidebar_tools"):
            if st.button("👤 完善求职画像", use_container_width=True, key="go_profile"):
                st.session_state.active_view = "profile"
                st.rerun()
            if st.button("📚 知识库管理", use_container_width=True, key="go_knowledge"):
                st.session_state.active_view = "knowledge"
                st.rerun()

        # 用户信息 + 退出登录：固定在侧边栏底部，不随列表滚动
        with st.container(key="sidebar_footer"):
            st.caption(f"👤 {st.session_state.email}")
            if st.button("退出登录", use_container_width=True, key="logout"):
                st.session_state.token = ""
                st.session_state.session_id = ""
                st.session_state.logged_in = False
                st.session_state.messages = []
                st.session_state.sessions = []
                st.session_state.pending_reply = False
                st.rerun()


def _render_session_list(sessions: list[dict]) -> None:
    """渲染一组会话：选中按钮 + 重命名按钮 + 删除按钮；重命名态显示行内输入."""
    for session in sessions:
        session_id = session.get("session_id", "")
        is_active = session_id == st.session_state.session_id
        label = get_session_label(session)
        is_renaming = session_id == st.session_state.get("renaming_session", "")

        if is_renaming:
            _render_rename_row(session_id)
            continue

        col_sel, col_ren, col_del = st.columns([4, 1, 1])

        with col_sel:
            if st.button(
                label,
                key=f"sel_{session_id}",
                use_container_width=True,
                disabled=is_active,
                help="切换到该对话",
            ):
                ok, _ = switch_session(session_id)
                if ok:
                    st.rerun()
                else:
                    st.error("历史消息加载失败")

        with col_ren:
            st.button(
                "✎",
                key=f"ren_{session_id}",
                use_container_width=True,
                help="重命名该对话",
                on_click=start_rename,
                args=(session_id,),
            )

        with col_del:
            if st.button("✕", key=f"del_{session_id}", help="删除该对话"):
                status, _ = delete_session(st.session_state.token, session_id)
                if status == 200:
                    if session_id == st.session_state.session_id:
                        st.session_state.session_id = ""
                        st.session_state.messages = []
                    refresh_sessions()
                    st.rerun()
                else:
                    st.error("删除失败")


def _render_rename_row(session_id: str) -> None:
    """渲染某会话的行内重命名：输入框 + 保存 / 取消."""
    col_input, col_save, col_cancel = st.columns([4, 1, 1])

    with col_input:
        st.text_input(
            "会话名称",
            key="rename_value",
            max_chars=60,
            label_visibility="collapsed",
            placeholder="输入新名称",
        )

    with col_save:
        st.button(
            "保存",
            key=f"save_{session_id}",
            use_container_width=True,
            on_click=commit_rename,
        )

    with col_cancel:
        st.button(
            "取消",
            key=f"cancel_{session_id}",
            use_container_width=True,
            on_click=cancel_rename,
        )


def render_topbar() -> None:
    """顶部栏：☰ 折叠侧边栏 + 品牌名。"""
    col_toggle, col_brand = st.columns([1, 11])
    with col_toggle:
        st.button(
            "☰",
            key="toggle_sidebar",
            help="折叠/展开侧边栏",
            on_click=toggle_sidebar,
        )
    with col_brand:
        st.markdown(
            '<div class="chat-topbar"><span class="eyebrow">EMPLOYMENT PLANNING</span>'
            '<span class="brand-name">就业规划智能问答系统</span></div>',
            unsafe_allow_html=True,
        )


def _render_mode_selector() -> None:
    """顶部人设模式选择器：职业顾问 / 简历评审 / 面试模拟."""
    mode_labels = {
        "career": "💼 职业顾问",
        "resume": "📄 简历评审",
        "interview": "🎤 面试模拟",
    }
    selected = st.segmented_control(
        "人设模式",
        options=list(mode_labels.keys()),
        format_func=lambda m: mode_labels[m],
        key="mode_control",
    )
    st.session_state.mode = selected or "career"


_MODE_PLACEHOLDERS = {
    "career": "向就业规划助手提问...",
    "resume": "上传简历或描述简历问题，我以评审专家角度分析...",
    "interview": "输入「开始面试」即开始模拟面试，随时可说「请评分」...",
}


def render_chat_page() -> None:
    """登录后的问答界面（ChatGPT 布局）。"""
    collapsed = st.session_state.sidebar_collapsed
    inject_styles("chat", collapsed=collapsed)

    render_sidebar()
    render_topbar()
    _render_mode_selector()

    if not st.session_state.session_id:
        st.info("请先在左侧点击「新聊天」开始。")
        return

    if not st.session_state.messages:
        _render_welcome()
    else:
        for message in st.session_state.messages:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            avatar = "👤" if role == "user" else "🧭"
            with st.chat_message(role, avatar=avatar):
                st.markdown(content)
                # RAG 知识库来源徽章：仅当轮回答携带来源时显示
                sources = message.get("knowledge_sources") or []
                if role == "assistant" and sources:
                    st.markdown(
                        f'<div class="knowledge-sources">📚 知识库来源：{"、".join(sources)}</div>',
                        unsafe_allow_html=True,
                    )

    # 有待回复的用户消息 → 以全宽气泡思考并请求后端
    if st.session_state.pending_reply:
        handle_pending_reply()

    # 附件分析：选择文件后提问即走文件分析接口（PDF/TXT/MD/DOCX，可选）。
    # key 带版本号：发送后 epoch+1 使控件重建为空，避免文件残留
    uploaded = st.file_uploader(
        "📎 附带文件让助手分析（PDF / TXT / MD / DOCX，可选）",
        type=["pdf", "txt", "md", "docx"],
        key=f"chat_file_{st.session_state._uploader_epoch}",
    )
    mode = st.session_state.get("mode", "career")
    user_input = st.chat_input(_MODE_PLACEHOLDERS.get(mode, _MODE_PLACEHOLDERS["career"]))
    if user_input:
        process_prompt(user_input, file=uploaded)


def _render_welcome() -> None:
    """空态欢迎屏：产品定位 + 按模式展示示例问题。"""
    mode = st.session_state.get("mode", "career")
    titles = {
        "career": ("就业规划智能问答系统", "职业定位 · 行业与岗位分析 · 求职策略 · 成长路径规划"),
        "resume": ("简历评审模式", "上传简历或描述简历的问题，获取评分、问题清单与逐条修改建议"),
        "interview": ("面试模拟模式", "我会扮演面试官按目标岗位提问并追问，随时可说「请评分」"),
    }
    title, sub = titles.get(mode, titles["career"])
    st.markdown(
        '<div class="welcome">'
        f'<div class="w-title">{title}</div>'
        f'<div class="w-sub">{sub}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    examples_by_mode = {
        "career": [
            "我学计算机科学，帮我规划一下职业路径",
            "我的专业适合哪些岗位？",
            "帮我写一份技术岗的求职策略",
        ],
        "resume": [
            "帮我分析简历的项目经历写法",
            "简历的 STAR 表达怎么改？",
            "这份简历的减分项有哪些？",
        ],
        "interview": [
            "开始面试（自我介绍）",
            "模拟一场产品岗面试",
            "给我出几道行为面试题",
        ],
    }
    examples = examples_by_mode.get(mode, examples_by_mode["career"])
    cols = st.columns(len(examples))
    for col, example in zip(cols, examples, strict=True):
        with col:
            if st.button(example, key=f"example_{example}", use_container_width=True):
                process_prompt(example)
