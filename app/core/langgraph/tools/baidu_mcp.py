"""百度地图 MCP Server 配置.

通过 MCP 协议接入**自建**的百度地图 MCP Server
（app/core/langgraph/mcp_servers/baidu_maps_server.py，基于官方 mcp SDK 的
FastMCP 实现，stdio 传输），包装百度地图 REST API，暴露 5 个工具：
  - baidu_geocoding           地理编码：地址 → 经纬度
  - baidu_reverse_geocoding   逆地理编码：经纬度 → 地址
  - baidu_place_search        地点 / 周边检索（POI）
  - baidu_direction           驾车 / 步行 / 骑行路线规划
  - baidu_weather             城市当前天气与预报

该 MCP Server 为 stdio 传输（本地 Python 子进程，随 Agent 容器运行，无需额外运行时）。
AK 未配置或已禁用时自动跳过该工具集，不影响 Agent 启动。

环境变量：
    BAIDU_MAP_MCP_ENABLED  是否启用百度地图 MCP 工具（默认 true）
    BAIDU_MAP_AK           百度地图开放平台 AK（个人实名认证即可申请，必填）
"""

import sys
from typing import Any

from app.core.config import settings
from app.core.logging import logger


def get_baidu_mcp_servers() -> dict[str, dict[str, Any]]:
    """返回百度地图 MCP Server 配置.

    返回 MultiServerMCPClient 所需的 servers 配置字典（stdio 传输）：
        {
            "baidu_maps": {
                "command": "<python>",
                "args": ["-m", "app.core.langgraph.mcp_servers.baidu_maps_server"],
                "transport": "stdio",
                "env": {"BAIDU_MAP_AK": "<AK>"},
            }
        }

    AK 未配置或已禁用时返回空字典，外层调用无需特判。
    """
    if not settings.BAIDU_MAP_MCP_ENABLED:
        logger.info("baidu_mcp_disabled", reason="BAIDU_MAP_MCP_ENABLED=false")
        return {}

    if not settings.BAIDU_MAP_AK:
        logger.warning("baidu_mcp_skipped", reason="BAIDU_MAP_AK not configured")
        return {}

    return {
        "baidu_maps": {
            "command": sys.executable,
            "args": ["-m", "app.core.langgraph.mcp_servers.baidu_maps_server"],
            "transport": "stdio",
            # mcp SDK 子进程默认只继承白名单环境变量（HOME/PATH 等），AK 必须显式传入
            "env": {"BAIDU_MAP_AK": settings.BAIDU_MAP_AK},
        }
    }
