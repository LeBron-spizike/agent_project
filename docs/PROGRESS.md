# 项目进度（PROGRESS）

> **每次对话/开发前请先读本文件**，同步当前进度与路线图，避免重复或遗漏。

## 项目定位

- **产品名**：就业规划智能问答系统
- **英文标识**：`Employment_Planning_Agent`（docker 项目名 `employment-planning-agent`）
- **定位**：面向求职者的就业规划问答服务 —— 职业定位、行业与岗位分析、求职策略、简历与面试辅导、成长路径规划
- **后端技术栈**（仅文档体现）：FastAPI · LangGraph · LangChain · PostgreSQL + pgvector · mem0 · Langfuse · Prometheus/Grafana · 阿里云 DashScope(Qwen)

## 当前运行方式

| 组件 | 命令 | 地址 |
|---|---|---|
| 后端 API + DB | `docker compose --env-file .env.development up -d --build db app` | http://127.0.0.1:8000 |
| 数据库迁移 | `docker compose --env-file .env.development exec app uv run alembic upgrade head` | — |
| 前端（Streamlit） | `streamlit run frontend_streamlit/app.py` | http://localhost:8501 |
| 监控（可选） | `docker compose --env-file .env.development up -d` | Grafana :3000 / Prometheus :9090 |

> ⚠️ **docker 项目名已从 `fastapi-langgraph-agent-zh-master` 改为 `employment-planning-agent`**（compose 顶层 `name:`）。旧项目名容器已下线；旧数据卷 `fastapi-langgraph-agent-zh-master_postgres-data` / `_grafana-storage` 已于 2026-08-23 删除（未迁移，新库为全新数据）。
> ⚠️ 注册接口限流 **10 次/小时/IP**，测试注册过多会 429；登录限流 20 次/分钟。

## 已完成里程碑

- [x] **MCP：高德 → 招聘职位聚合（mcp-jobs）→ 百度地图（自建 MCP Server）**（2026-08-31 全程）：
  - **高德 MCP** 因需企业认证拿不到 Key，已移除（`amap_mcp.py` 删除、`AMAP_*` 配置/env 清理）
  - **mcp-jobs 招聘职位聚合**（曾接入，反爬硬墙导致真实数据不可得，已整体移除）：Node.js 爬虫
    抓 BOSS/智联/猎聘/51job，猎聘验证码 + BOSS 强制登录 + 部分站点无抓取规则，工具链路全通但数据恒空，
    属于数据源路线的固有限制，非部署问题；相关代码/配置/Dockerfile Node 层已全部清除
  - **百度地图 MCP（自建，当前方案）**：基于官方 `mcp` SDK 的 **FastMCP 实现，stdio 传输**，包装百度地图
    REST API（个人实名认证免费 AK），暴露 5 个工具：
    `baidu_geocoding`（地址→坐标）/ `baidu_reverse_geocoding`（坐标→地址）/ `baidu_place_search`（POI 检索）/
    `baidu_direction`（驾车/步行/骑行路线，自动地理编码）/ `baidu_weather`（城市天气，行政区划编码兜底映射）
  - 新增 `app/core/langgraph/mcp_servers/baidu_maps_server.py`（FastMCP 服务端）+ `tools/baidu_mcp.py`
    （`get_baidu_mcp_servers()` 配置，stdio 子进程拉起，AK 未配置自动跳过）；`load_all_tools()` 沿用既有降级机制
  - 新增配置 `BAIDU_MAP_MCP_ENABLED` / `BAIDU_MAP_AK`；**Dockerfile 移除 Node/Playwright，恢复纯 Python 镜像**
  - ⚠️ **关键坑：mcp SDK 子进程 env 白名单**——stdio 子进程默认只继承 HOME/PATH/SHELL/TERM/USER，
    容器 env_file 里的 AK 不会透传，必须在 server 配置里显式 `"env": {"BAIDU_MAP_AK": ...}` 传入
  - ⚠️ **百度 API 坐标顺序坑**：directionlite / reverse_geocoding 要求**纬度,经度**（lat,lng），
    与 geocoding 返回的"经度,纬度"相反，代码内已翻转（实测 lat,lng → 200，lng,lat → "origin or destination is invalid"）
  - ⚠️ **天气 district_id 坑**：weather/v1 用**地级行政区划码**（直辖市要"市辖区"编码，如北京 110100 而非 110000），
    省级编码返回 status=40；api_region_search 的 code 字段已为空，改用内置常用城市映射（14 城，均已实测有效）
  - **已验证（真实 AK，2026-09-01）**：`tools_loaded {mcp_count: 5}`；`pytest tests/test_mcp_client.py` 3 passed；
    `pytest tests/test_mcp_with_llm.py -m slow` **3 passed**（天气=晴25℃/周边=上海5家咖啡厅/路线=天安门→颐和园 均真实数据）
  - **AK 安全约定**：真实 AK 只放 `.env.development`（gitignore 忽略）；`.env.example`（被 git 跟踪）只留占位符，
    禁止提交真实值——曾误填 `.env.example`，已修正并确认 git 历史无泄露
  - system.md 增加地图工具使用指引（路线/周边/天气/地址解析，失败不编造）
  - 产品场景：offer 通勤对比、面试地点路线、简历地址解析等，结合 RAG 知识库给出建议
  - 测试重写：`test_mcp_client.py`（配置结构）、`test_mcp_with_llm.py`（LLM ReAct 天气/周边/路线，AK 缺失自动跳过）
  - 镜像顺带补装 curl（修复 healthcheck 因缺 curl 永远 unhealthy 的老问题）
