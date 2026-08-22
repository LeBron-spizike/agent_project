# 配置说明

## 配置文件加载顺序

项目会根据 `APP_ENV` 加载环境变量文件，优先级大致为：

```text
.env.<environment>.local
.env.<environment>
.env.local
.env
```

## 常用环境

```env
APP_ENV=development
DEBUG=true
LOG_FORMAT=text
```

生产环境建议：

```env
APP_ENV=production
DEBUG=false
```

> ⚠️ **注意**：当前 `LOG_FORMAT` 配置项**尚未生效**——日志模块（`app/core/logging.py`）所有环境一律输出 `text` 格式（本地彩色 / 容器纯文本自动切换）。如需接入 ES/Loki 等平台，需要先为日志模块实现 JSON 渲染，仅改 `.env` 无效。

## 数据库配置

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mydb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

## JWT 配置

```env
JWT_SECRET_KEY=please-change-me
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=30
```

## LLM 配置

```env
DEFAULT_LLM_MODEL=qwen-plus
DASHSCOPE_API_KEY=your-key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MAX_TOKENS=2000
LLM_TOTAL_TIMEOUT=60
```

## 长期记忆配置

```env
LONG_TERM_MEMORY_MODEL=qwen-plus
LONG_TERM_MEMORY_EMBEDDER_MODEL=text-embedding-v4
LONG_TERM_MEMORY_EMBEDDING_DIMS=1024
LONG_TERM_MEMORY_COLLECTION_NAME=longterm_memory_qwen_1024_v2
```

## 缓存配置

如果配置了 `VALKEY_HOST`，项目会使用 Valkey/Redis；否则使用进程内存缓存。

```env
VALKEY_HOST=localhost
VALKEY_PORT=6379
CACHE_TTL_SECONDS=60
```

## 日志配置

当前日志输出特点：

- **格式**：固定 `text`（`LOG_FORMAT` 配置项当前不生效）
- **级别**：由 `DEBUG` 决定（`DEBUG=true` 输出 DEBUG，否则 INFO；`LOG_LEVEL` 配置项当前不生效）
- **输出位置**：仅到控制台/容器 stdout（日志文件 handler 已定义但未挂载，`LOG_DIR` 暂未使用）

```env
DEBUG=true
```

接 Elasticsearch/Loki/OpenSearch 时，需要先实现 JSON 渲染与文件/转发输出，再配置对应项。
