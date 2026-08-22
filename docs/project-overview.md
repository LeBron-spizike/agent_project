# 项目总览（Project Overview）

> 本文件是 `fastapi-langgraph-agent-zh` 的**完整内容介绍**：项目定位、架构、全部文件职责、功能清单、命令参考、注意事项与 FAQ。
> 如何复现启动与详细使用，见根目录 [README.md](../README.md)。

---

## 1. 项目定位

一个开箱即用的 **LangGraph + FastAPI 生产级 AI Agent 后端模板**，中文适配版。

在原始模板基础上完成：

- 全面中文注释，降低接手门槛
- 对接阿里云 DashScope（Qwen 系列模型 + qwen-embedding），国内网络开箱即用
- 完整本地链路验证（PostgreSQL + pgvector + mem0 + qwen-embedding）
- 认证流程简化：登录获取 token 后所有接口通用（去掉了原版"再换 session token"一步）
- 日志系统重构：统一 text 格式，本地彩色 / 容器纯文本自动切换
- 限流改为按用户 ID，独立配额互不干扰
- 内置两个前端（Streamlit + 静态网页），开箱即用

---

## 2. 技术栈

```
FastAPI · LangGraph · LangChain · PostgreSQL + pgvector
mem0ai · SQLModel · structlog · Prometheus + Grafana
Langfuse · slowapi · tenacity · Pydantic v2
阿里云 DashScope（qwen-plus 等 + text-embedding-v4）
```

---

## 3. 功能清单

### 3.1 核心对话能力
- **多轮对话**：LangGraph StateGraph 状态机，多轮上下文保持
- **断点持久化**：`AsyncPostgresSaver` 把每轮对话 checkpoint 存入 PostgreSQL，服务重启对话不丢
- **流式输出**：`/chat/stream` 提供 SSE 流式响应
- **工具调用**：Agent 可自主调用工具回答问题
  - `calculator`：安全四则运算（AST 白名单解析）
  - `duckduckgo_results_json`：联网搜索
  - `ask_human`：人类介入确认
  - MCP：高德地图（`.env` 里 `AMAP_MCP_ENABLED=false` 默认关闭）

### 3.2 记忆系统
- **短期记忆**：LangGraph checkpoint（会话内）
- **长期记忆**：mem0ai 自动从对话抽取/更新/检索，存 `longterm_memory_qwen_1024_v2` 向量表
- **向量化**：阿里云 `text-embedding-v4`（1024 维）+ pgvector

### 3.3 认证与安全
- JWT 鉴权（HS256），token 30 天有效
- 注册密码强度校验（必须含特殊字符）
- 输入清洗（sanitize）+ 邮箱格式校验
- slowapi 限流（按用户 ID，未登录降级按 IP）
- 会话归属校验（不能操作别人的会话）

### 3.4 可观测性
- structlog 结构化日志（中文事件名，request_id/session_id/user_id 自动绑定）
- Prometheus 指标：请求数/耗时、LLM 调用时长
- Grafana 看板：LLM 延迟面板
- Langfuse：LLM 调用全链路追踪

### 3.5 其他
- 限流压测调试接口（仅开发环境）
- LLM 评测框架（evals/，5 个评测维度）
- 两个现成前端

---

## 4. 架构与请求链路

```
浏览器 / Streamlit / curl
        │  HTTP + JWT(Bearer)
        ▼
FastAPI app.main
  ├─ 中间件链：CorrelationId → Profiling → Metrics → LoggingContext → 路由
  ├─ 限流 slowapi（按用户 ID）
  ├─ CORS / 异常处理器
        ▼
api/v1 路由层
  ├─ auth.py     注册/登录/会话管理
  └─ chatbot.py  聊天/流式/历史
        ▼
services 业务层
  ├─ database.py      用户/会话/消息 读写（SQLModel）
  ├─ memory.py        mem0 长期记忆
  ├─ session_naming.py 会话自动命名
  └─ llm/             LLM 注册表 + 服务（重试/降级/流式）
        ▼
core/langgraph/graph.py  ←  LangGraph Agent 图 + 工具
        ▼
LLM（DashScope Qwen） · PostgreSQL（业务表+checkpoint+向量） · 外部工具
```