- [x] **仓库整理与发布（2026-09-01）**：
  - 删除 unused 的 `daily-report` 技能（`.claude/skills/daily-report/` + settings.local.json 白名单行 + project-overview.md 提及），保留 frontend-design / webapp-testing
  - 新增 [docs/from-template.md](from-template.md)：基于 wassim249/fastapi-langgraph-agent-production-ready-template 的复现步骤 + Agent 系统架构 + 相对模板新增功能矩阵；README 致谢/文档索引同步，并修正两处过时注意事项（git 版本控制、unhealthy-curl）
  - `push.sh` / `push.bat` 增加 `--force` 选项（覆盖远端历史用）
  - 提交 `d3f623a` 并推送至 **github.com/LeBron-spizike/agent_project**（fast-forward 更新，远端 main 已确认指向 d3f623a）
- [x] **改名**：`fastapi-langgraph-agent-zh` → `Employment_Planning_Agent`（pyproject / config / env / README / docs / docker / 脚本 / 前端，全量替换；技术栈仅保留在文档）
- [x] **后端产品化**：系统提示词改为「就业规划专家」（中文角色 + 分点回答 + 长期记忆个性化）；`SessionResponse` 增加 `created_at`（前端会话分组用）
- [x] **后端健壮性**：`app/utils/graph.py` 的 tiktoken 计数增加离线估算兜底（容器无外网时不再启动崩溃）
- [x] **前端登录/注册页**：全屏品牌化（就业规划主题：职业路径背景 + 琥珀信号色 + EMPLOYMENT PLANNING 标识），登录后自动进入最近会话
- [x] **前端问答页（ChatGPT 布局）**：左侧会话栏（新建对话 / 按"今天·更早"分组历史 / 删除 / 折叠 / 退出登录）+ 居中消息流（780px，用户靠右带头像）+ 空态欢迎屏（示例问题）+ 底部圆角输入条
- [x] **Playwright 端到端验证**：登录页品牌、注册→进聊天、会话复用、侧边栏折叠、示例问题点击、真实 LLM 就业规划回复、0 JS 报错
- [x] **前端问答页体验升级**（2026-08-26）：
  - 用户信息 + 退出登录**固定侧边栏左下**（覆盖 Streamlit 默认 96px 底部预留）
  - 顶部按钮「新建对话」→「＋ 新聊天」；空白会话统一显示"新聊天"
  - **会话标题**：新会话首条消息自动命名（占位=首问前 24 字，后台 qwen-turbo 生成中文概括标题并覆盖，DashScope 实测成功）；旧会话在 `/sessions` 响应中按首条提问回填，不再显示"新对话"
  - **快捷提问**：点击任一后三个按钮立即消失（`pending_reply` + `st.rerun()` 状态机）
  - **全宽自适应**：消息气泡/思考中气泡/底部输入框均占主区 100%（左右各 24px 留白对齐），去掉原 780px 窄列
  - 侧边栏会话标题超长省略号截断；删除按钮「✕」不被省略规则误伤
