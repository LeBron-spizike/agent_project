"""前端样式：设计系统 Token、页面 CSS、背景装饰与样式注入."""

import streamlit as st

FONT_IMPORT = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
"""

BASE_CSS = """
:root {
  --ink: #0A0E1C;            /* 深墨蓝 · 页面底色 */
  --surface: #121A33;        /* 卡片/气泡 */
  --surface-2: #182246;      /* 次级表面 */
  --line: rgba(148, 163, 216, 0.14);
  --cyan: #7DD3FC;           /* 路径/里程碑 */
  --signal: #F6C453;         /* 信号琥珀 · 主操作 */
  --signal-strong: #FFD97A;
  --text: #E7ECFA;
  --muted: #94A0C4;
  --ok: #34D399;
  --err: #F87171;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--ink);
  color: var(--text);
  font-family: 'Inter', 'Space Grotesk', 'PingFang SC', 'Hiragino Sans GB',
               'Microsoft YaHei', 'Noto Sans SC', sans-serif;
}

[data-testid="stHeader"] { background: transparent; pointer-events: none; }
[data-testid="stToolbar"] { display: none; }

[data-testid="stMainBlockContainer"] {
  position: relative;
  z-index: 2;
  padding-top: 1.4rem;
  padding-bottom: 2rem;
}

/* 通用 widget 文案 */
[data-testid="stWidgetLabel"] p { color: var(--muted); font-size: 0.9rem; font-weight: 500; }
.stMarkdown p, .stMarkdown li { color: var(--text); }

