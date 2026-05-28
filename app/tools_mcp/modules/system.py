import aiohttp
from datetime import datetime
from claude_agent_sdk import tool
from app.tools_mcp.base import http_get, ok_response, error_response
from app.utils.http_client import HttpClientManager

@tool("get_time", "获取当前日期和时间", {})
async def get_time(args: dict) -> dict:
    return ok_response(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@tool("get_weather", "获取城市天气。city 为空时自动使用当前 IP 位置", {"city": str})
async def get_weather(args: dict) -> dict:
    city = args.get("city", "")
    try:
        if not city:
            ip_data = await http_get("/api/user/ip")
            ip = ip_data.get("data", "")
            session = HttpClientManager.get_session()
            async with session.get(f"https://api.52vmy.cn/api/query/itad?ip={ip}") as r:
                city_data = await r.json()
            city = city_data.get("data", {}).get("address", "").split(" ")[0]

        session = HttpClientManager.get_session()
        async with session.get(f"https://api.52vmy.cn/api/query/tian?city={city}") as r:
            data = await r.json()
        return ok_response(data)
    except Exception as e:
        return error_response(f"天气查询失败: {e}")