---

## 5. 目录与文件详解（清理后现状）

### 5.1 根目录

| 文件/目录 | 作用 |
|---|---|
| [app/](../app/) | 后端主代码（详见 5.2） |
| [alembic/](../alembic/) + alembic.ini | 数据库迁移（env.py 绑定 SQLModel 元数据） |
| [Dockerfile](../Dockerfile) | 后端镜像：Python 3.13.2 + uv 装依赖 + 阿里云镜像源加速 |
| [docker-compose.yml](../docker-compose.yml) | 开发编排：db(pgvector) + app + valkey + prometheus + grafana + cadvisor |
| [docker-compose.production.yml](../docker-compose.production.yml) | 生产编排（仅上线用） |
| [Makefile](../Makefile) | 命令入口（见第 6 节命令表） |
| [pyproject.toml](../pyproject.toml) | 依赖声明 + ruff/pyright/pytest 配置 |
| [uv.lock](../uv.lock) | 依赖锁定（`uv sync --frozen` 保证一致） |
| .env.development | 开发环境变量（数据库/DashScope/JWT；已被 .gitignore 忽略） |
| .env.example | 环境变量模板 |
| .gitignore / .dockerignore | 忽略规则 |
| README.md / AGENTS.md / CLAUDE.md | 项目说明 + AI 编码助手规则 |
| LICENSE / SECURITY.md | 许可证 / 安全 |
| .pre-commit-config.yaml | 提交前检查钩子 |
| .python-version | 指定 Python 版本（uv 用） |
| .secrets.baseline | detect-secrets 密钥扫描基线 |
| .vscode/settings.json | VSCode 项目设置 |
| .github/workflows/ | GitHub CI/CD（ci.yaml / deploy.yaml） |
| .claude/ | Claude Code 配置 + daily-report 技能 |
| typings/ | pyright 类型桩目录 |
| logs/ | 日志目录（Docker 挂载，空） |

### 5.2 后端 app/

