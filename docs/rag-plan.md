# RAG 职业知识库方案（docs/rag-plan.md）

> 状态：**已实现**（2026-08-29）。本文档同时是设计与使用手册：背景、架构、数据流、配置、使用与评测。

## 1. 背景与目标

就业规划智能问答系统此前回答只依赖 LLM 常识 + 用户长期记忆，缺少**职业领域结构化知识**支撑，
薪资区间、简历规范、面试流程等内容存在幻觉风险。

本方案在现有 LangGraph Agent 中引入 RAG（检索增强生成），目标：

- 求职者提问命中知识库时，回答基于结构化的职业知识内容，可追溯来源
- 知识内容以 Markdown 文档维护，摄取全自动（MD5 增量去重），无需手动操作数据库
- 复用现有 PostgreSQL + pgvector 与 DashScope embedding，不新增任何存储服务或模型供应商

## 2. 参考项目经验提炼与取舍

参考项目：`D:\project\AI_Agent\AI大模型RAG与智能体开发_Agent项目`（扫地机器人客服 RAG Agent）。

| 参考项目做法 | 取舍 | 说明 |
|---|---|---|
| 独立 `rag/` 包分层：vector_store / rag_service / evaluate_retrieval | ✅ 借鉴 | 落地为 `app/rag/` 包 + `evals/evaluate_retrieval.py` |
| Chroma 本地向量库 | ❌ 替换 | 改用项目现有 PostgreSQL + pgvector（mem0 已在用，docker 镜像 `pgvector/pgvector:pg16`），技术栈统一、免新增存储 |
| DashScope `DashScopeEmbeddings` | ⚠️ 调整 | 同样用 DashScope `text-embedding-v4`（与 mem0 一致），但走 `langchain_openai.OpenAIEmbeddings` 兼容模式，且必须 `check_embedding_ctx_length=False`（跳过 tiktoken，避免中文分词错乱与离线容器崩溃） |
| RAG 封装成 `@tool` 供 Agent 调用 | ✅ 保留为可选模式 | `knowledge_search` 工具（`RAG_MODE=tool` 时注册） |
| 检索后用独立 LCEL 链（prompt\|model\|parser）做总结回答 | ❌ 不采用 | 主体框架保持本项目 LangGraph Agent：检索结果注入 system prompt 或作为工具结果返回，由主 Agent 统一合成，保持人设与个性化，避免双 LLM 调用 |
| 文件 MD5 去重 | ✅ 借鉴并加强 | MD5 存数据库 `knowledge_files` 表（参考项目存本地 txt 文件），支持失败自愈重摄 |
| `RecursiveCharacterTextSplitter` 中文分隔符分块 | ✅ 借鉴 | `。！？；，` 句读优先，chunk_size/overlap 走配置 |
| YAML 配置文件 | ❌ 替换 | 统一用项目 `app/core/config.py` Settings + 环境变量 |
| 检索评测（hit@k / precision / MRR / keyword_recall） | ✅ 借鉴 | 落地为 `evals/evaluate_retrieval.py` + JSONL 评测集 |

## 3. 总体架构

```
                         ┌──────────────────────────────────────────────┐
                         │              LangGraph Agent（主体不变）        │
 用户提问 ──► /chatbot ──►│  get_response:                               │
                         │   asyncio.gather( aget_state,                │
                         │                   memory_service.search,  ───┼──► mem0 长期记忆（原有）
                         │                   rag_service.format_context)│
                         │        │                                     │
                         │        ▼                                     │
                         │   system prompt {knowledge} ◄── 知识上下文注入 │
                         │        │                                     │
                         │   chat ⇄ tool_call（tool 模式下另有            │
                         │   knowledge_search 工具可被 Agent 按需调用）    │
                         └──────────────────────────────────────────────┘
                                          │
        ┌─────────────┬──────────────────┼───────────────────┬──────────────┐
        ▼             ▼                  ▼                   ▼              ▼
  app/rag/embeddings  app/rag/rag_service  app/rag/vector_store  app/rag/document_loader  app/rag/ingest.py
  (DashScope          (检索/组装/摄取编排)   (pgvector 建表/写入/   (.md/.txt 加载/中文分块/   (命令行摄取入口，
   text-embedding-v4)                      余弦检索)             MD5)                     rich 报告)
                                              │
                                              ▼
                                   PostgreSQL + pgvector
                                    knowledge_files / knowledge_chunks
```

