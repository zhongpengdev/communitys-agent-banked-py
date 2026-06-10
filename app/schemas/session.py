from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class NewSessionRequest(BaseModel):
    """创建新会话请求结构"""
    content: str = Field(..., description="用户发送的第一句话")
    title: str = Field("新对话", description="默认会话标题")

class SessionCreateResponseData(BaseModel):
    """创建会话成功后的响应数据"""
    model_config = ConfigDict(from_attributes=True)
    
    sessionId: int = Field(..., description="新创建的会话 ID")
    title: str = Field(..., description="会话标题")

class SessionResponse(BaseModel):
    """会话详细信息"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="会话 ID")
    user_id: Optional[str] = Field(None, description="所属用户 ID")
    title: Optional[str] = Field(None, description="会话标题")
    created_at: Optional[str] = Field(None, description="创建时间（ISO 格式）")

class SessionRenameRequest(BaseModel):
    """会话重命名请求结构"""
    session_id: int = Field(..., description="会话 ID")
    rename_title: str = Field(..., description="新的会话标题")