- [x] **前端体验修复 + 模块化重构**（2026-08-26）：
  - **侧边栏用户区不再随滚动下滑**：会话列表独立滚动容器（`st.container(key="session_list")` 内 `overflow-y:auto`），用户信息/退出登录固定在滚动区外底部（实测 18+ 会话滚动到顶部/底部 gap 均 0）
  - **折叠/展开修复**：屏蔽 Streamlit 原生折叠按钮（`stSidebarCollapseButton`），只保留自定义 ☰ 一套机制；折叠改为 `width:0` 收窄而非 `display:none`（保留元素在 DOM，避免 Streamlit 前端测量 0 宽度后丢失布局导致重新展开失效）；☰ 改用 Streamlit `on_click` 回调避免按钮自动 rerun + 手动 rerun 的双重重渲染竞争；加入 UI 状态版本迁移使旧浏览器标签页自动恢复展开状态；localhost 与 LAN IP 分别实测 6 轮折叠/展开 + 主区自适应回流（1140↔1440）均正常
  - **模块化拆分**：`app.py` 瘦身为入口，逻辑按功能拆到同目录 —— `styles.py`（CSS/注入）、`api.py`（后端 HTTP）、`state.py`（会话状态/消息流）、`login_page.py`（登录注册页）、`chat_page.py`（问答页）
- [x] **启动体验**（2026-08-26）：
  - 新增根目录 `start.bat`：一键启动 + 自动探测当前局域网 IP 并打开浏览器（IP 由 DHCP 分配会变化，不写死；服务已运行时直接打开不重复启动）
  - 新增 `.streamlit/config.toml`：`browser.serverAddress = "192.168.2.102"`，使 `python -m streamlit run frontend_streamlit/app.py` 自动打开局域网地址而非 localhost；IP 变化时改这一行即可
  - 说明：`192.168.2.103` 已不是本机 IP（DHCP 已改为 `.102`，.103 现为局域网内其他设备）；若要固定 .103 需在路由器做 DHCP 静态绑定后改配置
- [x] **RAG 增强：标题分块 + PDF + 对话文件分析**（2026-08-29）：
  - **标题感知分块**：Markdown 按标题层级分节（章节标题进 metadata，来源显示"文件名 · 章节"）；实测相关查询 top-1 得分 0.535 → 0.765，MRR 95% → 100%
  - **PDF 支持**：知识库摄取支持 .pdf（pypdf 按页提取）；`ingest --force` 强制重摄（分块逻辑变更后用）
  - **对话文件分析**：`POST /chatbot/analyze`（multipart 上传 PDF/TXT/MD，提取文本拼入消息，上限 ANALYZE_MAX_CHARS=6000）；前端 📎 上传控件 + 提问自动走分析接口；上传后清空附件
  - `Message.content` 上限 3000 → 20000（文件分析消息与回答更长）；新增 `ANALYZE_*` 配置与 `analyze` 限流（10/分钟）
  - E2E 实测：MD/PDF 简历均被真实分析（PDF 内容被引用），来源徽章带章节标题，回答末尾标注「📚 参考：简历撰写指南.md」
- [x] **RAG 修复：上传控件重置 + PDF 提取升级**（2026-08-29）：
  - 前端 `StreamlitValueAssignmentNotAllowedError`：新版 Streamlit 禁止直接给控件赋值清空；
    改为「上传控件 key 带版本号（`_uploader_epoch`），发送后 +1 重建为空」的合规重置方式
  - PDF 提取 pypdf → **pdfplumber 为主 + pypdf 兜底**：对中文简历 PDF（WPS/Word 导出）提取更准
  - Playwright 实测（8502 端口，避开用户实例）：上传 md 简历提问 → 来源徽章带章节标题、无异常、上传控件自动重置
  - ⚠️ 收尾时 docker CLI 偶发挂起，见本地排查；容器内 /tmp 遗留 e2e 脚本随下次重建清除（无害）
