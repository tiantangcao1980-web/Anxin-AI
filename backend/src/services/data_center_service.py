"""
企业数据中心服务 (Data Center Service)
负责企业核心数据、知识数据、管理数据的安全存储、加密保护与权限控制。
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
from loguru import logger
from cryptography.fernet import Fernet
from pydantic import BaseModel

# 模拟数据库
_DATA_STORE = {}

class DataCategory(Enum):
    CORE_ASSET = "core_asset"       # 核心资产 (如：股权结构、财务底表) - 强加密
    KNOWLEDGE = "knowledge"         # 知识数据 (如：行业研报、法律模板) - 向量化+RAG
    MANAGEMENT = "management"       # 管理数据 (如：组织架构、审批日志) - 权限控制
    ARCHIVE = "archive"             # 归档数据 (如：历史合同) - 冷存储

class AccessLevel(Enum):
    L1_PUBLIC = 1      # 全员公开
    L2_INTERNAL = 2    # 内部保密 (部门级)
    L3_CONFIDENTIAL = 3 # 机密 (高管级)
    L4_TOP_SECRET = 4   # 绝密 (仅特定人)

class DataCenterService:
    
    def __init__(self):
        # 初始化加密密钥 (生产环境应从 HSM 或 KMS 获取)
        self._encryption_key = os.getenv("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
        self._cipher = Fernet(self._encryption_key.encode())
        logger.info("企业数据中心服务初始化完成 (加密模块已就绪)")

    def _encrypt(self, data: Union[str, Dict]) -> str:
        """加密数据"""
        if isinstance(data, dict):
            data = json.dumps(data)
        return self._cipher.encrypt(data.encode()).decode()

    def _decrypt(self, token: str) -> Union[str, Dict]:
        """解密数据"""
        decrypted = self._cipher.decrypt(token.encode()).decode()
        try:
            return json.loads(decrypted)
        except:
            return decrypted

    def _check_permission(self, user_role: str, required_level: int) -> bool:
        """简单的权限检查逻辑"""
        # 模拟角色权限映射
        role_levels = {
            "admin": 4,
            "executive": 3,
            "manager": 2,
            "employee": 1,
            "guest": 0
        }
        user_level = role_levels.get(user_role, 0)
        return user_level >= required_level

    async def store_data(
        self, 
        category: DataCategory, 
        key: str, 
        data: Any, 
        owner_id: str, 
        access_level: AccessLevel = AccessLevel.L2_INTERNAL,
        encrypt: bool = True
    ) -> Dict[str, Any]:
        """
        存储数据资产
        """
        record_id = f"{category.value}_{key}"
        
        # 处理内容
        stored_content = data
        is_encrypted = False
        
        # 核心数据强制加密，或根据参数加密
        if category == DataCategory.CORE_ASSET or encrypt:
            stored_content = self._encrypt(data)
            is_encrypted = True
            
        record = {
            "id": record_id,
            "category": category.value,
            "key": key,
            "content": stored_content,
            "owner_id": owner_id,
            "access_level": access_level.value,
            "is_encrypted": is_encrypted,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1
        }
        
        # 存入模拟数据库 (实际应存入 PG 或 MinIO)
        _DATA_STORE[record_id] = record
        
        logger.info(f"数据资产已存储: {record_id} (加密: {is_encrypted}, 等级: {access_level.name})")
        return {"id": record_id, "status": "stored"}

    async def retrieve_data(self, record_id: str, user_id: str, user_role: str) -> Dict[str, Any]:
        """
        获取数据资产 (包含解密和权限校验)
        """
        record = _DATA_STORE.get(record_id)
        if not record:
            raise ValueError("Data not found")
            
        # 1. 权限校验
        if not self._check_permission(user_role, record["access_level"]):
            # 如果是 Owner 本人，允许访问
            if record["owner_id"] != user_id:
                logger.warning(f"用户 {user_id} ({user_role}) 尝试访问 {record_id} 被拒绝")
                raise PermissionError("Access denied: insufficient permission")

        # 2. 数据解密
        content = record["content"]
        if record["is_encrypted"]:
            try:
                content = self._decrypt(content)
            except Exception as e:
                logger.error(f"解密失败: {e}")
                raise ValueError("Data corruption or decryption failed")
                
        # 返回脱敏后的元数据和明文内容
        return {
            "id": record["id"],
            "key": record["key"],
            "category": record["category"],
            "content": content,
            "updated_at": record["updated_at"]
        }

    async def list_data(self, category: Optional[DataCategory], user_role: str) -> List[Dict[str, Any]]:
        """列出可见的数据资产"""
        results = []
        for pid, record in _DATA_STORE.items():
            if category and record["category"] != category.value:
                continue
            
            # 权限过滤
            if self._check_permission(user_role, record["access_level"]):
                results.append({
                    "id": record["id"],
                    "key": record["key"],
                    "category": record["category"],
                    "access_level": record["access_level"],
                    "is_encrypted": record["is_encrypted"]
                })
        return results

# 全局实例
data_center_service = DataCenterService()
