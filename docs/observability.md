# 观测说明

## 观测组件

项目包含三类观测能力：

| 类型 | 工具 | 用途 |
| --- | --- | --- |
| 日志 | structlog + stdout | 排查业务链路和异常 |
| 指标 | Prometheus + Grafana | 查看 QPS、耗时、错误率 |
| LLM 追踪 | Langfuse | 查看模型输入、输出、耗时和 token |

## 日志

项目使用 structlog 输出结构化日志，**所有环境统一使用 `text` 格式**（本地终端自动着色，容器内 `isatty()=False` 自动关闭颜色）。

一条典型日志格式：

```text
{timestamp} - [{env}] - {LEVEL} - [{request_id}] - [{module.func:line}] - {事件}  {参数JSON}
```

实际示例：

```text
2026-05-13 10:30:45.123 - [development] - INFO - [6e932b38] - [chatbot.chat:138] - 收到聊天请求  {"session_id": "sess_abc", "user_id": "42", "message_count": 3}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 北京时间（UTC+8），毫秒级 |
| `env` | 运行环境（development / production…） |
| `LEVEL` | 日志级别（INFO/WARNING/ERROR…） |
| `request_id` | 一次 HTTP 请求的链路 ID（即 correlation_id） |
| `module.func:line` | 代码位置 |
| `事件` | **中文事件名**（例如「收到聊天请求」），是日志的核心语义 |
| `参数JSON` | 结构化参数（session_id、user_id、message_count、error 等） |

> ⚠️ 日志**只有单一中文事件名**，不再有 `event`/`event_cn`/`message` 三字段双键结构。需要按用户/会话检索时，直接搜 `user_id`、`session_id` 参数即可。

## 请求排查

生产环境中可以先搜 `request_id`，一条聊天请求通常会看到（事件名为中文）：

```text
收到请求
收到聊天请求
开始检索长期记忆
长期记忆检索完成
开始调用大模型
大模型调用成功
大模型回答已生成
聊天请求处理完成
请求完成
```

常用查询：

```text
request_id = "..."
error 且含 "聊天请求处理失败" / "chat_request_failed"
status_code >= 500
duration_ms > 3000
user_id = 1
```

## Prometheus 和 Grafana

FastAPI 暴露：

```text
GET /metrics
```

Prometheus 定时采集 `/metrics`，Grafana 根据 Prometheus 数据画图。

常见指标：

| 指标 | 说明 |
| --- | --- |
| `http_requests_total` | HTTP 请求总数 |
| `http_request_duration_seconds` | HTTP 请求耗时 |
| `llm_inference_duration_seconds` | LLM 调用耗时 |
| `llm_stream_duration_seconds` | 流式响应耗时 |
| `session_names_generated_total` | 会话标题生成次数 |

## Langfuse

Langfuse 用来查看 LLM 调用链路，包括输入、输出、模型、耗时和 token 用量。

本地不想启用可以配置：

```env
LANGFUSE_TRACING_ENABLED=false
```

## 慢请求分析

当 `DEBUG=true` 时，慢请求会写入 `PROFILING_DIR`，文件名包含 `request_id`，方便和日志对应起来。
