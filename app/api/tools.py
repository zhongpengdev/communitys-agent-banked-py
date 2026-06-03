"""
工具相关 API 路由
"""
from fastapi import APIRouter
from app.tools.tool_metadata import get_all_tools_metadata
from app.schemas import ToolMetadataResponse

router = APIRouter(prefix="/api/tools", tags=["工具"])


@router.get("/metadata", response_model=ToolMetadataResponse)
async def get_tools_metadata():
    """
    获取所有工具的元数据
    
    返回工具名称、显示名称、描述、图标等信息
    供前端展示使用
    """
    return {
        "success": True,
        "data": get_all_tools_metadata()
    }

