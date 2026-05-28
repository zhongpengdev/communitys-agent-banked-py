import asyncio
import aiohttp
from claude_agent_sdk import tool
from app.tools_mcp.base import ok_response, error_response, API_KEY, QWEN_CREATE_URL, QWEN_GET_URL

@tool(
    "generate_image_from_text",
    "根据文本描述使用通义万相生成图片。size 可选 '1024*1024'/'720*1280'/'1280*720'",
    {"prompt": str, "size": str, "n": int},
)
async def generate_image_from_text(args: dict) -> dict:
    if not API_KEY or not QWEN_CREATE_URL or not QWEN_GET_URL:
        return error_response("图片生成 API 未配置")

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
                return error_response("未能获取任务 ID")

            for _ in range(30):
                await asyncio.sleep(2)
                async with s.get(f"{QWEN_GET_URL}/{task_id}", headers=img_headers) as r:
                    check = await r.json()
                status = check.get("output", {}).get("task_status", "")
                if status == "SUCCEEDED":
                    return ok_response({"success": True, "images": check["output"].get("results", [])})
                if status == "FAILED":
                    return error_response("图片生成失败")

        return error_response("图片生成超时")
    except Exception as e:
        return error_response(f"图片生成异常: {e}")