## 4. 目录与文件分类

```
app/rag/                          # RAG 核心模块（新增独立包）
├── __init__.py                   # 导出 rag_service 单例
├── embeddings.py                 # DashScope 兼容模式 Embedding 客户端
├── vector_store.py               # pgvector：建表/登记/写入/相似度检索（函数式模块）
├── document_loader.py            # 文档加载 + 中文分块 + 文件 MD5
├── rag_service.py                # 编排层：search/format_context/ingest_directory/文件管理
└── ingest.py                     # 命令行摄取：python -m app.rag.ingest

app/core/langgraph/tools/
└── knowledge_search.py           # LangGraph 工具（tool 模式）

app/api/v1/
├── knowledge.py                  # 管理接口：POST ingest / GET files / DELETE files/{id}
└── chatbot.py                    # POST /chatbot/analyze：上传文件分析（multipart，PDF/TXT/MD）

app/schemas/
├── rag.py                        # IngestRequest/IngestReport/KnowledgeFileInfo/KnowledgeFileList
└── graph.py                      # GraphState 新增 knowledge / knowledge_sources 字段

data/knowledge/                   # 知识文档目录（.md/.txt/.pdf，支持子目录递归）
├── 简历撰写指南.md
├── 面试准备清单.md
└── 行业与岗位选择方法论.md

evals/
├── evaluate_retrieval.py         # 检索质量评测（hit@k/source_hit/precision/keyword_recall/mrr）
├── retrieval_eval.jsonl          # 评测集（10 条用例）
```

### 4.1 分块策略（标题感知）

- **Markdown**：先按标题层级（#/##/###）切出章节（`MarkdownHeaderTextSplitter`），章节标题
  写入 `metadata.section`；章节超过 chunk_size 再做字符级二次分块。检索来源显示
  「文件名 · 章节」，如"简历撰写指南.md · 二、STAR 法则描述经历"
- **PDF**：pdfplumber 逐页提取（版面感知、中文简历更稳），失败自动降级 pypdf；`metadata.page` 记录页码
- **TXT**：整篇读取后字符级分块
- 分块逻辑变更后必须 `uv run python -m app.rag.ingest --force` 强制重摄（MD5 未变不会自动重分块）

### 数据表（ensure_tables() 启动时 CREATE IF NOT EXISTS，不走 alembic）

```sql
knowledge_files(id TEXT PK,           -- 知识目录下 posix 相对路径
                name TEXT,            -- 文件名（检索结果来源展示）
                md5 TEXT,             -- 内容 MD5（增量去重）
                chunk_count INTEGER,
                created_at TIMESTAMPTZ)

knowledge_chunks(id BIGSERIAL PK,
                 file_id TEXT REFERENCES knowledge_files(id) ON DELETE CASCADE,
                 content TEXT,
                 metadata JSONB,      -- source / chunk_index
                 embedding vector(1024))  -- 维度由 RAG_EMBEDDING_DIMS 建表时固定

-- HNSW 索引：knowledge_chunks_embedding_idx USING hnsw (embedding vector_cosine_ops)
```

> ⚠️ 建表后修改 `RAG_EMBEDDING_DIMS` 需删表重建（`DROP TABLE knowledge_chunks, knowledge_files`）。

## 5. 数据流

### 5.1 摄取（写路径）

```
data/knowledge/*.md ─► 递归扫描(.md/.txt) ─► 逐文件：
  MD5 == 登记表.md5 ? ──是──► skipped
        │否
  读取(utf-8) ─► RecursiveCharacterTextSplitter(中文句读分隔符,
                 chunk_size=500, overlap=80)
  ─► 分批 aembed_documents(batch=16, tenacity 3 次指数退避)
  ─► 删旧块 ─► 插新块 ─► upsert 登记行(md5/chunk_count)
```

- 触发方式：① 应用启动自动增量摄取（`RAG_AUTO_INGEST=true`）；
  ② `POST /api/v1/knowledge/ingest`；③ `python -m app.rag.ingest`
- 中途失败的文件：下次摄取时 MD5 不匹配会自动重摄（自愈）

### 5.2 检索（读路径，两种模式）

