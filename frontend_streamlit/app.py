import requests
import streamlit as st


API_BASE = "http://127.0.0.1:8000"


st.set_page_config(
    page_title="FastAPI + LangGraph 问答系统",
    page_icon="🤖",
    layout="wide",
)


def init_state():
    defaults = {
        "token": "",
        "session_id": "",
        "logged_in": False,
        "messages": [],
        "sessions": [],
        "email": "user@example.com",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def check_health():
    try:
        res = requests.get(f"{API_BASE}/health", timeout=5)
        return res.ok, res.json()
    except Exception as e:
        return False, {"error": str(e)}


def register(email: str, password: str, username: str):
    payload = {
        "email": email,
        "password": password,
        "username": username,
    }

    res = requests.post(
        f"{API_BASE}/api/v1/auth/register",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )

    return res.status_code, res.json()


def login(email: str, password: str):
    data = {
        "email": email,
        "password": password,
        "grant_type": "password",
    }

    res = requests.post(
        f"{API_BASE}/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=data,
        timeout=15,
    )

    return res.status_code, res.json()


def create_session(token: str):
    res = requests.post(
        f"{API_BASE}/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )

    return res.status_code, res.json()


def get_sessions(token: str):
    res = requests.get(
        f"{API_BASE}/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )

    return res.status_code, res.json()


def send_chat(token: str, session_id: str, user_content: str):
    payload = {
        "session_id": session_id,
        "messages": [
            {
                "role": "user",
                "content": user_content,
            }
        ],
    }

    res = requests.post(
        f"{API_BASE}/api/v1/chatbot/chat",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    return res.status_code, res.json()


def load_history(token: str, session_id: str):
    res = requests.get(
        f"{API_BASE}/api/v1/chatbot/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"session_id": session_id},
        timeout=30,
    )

    return res.status_code, res.json()


def refresh_sessions() -> tuple[bool, object]:
    status, data = get_sessions(st.session_state.token)
    if status == 200:
        st.session_state.sessions = data
        return True, data
    return False, data


def switch_session(session_id: str) -> tuple[bool, object]:
    status, data = load_history(st.session_state.token, session_id)
    if status == 200:
        st.session_state.session_id = session_id
        st.session_state.messages = data.get("messages", [])
        return True, data
    return False, data


def get_session_label(session: dict) -> str:
    name = session.get("name") or "未命名会话"
    session_id = session.get("session_id", "")
    short_id = session_id[:8] if session_id else "unknown"
    return f"{name} · {short_id}"


init_state()


st.title("🤖 FastAPI + LangGraph 问答系统")

with st.sidebar:
    st.header("后端状态")

    ok, health = check_health()
    if ok:
        st.success("后端服务正常")
        st.json(health)
    else:
        st.error("后端服务异常")
        st.json(health)

    st.divider()

    st.header("用户登录")

    email = st.text_input("邮箱", value=st.session_state.email)
    password = st.text_input("密码", value="Password123!", type="password")
    username = st.text_input("用户名", value="orson")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("注册", use_container_width=True):
            status, data = register(email, password, username)

            if status == 200:
                st.success("注册成功")
                token_data = data.get("token", {})
                st.session_state.token = token_data.get("access_token", "")
                st.session_state.logged_in = bool(st.session_state.token)
                st.session_state.email = email
                st.session_state.session_id = ""
                st.session_state.messages = []
                refresh_sessions()
            else:
                st.error("注册失败")
                st.json(data)

    with col2:
        if st.button("登录", use_container_width=True):
            status, data = login(email, password)

            if status == 200:
                st.success("登录成功")
                st.session_state.token = data.get("access_token", "")
                st.session_state.logged_in = True
                st.session_state.email = email
                st.session_state.session_id = ""
                st.session_state.messages = []
                refresh_sessions()
            else:
                st.error("登录失败")
                st.json(data)

    if st.session_state.logged_in:
        st.success("当前已登录")

        if st.button("创建新会话", use_container_width=True):
            status, data = create_session(st.session_state.token)

            if status == 200:
                st.session_state.session_id = data.get("session_id", "")
                st.session_state.messages = []
                refresh_sessions()
                st.success("会话创建成功")
            else:
                st.error("会话创建失败")
                st.json(data)

        st.text_input("当前 Session ID", value=st.session_state.session_id, disabled=True)

        if st.button("刷新会话列表", use_container_width=True):
            ok, data = refresh_sessions()
            if ok:
                st.success("会话列表已刷新")
            else:
                st.error("会话列表加载失败")
                st.json(data)

        st.subheader("历史会话")
        if not st.session_state.sessions:
            st.caption("暂无历史会话")
        else:
            for session in st.session_state.sessions:
                session_id = session.get("session_id", "")
                is_active = session_id == st.session_state.session_id
                label = get_session_label(session)
                button_label = f"● {label}" if is_active else label

                if st.button(
                    button_label,
                    key=f"session_{session_id}",
                    use_container_width=True,
                    disabled=is_active,
                ):
                    ok, data = switch_session(session_id)
                    if ok:
                        st.rerun()
                    else:
                        st.error("历史消息加载失败")
                        st.json(data)

        if st.button("重新加载当前会话消息", use_container_width=True):
            if not st.session_state.session_id:
                st.warning("请先创建会话")
            else:
                ok, data = switch_session(st.session_state.session_id)
                if ok:
                    st.success("历史消息加载成功")
                else:
                    st.error("历史消息加载失败")
                    st.json(data)

    if st.button("退出登录", use_container_width=True):
        st.session_state.token = ""
        st.session_state.session_id = ""
        st.session_state.logged_in = False
        st.session_state.messages = []
        st.session_state.sessions = []
        st.rerun()


st.subheader("对话窗口")

if not st.session_state.logged_in:
    st.info("请先在左侧登录。")
elif not st.session_state.session_id:
    st.info("请先在左侧创建会话。")
else:
    for message in st.session_state.messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")

        with st.chat_message(role):
            st.markdown(content)

    user_input = st.chat_input("请输入你的问题...")

    if user_input:
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("模型思考中..."):
                status, data = send_chat(
                    st.session_state.token,
                    st.session_state.session_id,
                    user_input,
                )

            if status == 200:
                response_messages = data.get("messages", [])
                assistant_content = ""

                for msg in reversed(response_messages):
                    if msg.get("role") == "assistant":
                        assistant_content = msg.get("content", "")
                        break

                st.markdown(assistant_content)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_content,
                    }
                )
            else:
                st.error("请求失败")
                st.json(data)
