# 就业规划智能问答系统（Employment_Planning_Agent）本地运行记录

## 1. 项目说明

本项目是**就业规划智能问答系统**（后端技术栈：FastAPI + LangGraph + PostgreSQL + pgvector + DashScope/Qwen）的 Agent 后端项目。

本地已经完成以下验证：

* Docker 镜像构建成功
* PostgreSQL 数据库启动成功
* FastAPI 服务启动成功
* `/health` 接口返回 healthy
* Alembic 数据库迁移成功
* 用户注册成功
* JWT Token 获取成功
* Session 创建成功
* `/api/v1/chatbot/chat` 聊天接口调用成功
* DashScope/Qwen 模型成功返回回答

---

## 2. 启动命令

### 2.1 进入项目目录

```cmd
cd /d D:\employment-planning-agent
```

### 2.2 设置环境变量

如果使用 CMD：

```cmd
set APP_ENV=development
```

如果使用 PowerShell：

```powershell
$env:APP_ENV="development"
```

### 2.3 构建并启动数据库和后端服务

首次启动或修改 Dockerfile 后使用：

```cmd
docker compose --env-file .env.development up -d --build db app
```

平时已经构建过镜像后，可以直接使用：

```cmd
docker compose --env-file .env.development up -d db app
```

### 2.4 查看容器状态

```cmd
docker compose --env-file .env.development ps
```

正常情况下应看到：

```text
db    Up ... healthy
app   Up ...
```

当前存在一个遗留现象：`app` 可能显示 `unhealthy`，但 `/health` 实际返回 healthy，详见本文第 8 节。

### 2.5 查看运行日志

查看 app 和 db 日志：

```cmd
docker compose --env-file .env.development logs -f app db
```

只查看 app 最近 200 行日志：

```cmd
docker compose --env-file .env.development logs --tail=200 app
```

退出日志查看：

```cmd
Ctrl + C
```

注意：`Ctrl + C` 只是退出日志查看，不会停止容器。

### 2.6 停止服务

```cmd
docker compose --env-file .env.development down
```

---

## 3. `.env.development` 关键配置

项目根目录下需要有：

```text
.env.development
```

关键配置如下：

```env
APP_ENV=development
PROJECT_NAME="就业规划智能问答系统"
VERSION=1.0.0
DEBUG=true

API_V1_STR=/api/v1
ALLOWED_ORIGINS="http://localhost:8000"

LANGFUSE_TRACING_ENABLED=false
LANGFUSE_PUBLIC_KEY=""
LANGFUSE_SECRET_KEY=""
LANGFUSE_HOST=https://cloud.langfuse.com

DASHSCOPE_API_KEY="你的真实 DashScope API Key"
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEFAULT_LLM_MODEL=qwen-plus
DEFAULT_LLM_TEMPERATURE=0.2
SESSION_NAMING_ENABLED=false

BAIDU_MAP_MCP_ENABLED=true
BAIDU_MAP_AK="你的百度地图 AK"

LONG_TERM_MEMORY_MODEL=qwen-plus
LONG_TERM_MEMORY_EMBEDDER_MODEL=text-embedding-v4
LONG_TERM_MEMORY_EMBEDDING_DIMS=1024
LONG_TERM_MEMORY_COLLECTION_NAME=longterm_memory_qwen_1024_v2
LANGCHAIN_TRACING_V2=false
LANGSMITH_TRACING=false

JWT_SECRET_KEY="使用 python secrets 生成的一长串随机字符串"
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_DAYS=30

POSTGRES_HOST=db
POSTGRES_DB=mydb
POSTGRES_USER=myuser
POSTGRES_PORT=5432
POSTGRES_PASSWORD=mypassword
POSTGRES_POOL_SIZE=5
POSTGRES_MAX_OVERFLOW=10

RATE_LIMIT_DEFAULT="1000 per day,200 per hour"
RATE_LIMIT_CHAT="100 per minute"
RATE_LIMIT_CHAT_STREAM="100 per minute"
RATE_LIMIT_MESSAGES="200 per minute"
RATE_LIMIT_LOGIN="100 per minute"

PROFILING_DIR=/tmp/fastapi_profiles
PROFILING_THRESHOLD_SECONDS=2.0

LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

### 3.1 生成 JWT_SECRET_KEY

```cmd
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

然后将生成结果填入：

```env
JWT_SECRET_KEY="生成的一长串随机字符串"
```

### 3.2 数据库配置说明

因为 app 和 db 都运行在 Docker Compose 网络中，所以数据库主机必须写：

```env
POSTGRES_HOST=db
```

不要写成：

```env
POSTGRES_HOST=localhost
```

如果 app 在 Docker 容器里运行，`localhost` 指的是 app 容器自己，不是数据库容器。

---

## 4. 数据库迁移命令

首次启动后，需要执行 Alembic 数据库迁移：

