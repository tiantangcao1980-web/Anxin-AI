from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required, get_admin_user
from src.services.data_center_service import data_center_service, DataCategory, AccessLevel
from src.models.user import User

router = APIRouter()

class DataStoreRequest(BaseModel):
    category: str # core_asset, knowledge, management, archive
    key: str
    data: Dict[str, Any]
    access_level: int = 2
    encrypt: bool = True

class DataResponse(BaseModel):
    id: str
    key: str
    category: str
    content: Dict[str, Any]

@router.post("/store", summary="存储核心数据")
async def store_data(
    req: DataStoreRequest,
    user: User = Depends(get_current_user_required),
):
    """
    存储数据到企业数据中心 (支持自动加密)
    """
    try:
        category_enum = DataCategory(req.category)
        level_enum = AccessLevel(req.access_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category or access level")

    result = await data_center_service.store_data(
        category=category_enum,
        key=req.key,
        data=req.data,
        owner_id=str(user.id),
        access_level=level_enum,
        encrypt=req.encrypt
    )
    return result

@router.get("/retrieve/{record_id}", summary="读取核心数据")
async def retrieve_data(
    record_id: str,
    user: User = Depends(get_current_user_required),
):
    """
    读取并解密数据 (需要权限)
    """
    try:
        data = await data_center_service.retrieve_data(record_id, str(user.id), user.role)
        return data
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/list", summary="列出数据资产")
async def list_data(
    category: Optional[str] = None,
    user: User = Depends(get_current_user_required),
):
    """
    列出当前用户可见的数据资产
    """
    cat_enum = DataCategory(category) if category else None
    return await data_center_service.list_data(cat_enum, user.role)
