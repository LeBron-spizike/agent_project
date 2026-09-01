# 就业规划智能问答系统（Employment_Planning_Agent）

> 面向求职者的**就业规划智能问答系统**：提供职业定位、行业与岗位分析、求职策略、简历与面试辅导、成长路径规划等专业问答服务。基于 LLM Agent 能力构建（后端技术栈：FastAPI + LangGraph，详见下文技术栈）。

---

## 项目简介

一个产品化的**就业规划智能问答系统**，对接阿里云 DashScope（Qwen 系列模型），国内网络可直接使用。用户注册登录后即可开始对话，Agent 会结合用户背景与长期记忆给出个性化职业建议。

- 完整的本地链路调试验证（PostgreSQL + pgvector + mem0 + qwen-embedding）
- 认证流程简化：登录获取 token 后全程通用
- 结构化中文日志、Prometheus/Grafana 监控、Langfuse 追踪
- 内置前端：Streamlit 应用（ChatGPT 风格，唯一维护的前端）
- 后续规划：接入 RAG 职业知识库，提供带引用的行业数据与岗位信息问答

> 📖 完整的项目内容介绍（架构、目录详解、命令参考、注意事项、FAQ）见 [docs/project-overview.md](docs/project-overview.md)。

---

## 核心功能

| 能力 | 实现方式 |
|---|---|
| 异步 REST API | FastAPI |
| AI Agent 工作流编排 | LangGraph（StateGraph + 工具调用 + 断点持久化） |
| LLM 调用 / 重试 / Fallback | LangChain + tenacity（阿里云 Qwen） |
| 长期记忆 | mem0 + pgvector + qwen-embedding |
| 业务数据 + Checkpoint 持久化 | PostgreSQL + SQLModel + AsyncPostgresSaver |
| 用户鉴权 | JWT（注册/登录 token 全程通用） |
| Agent 工具 | 计算器、联网搜索（DuckDuckGo）、人类介入、MCP（百度地图：地理编码/周边检索/路线/天气） |
| 结构化日志 | structlog（本地彩色 / 容器纯文本自动切换） |
| 指标监控 | Prometheus + Grafana |
| LLM 链路追踪 | Langfuse |
| 限流 | slowapi（按用户 ID，独立配额） |
| 前端 | Streamlit 聊天应用（唯一维护的前端） |

---

## 技术栈

```
FastAPI · LangGraph · LangChain · PostgreSQL · pgvector
mem0ai · SQLModel · structlog · Prometheus · Grafana
Langfuse · slowapi · tenacity · Pydantic v2
阿里云 DashScope（Qwen LLM + qwen-embedding）
```

---

## 一、环境准备（前置条件）