```cmd
docker compose --env-file .env.development exec app uv run alembic upgrade head
```

成功日志示例：

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> b25d38b0cd7c, 初始数据库结构.
INFO  [alembic.runtime.migration] Running upgrade b25d38b0cd7c -> c7f2a08e4b1d, 新增聊天消息表.
```

---

## 5. 健康检查命令

### 5.1 测试 FastAPI 服务是否正常

```cmd
curl http://127.0.0.1:8000/health
```

成功返回示例：

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "components": {
    "api": "healthy",
    "database": "healthy"
  },
  "timestamp": "2026-06-13T09:48:23.825874"
}
```

### 5.2 打开接口文档

浏览器访问：

```text
http://127.0.0.1:8000/docs
```

---

## 6. 注册 / 登录 / Session / Chat 测试命令

## 6.1 注册用户

注册接口：

```cmd
curl -X POST http://127.0.0.1:8000/api/v1/auth/register -H "Content-Type: application/json" -d "{\"email\":\"user@example.com\",\"password\":\"Password123!\",\"username\":\"orson\"}"
```

用户信息：

```json
{
  "email": "user@example.com",
  "password": "Password123!",
  "username": "orson"
}
```

注意：密码必须包含特殊字符，例如：

```text
!
@
#
$
%
```

否则会报错：

```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "password",
      "message": "Value error, Password must contain at least one special character"
    }
  ]
}
```

注册成功后会返回：

```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "orson",
  "token": {
    "access_token": "xxxxx",
    "token_type": "bearer",
    "expires_at": "..."
  }
}
```

其中 `access_token` 是后续接口鉴权使用的 JWT Token。

---

## 6.2 保存 TOKEN 到 CMD 变量

将注册或登录返回的 `access_token` 保存到 CMD 变量：

```cmd
set TOKEN=你的access_token
```

检查 TOKEN 是否设置成功：

```cmd
echo %TOKEN%
```

注意：不要把真实 token 提交到 GitHub，也不要写进公开文档。

---

## 6.3 登录获取 Token

如果用户已经注册过，可以直接登录：

```cmd
curl -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "email=user@example.com&password=Password123!&grant_type=password"
```

登录成功后，同样会返回：

```json
{
  "access_token": "xxxxx",
  "token_type": "bearer",
  "expires_at": "..."
}
```

---

## 6.4 创建聊天 Session

```cmd
curl -X POST http://127.0.0.1:8000/api/v1/auth/session -H "Authorization: Bearer %TOKEN%"
```

成功返回示例：

```json
{
  "request_id": "34ff0e5b-4aaf-4b58-846d-3cc701d711bb",
  "session_id": "a3f599ec-933d-4455-adaf-31dc2e91fc52",
  "name": ""
}
```

保存 session_id：

```cmd
set SESSION_ID=你的session_id
```

检查 SESSION_ID：

```cmd
echo %SESSION_ID%
```

---

## 6.5 调用 Chat 接口：英文测试

Windows CMD 里直接发送中文 JSON 可能出现编码问题，因此先用英文测试：

```cmd
curl -X POST http://127.0.0.1:8000/api/v1/chatbot/chat -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"session_id\":\"%SESSION_ID%\",\"messages\":[{\"role\":\"user\",\"content\":\"hello, introduce yourself\"}]}"
```

成功返回示例：

```json
{
  "request_id": "49db8edc-9c2c-4bd0-9762-abf464a93c40",
  "messages": [
    {
      "role": "user",
      "content": "hello, introduce yourself"
    },
    {
      "role": "assistant",
      "content": "Hello, Orson! ..."
    }
  ]
}
```

这说明完整链路已经跑通：

```text
FastAPI 服务
→ JWT 鉴权
→ Session 校验
→ LangGraph Agent
→ DashScope/Qwen
→ 返回模型回答
```

---

## 6.6 中文 Chat 推荐使用 JSON 文件

Windows CMD 直接写中文 JSON 可能导致：

```json
{
  "detail": "There was an error parsing the body"
}
```

推荐创建文件：

```text
chat.json
```

内容如下：

```json
{
  "session_id": "你的session_id",
  "messages": [
    {
      "role": "user",
      "content": "你好，介绍一下你自己"
    }
  ]
}
```

保存时选择 UTF-8 编码。

然后执行：

```cmd
curl -X POST http://127.0.0.1:8000/api/v1/chatbot/chat -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json; charset=utf-8" --data-binary "@chat.json"
```

---

## 6.7 读取聊天历史

```cmd
curl "http://127.0.0.1:8000/api/v1/chatbot/messages?session_id=%SESSION_ID%" -H "Authorization: Bearer %TOKEN%"
```

---

## 6.8 流式聊天接口测试

```cmd
curl -N -X POST http://127.0.0.1:8000/api/v1/chatbot/chat/stream -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json" -d "{\"session_id\":\"%SESSION_ID%\",\"messages\":[{\"role\":\"user\",\"content\":\"tell me a joke\"}]}"
```

