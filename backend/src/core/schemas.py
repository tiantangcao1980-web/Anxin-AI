# -*- coding: utf-8 -*-
"""
通用 Pydantic 模型：分页参数、分页响应等。
"""

from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    items: list = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    has_next: bool = Field(default=False)
