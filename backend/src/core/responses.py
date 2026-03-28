"""
统一响应格式处理
"""

from typing import Any, Optional, Dict
from pydantic import BaseModel
import uuid

class UnifiedResponse(BaseModel):
    """统一响应结构"""
    code: int = 200
    data: Any = None
    message: str = "success"
    request_id: str = ""

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> Dict[str, Any]:
        """成功响应"""
        return {
            "code": 200,
            "data": data,
            "message": message,
            "request_id": str(uuid.uuid4())
        }

    @classmethod
    def error(cls, code: int = 400, message: str = "error", data: Any = None) -> Dict[str, Any]:
        """错误响应"""
        return {
            "code": code,
            "data": data,
            "message": message,
            "request_id": str(uuid.uuid4())
        }