| 路径 | 作用 |
|---|---|
| **main.py** | FastAPI 入口：中间件装配、CORS、限流挂载、启动预热 Agent 图与记忆服务、健康检查 |
| **api/v1/api.py** | 汇总子路由 |
| **api/v1/auth.py** | `POST /auth/register` `/login` `/session`；`GET /sessions`；会话改名/删除；JWT 依赖 `get_current_user` |
| **api/v1/chatbot.py** | `POST /chatbot/chat` `/chat/stream`；`GET/DELETE /chatbot/messages` |
| **api/v1/debug.py** | `GET /debug/rate-limit/ping|check|storage-info`（限流压测，仅开发/测试环境） |
| **core/config.py** | Pydantic Settings 读取 .env 全局配置 |
| **core/logging.py** | structlog 配置（中文事件名，彩色/纯文本切换） |
| **core/limiter.py** | slowapi 限流器（`get_user_id` 为 key） |
| **core/metrics.py** | Prometheus 指标定义 |
| **core/middleware.py** | LoggingContext / Metrics / Profiling 三个中间件 |
| **core/observability.py** | Langfuse 初始化 |
| **core/cache.py** | 缓存服务（内存 / 可选 valkey） |
| **core/prompts/system.md** | Agent 系统提示词 |
| **core/prompts/session_title.md** | 会话自动命名提示词 |
| **core/langgraph/graph.py** | LangGraph 状态图、checkpointer、多轮对话、清历史 |
| **core/langgraph/tools/** | `calculator.py` / `duckduckgo_search.py` / `ask_human.py` / `amap_mcp.py` / `mcp_client.py` |
| **models/base.py** | 公共基类 |
| **models/user.py** | 用户表 |
| **models/session.py** | 会话表 |
| **models/chat_message.py** | 消息表 |
| **models/thread.py** | 线程表（alembic 迁移依赖） |
| **schemas/auth.py / chat.py / graph.py / base.py** | Pydantic 请求/响应模型与图状态 |
| **services/database.py** | 异步数据库操作 |
| **services/memory.py** | mem0 长期记忆（初始化向量 schema、add/search/delete） |
| **services/session_naming.py** | 会话自动命名 |
| **services/llm/registry.py** | 模型注册表（默认 qwen-plus，可配多个） |
| **services/llm/service.py** | LLM 服务：重试、fallback、流式、结构化输出 |
| **utils/auth.py** | JWT 生成/校验 |
| **utils/sanitization.py** | 输入清洗、密码强度校验 |

### 5.3 前端

| 路径 | 类型 | 说明 |
|---|---|---|
| [frontend/index.html](../frontend/index.html) | 静态网页 | 纯 HTML+JS，登录+对话，需从 localhost 提供 |
| [frontend_streamlit/app.py](../frontend_streamlit/app.py) | Streamlit | 完整功能：健康检查/注册/登录/会话列表/历史/多会话 |

### 5.4 其他

| 路径 | 说明 |
|---|---|
| [evals/](../evals/) | LLM 评测：main.py 入口、evaluator.py 评测器、metrics/prompts/*.md 五个评测提示词（conciseness/hallucination/helpfulness/relevancy/toxicity） |
| [docs/](../docs/) | 文档（本目录） |
| [scripts/](../scripts/) | `docker-entrypoint.sh`（容器启动加载 .env + 校验密钥）、`build-docker.sh`（构建镜像）、`set_env.sh`（环境变量切换） |
| [prometheus/prometheus.yml](../prometheus/prometheus.yml) | Prometheus 抓取配置 |
| [grafana/dashboards/](../grafana/dashboards/) | 看板配置 + llm_latency.json 面板 |
| [tests/](../tests/) | MCP 客户端测试 |

---

## 6. 命令参考

### 6.1 Makefile

```bash
make install          # pip install uv + uv sync + 安装 pre-commit
make dev              # 本地热加载启动（uv run uvicorn app.main:app --reload --port 8000）
make staging / prod   # 以对应环境启动
make migrate          # alembic upgrade head
make migration MSG="描述"   # 生成迁移脚本
make migrate-downgrade / migrate-history
make eval / eval-quick / eval-no-report   # LLM 评测
make lint / format / typecheck / check    # ruff / pyright
make docker-build / docker-up / docker-down / docker-logs   # API + DB
make stack-up / stack-down / stack-logs   # 完整栈（含监控）
make clean            # 清理 .venv / __pycache__
```

### 6.2 Docker Compose（开发，最常用）

```bash
# 构建并启动 数据库+后端
docker compose --env-file .env.development up -d --build db app
# 日常启动
docker compose --env-file .env.development up -d db app
# 完整栈（+ valkey/prometheus/grafana/cadvisor）
docker compose --env-file .env.development up -d
# 迁移
docker compose --env-file .env.development exec app uv run alembic upgrade head
# 日志 / 停止
docker compose --env-file .env.development logs -f app
docker compose --env-file .env.development down
```

### 6.3 生产

```bash
APP_ENV=production docker compose -f docker-compose.production.yml up -d --build
```

---

## 7. 配置项说明（.env 关键变量）

| 变量 | 说明 |
|---|---|
| `APP_ENV` | development / staging / production / test |
| `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL` | 阿里云百炼 Key 与兼容模式地址 |
| `DEFAULT_LLM_MODEL` | 默认模型（qwen-plus） |
| `POSTGRES_*` | 数据库连接（Docker 内 `POSTGRES_HOST=db`；本地改 `localhost`） |
| `JWT_SECRET_KEY` / `JWT_ALGORITHM` / `JWT_ACCESS_TOKEN_EXPIRE_DAYS` | JWT 配置 |
| `ALLOWED_ORIGINS` | CORS 白名单（默认 `http://localhost:3000,http://localhost:8000`） |
| `LONG_TERM_MEMORY_*` | 记忆向量化配置（模型/维度/集合名） |
| `AMAP_API_KEY` / `AMAP_MCP_ENABLED` | 高德地图 MCP（默认关） |
| `SESSION_NAMING_ENABLED` | 会话自动命名（默认关） |
| `RATE_LIMIT_*` | 各接口限流配额 |
| `LANGFUSE_*` | Langfuse 追踪配置 |

---

## 8. 注意事项 / 常见坑

1. **登录字段是 `email=`**：旧文档写 `username=` 已过时，后端要求 `email` 字段（见 [auth.py](../app/api/v1/auth.py)），否则 422。
2. **静态前端 CORS**：`index.html` 不能用 `file://` 双击打开，必须从 `http://localhost:3000` 提供（见 README 前端章节）。
3. **注册密码**：必须含特殊字符，否则 422（`Password must contain at least one special character`）。
4. **聊天依赖 DashScope Key**：`DASHSCOPE_API_KEY` 失效则对话报错；同时需要能访问外网/阿里云。
5. **密钥不入库**：`.env.development` 已被 .gitignore 忽略；但分享目录压缩包前必须脱敏。
6. **本项目无版本控制**：`.git` 目录为空。建议 `git init` 并提交初始快照，任何删除/修改才有后悔药。
7. **app 容器显示 unhealthy**：容器内无 curl 导致 Docker 健康检查误报，`/health` 实际正常（镜像未装 curl）。
8. **多 Python 环境**：机器上存在多个解释器（conda base / ai_agent / Python3.12…），PATH 上的 `python` 未必是你想要的那个 → 命令工具报错或 import 不到包时，用 `python -m <工具>` 或写解释器全路径。
9. **python -m 是什么**：`python -m xxx` 让解释器运行"它自己环境里"的模块，不依赖 PATH 上的 exe。当包已安装但命令找不到（常见于 `pip install --user` 安装的工具 exe 不在 PATH）时，`-m` 是最稳的调用方式。
10. **限流**：聊天 30 次/分、登录 20 次/分、注册 10 次/时等；触发返回 429 中文提示。
11. **数据库迁移**：改模型后需 `alembic revision --autogenerate` + `upgrade head`，Docker 内经 `docker compose exec app` 执行。

---

## 9. FAQ

**Q1：为什么直接 `streamlit` / `uvicorn` 命令找不到？**
A：工具 exe 所在 Scripts 目录不在 PATH（常见是 `--user` 安装到 `AppData\Roaming\Python\Python311\Scripts`）。改用 `python -m streamlit run ...` 或写全路径。

**Q2：VSCode 运行按钮报错？**
A：项目 [.vscode/settings.json](../.vscode/settings.json) 里 `python.defaultInterpreterPath` 指向不存在的 `venv/bin/python`，导致解释器解析失败。改为你的实际解释器（如 conda ai_agent）即可。

**Q3：前端显示"后端服务异常"？**
A：后端没启动或 8000 端口被占用；Streamlit 侧边栏调 `GET /health` 探测，先确保 `curl http://127.0.0.1:8000/health` 返回 healthy。

**Q4：如何加新工具？**
A：在 [app/core/langgraph/tools/](../app/core/langgraph/tools/) 新建 `xxx.py` 定义 `@tool` 函数，在 `__init__.py` 导出，graph 会自动绑定。

**Q5：如何加新接口？**
A：在 [app/api/v1/](../app/api/v1/) 新建路由文件，用 `@router.post(...)` + `@limiter.limit(...)`，在 `api.py` 注册，并在 auth 依赖处加 `Depends(get_current_user)` 保护。

---

## 10. 相关文档

- [getting-started.md](getting-started.md) 快速开始
- [architecture.md](architecture.md) 架构
- [authentication.md](authentication.md) 鉴权
- [database.md](database.md) 数据库
- [memory.md](memory.md) 长期记忆
- [llm-service.md](llm-service.md) LLM 服务
- [docker.md](docker.md) Docker
- [observability.md](observability.md) 观测
- [configuration.md](configuration.md) 配置
- [evaluation.md](evaluation.md) 评测
- [local_run_record.md](local_run_record.md) 本地运行记录（个人笔记）
