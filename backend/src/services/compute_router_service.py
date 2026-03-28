from typing import Optional, Tuple, Dict
from src.core.privacy import SensitivityLevel, InferenceRequest, HardwareInterface, ComputeNodeStatus, HardwareCapabilities
from src.services.pii_service import pii_service

class MockLocalHardware(HardwareInterface):
    """
    模拟的本地硬件实现（用于开发阶段或纯软模式）
    """
    def __init__(self):
        self._status = ComputeNodeStatus.ONLINE
    
    async def get_status(self) -> ComputeNodeStatus:
        return self._status
    
    async def get_capabilities(self) -> HardwareCapabilities:
        # 模拟当前PC的能力
        return HardwareCapabilities(
            model_support=["local-tiny-llama"],
            npu_ops=0.0,
            has_secure_enclave=False,
            memory_gb=8.0
        )
    
    async def infer_local(self, request: InferenceRequest) -> str:
        # 这里在实际产品中会调用本地运行的小模型
        return f"【🔒 本地安全模式】\n您的数据已在本地硬件完成处理，未上传至任何云端服务器。\n\n针对您的问题：{request.prompt}\n\n(此处模拟本地小模型生成的法律建议...)"

class ComputeRouterService:
    """
    智能算力路由服务
    根据数据敏感度和硬件状态，决定由谁来处理请求
    """
    def __init__(self, local_hardware: Optional[HardwareInterface] = None):
        self.local_hardware = local_hardware or MockLocalHardware()
        
    async def route_request(self, request: InferenceRequest) -> Tuple[str, Optional[Dict[str, str]]]:
        """
        核心路由逻辑
        Returns:
            (processed_prompt_or_result, recovery_map)
            - 如果是本地处理，直接返回结果字符串
            - 如果是云端/混合，返回处理过的 prompt 和 还原映射表
        """
        print(f"Routing request with sensitivity: {request.sensitivity}")
        
        # 策略 1: 绝密数据 -> 强制本地
        if request.sensitivity == SensitivityLevel.CONFIDENTIAL:
            status = await self.local_hardware.get_status()
            if status == ComputeNodeStatus.ONLINE:
                result = await self.local_hardware.infer_local(request)
                return result, None # 直接返回最终结果
            else:
                # 硬件掉线时的降级策略：报错或排队，绝不上传
                raise Exception("Security Alert: Sensitive data requires local hardware, but device is offline.")
        
        # 策略 2: 混合数据 -> 脱敏后上云
        elif request.sensitivity == SensitivityLevel.HYBRID:
            anonymized_prompt, recovery_map = pii_service.scrub(request.prompt)
            return anonymized_prompt, recovery_map
            
        # 策略 3: 公开数据 -> 直接上云
        else:
            return request.prompt, None

    async def get_hardware_status(self):
        return await self.local_hardware.get_status()

# 单例模式导出
compute_router = ComputeRouterService()