---

## 7. 已修复的问题：缺少 `calculator.py`

### 7.1 问题现象

app 容器启动后反复重启，日志报错：

```text
ModuleNotFoundError: No module named 'app.core.langgraph.tools.calculator'
```

原因是：

```python
app/core/langgraph/tools/__init__.py
```

中引用了：

```python
from .calculator import calculator
```

但是项目目录中实际缺少：

```text
app/core/langgraph/tools/calculator.py
```

---

### 7.2 解决办法

在目录：

```text
app/core/langgraph/tools/
```

中新建文件：

```text
calculator.py
```

文件内容：

```python
"""简单计算器工具."""

import ast
import operator as op

from langchain_core.tools import tool


_ALLOWED_BINOPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
}

_ALLOWED_UNARYOPS = {
    ast.UAdd: op.pos,
    ast.USub: op.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _ALLOWED_BINOPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        operand = _safe_eval(node.operand)
        return _ALLOWED_UNARYOPS[type(node.op)](operand)

    raise ValueError("只支持基本四则运算表达式")


@tool
def calculator(expression: str) -> str:
    """计算一个基本数学表达式，例如 1 + 2 * 3。"""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        return str(result)
    except Exception as e:
        return f"计算失败: {e}"
```

---

### 7.3 修改后重新启动

如果只是改了 `app/` 目录下的代码，可以尝试不重新 build：

```cmd
docker compose --env-file .env.development down
docker compose --env-file .env.development up -d db app
```

如果修改了 Dockerfile 或需要重新构建镜像：

```cmd
docker compose --env-file .env.development down
docker compose --env-file .env.development up -d --build db app
```

---

## 8. 当前遗留问题：Docker ps 显示 unhealthy，但 `/health` 实际 healthy

### 8.1 现象

执行：

```cmd
docker compose --env-file .env.development ps
```

可能看到：

```text
app   Up ... (unhealthy)
db    Up ... (healthy)
```

但是外部访问：

```cmd
curl http://127.0.0.1:8000/health
```

返回：

```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "database": "healthy"
  }
}
```

说明 FastAPI 服务和数据库实际上是正常的。

---

### 8.2 可能原因

`docker-compose.yml` 中的 healthcheck 使用了：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

但 app 镜像内部可能没有安装 `curl`，导致容器内部健康检查失败。

外部 Windows CMD 有 `curl`，所以外部测试正常；容器内部没有 `curl`，所以 Docker 标记为 `unhealthy`。

---

### 8.3 修复方式一：Dockerfile 安装 curl

打开 `Dockerfile`，找到：

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
```

改成：

```dockerfile
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
```

然后重新构建：

```cmd
docker compose --env-file .env.development down
docker compose --env-file .env.development up -d --build db app
```

查看状态：

```cmd
docker compose --env-file .env.development ps
```

目标状态：

```text
app   Up ... healthy
db    Up ... healthy
```

---

### 8.4 修复方式二：改用 Python 做 healthcheck

也可以不安装 curl，直接改 `docker-compose.yml`：

```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()\""]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

然后重启：

```cmd
docker compose --env-file .env.development down
docker compose --env-file .env.development up -d --build db app
```

---

## 9. 常用命令汇总

### 启动项目

```cmd
docker compose --env-file .env.development up -d db app
```

### 重新构建并启动

```cmd
docker compose --env-file .env.development up -d --build db app
```

### 停止项目

```cmd
docker compose --env-file .env.development down
```

### 查看容器状态

```cmd
docker compose --env-file .env.development ps
```

### 查看日志

```cmd
docker compose --env-file .env.development logs -f app db
```

### 查看 app 最近日志

```cmd
docker compose --env-file .env.development logs --tail=200 app
```

### 执行数据库迁移

```cmd
docker compose --env-file .env.development exec app uv run alembic upgrade head
```

### 测试健康接口

```cmd
curl http://127.0.0.1:8000/health
```

### 打开接口文档

```text
http://127.0.0.1:8000/docs
```

---

## 10. 当前状态结论

当前已经完成：

```text
1. Docker 镜像构建成功
2. PostgreSQL 数据库启动成功
3. FastAPI 服务启动成功
4. /health 返回 healthy
5. Alembic 数据库迁移成功
6. 用户注册成功
7. JWT 鉴权成功
8. Session 创建成功
9. Chat 接口成功调用 Qwen 返回结果
10. 已修复 calculator.py 缺失导致 app 重启的问题
```

下一步建议：

```text
1. 修复 Docker ps 中 app unhealthy 显示问题
2. 测试 messages 历史记录接口
3. 测试 chat/stream 流式接口
4. 梳理项目调用链：main.py → auth.py → chatbot.py → graph.py → database.py → memory.py
5. 基于该模板继续扩展 RAG 知识库问答功能
```
