# 从原模板复现本项目（含 Agent 系统与新增功能）

> 本项目 **就业规划智能问答系统（Employment_Planning_Agent）** 基于开源模板
> [wassim249/fastapi-langgraph-agent-production-ready-template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
> 二次开发。本文档说明：① 模板是什么；② 如何从模板一步步复现本项目；③ 本 Agent 系统架构；
> ④ 相对模板新增了哪些功能。

---

## 一、原模板简介

`fastapi-langgraph-agent-production-ready-template` 是一个 **production-ready 的 FastAPI + LangGraph Agent 模板**，自带：

| 能力 | 实现 |
|---|---|
| 异步 REST API | FastAPI |
| Agent 工作流编排 | LangGraph（StateGraph + 工具调用 + checkpoint 持久化） |
| 用户认证与会话 | JWT 登录 + 会话管理 |
| 长期记忆 | mem0ai + pgvector |
| LLM 追踪 | Langfuse |
| 监控与日志 | Prometheus + Grafana + structlog |
| 限流 | slowapi |
| 编排部署 | Docker Compose + SQLModel + Alembic 迁移 |
| 评测框架 | Langfuse 驱动的 LLM evals |

**本项目的定位转变**：把"通用 AI 问答 Agent 骨架"改造为**面向求职者的就业规划专家系统**——产品化提示词、RAG 职业知识库、求职画像、多智能体模式、地图 MCP 工具，并配套完整的 ChatGPT 风格前端。

---

## 二、从模板到本项目的复现步骤

> 按实际开发顺序列出，每步标注关键命令；完整里程碑历史见 [docs/PROGRESS.md](docs/PROGRESS.md)。

### 前置条件

- Docker Desktop（推荐），或 Python 3.13+ + uv + 本机 PostgreSQL 15+（pgvector/pg_jieba）
- 阿里云百炼 DashScope API Key（对话 `qwen-plus` / 向量 `text-embedding-v4` / 精排 `gte-rerank-v2`）
- 百度地图开放平台 AK（个人实名认证，MCP 工具用，可选）

### 步骤 0：克隆模板并初始化

```bash
git clone https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template
cd fastapi-langgraph-agent-production-ready-template
# 安装依赖（uv）
uv sync
# 配置环境：cp .env.example .env.development 并填写数据库与 LLM Key
```

### 步骤 1：项目改名 + 中文化

将模板的包名 / 配置 / 文档统一改为本项目命名：

- 项目名 `fastapi-langgraph-agent-zh` → `Employment_Planning_Agent`
- docker 项目名 → `employment-planning-agent`（`docker-compose.yml` 顶层 `name:`）
- 全量替换 `pyproject.toml / app/core/config.py / README / docs / docker / 脚本 / 前端`

### 步骤 2：LLM 接入阿里云 DashScope（Qwen）

模板默认接 OpenAI；本项目改为国内可用的 DashScope 兼容模式：

```ini
DASHSCOPE_API_KEY=...
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_LLM_MODEL=qwen-plus
```

配套：`LONG_TERM_MEMORY_*`（qwen 记忆 + text-embedding-v4 向量）、会话命名模型 `qwen-turbo`。

### 步骤 3：后端产品化（就业规划专家）

- 系统提示词改为「就业规划专家」角色（中文、分点回答、长期记忆个性化）
- `SessionResponse` 增加 `created_at`（前端会话按时间分组）
- `app/utils/graph.py`：tiktoken 计数增加**离线估算兜底**（容器无外网不崩）

### 步骤 4：Streamlit 前端完整重构

模板仅有后端与简单静态页；本项目删除静态页，改为功能最全的 Streamlit 应用，并做模块化拆分：

```
frontend_streamlit/
  app.py            # 入口：set_page_config + 视图分发
  styles.py         # 设计系统 CSS（品牌化登录页、ChatGPT 风格问答）
  api.py            # 后端 HTTP 辅助（含 SSE 流式）
  state.py          # 会话状态与消息流
  login_page.py     # 登录/注册页
  chat_page.py      # 问答页（侧边栏会话 + 消息流 + 模式选择 + 工具区）
  profile_page.py   # 求职画像表单页
  knowledge_page.py # 知识库管理页
```

### 步骤 5：RAG 职业知识库

新增 `app/rag/` 包：标题感知分块 + MD5 增量去重 + .md/.txt/.pdf/.docx 摄取 + pgvector 余弦检索 + gte-rerank 二阶段精排 + 来源溯源 + 知识库管理 API + 检索质量评测。详见 [docs/rag-plan.md](docs/rag-plan.md)。

### 步骤 6：流式聊天 + 会话重命名 + 知识库扩充

- 聊天改走 `/chatbot/chat/stream`（SSE），前端 `st.write_stream` 打字机渲染，来源徽章不丢失
- 会话侧边栏 ✎ 重命名；新会话由 LLM 自动生成中文标题
- 知识库扩充至 8 篇，覆盖产品五大服务域

### 步骤 7：求职画像 + 多 Agent 模式 + rerank + docx + 知识库管理页

- 用户求职画像：`GET/PUT /users/me/profile`，画像摘要写 mem0 + 注入 system prompt 双通道
- 三模式切换：`mode=career/resume/interview` + `system.resume.md` / `system.interview.md` 差异化人设
- gte-rerank 精排（实测 precision@3 36.7% → 43.3%）；docx 摄取与上传；知识库管理页

### 步骤 8：MCP 百度地图（自建）

移除原高德 MCP（需企业认证）与开源招聘爬虫 MCP（反爬拿不到数据），改为**自建百度地图 MCP Server**：

```bash
# 自建 FastMCP Server 包装百度地图 REST API，stdio 传输，随 Agent 容器运行
python -m app.core.langgraph.mcp_servers.baidu_maps_server
# 配置：.env.development 中 BAIDU_MAP_MCP_ENABLED=true / BAIDU_MAP_AK=<AK>
```

详见 [docs/mcp-integration.md](docs/mcp-integration.md)。

### 步骤 9：部署验证

```bash
docker compose --env-file .env.development up -d --build db app
docker compose --env-file .env.development exec app uv run alembic upgrade head
curl http://127.0.0.1:8000/health
streamlit run frontend_streamlit/app.py   # 前端 http://localhost:8501
```

---

## 三、Agent 系统阐述

### 整体架构

```
Streamlit 前端 (frontend_streamlit/)
    │  REST / SSE
    ▼
FastAPI (app/api/v1/)
    ├── auth.py       注册 / 登录 / JWT / 会话
    ├── chatbot.py    聊天（含 SSE 流式）/ 文件分析
    ├── profile.py    求职画像
    ├── knowledge.py  知识库管理
    └── api.py        路由聚合 + 限流
    │
    ▼
LangGraph Agent (app/core/langgraph/graph.py)
    ├── StateGraph：chat → tool_call → chat 循环
    ├── AsyncPostgresSaver：多轮会话持久化（服务重启不丢）
    ├── 记忆检索：mem0 + pgvector（用户偏好）
    ├── RAG 检索注入：{knowledge} + 来源溯源
    ├── 画像注入：{profile}（结构化通道）
    └── 工具：
        ├── 静态：duckduckgo 搜索 / calculator / ask_human
        ├── 知识库：knowledge_search（tool 模式）
        └── MCP（自建百度地图，stdio 子进程）：geocoding / reverse_geocoding /
            place_search / direction / weather
    │
    ▼
DashScope(Qwen)  ·  PostgreSQL(pgvector)  ·  mem0  ·  Langfuse  ·  Prometheus/Grafana
```

### 一次典型请求链路（流式）

1. 前端发 `POST /chatbot/chat/stream`（携带 session_id、mode、消息）
2. FastAPI 鉴权 → LangGraph `create_graph()` 首次按需构建（加载 3 静态 + 5 MCP 工具）
3. Agent 并发检索长期记忆 + 知识库 → 组装 system prompt（角色 + 画像 + 记忆 + 知识）
4. LLM（qwen-plus）生成，如需工具则进入 `tool_call` 节点执行（如百度地图路线），结果回填再生成
5. SSE 逐 token 流回前端；结束事件携带 `knowledge_sources` → 前端渲染来源徽章
6. 消息与来源随会话持久化，Langfuse 全程打点

### 三类人设模式

| mode | 模板 | 职责 |
|---|---|---|
| `career`（默认） | system.md | 就业规划专家：职业定位 / 行业岗位 / 求职策略 / 成长路径 |
| `resume` | system.resume.md | 简历评审：评分 / 优点 / 问题 / 逐条建议 / 对照示例 |
| `interview` | system.interview.md | 面试官：一次一题 / 逐题追问 / 可评分 |

---

## 四、相对模板新增的功能清单

### 能力矩阵（✓ = 模板已有并保留，★ = 本项目新增）

| 能力 | 模板 | 本项目 | 说明 |
|---|---|---|---|
| FastAPI 异步 REST + JWT + 会话 | ✓ | ✓ | 沿用并补 `created_at` / 会话重命名 |
| LangGraph Agent + checkpoint | ✓ | ✓ | 沿用；新增流式 SSE 输出 |
| mem0 + pgvector 长期记忆 | ✓ | ✓ | 沿用；新增求职画像双通道注入 |
| Langfuse 追踪 / Prometheus+Grafana / slowapi | ✓ | ✓ | 沿用 |
| structlog 结构化日志 | ✓ | ✓ | 沿用 |
| LLM evals 框架 | ✓ | ✓ | 沿用 |
| 静态前端页 | ✓ | — | **删除**，改为 Streamlit 完整前端 |
| **产品化系统提示词** | — | ★ | 「就业规划专家」中文角色 |
| **LLM 接入 DashScope Qwen** | — | ★ | 对话 qwen-plus / 向量 v4 / 精排 rerank-v2 |
| **RAG 职业知识库** | — | ★ | 标题感知分块 + MD5 去重 + 来源溯源 + 管理 API |
| **gte-rerank 二阶段精排** | — | ★ | 实测 precision@3 36.7%→43.3%，异常降级纯向量 |
| **用户求职画像** | — | ★ | mem0 + 提示词双通道 |
| **多 Agent 轻量模式** | — | ★ | career / resume / interview 三模板 |
| **对话文件实时分析** | — | ★ | 上传 PDF/TXT/MD/DOCX，简历评审等 |
| **流式聊天（SSE）** | — | ★ | 打字机渲染 + 来源徽章 |
| **会话重命名 / LLM 自动标题** | — | ★ | 侧边栏 ✎ + qwen-turbo 概括 |
| **MCP 自建百度地图** | — | ★ | FastMCP + stdio，5 工具，优雅降级 |
| **Streamlit 前端全套** | — | ★ | 登录 / 问答 / 画像 / 知识库 / 模式切换 |
| **知识库检索质量评测** | — | ★ | hit@k / MRR / precision / keyword_recall |

### 新增功能要点（按价值排序）

1. **RAG 职业知识库 + Rerank**：让 Agent 回答带真实方法论支撑与「📚 参考：文件·章节」溯源；二阶段精排显著提升命中精度。
2. **求职画像 + 三模式多智能体**：简历评审、面试官模式各成体系，画像让回答个性化。
3. **MCP 自建地图工具**：从零实现 MCP Server（官方 SDK / FastMCP / stdio），LLM 自主多轮组合调用，优雅降级。
4. **流式对话 + 完整前端**：ChatGPT 风格交互 + SSE 打字机，产品可用性大幅提升。
5. **对话文件分析**：上传简历 PDF/DOCX 实时评审，闭环"求职辅导"场景。
