from pydantic import BaseModel, Field, ConfigDict

class ToolMetadata(BaseModel):
    """工具元数据信息"""
    model_config = ConfigDict(from_attributes=True)

    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="描述信息")
    icon: str = Field(..., description="图标名称")
    category: str = Field(..., description="分类")
