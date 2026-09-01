# MCP 工具集成

## 概述

本项目通过 **MCP（Model Context Protocol）** 协议接入地图工具服务，当前集成了**自建的百度地图 MCP Server**——基于官方 `mcp` Python SDK 的 FastMCP 实现，包装百度地图 REST API，为 LangGraph Agent 提供地理编码、周边检索、路线规划、天气查询等能力。

MCP 是 Anthropic 推出的开放标准，定义了 AI 应用与外部工具之间的通信接口。任何实现了 MCP 协议的服务，都可以用同一套方式接入，不需要为每个服务单独写适配代码。

---

## 架构设计

### 两种 MCP 接入方式

项目中同时保留两种调用方式，对应不同场景：

```
app/core/langgraph/tools/mcp_client.py
├── MCPClient                      # 方式一：原生 MCP 协议（底层控制，仅 HTTP/SSE 传输）
│   ├── list_tools() → list[Tool]
│   └── call_tool()  → str
│
└── get_langchain_mcp_tools()      # 方式二：LangChain 适配器（推荐与 Agent 配合）
    └── 返回 list[BaseTool]，支持 stdio / streamable_http / sse
```

| 场景 | 推荐方式 |
|------|---------|
| 接入 LangGraph Agent / ToolNode | `get_langchain_mcp_tools()` |
| LLM 自动决策调用工具（ReAct 模式） | `get_langchain_mcp_tools()` |
| 本地 stdio 型 MCP Server（如自建百度地图） | `get_langchain_mcp_tools()`（command/args） |
| 手动控制远程 HTTP MCP 工具调用 | `MCPClient` |

> **注意**：自建百度地图 MCP 是 **stdio 传输**（本地 Python 子进程），只能通过
> `get_langchain_mcp_tools()` 方式接入；`MCPClient` 仅支持 Streamable HTTP / SSE，
> 适用于远程 MCP Server。

### 与 LangGraph Agent 的集成方式

MCP 工具在 Agent 初始化时一次性加载，流程如下：

```
FastAPI 启动
  └── LangGraphAgent.__init__()         同步，用静态工具（DuckDuckGo、ask_human 等）占位
        └── create_graph()（首次请求）   异步
              ├── load_all_tools()       静态工具(3~4) + 百度地图 MCP 工具(5)
              ├── llm_service.bind_tools() 绑定全部工具给 LLM
              └── graph_builder.compile() 图编译完成，工具可用
```

工具加载完成后，LLM 在对话中会自动决定是否调用工具，整个过程对上层 API 完全透明。

---

## 百度地图 MCP（自建）

### 为什么自建

早期尝试过第三方开源 MCP（招聘职位聚合 mcp-jobs，Node.js 爬虫）与高德官方 MCP（需企业认证），
分别因**反爬硬墙拿不到数据**和**企业认证门槛**不可用。自建方案：
- 包装**官方、稳定的百度地图 REST API**（个人实名认证即可免费调用），数据可靠
- 基于官方 `mcp` Python SDK（FastMCP），十几行即可暴露一个标准 MCP 工具
- stdio 传输随 Agent 容器运行，**无需额外运行时**（不依赖 Node.js / 浏览器）

### 传输协议：stdio

MCP Server 以本地 Python 子进程方式运行，通过标准输入输出与 MCP 客户端通信：

| 协议 | 方向 | 特点 |
|------|------|------|
| stdio | 进程间双向 | 本地子进程，无需暴露端口，适合部署在 Agent 同一环境 |
| Streamable HTTP | 客户端 ⇄ 服务端 | 新版远程标准，客户端发请求 + 服务端流式返回 |

### 可用工具（5 个）

| 工具名 | 功能 | 关键参数 |
|--------|------|---------|
| `baidu_geocoding` | 地理编码：地址 → 经纬度 | `address`(必填) |
| `baidu_reverse_geocoding` | 逆地理编码：经纬度 → 地址 | `location`(必填，`经度,纬度`) |
| `baidu_place_search` | 地点 / 周边检索（POI） | `query`(必填) `region`(必填) `page_size` |
| `baidu_direction` | 驾车 / 步行 / 骑行路线规划（自动解析起终点坐标） | `origin` `destination` `mode` |
| `baidu_weather` | 城市当前天气与未来 3 天预报 | `city`(必填) |

> 所有工具均走百度地图 Web 服务 API（个人认证 AK 免费调用，各服务有每日配额，超限返回错误）。

### 多轮工具调用（ReAct 模式）

LLM 可能需要多轮才能完成一个复杂任务，例如「北京国贸到望京怎么坐地铁最方便」：

```
第 1 轮：LLM 调用 baidu_geocoding × 2（分别解析国贸、望京坐标）
第 2 轮：LLM 调用 baidu_direction（mode=driving 计算路线与耗时）
第 3 轮：LLM 没有 tool_calls，结合结果给出最终文字回答 → 结束
```

LangGraph 的 `chat → tool_call → chat` 循环结构天然支持这个模式，无需额外处理。

---

## 配置

### 环境变量

在 `.env`（本地）或 `.env.production`（生产）中添加：