- **Docker Desktop**（推荐方式必需；后端所有依赖与数据库都在容器里）
- 或：Python 3.13+ + [uv](https://docs.astral.sh/uv/) + 本机 PostgreSQL 15+（本地方式）
- 阿里云百炼 DashScope API Key（`.env.development` 中的 `DASHSCOPE_API_KEY`）

---

## 二、启动后端（两种方式）

### 方式 A：Docker Compose（推荐，最省事）

项目根目录已有 `.env.development`（内含数据库与 DashScope 配置，`POSTGRES_HOST=db` 是容器网络主机名）。

```bash
# 1. 启动 Docker Desktop（确保 daemon 已运行）

# 2. 构建并启动 数据库 + 后端（首次或改动 Dockerfile 后）
docker compose --env-file .env.development up -d --build db app

#    已构建过，日常直接启动
docker compose --env-file .env.development up -d db app

# 3. 执行数据库迁移（首次必须；之后如提示有新版才需要）
docker compose --env-file .env.development exec app uv run alembic upgrade head

# 4. 验证后端已就绪
curl http://127.0.0.1:8000/health
```

预期返回（`status: healthy` 即成功）：

```json
{"status":"healthy","version":"1.0.0","environment":"development","components":{"api":"healthy","database":"healthy"}}
```

> 镜像已内置 curl，`/health` 健康检查正常；若 `docker compose ps` 仍显示 unhealthy 以 `/health` 实际返回为准。

**常用运维命令：**

```bash
docker compose --env-file .env.development ps           # 查看容器状态
docker compose --env-file .env.development logs -f app  # 跟踪后端日志
docker compose --env-file .env.development down         # 停止服务
```

**可选：完整监控栈**（多拉起 Prometheus/Grafana/valkey/cadvisor）：

```bash
docker compose --env-file .env.development up -d
```

### 方式 B：本地 uv + PostgreSQL

```bash
# 1. 安装依赖
pip install uv && uv sync

# 2. 配置环境变量（关键：本地数据库要把 POSTGRES_HOST 改成 localhost）
cp .env.example .env.development
# 编辑 .env.development：POSTGRES_HOST=localhost，并填写本机库账号密码

# 3. 执行迁移
uv run alembic upgrade head

# 4. 启动（热加载，端口 8000）
make dev
# 等价于：uv run uvicorn app.main:app --reload --port 8000
```

> 注意：pyproject 要求 Python ≥ 3.13，本机需自备该版本解释器与带 pgvector/pg_jieba 扩展的 PostgreSQL，否则本地方式跑不起来（此时请用方式 A）。

---

## 三、启动前端（后端必须先运行在 8000 端口）

### 前端 1：Streamlit 应用（功能最全，推荐）

```bash
# 任选一种方式
streamlit run frontend_streamlit/app.py
# 或（多 Python 环境时推荐，强制用指定解释器）
C:\Users\Administrator\.conda\envs\ai_agent\python.exe -m streamlit run frontend_streamlit/app.py
```

浏览器打开 **http://localhost:8501**。支持：后端健康状态、注册、登录、创建会话、会话列表、历史消息、多会话切换、对话、求职画像、知识库管理、模式切换。

> ℹ️ **前端统一为 Streamlit**：原模板遗留的静态页 `frontend/index.html` 已删除，不再提供。

---

## 四、详细使用（API 演练）

接口文档：**http://127.0.0.1:8000/docs**（Swagger UI）

> 完整请求链路：`注册/登录 → 建会话 → 聊天 → 查历史`

### 1. 注册用户

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"Password123!","username":"orson"}'
```

- 密码**必须包含特殊字符**（如 `!@#$%`），否则返回 422
- 成功返回 `id`、用户信息、`token.access_token`（可直接用于后续请求）

### 2. 登录

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "email=user@example.com" \
  --data-urlencode "password=Password123!" \
  --data-urlencode "grant_type=password"
```

> ⚠️ **表单字段是 `email=`**（不是 `username=`）。后端 [auth.py](app/api/v1/auth.py) 要求 `email` 字段，旧文档里写的 `username=` 已过时，按此写法会报 `email: Field required`。前端内部均使用 `email=`，网页操作不受影响。

登录成功返回 `access_token`（30 天有效），保存后用于下面的鉴权。

### 3. 创建聊天会话

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/session \
  -H "Authorization: Bearer <access_token>"
```

返回 `session_id`，后续聊天都基于该会话。

### 4. 聊天（就业规划问答）

```bash
curl -X POST http://127.0.0.1:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","messages":[{"role":"user","content":"你好，介绍一下你自己"}]}'
```

### 5. 流式聊天（SSE）

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/chatbot/chat/stream \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","messages":[{"role":"user","content":"讲个笑话"}]}'
```

### 6. 查询 / 清空聊天历史

```bash
# 查询历史
curl "http://127.0.0.1:8000/api/v1/chatbot/messages?session_id=<session_id>" \
  -H "Authorization: Bearer <access_token>"

# 清空历史
curl -X DELETE "http://127.0.0.1:8000/api/v1/chatbot/messages?session_id=<session_id>" \
  -H "Authorization: Bearer <access_token>"
