"""百度地图 MCP Server（自建，包装百度地图 REST API）.

基于官方 mcp Python SDK 的 FastMCP 实现，以 **stdio** 传输暴露地图工具，
供 LangGraph Agent 通过 langchain-mcp-adapters 接入调用（见
app/core/langgraph/tools/baidu_mcp.get_baidu_mcp_servers）。

覆盖能力（均走百度地图 Web 服务 API，个人认证 AK 即可免费调用）：
  - baidu_geocoding           地理编码：地址 → 经纬度
  - baidu_reverse_geocoding   逆地理编码：经纬度 → 地址
  - baidu_place_search        地点 / 周边检索（POI）
  - baidu_direction           驾车 / 步行 / 骑行路线规划（自动解析起终点坐标）
  - baidu_weather             城市当前天气与未来预报

环境变量：
    BAIDU_MAP_AK  百度地图开放平台 AK（个人实名认证即可申请，必填）

运行方式（stdio 模式）：
    python -m app.core.langgraph.mcp_servers.baidu_maps_server
"""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

# 百度地图 Web 服务 API 根地址与 AK（AK 由调用方进程环境注入，随容器 env_file 透传）
_MAP_BASE = "https://api.map.baidu.com"
_AK = os.getenv("BAIDU_MAP_AK", "")

# 常用城市行政区划编码（weather/v1 的 district_id 为**地级行政区划码**：
# 直辖市用"市辖区"编码（如 110100 北京），普通地级市用市级编码（如 440300 深圳）；
# 省级编码（110000 等）weather/v1 返回 status=40 无效。实测确认有效。
_CITY_DISTRICT_IDS: dict[str, int] = {
    "北京": 110100,
    "上海": 310100,
    "天津": 120100,
    "重庆": 500100,
    "广州": 440100,
    "深圳": 440300,
    "杭州": 330100,
    "南京": 320100,
    "武汉": 420100,
    "成都": 510100,
    "西安": 610100,
    "苏州": 320500,
    "长沙": 430100,
    "青岛": 370200,
}

mcp = FastMCP("baidu-maps")