- [x] **RAG 对话可见性**（2026-08-29）：
  - system.md 回答要求新增「知识库溯源」：使用知识库内容时回答末尾标注「📚 参考：文件名」（随 content 入库，历史永久可见）
  - `GraphState` 新增 `knowledge_sources`；`get_response` 返回 `(messages, sources)`；`ChatResponse` 新增 `knowledge_sources` 字段
  - Streamlit 前端：assistant 消息携带来源，气泡下方渲染「📚 知识库来源：…」徽章（`.knowledge-sources` 样式）
  - Playwright 实测：提问"简历的项目经历怎么写" → 回答末尾出现文字标注 + 徽章显示 3 个命中文档
- [x] **引入 RAG 职业知识库**（2026-08-29，设计与使用手册见 `docs/rag-plan.md`）：
  - 新增 `app/rag/` 包：`embeddings.py`（DashScope text-embedding-v4 兼容模式）、`vector_store.py`（pgvector 建表/写入/余弦检索，启动时 CREATE IF NOT EXISTS 不走 alembic）、`document_loader.py`（.md/.txt 加载 + 中文分块 + MD5）、`rag_service.py`（检索/组装/摄取编排）、`ingest.py`（`python -m app.rag.ingest` 命令行摄取）
  - **inject 模式（默认）**：每轮提问与记忆检索同一批 gather 并发检索，结果注入 system prompt `{knowledge}` 占位；**tool 模式**：`knowledge_search` 工具按需调用；`RAG_MODE` 配置切换
  - 知识库管理 API：`POST /knowledge/ingest`、`GET /knowledge/files`、`DELETE /knowledge/files/{id}`（均限流 + 鉴权）
  - 摄取三触发：启动自动增量摄取（`RAG_AUTO_INGEST`，MD5 去重）/ API / 命令行
  - 示例知识文档 3 篇（`data/knowledge/`：简历撰写指南 / 面试准备清单 / 行业与岗位选择方法论）
  - 检索质量评测：`evals/evaluate_retrieval.py`（hit@k / source_hit / precision / keyword_recall / mrr）+ `evals/retrieval_eval.jsonl` 10 条用例
  - `GraphState` 新增 `knowledge` 字段；新依赖仅显式声明 `langchain-text-splitters`（原传递依赖）
- [x] **P0 收尾：流式聊天 + 会话重命名 + 知识库扩充**（2026-08-30）：
  - **流式聊天前端**：普通提问改走 `/chatbot/chat/stream` SSE，`st.write_stream` 打字机渲染；
    流式接口随结束事件返回 `knowledge_sources`（`get_stream_response` 改为产出 `(text, sources)` 元组、
    `StreamResponse` 新增字段、`chat_stream` 元数据记录来源），来源徽章在流式路径不丢失
  - **会话重命名**：侧边栏会话行新增 ✎ 按钮 + 行内输入/保存/取消；后端 `PATCH /session/{id}/name`（Form）
    由前端 `api.rename_session` 接入；切换会话自动退出重命名态
  - **知识库内容扩充**：`data/knowledge/` 新增 5 篇（职业定位与自我认知 / 求职策略与投递指南 /
    薪资谈判与Offer选择 / 转行与职业转型实操指南 / 职业成长与晋升路径规划），覆盖产品五大服务域
  - 文件分析 `/analyze` 无流式端点，保持一次性请求（本次不改）
- [x] **gte-rerank 精排生效**（2026-08-31）：
  - 排查确认：账号开通的是**新版模型 `gte-rerank-v2`**，老模型名 `gte-rerank` 对新账号不再授权（403 AccessDenied）
  - `config.py` 默认 `RAG_RERANK_MODEL` 改为 `gte-rerank-v2`；`.env.example` 同步（无需动 .env.development，重启容器即生效）
  - 容器实测：`knowledge_rerank_completed`（20 候选精排回 top-k）、`knowledge_search_completed {"rerank": true}`
  - 评测对比（10 条用例）：`--no-rerank` precision@3 36.67% → `--rerank` **43.33%**；hit/source_hit/keyword_recall 已饱和 100%、mrr 持平 95%
