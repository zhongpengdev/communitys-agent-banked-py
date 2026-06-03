from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class MessageResponse(BaseModel):
    """消息详细信息"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="消息 ID")
    session_id: int = Field(..., description="所属会话 ID")
    role: str = Field(..., description="角色 (user/assistant)")
    content: str = Field(..., description="消息内容")
    created_at: Optional[str] = Field(None, description="创建时间（ISO 格式）")
