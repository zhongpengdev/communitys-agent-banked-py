from claude_agent_sdk import tool
from app.tools_mcp.base import http_get, http_post, http_delete, ok_response, error_response

@tool(
    "send_scheduled_email",
    "发送定时邮件。scheduledTime 格式为 '2026-01-20T14:30:00'",
    {"subject": str, "content": str, "scheduledTime": str, "isHtml": bool},
)
async def send_scheduled_email(args: dict) -> dict:
    try:
        data = await http_post("/api/scheduled-email", {
            "subject": args["subject"],
            "content": args["content"],
            "scheduledTime": args["scheduledTime"],
            "isHtml": args.get("isHtml", False),
        })
        return ok_response(data)
    except Exception as e:
        return error_response(f"发送定时邮件失败: {e}")


@tool("get_scheduled_email", "查询用户的定时邮件记录，支持分页", {"pageNum": int, "pageSize": int})
async def get_scheduled_email(args: dict) -> dict:
    try:
        data = await http_get("/api/scheduled-email/list", {
            "page": args.get("pageNum", 0),
            "size": args.get("pageSize", 10),
        })
        return ok_response(data)
    except Exception as e:
        return error_response(f"查询定时邮件失败: {e}")


@tool("delete_scheduled_email", "删除指定的定时邮件记录", {"id": str})
async def delete_scheduled_email(args: dict) -> dict:
    try:
        data = await http_delete(f"/api/scheduled-email/{args['id']}")
        return ok_response(data)
    except Exception as e:
        return error_response(f"删除定时邮件失败: {e}")