/* 文字输入 */
[data-testid="stTextInput"] input {
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--line);
  border-radius: 12px;
  color: var(--text);
  padding: 0.8rem 1rem;
  font-size: 1rem;
  caret-color: var(--signal);
}
[data-testid="stTextInput"] input:focus {
  border-color: rgba(246, 196, 83, 0.6);
  box-shadow: 0 0 0 3px rgba(246, 196, 83, 0.14);
}
[data-testid="stTextInput"] input::placeholder { color: #5C688F; }

/* 按钮 */
[data-testid="stButton"] button {
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--text);
  font-weight: 500;
  padding: 0.6rem 1rem;
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
[data-testid="stButton"] button:hover { border-color: rgba(125, 211, 252, 0.4); }
[data-testid="stButton"] button[kind="primary"] {
  background: linear-gradient(135deg, #F6C453 0%, #E9A93B 100%);
  border: none;
  color: #171102;
}
[data-testid="stButton"] button[kind="primary"]:hover {
  background: linear-gradient(135deg, #FFD97A 0%, #F6C453 100%);
  box-shadow: 0 8px 24px rgba(246, 196, 83, 0.25);
  transform: translateY(-1px);
}

/* 登录/注册 Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 0.5rem; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent;
  border: none;
  color: var(--muted);
  font-weight: 500;
  padding: 0.6rem 1.2rem;
  border-radius: 10px 10px 0 0;
}
[data-testid="stTabs"] [aria-selected="true"] { color: var(--signal); border-bottom: 2px solid var(--signal); }

/* 提示框 */
[data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--line); }

/* 侧边栏 */
[data-testid="stSidebar"] {
  background: rgba(10, 14, 28, 0.88);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown p { color: var(--text); }

/* JSON 面板低调化 */
[data-testid="stJson"] { background: transparent; }
"""

LOGIN_CSS = """
[data-testid="stMainBlockContainer"] { max-width: 460px; }

/* 品牌区 */
.login-brand { display: flex; align-items: center; gap: 0.75rem; margin: 1.2rem 0 2rem; }
[data-testid="stMarkdownContainer"] .eyebrow {
  font-family: 'IBM Plex Mono', 'PingFang SC', monospace;
  font-size: 0.78rem;
  letter-spacing: 0.35em;
  color: var(--muted);
  text-transform: uppercase;
}
[data-testid="stMarkdownContainer"] h1.login-title {
  font-family: 'Space Grotesk', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 2.1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.3;
  margin: 0.2rem 0 0.9rem;
  color: var(--text);
}
[data-testid="stMarkdownContainer"] .login-sub {
  color: var(--muted);
  font-size: 0.95rem;
  line-height: 1.7;
  margin-bottom: 2rem;
}

/* 页脚状态 */
[data-testid="stMarkdownContainer"] .login-footer {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 0.75rem;
  color: var(--muted);
  letter-spacing: 0.05em;
  margin-top: 2.4rem;
  text-align: center;
}
.login-footer .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.45rem; }
"""

CHAT_CSS = """
/* 聊天主区：全宽自适应，避免左右留白与不对齐 */
[data-testid="stMainBlockContainer"] {
  max-width: 100%;
  padding: 0.6rem 1.5rem 2rem;
}

.chat-topbar { display: flex; align-items: center; gap: 0.8rem; margin-bottom: 0.6rem; }
[data-testid="stMarkdownContainer"] .chat-topbar .eyebrow {
  font-family: 'IBM Plex Mono', 'PingFang SC', monospace;
  font-size: 0.72rem; letter-spacing: 0.3em; color: var(--muted); text-transform: uppercase;
}
.chat-topbar .brand-name { color: var(--text); font-weight: 600; font-size: 1rem; }

/* 侧边栏：会话列表独立滚动，用户区固定底部，不随滚动条下滑 */
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
  padding-bottom: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div,
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
/* 会话列表容器：占满剩余高度并独立滚动 */
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(.st-key-session_list) {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
[data-testid="stSidebar"] .st-key-session_list {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
/* 用户信息/退出登录：固定底部 */
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(.st-key-sidebar_footer) {
  flex: 0 0 auto;
}
[data-testid="stSidebar"] .st-key-sidebar_footer {
  flex: 0 0 auto;
  padding-top: 0.7rem;
  border-top: 1px solid var(--line);
  background: var(--ink);
}
[data-testid="stSidebar"] .st-key-sidebar_footer .stCaptionContainer p { color: var(--muted); }

/* 侧边栏工具区（完善求职画像 / 知识库管理入口）：会话列表下方、用户区上方固定 */
[data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(.st-key-sidebar_tools) {
  flex: 0 0 auto;
}
[data-testid="stSidebar"] .st-key-sidebar_tools {
  flex: 0 0 auto;
  padding: 0.55rem 0 0.7rem;
  border-top: 1px solid var(--line);
}
[data-testid="stSidebar"] .st-key-sidebar_tools [data-testid="stButton"] button {
  justify-content: flex-start;
  font-size: 0.85rem;
  padding: 0.45rem 0.7rem;
}

/* 隐藏 Streamlit 原生折叠按钮，避免与自定义 ☰ 状态互相打架 */
[data-testid="stSidebarCollapseButton"] { display: none !important; }

/* 侧边栏会话按钮：超长标题省略号截断 */
[data-testid="stSidebar"] [data-testid="stButton"] button p {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}
[data-testid="stSidebar"] [class*="st-key-del_"] button p {
  min-width: 1em;
  overflow: visible;
  text-overflow: clip;
}

/* 重命名图标按钮（✎/保存/取消）与删除键一致：图标不被省略号规则误伤 */
[data-testid="stSidebar"] [class*="st-key-ren_"] button,
[data-testid="stSidebar"] [class*="st-key-save_"] button,
[data-testid="stSidebar"] [class*="st-key-cancel_"] button {
  padding: 0.4rem 0.35rem;
}
[data-testid="stSidebar"] [class*="st-key-ren_"] button p,
[data-testid="stSidebar"] [class*="st-key-save_"] button p,
[data-testid="stSidebar"] [class*="st-key-cancel_"] button p {
  min-width: 1em;
  overflow: visible;
  text-overflow: clip;
}
/* 重命名行输入框：紧凑，避免挤占侧边栏 */
[data-testid="stSidebar"] [class*="st-key-rename_value"] input {
  font-size: 0.85rem;
  padding: 0.45rem 0.6rem;
}

/* 侧边栏历史分组标题 */
[data-testid="stMarkdownContainer"] .hist-group {
  font-size: 0.72rem; letter-spacing: 0.12em; color: var(--muted);
  margin: 0.6rem 0 0.2rem; text-transform: uppercase;
}

/* 聊天消息：全宽气泡，用户靠右、助手靠左 */
[data-testid="stChatMessage"] {
  width: 100%;
  max-width: none;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 0.6rem 1.1rem;
  margin-bottom: 0.4rem;
}
[data-testid="stChatMessage"] p { color: var(--text); }
/* RAG 知识库来源徽章：回答气泡底部的小字标注 */
[data-testid="stMarkdownContainer"] .knowledge-sources {
  font-size: 0.72rem;
  color: var(--muted);
  background: var(--surface-2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.25rem 0.6rem;
  margin-top: 0.45rem;
  display: inline-block;
}
/* 用户消息靠右，头像在右 */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--surface-2);
  flex-direction: row-reverse;
}
/* 底部输入区：覆盖 Streamlit 默认 80px 内边距，和消息区完全对齐 */
[data-testid="stBottomBlockContainer"] {
  background: var(--ink) !important;
  padding-left: 1.5rem !important;
  padding-right: 1.5rem !important;
}
[data-testid="stChatInput"] {
  width: 100%;
  max-width: none;
  margin: 0;
}
[data-testid="stChatInput"] textarea {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  color: var(--text);
  padding: 0.8rem 1rem;
}
[data-testid="stChatInput"] textarea:focus {
  border-color: rgba(246, 196, 83, 0.5);
  box-shadow: 0 0 0 3px rgba(246, 196, 83, 0.12);
}

/* 欢迎空态 */
.welcome { text-align: center; padding-top: 3rem; }
[data-testid="stMarkdownContainer"] .welcome .w-title {
  font-family: 'Space Grotesk', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 1.8rem; font-weight: 700; margin: 1rem 0 0.5rem; color: var(--text);
}
[data-testid="stMarkdownContainer"] .welcome .w-sub { color: var(--muted); margin-bottom: 1.8rem; }
"""

CAREER_BG = """
<style>
  .career-path { position: fixed; inset: 0; z-index: 1; pointer-events: none; opacity: 0.9; }
  .career-path path.main { fill: none; stroke: url(#pathGrad); stroke-width: 2;
                            stroke-dasharray: 4 7; stroke-linecap: round; }
  .milestone { fill: #7DD3FC; opacity: 0.7; }
  .goal { animation: goalGlow 3.2s ease-in-out infinite; }
  @keyframes goalGlow { 0%, 100% { opacity: 1; } 50% { opacity: 0.45; } }
  .travel { offset-path: path('M -20 780 C 240 740, 320 700, 520 640 S 900 460, 1180 300 S 1380 160, 1460 110');
            animation: travel 12s linear infinite; }
  @keyframes travel { 0% { offset-distance: 0%; opacity: 0; }
                      10% { opacity: 1; } 90% { opacity: 1; }
                      100% { offset-distance: 100%; opacity: 0; } }
  .vignette { position: fixed; inset: 0; z-index: 1; pointer-events: none;
    background: radial-gradient(120% 90% at 50% 0%, transparent 45%, rgba(4, 7, 15, 0.6) 100%); }
  @media (prefers-reduced-motion: reduce) {
    .travel, .goal { animation: none; }
  }
</style>
<svg class="career-path" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs>
    <linearGradient id="pathGrad" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="#7DD3FC" stop-opacity="0"/>
      <stop offset="0.6" stop-color="#7DD3FC" stop-opacity="0.35"/>
      <stop offset="1" stop-color="#F6C453" stop-opacity="0.55"/>
    </linearGradient>
  </defs>
  <path class="main" d="M -20 780 C 240 740, 320 700, 520 640 S 900 460, 1180 300 S 1380 160, 1460 110"/>
  <circle class="milestone" cx="520" cy="640" r="3.4"/>
  <circle class="milestone" cx="820" cy="500" r="3"/>
  <circle class="milestone" cx="1180" cy="300" r="3.6"/>
  <circle class="milestone" cx="1460" cy="110" r="5" fill="#F6C453"/>
  <circle class="goal" cx="1460" cy="110" r="9" fill="#F6C453" opacity="0.25"/>
  <circle class="travel" cx="1460" cy="110" r="4.5" fill="#F6C453"/>
</svg>
<div class="vignette"></div>
"""

BRAND_LOGO = """
<svg width="38" height="38" viewBox="0 0 38 38" fill="none" aria-hidden="true">
  <path d="M3 31 C 11 29, 15 23, 21 19 S 30 10, 34 7" stroke="#7DD3FC" stroke-width="2"
        stroke-linecap="round" stroke-dasharray="3 3" opacity="0.75"/>
  <circle cx="3" cy="31" r="2.8" fill="#7DD3FC"/>
  <circle cx="21" cy="19" r="2.8" fill="#7DD3FC"/>
  <circle cx="34" cy="7" r="3.2" fill="#F6C453"/>
  <circle cx="34" cy="7" r="6.5" stroke="#F6C453" stroke-opacity="0.35" fill="none"/>
</svg>
"""


def inject_styles(scope: str, collapsed: bool = False) -> None:
    """按页面作用域注入样式；聊天页折叠侧边栏时收窄 stSidebar 为 0 宽."""
    css = FONT_IMPORT + BASE_CSS
    if scope == "login":
        css += LOGIN_CSS
    else:
        css += CHAT_CSS
        if collapsed:
            # 用 width:0 收窄而非 display:none：保留元素在 DOM/布局树，
            # 避免 Streamlit 前端测量到"侧边栏不存在"后丢失布局，导致重新展开失效
            css += """
[data-testid="stSidebar"] {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  flex-basis: 0 !important;
  overflow: hidden !important;
  border-right: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  display: none !important;
}
"""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
