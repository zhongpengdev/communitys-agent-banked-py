"""
MCP 工具服务器
将所有社区业务工具注册为 Claude Agent SDK 的 MCP 工具
token 通过 contextvars 传递（由 WebSocket 处理器在每次请求前设置）
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from dotenv import load_dotenv
from claude_agent_sdk import tool, create_sdk_mcp_server
from app.utils.context import get_request_token

load_dotenv()

BANKED_URL = os.getenv("Banked_URL", "")
SERP_KEY = os.getenv("SERP_KEY", "")
DOMAINSDB_KEY = os.getenv("DOMAINSDB_KEY", "")
API_KEY = os.getenv("API_KEY", "")
QWEN_CREATE_URL = os.getenv("QWEN_CREATE_TEXT_URL", "")
QWEN_GET_URL = os.getenv("QWEN_GET_RESULT_URL", "")


# ─── HTTP 工具函数 ────────────────────────────────────────────────────────────

def _auth_headers() -> dict:
    token = get_request_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _get(endpoint: str, params: dict = None) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get(url, params=params, headers=_auth_headers()) as r:
            r.raise_for_status()
            return await r.json()


async def _post(endpoint: str, json_data: dict = None) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.post(url, json=json_data, headers=_auth_headers()) as r:
            r.raise_for_status()
            return await r.json()


async def _delete(endpoint: str) -> dict:
    url = f"{BANKED_URL}{endpoint}"
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.delete(url, headers=_auth_headers()) as r:
            r.raise_for_status()
            return await r.json()


def _ok(data) -> dict:
    text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return {"content": [{"type": "text", "text": text}]}


def _err(msg: str) -> dict:
    return {"content": [{"type": "text", "text": json.dumps({"success": False, "message": msg}, ensure_ascii=False)}]}


# ─── 工具定义 ─────────────────────────────────────────────────────────────────

@tool("get_time", "获取当前日期和时间", {})
async def get_time(args: dict) -> dict:
    return _ok(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@tool("get_weather", "获取城市天气。city 为空时自动使用当前 IP 位置", {"city": str})
async def get_weather(args: dict) -> dict:
    city = args.get("city", "")
    try:
        if not city:
            ip_data = await _get("/api/user/ip")
            ip = ip_data.get("data", "")
            async with aiohttp.ClientSession() as s:
                async with s.get(f"https://api.52vmy.cn/api/query/itad?ip={ip}") as r:
                    city_data = await r.json()
            city = city_data.get("data", {}).get("address", "").split(" ")[0]

        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://api.52vmy.cn/api/query/tian?city={city}") as r:
                data = await r.json()
        return _ok(data)
    except Exception as e:
        return _err(f"天气查询失败: {e}")


@tool("query_unpaid_bills", "查询用户所有代缴物业费账单", {"status": int})
async def query_unpaid_bills(args: dict) -> dict:
    try:
        data = await _get("/api/property-fee/bills", {"status": args.get("status", 0)})
        return _ok(data)
    except Exception as e:
        return _err(f"账单查询失败: {e}")


@tool("get_user_notifications", "查询用户通知列表，支持分页", {"pageNum": int, "pageSize": int})
async def get_user_notifications(args: dict) -> dict:
    try:
        data = await _get("/api/notification/list", {
            "pageNum": args.get("pageNum", 0),
            "pageSize": args.get("pageSize", 10),
        })
        return _ok(data)
    except Exception as e:
        return _err(f"通知查询失败: {e}")


@tool("read_notification", "标记指定通知为已读", {"notificationId": str})
async def read_notification(args: dict) -> dict:
    try:
        data = await _post(f"/api/notification/{args['notificationId']}/read")
        return _ok(data)
    except Exception as e:
        return _err(f"标记已读失败: {e}")


@tool("send_private_messages", "代替用户向其他用户发送私信", {"content": str, "toUserId": str})
async def send_private_messages(args: dict) -> dict:
    try:
        data = await _post("/api/message/send", {
            "content": args["content"],
            "toUserId": args["toUserId"],
        })
        return _ok(data)
    except Exception as e:
        return _err(f"发送私信失败: {e}")


@tool(
    "create_visitor",
    "登记访客信息。allowTime 和 validDate 格式必须为 'yyyy-MM-dd HH:mm:ss'",
    {"visitorName": str, "visitorPhone": str, "visitPurpose": str, "allowTime": str, "validDate": str},
)
async def create_visitor(args: dict) -> dict:
    try:
        data = await _post("/api/visitor/register", {
            "visitorName": args["visitorName"],
            "visitorPhone": args["visitorPhone"],
            "visitPurpose": args["visitPurpose"],
            "allowTime": args["allowTime"],
            "validDate": args["validDate"],
        })
        return _ok(data)
    except Exception as e:
        return _err(f"访客登记失败: {e}")


@tool("search_goods", "搜索社区商城商品，支持关键词和分类筛选", {"keyword": str, "category_id": int, "page_num": int, "page_size": int})
async def search_goods(args: dict) -> dict:
    try:
        data = await _post("/api/mall/list", {
            "categoryId": args.get("category_id", 0),
            "keyword": args.get("keyword"),
            "pageNum": args.get("page_num", 1),
            "pageSize": args.get("page_size", 10),
        })
        return _ok(data)
    except Exception as e:
        return _err(f"商品搜索失败: {e}")


@tool(
    "send_scheduled_email",
    "发送定时邮件。scheduledTime 格式为 '2026-01-20T14:30:00'",
    {"subject": str, "content": str, "scheduledTime": str, "isHtml": bool},
)
async def send_scheduled_email(args: dict) -> dict:
    try:
        data = await _post("/api/scheduled-email", {
            "subject": args["subject"],
            "content": args["content"],
            "scheduledTime": args["scheduledTime"],
            "isHtml": args.get("isHtml", False),
        })
        return _ok(data)
    except Exception as e:
        return _err(f"发送定时邮件失败: {e}")


@tool("get_scheduled_email", "查询用户的定时邮件记录，支持分页", {"pageNum": int, "pageSize": int})
async def get_scheduled_email(args: dict) -> dict:
    try:
        data = await _get("/api/scheduled-email/list", {
            "page": args.get("pageNum", 0),
            "size": args.get("pageSize", 10),
        })
        return _ok(data)
    except Exception as e:
        return _err(f"查询定时邮件失败: {e}")


@tool("delete_scheduled_email", "删除指定的定时邮件记录", {"id": str})
async def delete_scheduled_email(args: dict) -> dict:
    try:
        data = await _delete(f"/api/scheduled-email/{args['id']}")
        return _ok(data)
    except Exception as e:
        return _err(f"删除定时邮件失败: {e}")


@tool("web_search", "使用 Google 搜索联网查询实时信息", {"query": str})
async def web_search(args: dict) -> dict:
    if not SERP_KEY:
        return _err("SERP_KEY 未配置")
    params = {
        "engine": "google", "q": args["query"],
        "api_key": SERP_KEY, "hl": "zh-cn", "gl": "cn",
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://serpapi.com/search", params=params) as r:
                data = await r.json()

        results = []
        if "answer_box" in data:
            box = data["answer_box"]
            results.append(f"【直接答案】: {box.get('answer') or box.get('snippet', '')}")
        if "knowledge_graph" in data:
            kg = data["knowledge_graph"]
            results.append(f"【知识图谱】{kg.get('title', '')}: {kg.get('description', '')}")
        for res in data.get("organic_results", [])[:5]:
            results.append(f"【搜索结果】{res.get('title', '')}\n摘要: {res.get('snippet', '')}\n链接: {res.get('link', '')}")

        return _ok("\n\n".join(results) if results else "未找到相关结果")
    except Exception as e:
        return _err(f"搜索失败: {e}")


@tool("wikipedia_search", "维基百科搜索，lang 默认 'zh' 中文", {"query": str, "lang": str})
async def wikipedia_search(args: dict) -> dict:
    lang = args.get("lang", "zh")
    url = f"https://{lang}.wikipedia.org/w/api.php"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params={"action": "query", "format": "json", "list": "search", "srsearch": args["query"], "srlimit": 1, "utf8": 1}) as r:
                search_data = await r.json()

            search = search_data.get("query", {}).get("search", [])
            if not search:
                return _ok("未找到相关维基百科词条")

            title = search[0]["title"]
            async with s.get(url, params={"action": "query", "format": "json", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": title, "utf8": 1}) as r:
                detail = await r.json()

        for pid, pinfo in detail.get("query", {}).get("pages", {}).items():
            if pid != "-1":
                return _ok(f"【维基百科·{title}】\n{pinfo.get('extract', '')}")
        return _ok("无法获取词条内容")
    except Exception as e:
        return _err(f"维基百科搜索失败: {e}")


@tool("toutiao_hot_news", "获取今日头条实时热榜新闻", {"limit": int})
async def toutiao_hot_news(args: dict) -> dict:
    limit = args.get("limit", 10)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://tenapi.cn/v2/toutiaohotnew", headers=headers) as r:
                data = await r.json()

        news_list = data.get("data", [])
        lines = ["【今日头条热榜】"] + [
            f"{i + 1}. {n.get('name', '')}\n   链接: {n.get('url', '')}"
            for i, n in enumerate(news_list[:limit])
        ]
        return _ok("\n".join(lines))
    except Exception as e:
        return _err(f"获取热榜失败: {e}")


@tool("search_domains_info", "搜索域名注册信息", {"query": str, "limit": int})
async def search_domains_info(args: dict) -> dict:
    if not DOMAINSDB_KEY:
        return _err("DOMAINSDB_KEY 未配置")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://api.domainsdb.info/v1/domains/search",
                params={"api_key": DOMAINSDB_KEY, "domain": args["query"], "limit": args.get("limit", 10)},
            ) as r:
                data = await r.json()

        domains = data.get("domains", [])
        lines = [f"共找到 {data.get('total', 0)} 个域名："] + [
            f"• {d.get('domain')} ({d.get('country', 'N/A')}) - 创建时间: {d.get('create_date', 'N/A')}"
            for d in domains
        ]
        return _ok("\n".join(lines))
    except Exception as e:
        return _err(f"域名搜索失败: {e}")


@tool(
    "generate_image_from_text",
    "根据文本描述使用通义万相生成图片。size 可选 '1024*1024'/'720*1280'/'1280*720'",
    {"prompt": str, "size": str, "n": int},
)
async def generate_image_from_text(args: dict) -> dict:
    if not API_KEY or not QWEN_CREATE_URL or not QWEN_GET_URL:
        return _err("图片生成 API 未配置")

    img_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": "wanx-v1",
        "input": {"prompt": args["prompt"]},
        "parameters": {"style": "<auto>", "size": args.get("size", "1024*1024"), "n": args.get("n", 1)},
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(QWEN_CREATE_URL, headers=img_headers, json=payload) as r:
                result = await r.json()

            task_id = result.get("output", {}).get("task_id")
            if not task_id:
                return _err("未能获取任务 ID")

            for _ in range(30):
                await asyncio.sleep(2)
                async with s.get(f"{QWEN_GET_URL}/{task_id}", headers=img_headers) as r:
                    check = await r.json()
                status = check.get("output", {}).get("task_status", "")
                if status == "SUCCEEDED":
                    return _ok({"success": True, "images": check["output"].get("results", [])})
                if status == "FAILED":
                    return _err("图片生成失败")

        return _err("图片生成超时")
    except Exception as e:
        return _err(f"图片生成异常: {e}")


# ─── 注册 MCP 服务器 ──────────────────────────────────────────────────────────

community_server = create_sdk_mcp_server(
    name="community",
    tools=[
        get_time,
        get_weather,
        query_unpaid_bills,
        get_user_notifications,
        read_notification,
        send_private_messages,
        create_visitor,
        search_goods,
        send_scheduled_email,
        get_scheduled_email,
        delete_scheduled_email,
        web_search,
        wikipedia_search,
        toutiao_hot_news,
        search_domains_info,
        generate_image_from_text,
    ],
)