async def _get(path: str, params: dict) -> dict:
    """请求百度地图 REST API，返回 JSON 字典."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(_MAP_BASE + path, params=params)
        resp.raise_for_status()
        return resp.json()


def _status_message(data: dict) -> str:
    """从百度 API 响应中提取错误信息."""
    return data.get("message") or data.get("msg") or str(data)


async def _resolve_coord(text: str) -> dict | None:
    """将"经度,纬度"或中文地址解析为百度坐标系坐标（bd09ll）.

    先尝试直接按经纬度解析，失败则走地理编码接口。
    """
    parts = [p.strip() for p in text.split(",")]
    if len(parts) == 2:
        try:
            return {"lng": float(parts[0]), "lat": float(parts[1])}
        except ValueError:
            pass

    data = await _get("/geocoding/v3/", {"address": text, "output": "json", "ak": _AK})
    if data.get("status") == 0:
        return data["result"]["location"]
    return None


def _resolve_district_id(city: str) -> int | None:
    """将城市名解析为百度天气 district_id（内置地级行政区划码映射）.

    注：曾尝试 api_region_search 动态解析，但其返回的 code 字段已为空，故用内置映射。
    """
    return _CITY_DISTRICT_IDS.get(city)


@mcp.tool()
async def baidu_geocoding(address: str) -> str:
    """地理编码：将地址（如"北京市海淀区上地十街10号"）转换为经纬度坐标."""
    data = await _get("/geocoding/v3/", {"address": address, "output": "json", "ak": _AK})
    if data.get("status") != 0:
        return f"地理编码失败：{_status_message(data)}"
    loc = data["result"]["location"]
    precise = "（精确匹配）" if data["result"].get("precise") else "（模糊匹配）"
    return f"地址「{address}」经纬度：经度 {loc['lng']}，纬度 {loc['lat']}（百度坐标系 bd09ll）{precise}"


@mcp.tool()
async def baidu_reverse_geocoding(location: str) -> str:
    """逆地理编码：将经纬度（格式"纬度,经度"，如"39.909652,116.404177"）转换为详细地址.

    注意：百度接口坐标为**纬度在前**（lat,lng），与地理编码返回的"经度,纬度"相反。
    """
    data = await _get(
        "/reverse_geocoding/v3/",
        {"location": location, "output": "json", "ak": _AK, "coordtype": "bd09ll"},
    )
    if data.get("status") != 0:
        return f"逆地理编码失败：{_status_message(data)}"
    result = data["result"]
    detail = result.get("formatted_address", "")
    roads = result.get("roads", [])
    road = f"，临近 {roads[0]['name']}" if roads else ""
    return f"坐标（{location}）对应的地址：{detail}{road}"


@mcp.tool()
async def baidu_place_search(query: str, region: str, page_size: int = 5) -> str:
    """地点 / 周边检索：在指定城市（region）内按关键词（query）搜索地点，如"上海人民广场附近有什么咖啡厅"."""
    page_size = max(1, min(int(page_size), 20))
    data = await _get(
        "/place/v2/search",
        {"query": query, "region": region, "output": "json", "ak": _AK, "scope": 2, "page_size": page_size},
    )
    if data.get("status") != 0:
        return f"地点检索失败：{_status_message(data)}"
    results = data.get("results", [])
    if not results:
        return f"在「{region}」未检索到与「{query}」相关的地点。"
    lines = [f"在「{region}」检索到 {len(results)} 个「{query}」相关地点："]
    for i, r in enumerate(results[:page_size], 1):
        address = r.get("address") or r.get("area") or ""
        detail = r.get("detail_info", {})
        price = f"，消费约 {detail['price']} 元" if detail.get("price") else ""
        lines.append(f"{i}. {r.get('name')}（{address}）{price}")
    return "\n".join(lines)


@mcp.tool()
async def baidu_direction(origin: str, destination: str, mode: str = "driving") -> str:
    """路线规划：计算两点之间的驾车 / 步行 / 骑行路线与距离、耗时.

    origin / destination 可为地址（自动地理编码）或"经度,纬度"坐标；mode 可选 driving（驾车）/ walking（步行）/ riding（骑行）。
    """
    mode = (mode or "driving").lower()
    if mode not in ("driving", "walking", "riding"):
        return f"不支持的出行方式：{mode}（可选 driving / walking / riding）"

    o = await _resolve_coord(origin)
    d = await _resolve_coord(destination)
    if not o or not d:
        return f"无法解析起终点坐标（origin={origin}，destination={destination}），请提供准确地址或坐标。"

    data = await _get(
        f"/directionlite/v1/{mode}",
        # 百度路线规划接口坐标顺序为"纬度,经度"，与地理编码返回的"经度,纬度"相反，此处翻转
        {"origin": f"{o['lat']},{o['lng']}", "destination": f"{d['lat']},{d['lng']}", "ak": _AK},
    )
    if data.get("status") != 0:
        return f"{mode} 路线规划失败：{_status_message(data)}"
    routes = data.get("result", {}).get("routes", [])
    if not routes:
        return "未找到可行路线。"
    route = routes[0]
    distance_km = route.get("distance", 0) / 1000
    duration_min = route.get("duration", 0) / 60
    label = {"driving": "驾车", "walking": "步行", "riding": "骑行"}[mode]
    detail = route.get("steps", [])
    if detail:
        first = detail[0]
        summary = f"；首段：{first.get('instruction', '')}"
    else:
        summary = ""
    return f"{label}路线：{origin} → {destination}，全程约 {distance_km:.1f} 公里，预计 {duration_min:.0f} 分钟{summary}"


@mcp.tool()
async def baidu_weather(city: str) -> str:
    """查询城市当前天气与未来 3 天预报，如"北京今天天气怎么样"."""
    district_id = _resolve_district_id(city)
    if not district_id:
        return f"暂不支持查询城市「{city}」的天气，可尝试：北京/上海/广州/深圳/杭州/南京/武汉/成都/西安/苏州/长沙/青岛/天津/重庆。"
    data = await _get(
        "/weather/v1/",
        {"district_id": district_id, "data_type": "all", "ak": _AK},
    )
    if data.get("status") != 0:
        return f"天气查询失败：{_status_message(data)}"
    result = data["result"]
    now = result.get("now", {})
    location = result.get("location", {})
    lines = [
        f"{location.get('name', city)}当前天气：{now.get('text')}，温度 {now.get('temp')}℃，"
        f"体感 {now.get('feels_like')}℃，{now.get('wind_class')} {now.get('wind_dir')}，湿度 {now.get('rh')}%",
        "未来预报：",
    ]
    for forecast in result.get("forecasts", [])[:3]:
        lines.append(
            f"- {forecast.get('date')}：{forecast.get('text_day')}（{forecast.get('temp_min')}~{forecast.get('temp_max')}℃）"
        )
    return "\n".join(lines)


def main() -> None:
    """以 stdio 模式启动 MCP Server（由 get_baidu_mcp_servers 配置子进程拉起）."""
    if not _AK:
        raise SystemExit("BAIDU_MAP_AK 未配置，无法启动百度地图 MCP Server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
