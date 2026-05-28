from claude_agent_sdk import tool
from app.tools_mcp import base

@tool("query_unpaid_bills", "查询用户所有代缴物业费账单", {"status": int})
async def query_unpaid_bills(args: dict) -> dict:
    try:
        data = await base.http_get("/api/property-fee/bills", {"status": args.get("status", 0)})
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"账单查询失败: {e}")


@tool("get_user_notifications", "查询用户通知列表，支持分页", {"pageNum": int, "pageSize": int})
async def get_user_notifications(args: dict) -> dict:
    try:
        data = await base.http_get("/api/notification/list", {
            "pageNum": args.get("pageNum", 0),
            "pageSize": args.get("pageSize", 10),
        })
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"通知查询失败: {e}")


@tool("read_notification", "标记指定通知为已读", {"notificationId": str})
async def read_notification(args: dict) -> dict:
    try:
        data = await base.http_post(f"/api/notification/{args['notificationId']}/read")
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"标记已读失败: {e}")


@tool("send_private_messages", "代替用户向其他用户发送私信", {"content": str, "toUserId": str})
async def send_private_messages(args: dict) -> dict:
    try:
        data = await base.http_post("/api/message/send", {
            "content": args["content"],
            "toUserId": args["toUserId"],
        })
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"发送私信失败: {e}")


@tool(
    "create_visitor",
    "登记访客信息。allowTime 和 validDate 格式必须为 'yyyy-MM-dd HH:mm:ss'",
    {"visitorName": str, "visitorPhone": str, "visitPurpose": str, "allowTime": str, "validDate": str},
)
async def create_visitor(args: dict) -> dict:
    try:
        data = await base.http_post("/api/visitor/register", {
            "visitorName": args["visitorName"],
            "visitorPhone": args["visitorPhone"],
            "visitPurpose": args["visitPurpose"],
            "allowTime": args["allowTime"],
            "validDate": args["validDate"],
        })
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"访客登记失败: {e}")


@tool("search_goods", "搜索社区商城商品，支持关键词和分类筛选", {"keyword": str, "category_id": int, "page_num": int, "page_size": int})
async def search_goods(args: dict) -> dict:
    try:
        data = await base.http_post("/api/mall/list", {
            "categoryId": args.get("category_id", 0),
            "keyword": args.get("keyword"),
            "pageNum": args.get("page_num", 1),
            "pageSize": args.get("page_size", 10),
        })
        return base.ok_response(data)
    except Exception as e:
        return base.error_response(f"商品搜索失败: {e}")
