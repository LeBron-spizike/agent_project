"""知识库管理页：查看文件列表、上传文档、触发摄取、删除文件."""

import streamlit as st

from api import (
    delete_knowledge,
    extract_error,
    get_knowledge_files,
    ingest_knowledge,
    upload_knowledge,
)
from styles import inject_styles


def _refresh_files() -> None:
    """刷新知识文件列表缓存到 session_state."""
    status, data = get_knowledge_files(st.session_state.token)
    st.session_state.knowledge_cache = (status, data)


def render_knowledge_page() -> None:
    """渲染知识库管理页."""
    inject_styles("chat")
    if "knowledge_cache" not in st.session_state:
        _refresh_files()

    st.markdown(
        '<div class="chat-topbar"><span class="eyebrow">KNOWLEDGE BASE</span>'
        '<span class="brand-name">知识库管理</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("知识库内容用于 RAG 检索注入，回答会标注来源。改动后点「立即增量摄取」生效。")

    col_back, _ = st.columns([1, 5])
    if col_back.button("← 返回聊天", use_container_width=True):
        st.session_state.active_view = "chat"
        st.rerun()

    # 上传
    st.markdown("#### 上传知识文档")
    uploaded = st.file_uploader(
        "选择文档（MD / TXT / PDF / DOCX），上传后自动摄取",
        type=["md", "txt", "pdf", "docx"],
        key="knowledge_upload",
    )
    if uploaded is not None:
        status, data = upload_knowledge(st.session_state.token, uploaded)
        if status == 200:
            ingested = len(data.get("ingested_files", [])) if isinstance(data, dict) else 0
            skipped = len(data.get("skipped_files", [])) if isinstance(data, dict) else 0
            st.success(f"上传并摄取完成：新增 {ingested} 个，跳过 {skipped} 个")
        else:
            st.error(f"上传失败：{extract_error(data)}")
        _refresh_files()
        st.rerun()

    col_ingest, _ = st.columns([1, 5])
    if col_ingest.button("立即增量摄取", use_container_width=True):
        status, data = ingest_knowledge(st.session_state.token)
        if status == 200:
            ingested = len(data.get("ingested_files", [])) if isinstance(data, dict) else 0
            skipped = len(data.get("skipped_files", [])) if isinstance(data, dict) else 0
            st.success(f"摄取完成：新增 {ingested} 个，跳过 {skipped} 个")
        else:
            st.error(f"摄取失败：{extract_error(data)}")
        _refresh_files()
        st.rerun()

    # 文件列表
    status, data = st.session_state.knowledge_cache
    files = data.get("files", []) if isinstance(data, dict) else []
    st.markdown(f"#### 已摄取文档（{len(files)}）")
    if not files:
        st.caption("暂无文件。上传文档，或把 .md/.txt/.pdf/.docx 放进 data/knowledge 目录后点「立即增量摄取」。")
    else:
        header = st.columns([4, 1, 2, 2, 1])
        header[0].markdown("**文件名**")
        header[1].markdown("**块数**")
        header[2].markdown("**摄取时间**")
        header[3].markdown("**MD5 前8位**")
        header[4].markdown("")
        for f in files:
            c1, c2, c3, c4, c5 = st.columns([4, 1, 2, 2, 1])
            c1.markdown(f"**{f['name']}**")
            c2.markdown(f"{f['chunk_count']}")
            c3.markdown(str(f.get("created_at", ""))[:10])
            c4.code(str(f.get("md5", ""))[:8])
            if c5.button("删", key=f"kdel_{f['id']}", help="删除该文件"):
                del_status, del_data = delete_knowledge(st.session_state.token, f["id"])
                if del_status == 200:
                    st.success(f"已删除 {f['name']}")
                else:
                    st.error(f"删除失败：{extract_error(del_data)}")
                _refresh_files()
                st.rerun()