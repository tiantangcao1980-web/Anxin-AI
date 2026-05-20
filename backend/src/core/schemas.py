"""
通用 Pydantic 模型：分页参数、分页响应等。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class APIModel(BaseModel):
    """API 默认基类：Python 端 snake_case，序列化为 camelCase。

    历史名为 ``CamelModel``（指 camelCase 别名生成器），与 CAMEL-AI 框架无关。
    为避免品牌/框架混淆已重命名为 ``APIModel``。
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# 历史别名：5 处路由仍在使用 CamelModel，保留兼容以便单 PR 渐进迁移。
CamelModel = APIModel


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    items: list[Any] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_next: bool = Field(default=False)