```bash
# 是否启用百度地图 MCP 工具（默认 true）
BAIDU_MAP_MCP_ENABLED=true

# 百度地图开放平台 AK（个人实名认证即可申请，必填）
# 申请地址：https://lbsyun.baidu.com/apiconsole/key
BAIDU_MAP_AK=your-baidu-map-ak
```

> **注意**：`.env` 文件已在 `.gitignore` 中，AK 不会提交到代码仓库。

### AK 申请步骤

1. 登录[百度地图开放平台](https://lbsyun.baidu.com/)，完成**个人实名认证**（无需企业认证）
2. 控制台「应用管理 → 我的应用 → 创建应用」，服务端类型选择 **Server 端**
3. 复制生成的 AK，填入 `BAIDU_MAP_AK`

### 降级机制

AK 未配置或网络不通时，Agent 自动降级，**不影响服务启动**：

| 情况 | 结果 |
|------|------|
| `BAIDU_MAP_MCP_ENABLED=false` | 跳过百度地图工具，仅使用静态工具 |
| `BAIDU_MAP_AK` 为空 | `get_baidu_mcp_servers()` 返回空字典，跳过 |
| MCP 子进程启动失败 / 连接失败 | `load_all_tools()` 捕获异常后降级，仅静态工具，打印 warning 日志 |
| 地图 API 调用失败（配额 / 网络） | 工具返回可读错误文本，LLM 如实转达，不编造数据 |

---

## 核心代码

### MCP Server 实现（FastMCP）

```python
# app/core/langgraph/mcp_servers/baidu_maps_server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("baidu-maps")

@mcp.tool()
async def baidu_geocoding(address: str) -> str:
    """地理编码：将地址转换为经纬度坐标."""
    data = await _get("/geocoding/v3/", {"address": address, "output": "json", "ak": _AK})
    ...

if __name__ == "__main__":
    mcp.run(transport="stdio")   # stdio 模式启动
```

### MCP Server 配置（新增工具集只需仿照此文件）

```python
# app/core/langgraph/tools/baidu_mcp.py
def get_baidu_mcp_servers() -> dict[str, dict[str, Any]]:
    """返回百度地图 MCP Server 配置（stdio 传输）."""
    if not settings.BAIDU_MAP_MCP_ENABLED or not settings.BAIDU_MAP_AK:
        return {}
    return {
        "baidu_maps": {
            "command": sys.executable,
            "args": ["-m", "app.core.langgraph.mcp_servers.baidu_maps_server"],
            "transport": "stdio",
        }
    }
```

### 工具加载入口

```python
# app/core/langgraph/tools/__init__.py
static_tools = [duckduckgo_search_tool, calculator, ask_human]  # 同步，始终可用

async def load_all_tools() -> list[BaseTool]:
    """静态工具 + MCP 工具，MCP 失败时自动降级."""
    try:
        mcp_tools = await get_langchain_mcp_tools(get_baidu_mcp_servers())
        return static_tools + mcp_tools    # 静态 + 5 个百度地图工具
    except Exception:
        return list(static_tools)          # 降级：仅静态工具
```

---

## 依赖

```toml
# pyproject.toml
mcp = ">=1.9.0"                    # MCP 官方 SDK（FastMCP + stdio 支持）
langchain-mcp-adapters = ">=0.1.0" # MCP → LangChain BaseTool 转换
httpx                              # 百度地图 REST API 调用（已声明）
```

> 纯 Python 实现，**无需 Node.js / 浏览器**，Docker 镜像无额外运行时负担。

---

## 测试

```bash
# 测试百度地图 MCP 配置结构（AK 未配置时自动跳过）
uv run pytest tests/test_mcp_client.py -v -s

# 测试 LLM 通过 MCP 工具自动调用（天气 / 周边检索 / 路线规划）
uv run pytest tests/test_mcp_with_llm.py -v -s -m slow
```

测试文件位置：

```
tests/
├── test_mcp_client.py      # baidu_mcp 配置结构测试
└── test_mcp_with_llm.py    # LLM + MCP 工具端到端测试
```

---

## 扩展：接入其他 MCP Server

百度地图只是当前接入的一个 MCP Server。如需新增其他服务（如招聘、天气、企业内部系统），只需：

**1. 新建配置文件**

```python
# app/core/langgraph/tools/my_service_mcp.py
def get_my_service_mcp_servers() -> dict[str, dict[str, Any]]:
    if not settings.MY_SERVICE_ENABLED:
        return {}
    return {
        "my_service": {
            "command": sys.executable,          # 或远程: {"url": ..., "transport": "sse"}
            "args": ["-m", "app.core.langgraph.mcp_servers.my_service_server"],
            "transport": "stdio",
        }
    }
```

**2. 在 `load_all_tools()` 中合并**

```python
async def load_all_tools() -> list[BaseTool]:
    servers = {}
    servers.update(get_baidu_mcp_servers())
    servers.update(get_my_service_mcp_servers())   # 新增这行
    mcp_tools = await get_langchain_mcp_tools(servers)
    return static_tools + mcp_tools
```

**3. 添加配置项**

```bash
# .env
MY_SERVICE_ENABLED=true
```

其余代码无需改动，LLM 会自动发现并使用新工具。
