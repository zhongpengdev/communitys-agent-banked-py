import aiohttp
from claude_agent_sdk import tool
from app.tools_mcp import base

@tool("web_search", "使用 Google 搜索联网查询实时信息", {"query": str})
async def web_search(args: dict) -> dict:
    if not base.SERP_KEY:
        return base.error_response("SERP_KEY 未配置")
    params = {
        "engine": "google", "q": args["query"],
        "api_key": base.SERP_KEY, "hl": "zh-cn", "gl": "cn",
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

        return base.ok_response("\n\n".join(results) if results else "未找到相关结果")
    except Exception as e:
        return base.error_response(f"搜索失败: {e}")


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
                return base.ok_response("未找到相关维基百科词条")

            title = search[0]["title"]
            async with s.get(url, params={"action": "query", "format": "json", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": title, "utf8": 1}) as r:
                detail = await r.json()

        for pid, pinfo in detail.get("query", {}).get("pages", {}).items():
            if pid != "-1":
                return base.ok_response(f"【维基百科·{title}】\n{pinfo.get('extract', '')}")
        return base.ok_response("无法获取词条内容")
    except Exception as e:
        return base.error_response(f"维基百科搜索失败: {e}")


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
        return base.ok_response("\n".join(lines))
    except Exception as e:
        return base.error_response(f"获取热榜失败: {e}")


@tool("search_domains_info", "搜索域名注册信息", {"query": str, "limit": int})
async def search_domains_info(args: dict) -> dict:
    if not base.DOMAINSDB_KEY:
        return base.error_response("DOMAINSDB_KEY 未配置")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://api.domainsdb.info/v1/domains/search",
                params={"api_key": base.DOMAINSDB_KEY, "domain": args["query"], "limit": args.get("limit", 10)},
            ) as r:
                data = await r.json()

        domains = data.get("domains", [])
        lines = [f"共找到 {data.get('total', 0)} 个域名："] + [
            f"• {d.get('domain')} ({d.get('country', 'N/A')}) - 创建时间: {d.get('create_date', 'N/A')}"
            for d in domains
        ]
        return base.ok_response("\n".join(lines))
    except Exception as e:
        return base.error_response(f"域名搜索失败: {e}")
