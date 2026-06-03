from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    """统一 API 响应结构"""
    model_config = ConfigDict(from_attributes=True)

    code: int = Field(200, description="状态码，200 表示成功")
    message: str = Field("成功", description="响应消息说明")
    data: Optional[T] = Field(None, description="响应数据")

class PageData(BaseModel, Generic[T]):
    """分页数据包"""
    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(default=[], description="当前页数据列表")
    total: int = Field(0, description="数据总条数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(10, description="每页条数")

class PaginatedResponse(BaseResponse[PageData[T]], Generic[T]):
    """统一分页响应结构"""
    pass
