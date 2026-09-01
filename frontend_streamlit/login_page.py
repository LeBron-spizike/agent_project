"""登录/注册页面渲染."""

import streamlit as st

from api import (
    API_BASE,
    check_health,
    extract_error,
    login,
    register,
)
from state import enter_chat
from styles import (
    BRAND_LOGO,
    CAREER_BG,
    inject_styles,
)


def render_login_page() -> None:
    """全屏登录/注册页（隐藏侧边栏）。"""
    inject_styles("login")
    st.markdown(CAREER_BG, unsafe_allow_html=True)

    st.markdown(
        f'<div class="login-brand">{BRAND_LOGO}<span class="eyebrow">EMPLOYMENT PLANNING</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<h1 class="login-title">规划属于你的职业路径。</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="login-sub">就业规划智能问答系统 —— 结合你的专业与背景，提供职业定位、'
        "行业与岗位分析、求职策略与成长路径建议。登录后立即开始对话。</p>",
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["登录", "注册"])

    with tab_login:
        email = st.text_input("邮箱", value=st.session_state.email, key="login_email")
        password = st.text_input("密码", value="Password123!", type="password", key="login_password")

        if st.button("进入对话", type="primary", use_container_width=True):
            status, data = login(email, password)
            if status == 200:
                st.session_state.token = data.get("access_token", "")
                st.session_state.logged_in = bool(st.session_state.token)
                st.session_state.email = email
                st.session_state.messages = []
                enter_chat()
                st.rerun()
            else:
                st.error(f"登录失败：{extract_error(data)}")

    with tab_register:
        reg_email = st.text_input("邮箱", value="", placeholder="you@example.com", key="reg_email")
        reg_username = st.text_input("用户名", value="", placeholder="如何称呼你", key="reg_username")
        reg_password = st.text_input("密码", value="", type="password", key="reg_password",
                                     help="至少 8 位，需包含大写字母、小写字母、数字与符号")

        if st.button("创建账户", type="primary", use_container_width=True):
            status, data = register(reg_email, reg_password, reg_username)
            if status == 200:
                token_data = data.get("token", {})
                st.session_state.token = token_data.get("access_token", "")
                st.session_state.logged_in = bool(st.session_state.token)
                st.session_state.email = reg_email
                st.session_state.messages = []
                enter_chat()
                st.rerun()
            else:
                st.error(f"注册失败：{extract_error(data)}")

    ok, health = check_health()
    status_text = "后端服务正常" if ok else "后端服务异常"
    status_color = "var(--ok)" if ok else "var(--err)"
    st.markdown(
        f'<p class="login-footer"><span class="dot" style="background:{status_color}"></span>'
        f"{status_text} · {API_BASE}</p>",
        unsafe_allow_html=True,
    )
