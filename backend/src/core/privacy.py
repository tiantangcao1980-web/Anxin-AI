from enum import Enum
from typing import List, Dict, Any, Optional, Protocol
from pydantic import BaseModel

class SensitivityLevel(str, Enum):
    """
    数据敏感度分级
    """
    # L1: 绝密 - 必须完全在本地硬件/私有环境处理，严禁上传公有云
    CONFIDENTIAL = "CONFIDENTIAL"
    
    # L2: 混合 - 包含敏感信息，但允许脱敏后上传，或使用受信任的私有云
    HYBRID = "HYBRID"
    
    # L3: 公开 - 非敏感数据，可使用公有云大模型以获得最佳效果
    PUBLIC = "PUBLIC"

class ComputeNodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"

class HardwareCapabilities(BaseModel):
    """
    硬件算力能力描述
    """
    model_support: List[str]  # e.g. ["llama3-8b-quantized", "mistral-7b"]
    npu_ops: float            # TOPS (Trillions of Operations Per Second)
    has_secure_enclave: bool  # 是否有安全芯片
    memory_gb: float          # 显存/内存大小

class InferenceRequest(BaseModel):
    prompt: str
    context_data: Optional[Dict[str, Any]] = None
    sensitivity: SensitivityLevel = SensitivityLevel.PUBLIC
    max_tokens: int = 1000

class HardwareInterface(Protocol):
    """
    硬件抽象层接口 (HAL)
    未来适配专用AI盒子时，只需实现此接口
    """
    async def get_status(self) -> ComputeNodeStatus:
        ...
        
    async def get_capabilities(self) -> HardwareCapabilities:
        ...
        
    async def infer_local(self, request: InferenceRequest) -> str:
        """
        在本地硬件上执行推理
        """
        ...