- **inject 模式（默认）**：每轮提问时与 `aget_state` / 长期记忆检索同一批 `asyncio.gather`
  并发执行，不增加串行延迟；结果格式化为
  `【参考资料N】（来源：xxx.md）\n内容`，注入 system prompt 的 `{knowledge}` 占位符
- **tool 模式**：注册 `knowledge_search` 工具，Agent 对知识性问题按需调用，返回同样的格式化文本
- 检索失败/未启用/无命中一律返回空串，不阻断对话（与 memory_service 同降级策略）

### 5.3 对话中的 RAG 可见性（来源标注）

RAG 在对话中有两层可见体现：

1. **回答文本内标注**（system.md 回答要求）：使用知识库内容回答时，模型须在回答末尾另起一行
   标注「📚 参考：文件名1、文件名2」——对前端/API/历史记录永久可见（随 content 入库）
2. **前端来源徽章**：`GET /chatbot/chat` 响应新增 `knowledge_sources: list[str]`（本轮命中并
   去重后的来源文件名，来自 `GraphState.knowledge_sources`）；Streamlit 前端把它存进 assistant
   消息并在气泡下方渲染徽章「📚 知识库来源：…」（`chat_page.py` + `styles.py` 的
   `.knowledge-sources` 样式）。徽章只对当轮新回答显示；历史回答靠 content 内的文字标注。
   流式接口（/chat/stream）暂未返回 sources，前端当前用非流式接口，不受影响。

## 6. 配置说明（app/core/config.py / .env）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `RAG_ENABLED` | true | 总开关；false 时不建表、不检索、不注册工具 |
| `RAG_MODE` | inject | inject=自动注入 / tool=Agent 工具调用 / off=关闭检索 |
| `RAG_KNOWLEDGE_DIR` | data/knowledge | 知识文档目录 |
| `RAG_EMBEDDING_MODEL` | text-embedding-v4 | DashScope embedding 模型 |
| `RAG_EMBEDDING_DIMS` | 1024 | 向量维度（建表后修改需删表重建） |
| `RAG_CHUNK_SIZE` | 500 | 分块最大字符数 |
| `RAG_CHUNK_OVERLAP` | 80 | 相邻分块重叠字符数 |
| `RAG_TOP_K` | 4 | 检索返回条数 |
| `RAG_SCORE_THRESHOLD` | 0.0 | 余弦相似度阈值，0 不过滤 |
| `RAG_AUTO_INGEST` | true | 启动时自动增量摄取 |
| `RAG_INGEST_BATCH_SIZE` | 16 | embedding 批量大小 |
| 限流 `knowledge` | 20 per minute | 知识库管理接口限流 |

## 7. 使用手册

```bash
# 添加/修改知识：直接编辑 data/knowledge/ 下的 .md/.txt，重启应用即自动增量摄取
# 或手动触发：

# ① 命令行（本地 uv 环境或容器内）
uv run python -m app.rag.ingest

# ② 容器内
docker compose --env-file .env.development exec app uv run python -m app.rag.ingest

# ③ API（需登录 token）
POST /api/v1/knowledge/ingest        {"directory": null}
GET  /api/v1/knowledge/files
DELETE /api/v1/knowledge/files/简历撰写指南.md
```

### 7.1 检索诊断（判断单个问题召回准不准）

```bash
# 直接查看某问题的 top-k 命中结果与相似度得分（不经过 LLM）
docker compose --env-file .env.development exec app uv run python -m app.rag.query "面试自我介绍应该怎么说"
```

输出每条结果的「得分 / 来源文档 / 内容预览」。得分 = 1 - 余弦距离（0~1），
text-embedding-v4 在本知识库上的实测分布（top-1）：

| 问题类型 | 得分范围（实测） |
|---|---|
| 直接命中对应章节（如"面试自我介绍应该怎么说"） | 0.55 ~ 0.60 |
| 同义改述 / 泛化问题（如"零基础转行怎么开始"） | 0.36 ~ 0.54 |
| 知识库外无关问题（如"北京有哪些滑雪场"） | 0.19 ~ 0.22 |

据此 `RAG_SCORE_THRESHOLD` 建议 0.35~0.45：可过滤无关问题注入，同时保留改述类命中。

## 8. 评测

```bash
# 需数据库与 DASHSCOPE_API_KEY（embedding 查询）
uv run python evals/evaluate_retrieval.py --k 3 5
```

