"""
电子签约与存证服务 (Signature & Traceability Service)
集成第三方电子签章平台（模拟），实现合同签署、规章制度宣贯、公告阅知存证。
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from enum import Enum

class SignStatus(Enum):
    PENDING = "pending"   # 待签署/待阅读
    SIGNED = "signed"     # 已签署/已确认
    REJECTED = "rejected" # 已拒签
    EXPIRED = "expired"   # 已过期

class SignType(Enum):
    CONTRACT = "contract"           # 外部合同 (强校验)
    POLICY_SIGN = "policy_sign"     # 规章制度签字 (强校验: 员工手册等)
    NOTICE_READ = "notice_read"     # 公告阅知 (弱校验: 点击确认即可)

class SignatureService:
    
    def __init__(self):
        # 模拟存储: sign_id -> task_info
        self._tasks: Dict[str, Dict[str, Any]] = {}
        # 模拟存储: batch_id -> [task_ids]
        self._batches: Dict[str, List[str]] = {}
        logger.info("全场景电子签约与存证服务初始化完成")

    async def create_signature_task(
        self, 
        document_id: str, 
        signers: List[Dict[str, str]], 
        initiator_id: str,
        sign_type: SignType = SignType.CONTRACT,
        title: str = "文件签署任务"
    ) -> Dict[str, Any]:
        """
        发起单份/多方签约任务
        """
        task_id = str(uuid.uuid4())
        
        # 模拟调用第三方 API
        action_verb = "read" if sign_type == SignType.NOTICE_READ else "sign"
        signing_url = f"https://esign.example.com/{action_verb}/{task_id}"
        
        task_info = {
            "task_id": task_id,
            "document_id": document_id,
            "title": title,
            "type": sign_type.value,
            "initiator_id": initiator_id,
            "signers": signers,
            "status": SignStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "signing_url": signing_url,
            "audit_trail": [
                {
                    "action": "CREATE",
                    "timestamp": datetime.now().isoformat(),
                    "actor": initiator_id,
                    "detail": f"发起{title}，类型: {sign_type.value}"
                }
            ]
        }
        
        self._tasks[task_id] = task_info
        logger.info(f"创建签署任务: {task_id}, 类型: {sign_type.value}")
        return task_info

    async def create_batch_task(
        self,
        document_id: str,
        signer_list: List[Dict[str, str]], # 全体员工列表
        initiator_id: str,
        sign_type: SignType,
        title: str
    ) -> Dict[str, Any]:
        """
        发起批量分发任务 (如：全员签署员工手册)
        """
        batch_id = str(uuid.uuid4())
        task_ids = []
        
        # 为每个人创建一个独立的签署/阅知任务
        for signer in signer_list:
            task = await self.create_signature_task(
                document_id, [signer], initiator_id, sign_type, title
            )
            task_ids.append(task["task_id"])
            
        self._batches[batch_id] = task_ids
        
        return {
            "batch_id": batch_id,
            "total_count": len(task_ids),
            "message": f"已成功向 {len(task_ids)} 人发送 '{title}' 任务"
        }

    async def get_batch_progress(self, batch_id: str) -> Dict[str, Any]:
        """查询批量任务进度"""
        if batch_id not in self._batches:
            return {"error": "Batch not found"}
            
        task_ids = self._batches[batch_id]
        total = len(task_ids)
        signed = 0
        pending = 0
        
        for tid in task_ids:
            t = self._tasks.get(tid)
            if t and t["status"] == SignStatus.SIGNED.value:
                signed += 1
            else:
                pending += 1
                
        return {
            "batch_id": batch_id,
            "total": total,
            "signed_count": signed,
            "pending_count": pending,
            "completion_rate": f"{(signed/total)*100:.1f}%" if total > 0 else "0%"
        }

    async def mock_sign_action(self, task_id: str, signer_name: str, action: str = "agree", ip_address: str = "192.168.1.101") -> Dict[str, Any]:
        """
        【模拟】用户执行签署/阅知操作 (留痕核心)
        """
        if task_id not in self._tasks:
            return {"error": "Task not found"}
        
        task = self._tasks[task_id]
        
        new_status = SignStatus.SIGNED.value if action == "agree" else SignStatus.REJECTED.value
        task["status"] = new_status
        
        action_name = "阅知确认" if task["type"] == SignType.NOTICE_READ.value else "电子签名"
        
        # 详细留痕：包含 IP、设备、时间精确到毫秒
        task["audit_trail"].append({
            "action": "SIGN" if action == "agree" else "REJECT",
            "timestamp": datetime.now().isoformat(),
            "actor": signer_name,
            "ip": ip_address, 
            "detail": f"用户 {signer_name} 完成 {action_name}，IP: {ip_address}"
        })
        
        if action == "agree":
            # 模拟生成存证哈希
            task["evidence_hash"] = f"tsa_{uuid.uuid4()}_sha256"
            
        logger.info(f"任务 {task_id} ({action_name}) 更新为: {new_status}")
        return task

# 全局实例
signature_service = SignatureService()
