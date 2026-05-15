from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.data_center_service import AccessLevel, DataCategory, data_center_service

router = APIRouter()


def _max_access_level_for_role(role: str) -> int:
    if role in {"super_admin", "admin"}:
        return 4
    if role in {"org_admin", "partner", "executive"}:
        return 3
    if role in {"dept_admin", "lawyer", "manager"}:
        return 2
    return 1


class DataStoreRequest(BaseModel):
    category: str  # core_asset, knowledge, management, archive
    key: str
    data: dict[str, Any]
    access_level: int = 2
    encrypt: bool = True


class DataResponse(BaseModel):
    id: str
    key: str
    category: str
    content: dict[str, Any]


@router.post("/store", summary="存储核心数据")
async def store_data(
    req: DataStoreRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    存储数据到企业数据中心 (支持自动加密)
    """
    try:
        category_enum = DataCategory(req.category)
        level_enum = AccessLevel(req.access_level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid category or access level") from e

    if req.access_level > _max_access_level_for_role(user.role):
        raise HTTPException(status_code=403, detail="无权设置该访问等级")

    result = await data_center_service.store_data(
        category=category_enum,
        key=req.key,
        data=req.data,
        owner_id=str(user.id),
        access_level=level_enum,
        encrypt=req.encrypt,
    )
    return result


@router.get("/retrieve/{record_id}", summary="读取核心数据")
async def retrieve_data(
    record_id: str,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """
    读取并解密数据 (需要权限)
    """
    try:
        data = await data_center_service.retrieve_data(record_id, str(user.id), user.role)
        return data
    except PermissionError as e:
        raise HTTPException(status_code=403, detail="Access denied") from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/list", summary="列出数据资产")
async def list_data(
    category: str | None = None,
    user: User = Depends(get_current_user_required),
) -> list[dict[str, Any]]:
    """
    列出当前用户可见的数据资产
    """
    cat_enum = DataCategory(category) if category else None
    return await data_center_service.list_data(cat_enum, user.role, str(user.id))