```

### 7. 常用辅助接口

| 接口 | 说明 |
|---|---|
| `GET /` | 项目基础信息（名称/版本/状态） |
| `GET /health` | 健康检查（含数据库状态） |
| `GET /api/v1/auth/sessions` | 当前用户会话列表 |
| `GET /api/v1/debug/rate-limit/check?user_id=1` | 查看限流计数（仅开发环境） |

---

## 五、常用命令速查

```bash
make install          # 安装依赖（uv sync）
make dev              # 本地热加载启动（端口 8000）
make lint             # ruff 代码检查
make format           # ruff 格式化
make typecheck        # pyright 类型检查
make check            # lint + typecheck
make migrate          # 数据库迁移到最新
make docker-up        # Docker 启动 API + DB
make docker-down      # Docker 停止
make docker-logs      # 跟踪日志
make stack-up         # 完整栈（API + DB + Prometheus + Grafana）
make eval             # 运行 LLM 评测（交互式）
make eval-quick       # 运行 LLM 评测（默认配置）
```

---

## 六、注意事项（常见坑）

1. **登录字段**：用 `email=`，勿用旧文档的 `username=`。
2. **前端 CORS**：静态页必须从 localhost 打开，不能 `file://`；Streamlit 走服务端不受 CORS 限制。
3. **密码强度**：注册密码需含特殊字符，否则 422。
4. **聊天依赖网络**：对话出结果依赖 `.env.development` 里的 `DASHSCOPE_API_KEY` 有效（阿里云百炼），Key 失效会报错。
5. **密钥安全**：`.env.development` 含真实密钥，已被 `.gitignore` 忽略不会入库；项目已纳入 git 版本控制，提交前确认 `.env.*` 等含密钥文件未被跟踪，分享/打包项目目录时务必脱敏。
6. **app 显示 unhealthy**：多为启动初期瞬时状态，`/health` 返回 healthy 即正常；镜像已内置 curl（历史"缺 curl 误报"已修复）。
7. **多 Python 环境**：本机存在多个 Python（conda base / ai_agent / Python3.12…），裸命令可能指向错误的解释器；命令行工具报「command not found」时改用 `python -m <tool>` 或写全路径。
8. **限流**：`POST /chatbot/chat` 30 次/分钟、登录 20 次/分钟等；触发返回 429 中文提示。

---

## 七、文档索引

| 文档 | 说明 |
|---|---|
| [docs/from-template.md](docs/from-template.md) | **从原模板复现 + Agent 系统架构 + 相对模板新增功能** |
| [docs/project-overview.md](docs/project-overview.md) | **项目总览**：架构、目录详解、命令参考、FAQ |
| [docs/getting-started.md](docs/getting-started.md) | 快速开始 |
| [docs/architecture.md](docs/architecture.md) | 架构与请求链路 |
| [docs/authentication.md](docs/authentication.md) | JWT 鉴权 |
| [docs/database.md](docs/database.md) | 数据库与迁移 |
| [docs/memory.md](docs/memory.md) | 长期记忆（mem0 + pgvector） |
| [docs/llm-service.md](docs/llm-service.md) | LLM 服务 |
| [docs/docker.md](docs/docker.md) | Docker 部署 |
| [docs/observability.md](docs/observability.md) | 日志 / Prometheus / Grafana / Langfuse |
| [docs/configuration.md](docs/configuration.md) | 环境配置 |
| [docs/evaluation.md](docs/evaluation.md) | LLM 评测 |

---

## 项目结构（简版）

```
app/                 # 后端源码（api / core / models / schemas / services / utils）
alembic/             # 数据库迁移
frontend_streamlit/  # Streamlit 前端（app.py）
evals/               # LLM 评测框架
docs/                # 文档
scripts/             # Docker / 环境脚本
prometheus/ grafana/ # 监控配置
tests/               # 测试
```

---

## 致谢

本项目基于 [wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template) 二次开发，感谢原作者开源贡献。

> 从原模板一步步复现本项目的步骤、Agent 系统架构，以及相对模板新增的全部功能，见 [docs/from-template.md](docs/from-template.md)。