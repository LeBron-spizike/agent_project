"""就业规划智能问答系统 —— Streamlit 前端入口.

未登录 -> 登录/注册页；登录成功 -> 自动进入最近会话 -> 问答界面；退出 -> 回到登录页。
登录后按 active_view 分发三个视图：
- chat       问答页（侧边栏 / 顶栏 / 消息流 / 欢迎屏）
- profile    求职画像页（onboarding 表单）
- knowledge  知识库管理页
页面与逻辑按模块拆分在同目录下：
- styles.py      设计系统 CSS 与样式注入
- api.py         后端 HTTP 辅助
- state.py       会话状态与消息流控制
- login_page.py  登录/注册页
- chat_page.py   问答页
- profile_page.py 求职画像页
- knowledge_page.py 知识库管理页
"""

import streamlit as st

from chat_page import render_chat_page
from knowledge_page import render_knowledge_page
from login_page import render_login_page
from profile_page import render_profile_page
from state import init_state

st.set_page_config(
    page_title="就业规划智能问答系统",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_state()

if st.session_state.logged_in:
    view = st.session_state.get("active_view", "chat")
    if view == "profile":
        render_profile_page()
    elif view == "knowledge":
        render_knowledge_page()
    else:
        render_chat_page()
else:
    render_login_page()
