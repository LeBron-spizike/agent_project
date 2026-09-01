"""MCP 客户端配置测试（百度地图 MCP）.

运行方式：
    uv run pytest tests/test_mcp_client.py -v
"""

import sys

import pytest

from app.core.config import settings
from app.core.langgraph.tools.baidu_mcp import get_baidu_mcp_servers

skip_if_no_ak = pytest.mark.skipif(
    not settings.BAIDU_MAP_AK,
    reason="BAIDU_MAP_AK 未配置，跳过百度地图 MCP 测试（在 .env 中设置 BAIDU_MAP_AK）",
)


class TestBaiduMcpConfig:
    """测试 get_baidu_mcp_servers 返回的 MCP Server 配置结构."""

    @skip_if_no_ak
    def test_returns_stdio_config(self) -> None:
        """AK 就绪时，应返回百度地图 MCP 的 stdio 配置."""
        servers = get_baidu_mcp_servers()
        assert "baidu_maps" in servers, "配置应包含 baidu_maps 键"

        config = servers["baidu_maps"]
        assert config["transport"] == "stdio"
        assert config["command"] == sys.executable
        assert config["args"][-1].endswith("baidu_maps_server"), f"入口应为自建 server: {config['args']}"

    def test_disabled_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BAIDU_MAP_MCP_ENABLED=false 时应返回空字典."""
        monkeypatch.setattr(settings, "BAIDU_MAP_MCP_ENABLED", False)
        assert get_baidu_mcp_servers() == {}

    def test_no_ak_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AK 未配置时应返回空字典（降级路径）."""
        monkeypatch.setattr(settings, "BAIDU_MAP_AK", "")
        assert get_baidu_mcp_servers() == {}
