"""求职画像页：填写 / 编辑用户求职画像，保存后写入后端（含 mem0 记忆）."""

import streamlit as st

from api import (
    extract_error,
    get_profile,
    update_profile,
)
from styles import (
    BRAND_LOGO,
    inject_styles,
)

_EDUCATION_OPTIONS = ["", "高中及以下", "大专", "本科", "硕士", "博士"]
_EXPERIENCE_OPTIONS = ["", "应届生", "1 年以内", "1-3 年", "3-5 年", "5-10 年", "10 年以上"]
_STATUS_OPTIONS = ["", "在校学生", "应届生待就业", "在职找工作", "离职待业"]


def _index(options: list[str], value: str) -> int:
    """返回 value 在 options 中的下标（无匹配时 0，映射为"请选择"空项）."""
    return options.index(value) if value in options else 0


def _load_profile() -> None:
    """从后端拉取当前画像并缓存到 session_state（避免每次重渲染重复请求）."""
    if "profile_cache" not in st.session_state:
        status, data = get_profile(st.session_state.token)
        st.session_state.profile_cache = data if status == 200 and isinstance(data, dict) else {}


def render_profile_page() -> None:
    """渲染求职画像填写/编辑页."""
    inject_styles("login")
    _load_profile()
    p: dict = st.session_state.profile_cache

    st.markdown(
        f'<div class="login-brand">{BRAND_LOGO}<span class="eyebrow">CAREER PROFILE</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<h1 class="login-title">完善求职画像</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="login-sub">填写后，你的回答会结合这些背景给出更针对性的职业建议（可随时修改）。</p>',
        unsafe_allow_html=True,
    )

    with st.form("profile_form"):
        job_direction = st.text_input(
            "求职方向", value=p.get("job_direction", ""), placeholder="如：互联网产品经理"
        )
        col_left, col_right = st.columns(2)
        with col_left:
            education = st.selectbox(
                "最高学历",
                _EDUCATION_OPTIONS,
                index=_index(_EDUCATION_OPTIONS, p.get("education", "")),
            )
            work_experience = st.selectbox(
                "工作年限",
                _EXPERIENCE_OPTIONS,
                index=_index(_EXPERIENCE_OPTIONS, p.get("work_experience", "")),
            )
            current_status = st.selectbox(
                "求职状态",
                _STATUS_OPTIONS,
                index=_index(_STATUS_OPTIONS, p.get("current_status", "")),
            )
        with col_right:
            major = st.text_input("专业", value=p.get("major", ""))
            target_position = st.text_input("目标岗位", value=p.get("target_position", ""))
            target_city = st.text_input("目标城市", value=p.get("target_city", ""))

        target_salary = st.text_input(
            "期望薪资", value=p.get("target_salary", ""), placeholder="如：15-20K"
        )
        key_skills = st.text_input(
            "核心技能",
            value=p.get("key_skills", ""),
            placeholder="逗号分隔，如：数据分析、SQL、沟通协调",
        )
        career_goal = st.text_area(
            "职业目标",
            value=p.get("career_goal", ""),
            placeholder="如：3 年内成长为独当一面的产品经理",
            height=80,
        )

        submitted = st.form_submit_button("保存画像", type="primary", use_container_width=True)

    col_back, _ = st.columns([1, 3])
    if col_back.button("← 返回聊天", use_container_width=True):
        st.session_state.active_view = "chat"
        st.rerun()

    if submitted:
        profile = {
            "job_direction": job_direction.strip(),
            "education": education,
            "major": major.strip(),
            "work_experience": work_experience,
            "target_position": target_position.strip(),
            "target_city": target_city.strip(),
            "target_salary": target_salary.strip(),
            "current_status": current_status,
            "key_skills": key_skills.strip(),
            "career_goal": career_goal.strip(),
        }
        status, data = update_profile(st.session_state.token, profile)
        if status == 200:
            st.session_state.profile_cache = profile
            st.session_state.active_view = "chat"
            st.rerun()
        else:
            st.error(f"保存失败：{extract_error(data)}")