- [x] **P1/P2：求职画像 + 简历评审/面试模拟 + rerank + docx + 知识库管理 + 多Agent轻量切换**（2026-08-30）：
  - **用户求职画像**：`User.profile`(JSON) 列 + alembic 迁移；`GET/PUT /users/me/profile`；保存后画像摘要
    写入 mem0（记忆通道）+ 注入 system prompt `{profile}`（结构化通道）；前端侧边栏「完善求职画像」可选按钮
  - **多Agent 轻量模式切换**：`ChatRequest.mode`（career/resume/interview）+ `GraphState.mode/profile`；
    新增 `system.resume.md`（简历评审：评分/优点/问题/逐条建议/对照示例）、`system.interview.md`（面试官：
    一次一题/逐题追问/可评分）；前端顶部 `segmented_control` 切换；`/analyze` 支持 `mode=resume` 简历诊断
  - **rerank**：新增 `app/rag/reranker.py`（DashScope text-rerank 原生端点）；`search()` 候选窗口 20 →
    gte-rerank 精排回 top-k；异常自动降级纯向量；`RAG_RERANK_*` 配置；评测 `--rerank` 开关
    ⚠️ 当前账号 **403 AccessDenied**（gte-rerank 未开通），运行在降级模式，开通即生效
  - **docx**：`python-docx` 依赖；`document_loader` 支持 .docx 摄取（标题段映射 section）与上传分析；
    `SUPPORTED_EXTENSIONS`/`SUPPORTED_UPLOAD_EXTENSIONS`/前端上传控件加 docx
  - **知识库管理页**：后端新增 `POST /knowledge/upload`（上传→落盘→摄取）；`delete_file` 同时删除磁盘源文件
    （防复活）；前端新增 `knowledge_page.py`（上传/立即摄取/文件列表删除）+ 侧边栏入口
  - **alembic 规范化**：`./alembic:/app/alembic` 绑定挂载（迁移主机可维护）；修复 `script.py.mako` 模板 docstring
    错位；`env.py` 排除外部表（longterm_memory*、knowledge_*）+ 导入 ChatMessage，autogenerate 不再误删外部表

## 待办 / 后续规划

- [x] ~~前端静态页 `frontend/index.html` 同步 ChatGPT 风格~~（**已删除**：前端统一使用 Streamlit，
  `frontend/` 目录已移除，CORS 白名单同步去掉 localhost:3000）
- [x] ~~DashScope gte-rerank 待账号开通后生效~~（**2026-08-31 已完成**：模型名改用 gte-rerank-v2 并实测生效，见上文里程碑）
- [ ] 前端自动化 E2E 回归（画像页/知识库页/模式切换，本次后端全量验证通过、前端待人工在 8501 确认）

## 本次改动文件清单（未提交）