指标含义（对 `evals/retrieval_eval.jsonl` 的每条用例）：

- **hit@k**：top-k 中至少一条"来源正确且命中任一期望关键词"的用例占比——**这就是召回率的直接度量**
- **source_hit@k**：top-k 中出现正确来源文件的用例占比
- **precision@k**：top-k 中命中条目的平均占比（衡量噪声水平）
- **keyword_recall@k**：期望关键词在检索结果中的平均覆盖率
- **mrr@k**：首条命中结果排名倒数的均值（衡量排序质量）

参考线：hit@3 ≥ 90%、MRR ≥ 80% 为良好；precision 随 k 增大被稀释，看相对变化即可。

**扩充评测集**：往 `evals/retrieval_eval.jsonl` 加一行 JSON（id / query / expected_sources /
expected_keywords），query 写你真实关心的用户问法。改分块参数或加文档后重跑，指标对比调参。

**召回不准的排查路径**：
1. 该中的没中 → `python -m app.rag.query` 看该问题命中了什么：来源文件不在结果里 →
   先确认文件已摄取（`GET /knowledge/files`）；在但排名靠后 → 命中段落被分块切断
   （调大 `RAG_CHUNK_SIZE`）或问法与文档措辞差异过大（换措辞再测，或把该知识点补进文档）
2. 无关问题也注入 → 得分普遍偏低仍返回 top-k → 设 `RAG_SCORE_THRESHOLD`（见 7.1）
3. 命中但回答没用知识内容 → 看回答是否带「📚 参考：」标注；带标注说明注入成功、
   是模型取舍问题；不带标注查 Langfuse trace 里 system prompt 是否包含【参考资料】

## 9. 后续演进

- [x] ~~前端"引用来源"展示~~（已实现，见 5.3 节：回答文本标注 + 气泡下方来源徽章）
- [x] ~~PDF 支持与标题感知分块~~（2026-08-29：Markdown 按标题分节、PDF 按页提取，见第 4.1 节）
- [x] ~~对话文件分析~~（2026-08-29：`POST /chatbot/analyze` 上传 PDF/TXT/MD，前端 📎 上传控件）
- [x] ~~流式接口（/chat/stream）返回 knowledge_sources~~（2026-08-30：`get_stream_response` 产出
  `(text, sources)`、`StreamResponse` 新增字段、结束事件携带来源，前端流式路径徽章正常）
- [x] ~~docx 格式上传支持（python-docx）~~（2026-08-30：`document_loader` 摄取/提取 .docx，
  标题段映射 section；知识库上传与对话文件分析均支持）
- [x] ~~知识文档增多后引入 rerank（如 DashScope gte-rerank）做二阶段精排~~（2026-08-30：
  `app/rag/reranker.py` 调用 DashScope text-rerank 原生端点；`search()` 候选窗口 20 → 精排回 top-k，
  异常自动降级纯向量；`RAG_RERANK_ENABLED/MODEL/CANDIDATES/TOP_K` 配置；评测 `--rerank` 对比。
  ⚠️ 当前账号未开通 gte-rerank（403 AccessDenied），处于降级模式，开通后自动生效）

## 10. 召回率提升指南（实测数据）

**优先级：内容质量 > 分块策略 > 检索参数。**

1. **增加知识库内容（收益最大）**：召回的前提是"答案在库里"。文档要覆盖用户真实问题域，
   每个主题写成独立小节（标题即语义单元）。改文档后重启即自动增量摄取。
2. **标题感知分块（已实现）**：Markdown 按标题层级分节，章节标题进 metadata，
   检索段落语义完整、引用显示"文件名 · 章节"。实测收益：相关查询 top-1 得分
   0.535 → **0.765**，评测 MRR 95% → **100%**。分块逻辑变更后需
   `uv run python -m app.rag.ingest --force` 强制重摄。
3. **检索参数**：`RAG_SCORE_THRESHOLD` 按 `python -m app.rag.query` 实测分布设定
   （当前知识库建议 0.35~0.45，过滤无关注入）；`RAG_TOP_K` 用评测脚本对比不同取值。
4. **问法与文档对齐**：评测集（retrieval_eval.jsonl）里补真实用户问法；召回差的用例
   对应把知识点补进文档，而不是只调参数。