```
pyproject.toml / uv.lock      # 包名 -> employment-planning-agent
app/core/config.py            # PROJECT_NAME / DESCRIPTION
app/core/prompts/system.md    # 就业规划专家角色
app/core/prompts/__init__.py  # user_context 中文化 + knowledge 注入支持
app/schemas/auth.py           # SessionResponse.created_at
app/api/v1/auth.py            # 会话接口填充 created_at
app/utils/graph.py            # tiktoken 离线兜底（新增）
docker-compose.yml            # name: employment-planning-agent
.env.development / .env.example  # PROJECT_NAME
scripts/build-docker.sh / .github/workflows/deploy.yaml  # 镜像名
README.md / docs/project-overview.md / docs/production-deployment.md / docs/local_run_record.md
frontend/index.html           # 标题改名
frontend_streamlit/app.py     # 入口瘦身：只做 set_page_config + 状态门控
frontend_streamlit/styles.py  # 设计系统 CSS + inject_styles（新增，自 app.py 拆出）
frontend_streamlit/api.py     # 后端 HTTP 辅助（新增，自 app.py 拆出）
frontend_streamlit/state.py   # 会话状态与消息流（新增，自 app.py 拆出）
frontend_streamlit/login_page.py  # 登录/注册页（新增，自 app.py 拆出）
frontend_streamlit/chat_page.py   # 问答页（新增，自 app.py 拆出）
app/services/session_naming.py  # 命名模型 gpt-5.4-nano -> qwen-turbo（DashScope）；占位名 40 -> 24 字；build_session_placeholder 公开
app/services/database.py      # get_user_sessions 旧会话按首条提问回填标题

# —— RAG 知识库（2026-08-29）——
app/rag/                      # RAG 核心包（新增）：__init__/embeddings/vector_store/document_loader/rag_service/query/ingest
app/rag/document_loader.py    # 标题感知分块（MarkdownHeaderTextSplitter）+ PDF 按页 + 上传文件文本提取
app/api/v1/chatbot.py         # POST /analyze 文件分析端点；sources 随响应返回；metadata 记录命中来源
app/core/prompts/system.md    # 知识库溯源 + 文件分析回答要求
frontend_streamlit/           # 📎 文件上传控件 + analyze 走分析接口 + 来源徽章
pyproject.toml / uv.lock      # 新增 pypdf、rich、langchain-text-splitters 声明
app/schemas/rag.py            # 知识库接口 schema（新增）
app/schemas/graph.py          # GraphState 新增 knowledge / knowledge_sources 字段
app/schemas/chat.py           # ChatResponse 新增 knowledge_sources 字段
app/api/v1/knowledge.py       # 知识库管理接口（新增）
app/api/v1/api.py             # 注册 /knowledge 路由
app/api/v1/chatbot.py         # get_response 解包 sources 并随响应返回；metadata 记录命中来源
app/core/langgraph/tools/knowledge_search.py  # knowledge_search 工具（新增，tool 模式）
app/core/langgraph/tools/__init__.py          # 按 RAG_MODE 注册工具
app/core/langgraph/graph.py   # 检索注入 knowledge/sources；get_response 返回 (messages, sources)
app/core/prompts/system.md    # 知识库溯源要求（回答末尾标注「📚 参考：…」）
app/main.py                   # lifespan 初始化 rag_service + 自动增量摄取
app/core/config.py / .env.example  # RAG_* 配置段
frontend_streamlit/state.py   # assistant 消息保存 knowledge_sources
frontend_streamlit/chat_page.py   # 气泡下方渲染「📚 知识库来源」徽章
frontend_streamlit/styles.py  # .knowledge-sources 徽章样式
pyproject.toml / uv.lock      # 显式声明 langchain-text-splitters；新增 rich
data/knowledge/               # 示例知识文档（新增）：简历撰写指南/面试准备清单/行业与岗位选择方法论
evals/evaluate_retrieval.py   # 检索质量评测（新增）
evals/retrieval_eval.jsonl    # 检索评测集 10 条（新增）
docs/rag-plan.md              # RAG 方案文档（新增）

.claude/skills/frontend-design/、webapp-testing/   # 从 anthropics/skills 下载的前端设计/测试 skill
AGENTS.md / .claude/settings.local.json

# —— P0：流式聊天 + 会话重命名 + 知识库扩充（2026-08-30）——
app/schemas/chat.py            # StreamResponse 新增 knowledge_sources 字段
app/core/langgraph/graph.py    # get_stream_response 产出 (text, knowledge_sources)
app/api/v1/chatbot.py          # chat_stream 末帧带 sources + metadata 记录
frontend_streamlit/api.py      # 新增 stream_chat(SSE 生成器)+ChatStreamError+rename_session；删除 send_chat
frontend_streamlit/state.py    # handle_pending_reply 流式化；重命名状态 start/commit/cancel_rename
frontend_streamlit/chat_page.py  # 侧边栏 ✎ 重命名按钮 + 行内输入/保存/取消
frontend_streamlit/styles.py   # 重命名行按钮/输入样式
data/knowledge/                # 新增 5 篇职业知识文档（详见上文里程碑）
docs/rag-plan.md               # §9 勾选"流式接口返回 knowledge_sources"

# —— P1/P2：画像 / 模式切换 / rerank / docx / 知识库管理 / alembic 规范化（2026-08-30）——
app/models/user.py             # User 新增 profile(JSON) 列
app/schemas/profile.py         # UserProfile schema + to_summary()（新增）
app/schemas/chat.py            # ChatRequest 新增 mode（career/resume/interview）
app/schemas/graph.py           # GraphState 新增 profile / mode
app/services/database.py       # 新增 get_user_profile / update_user_profile
app/api/v1/profile.py          # GET/PUT /users/me/profile（新增，保存画像并写 mem0）
app/api/v1/api.py              # 挂载 profile 路由
app/api/v1/chatbot.py          # chat/chat_stream/analyze 透传 mode（analyze 加 Form mode）
app/core/langgraph/graph.py    # _fetch_profile + profile/mode 注入 graph input；_chat 按 mode 选模板
app/core/prompts/system.md     # 新增 {profile} 画像块
app/core/prompts/system.resume.md / system.interview.md  # 简历评审 / 面试官人设模板（新增）
app/core/prompts/__init__.py   # load_system_prompt 支持 mode 模板 + profile 默认值
app/rag/reranker.py            # DashScope gte-rerank 轻量客户端（新增）
app/rag/rag_service.py         # search() rerank 精排 + 降级；delete_file 删除磁盘源文件
app/rag/document_loader.py     # .docx 摄取/提取 + 扩展名支持
app/core/config.py             # RAG_RERANK_* 配置 + profile 限流
app/api/v1/knowledge.py        # 新增 POST /upload
evals/evaluate_retrieval.py    # 新增 --rerank / --no-rerank 对比开关
pyproject.toml / uv.lock       # 新增 python-docx（httpx 直声明）
alembic/env.py                 # 排除外部表（longterm_memory*、knowledge_*）+ 导入 ChatMessage
alembic/script.py.mako         # 修复模板 docstring 错位
docker-compose.yml             # app 服务新增 ./alembic:/app/alembic 挂载
frontend_streamlit/api.py      # 画像/知识库 helpers + mode 参数
frontend_streamlit/state.py    # active_view / mode 状态与透传
frontend_streamlit/chat_page.py  # 模式选择器 + 侧边栏工具区（画像/知识库）+ 按模式欢迎/占位 + docx
frontend_streamlit/profile_page.py  # 求职画像表单页（新增）
frontend_streamlit/knowledge_page.py  # 知识库管理页（新增）
frontend_streamlit/app.py      # 按 active_view 分发三视图
frontend_streamlit/styles.py   # 侧边栏工具区样式
.env.example                   # RAG_RERANK_* 配置
docs/rag-plan.md               # §9 勾选 docx/rerank

# —— MCP：高德 → mcp-jobs → 百度地图（自建，2026-08-31）——
app/core/langgraph/mcp_servers/baidu_maps_server.py  # 百度地图 MCP Server（新增）：FastMCP 包装 REST API，5 工具
app/core/langgraph/mcp_servers/__init__.py           # MCP Server 包（新增）
app/core/langgraph/tools/baidu_mcp.py                # 百度地图 MCP 配置（新增）：get_baidu_mcp_servers()（stdio）
app/core/langgraph/tools/jobs_mcp.py                 # 已删除（mcp-jobs 反爬拿不到真实数据，整体移除）
app/core/langgraph/tools/amap_mcp.py                 # 已删除（高德需企业认证，Key 不可用）
app/core/langgraph/tools/__init__.py                 # load_all_tools() 改用 get_baidu_mcp_servers()
app/core/langgraph/tools/mcp_client.py               # 文档引用 jobs_mcp → baidu_mcp
app/core/config.py                                   # JOBS_MCP_* → BAIDU_MAP_MCP_ENABLED/BAIDU_MAP_AK
app/core/prompts/system.md                           # 职位工具指引 → 百度地图工具指引
.env.example / .env.development / docs/local_run_record.md  # JOBS_MCP_* → BAIDU_MAP_*
README.md / docs/project-overview.md / docs/mcp-integration.md  # mcp-jobs → 百度地图（自建）
Dockerfile                     # 移除 Node 22 / mcp-jobs / Playwright chromium，恢复纯 Python（保留 curl）
tests/test_mcp_client.py / test_mcp_with_llm.py  # 重写为 baidu_mcp 配置/LLM ReAct 测试
```

## 验证命令速查

```bash
# 后端
curl http://127.0.0.1:8000/health

# 前端（webapp-testing skill 的 Playwright 流程，见 .claude/skills/webapp-testing/）
python .claude/skills/webapp-testing/scripts/with_server.py \
  --server "python -m streamlit run frontend_streamlit/app.py --server.headless true --server.port 8501" \
  --port 8501 -- python <测试脚本>
```
