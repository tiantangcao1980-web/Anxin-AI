"""
多Agent协作基础设施

1. AgentContext: 每个 Agent 在一次任务中拥有独立的、隔离的上下文空间
2. MessagePool: Agent 通过直接通信和同步通信方式将关键信息发布到公共消息池
3. AgentLifecycleManager: Agent 生命周期管理 — 重试、替换、接管
4. MemoryIntegration: 三层记忆系统与多 Agent 协作的集成层
"""

import asyncio
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger

from src.core.config import settings


# ========== 1. Agent 独立上下文 ==========

@dataclass
class AgentContext:
    """单个 Agent 的独立任务上下文"""
    
    agent_id: str
    agent_name: str
    task_id: str
    local_state: Dict[str, Any] = field(default_factory=dict)
    reasoning_chain: List[str] = field(default_factory=list)
    input_context: Dict[str, Any] = field(default_factory=dict)
    output_artifacts: List[Dict] = field(default_factory=list)
    status: str = "idle"  # idle / working / completed / failed / retrying
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    
    def set_local(self, key: str, value: Any):
        """设置私有状态"""
        self.local_state[key] = value
    
    def get_local(self, key: str, default: Any = None) -> Any:
        """获取私有状态"""
        return self.local_state.get(key, default)
    
    def add_reasoning(self, step: str):
        """添加推理链步骤"""
        self.reasoning_chain.append(f"[{time.strftime('%H:%M:%S')}] {step}")
    
    def to_snapshot(self) -> dict:
        """导出快照（用于持久化或接管传递）"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "local_state": self.local_state.copy(),
            "reasoning_chain": list(self.reasoning_chain),
            "input_context": self.input_context.copy(),
            "output_artifacts": list(self.output_artifacts),
            "status": self.status,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_snapshot(cls, snapshot: dict) -> 'AgentContext':
        """从快照恢复（用于 Agent 重启/接管时继承前任的推理链）"""
        ctx = cls(
            agent_id=snapshot.get("agent_id", str(uuid.uuid4())[:8]),
            agent_name=snapshot.get("agent_name", "unknown"),
            task_id=snapshot.get("task_id", ""),
        )
        ctx.local_state = snapshot.get("local_state", {})
        ctx.reasoning_chain = snapshot.get("reasoning_chain", [])
        ctx.input_context = snapshot.get("input_context", {})
        ctx.output_artifacts = snapshot.get("output_artifacts", [])
        ctx.status = snapshot.get("status", "idle")
        ctx.retry_count = snapshot.get("retry_count", 0)
        ctx.created_at = snapshot.get("created_at", time.time())
        return ctx


# ========== 2. 公共消息池 ==========

@dataclass
class PoolMessage:
    """消息池中的单条消息"""
    id: str
    sender: str
    topic: str        # finding / alignment / dependency / warning / request
    content: Any
    priority: str     # normal / high / critical
    timestamp: float
    

class MessagePool:
    """
    多Agent公共消息池
    
    Agent 通过直接通信和同步通信两种方式将关键信息发布到公共消息池。
    基于内存实现，可通过 MemoryIntegration 桥接到 Redis。
    """
    
    def __init__(self, task_id: str, session_id: str = ""):
        self.task_id = task_id
        self.session_id = session_id
        self.messages: List[PoolMessage] = []
        self._lock = asyncio.Lock()
        self._subscribers: Dict[str, List[asyncio.Event]] = {}
    
    async def publish(self, sender: str, topic: str, content: Any, priority: str = "normal"):
        """
        Agent 发布消息到公共池（直接通信 — 立即写入，立即可见）
        
        topic 类型:
        - "finding"    : 发现了关键信息
        - "alignment"  : 对齐信息（任务理解、方向确认）
        - "dependency" : 依赖结果已就绪
        - "warning"    : 警告（发现冲突、不一致等）
        - "request"    : 请求其他 Agent 协助
        """
        msg = PoolMessage(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            topic=topic,
            content=content,
            priority=priority,
            timestamp=time.time(),
        )
        async with self._lock:
            self.messages.append(msg)
        
        # 通知等待此 topic 的订阅者
        events = self._subscribers.get(topic, [])
        for event in events:
            event.set()
        
        logger.debug(f"[MessagePool] {sender} -> {topic}: {str(content)[:80]}")
    
    async def wait_for(self, topic: str, sender: str = None, timeout: float = 60) -> Optional[PoolMessage]:
        """同步通信 — 阻塞等待公共池中出现特定 topic 的消息（有超时保护）"""
        # 先检查已有消息
        existing = await self.get_messages(topic=topic, sender=sender)
        if existing:
            return existing[-1]
        
        # 创建 Event 等待
        event = asyncio.Event()
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(event)
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            messages = await self.get_messages(topic=topic, sender=sender)
            return messages[-1] if messages else None
        except asyncio.TimeoutError:
            logger.warning(f"[MessagePool] wait_for({topic}) 超时 ({timeout}s)")
            return None
        finally:
            if event in self._subscribers.get(topic, []):
                self._subscribers[topic].remove(event)
    
    async def get_messages(self, topic: str = None, sender: str = None, since: float = None) -> List[PoolMessage]:
        """查询消息"""
        async with self._lock:
            result = list(self.messages)
        
        if topic:
            result = [m for m in result if m.topic == topic]
        if sender:
            result = [m for m in result if m.sender == sender]
        if since:
            result = [m for m in result if m.timestamp >= since]
        
        return result
    
    async def get_latest_by_sender(self, sender: str) -> Optional[PoolMessage]:
        """获取某 Agent 最新的消息"""
        msgs = await self.get_messages(sender=sender)
        return msgs[-1] if msgs else None
    
    def to_dict(self) -> dict:
        """序列化为 dict（用于持久化）"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "messages": [
                {
                    "id": m.id, "sender": m.sender, "topic": m.topic,
                    "content": m.content, "priority": m.priority,
                    "timestamp": m.timestamp,
                }
                for m in self.messages
            ],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MessagePool':
        """从 dict 恢复"""
        pool = cls(task_id=data.get("task_id", ""), session_id=data.get("session_id", ""))
        for m in data.get("messages", []):
            pool.messages.append(PoolMessage(**m))
        return pool


# ========== 3. Agent 生命周期管理器 ==========

MAX_TASK_RETRIES = settings.AGENT_MAX_RETRIES            # 单任务最大重试次数（默认 2）
TASK_TIMEOUT_SECONDS = settings.AGENT_TASK_TIMEOUT       # 单任务超时（默认 120s）

# Agent 能力映射表（某 Agent 失败后，可以被哪些替代）
AGENT_REPLACEMENT_MAP: Dict[str, List[str]] = {
    "contract_reviewer": ["legal_advisor", "compliance_officer"],
    "risk_assessor": ["legal_advisor", "compliance_officer"],
    "document_drafter": ["legal_advisor"],
    "legal_researcher": ["legal_advisor"],
    "due_diligence": ["legal_advisor"],
    "litigation_strategist": ["legal_advisor", "legal_researcher"],
    "ip_specialist": ["legal_advisor"],
    "regulatory_monitor": ["legal_advisor", "compliance_officer"],
    "tax_compliance": ["legal_advisor", "compliance_officer"],
    "labor_compliance": ["legal_advisor"],
    "evidence_analyst": ["legal_advisor"],
    "contract_steward": ["legal_advisor"],
}


class AgentLifecycleManager:
    """
    Agent 生命周期管理器
    
    负责 Agent 的健康监控、故障检测和自动恢复。
    故障恢复策略（按优先级）：
    1. 重试同一 Agent（可恢复错误，最多 2 次，超时递增）
    2. 替换为备选 Agent（查找能力映射表，传递 AgentContext 快照）
    3. 降级输出（所有恢复策略失败后，生成明确的降级响应）
    """
    
    def __init__(self, agents: dict, ws_callback=None):
        self.agents = agents
        self._ws_callback = ws_callback
        self.agent_health: Dict[str, Dict[str, Any]] = {}
    
    async def _notify(self, event_type: str, data: dict):
        """发送 WebSocket 事件"""
        if self._ws_callback:
            try:
                await self._ws_callback(event_type, data)
            except Exception:
                pass
    
    async def execute_with_lifecycle(
        self,
        agent_name: str,
        task_info: dict,
        agent_context: AgentContext,
        message_pool: MessagePool,
        context: dict,
    ):
        """
        带生命周期管理的 Agent 执行
        
        Returns:
            AgentResponse 或降级响应
        """
        from src.agents.base import AgentResponse, _task_llm_config_var
        
        for attempt in range(MAX_TASK_RETRIES + 1):
            try:
                agent_context.status = "working"
                agent_context.retry_count = attempt
                agent_context.add_reasoning(f"开始执行 (尝试 {attempt + 1})")
                
                timeout = self._get_timeout(agent_name, attempt)
                
                # 设置 LLM 配置上下文
                llm_config = context.get("llm_config")
                token = _task_llm_config_var.set(llm_config)
                
                try:
                    agent_obj = self.agents.get(agent_name)
                    if not agent_obj:
                        raise Exception(f"未找到 Agent: {agent_name}")
                    
                    result = await asyncio.wait_for(
                        agent_obj.process({
                            "description": task_info.get("instruction", ""),
                            "context": context,
                            "dependent_results": task_info.get("dependent_results", {}),
                            "llm_config": llm_config,
                        }),
                        timeout=timeout,
                    )
                finally:
                    _task_llm_config_var.reset(token)
                
                # 检查结果
                if isinstance(result, AgentResponse) and not result.metadata.get("error"):
                    agent_context.status = "completed"
                    agent_context.add_reasoning(f"执行成功")
                    agent_context.output_artifacts.append({
                        "content": result.content[:500],
                        "agent": result.agent_name,
                    })
                    
                    # 发布成果到消息池
                    await message_pool.publish(
                        agent_name, "finding",
                        {"summary": result.content[:200], "agent": agent_name},
                    )
                    
                    self.agent_health[agent_name] = {"status": "healthy", "last_success": time.time()}
                    return result
                
                # 有错误的响应
                error_msg = result.content if isinstance(result, AgentResponse) else str(result)
                
                if self._is_recoverable(error_msg) and attempt < MAX_TASK_RETRIES:
                    agent_context.status = "retrying"
                    agent_context.add_reasoning(f"可恢复错误，准备重试: {error_msg[:100]}")
                    
                    await message_pool.publish(
                        agent_name, "warning",
                        f"执行出错，正在重试 ({attempt + 1}/{MAX_TASK_RETRIES})",
                    )
                    await self._notify("agent_task_retry", {
                        "task_id": task_info.get("id"),
                        "agent": agent_name,
                        "attempt": attempt + 1,
                        "max_retries": MAX_TASK_RETRIES,
                        "reason": error_msg[:100],
                    })
                    continue
                
                # 不可恢复错误 → 尝试替换 Agent
                replacement = self._find_replacement(agent_name)
                if replacement:
                    agent_context.add_reasoning(f"不可恢复，尝试由 {replacement} 接管")
                    
                    new_ctx = AgentContext.from_snapshot(agent_context.to_snapshot())
                    new_ctx.agent_name = replacement
                    new_ctx.input_context["takeover_from"] = agent_name
                    new_ctx.input_context["previous_reasoning"] = agent_context.reasoning_chain
                    
                    await message_pool.publish(
                        "system", "alignment",
                        f"{agent_name} 失败，由 {replacement} 接管",
                        priority="high",
                    )
                    await self._notify("agent_replaced", {
                        "task_id": task_info.get("id"),
                        "failed_agent": agent_name,
                        "replacement_agent": replacement,
                    })
                    
                    # 执行替代 Agent（不递归 lifecycle，直接执行一次）
                    try:
                        replacement_obj = self.agents.get(replacement)
                        if replacement_obj:
                            token2 = _task_llm_config_var.set(llm_config)
                            try:
                                takeover_instruction = (
                                    task_info.get("instruction", "")
                                    + f"\n\n[接管上下文] 原 Agent '{agent_name}' 执行失败。"
                                    f"推理链: {'; '.join(agent_context.reasoning_chain[-3:])}"
                                )
                                replacement_result = await asyncio.wait_for(
                                    replacement_obj.process({
                                        "description": takeover_instruction,
                                        "context": context,
                                        "dependent_results": task_info.get("dependent_results", {}),
                                        "llm_config": llm_config,
                                    }),
                                    timeout=self._get_timeout(replacement, 0),
                                )
                                return replacement_result
                            finally:
                                _task_llm_config_var.reset(token2)
                    except Exception as rep_err:
                        logger.error(f"替代 Agent {replacement} 也失败: {rep_err}")
                
                # 所有恢复策略失败 → 降级输出
                return self._create_degraded_response(agent_name, error_msg)
                
            except asyncio.TimeoutError:
                agent_context.add_reasoning(f"超时 ({self._get_timeout(agent_name, attempt)}s)")
                if attempt < MAX_TASK_RETRIES:
                    await self._notify("agent_task_retry", {
                        "task_id": task_info.get("id"),
                        "agent": agent_name,
                        "attempt": attempt + 1,
                        "reason": "timeout",
                    })
                    continue
                
                self.agent_health[agent_name] = {"status": "failed", "last_failure": time.time()}
                return self._create_timeout_response(agent_name, attempt)
            
            except Exception as e:
                agent_context.add_reasoning(f"异常: {str(e)[:100]}")
                logger.error(f"AgentLifecycle: {agent_name} 异常: {e}")
                if attempt < MAX_TASK_RETRIES:
                    continue
                return self._create_degraded_response(agent_name, str(e))
        
        return self._create_degraded_response(agent_name, "超过最大重试次数")
    
    def _find_replacement(self, failed_agent: str) -> Optional[str]:
        """查找能接管的替代 Agent"""
        candidates = AGENT_REPLACEMENT_MAP.get(failed_agent, [])
        for c in candidates:
            health = self.agent_health.get(c, {})
            if health.get("status") != "failed" and c in self.agents:
                return c
        return None
    
    def _is_recoverable(self, error_msg: str) -> bool:
        """判断是否为可恢复错误"""
        recoverable_patterns = ["timeout", "超时", "429", "rate limit", "connection", "连接"]
        return any(p in error_msg.lower() for p in recoverable_patterns)
    
    def _get_timeout(self, agent_name: str, attempt: int) -> float:
        """动态超时：每次重试增加 50%"""
        return TASK_TIMEOUT_SECONDS * (1.5 ** attempt)
    
    def _create_degraded_response(self, agent_name: str, error_msg: str):
        """创建降级响应"""
        from src.agents.base import AgentResponse
        return AgentResponse(
            agent_name=agent_name,
            content=f"[降级输出] {agent_name} 执行失败: {error_msg[:200]}。建议稍后重试或换用其他方式。",
            metadata={"error": True, "degraded": True},
        )
    
    def _create_timeout_response(self, agent_name: str, attempt: int):
        """创建超时响应"""
        from src.agents.base import AgentResponse
        return AgentResponse(
            agent_name=agent_name,
            content=f"[超时] {agent_name} 在 {MAX_TASK_RETRIES + 1} 次尝试后仍超时，请简化问题或稍后重试。",
            metadata={"error": True, "timeout": True},
        )


# ========== 4. 三层记忆集成 ==========

class MemoryIntegration:
    """
    记忆系统与多Agent协作的集成层
    
    - L1 工作记忆 (Redis): Agent上下文持久化 + 消息池状态
    - L2 情景记忆 (Qdrant): 历史任务经验检索
    - L3 语义记忆 (Qdrant+PG): 法律知识增强
    """
    
    def __init__(self, session_id: str = "", task_id: str = ""):
        self.session_id = session_id
        self.task_id = task_id
    
    # === L1 工作记忆：Agent上下文持久化 ===
    async def save_agent_context(self, agent_context: AgentContext):
        """持久化 AgentContext 到 WorkingMemory.agent_states"""
        try:
            from src.core.memory.working_memory import WorkingMemoryService
            wm = WorkingMemoryService()
            await wm.ensure_initialized()
            if wm.redis and self.session_id:
                await wm.set_agent_state(
                    self.session_id,
                    agent_context.agent_name,
                    agent_context.to_snapshot(),
                )
        except Exception as e:
            logger.warning(f"保存 AgentContext 失败: {e}")
    
    async def restore_agent_context(self, agent_name: str) -> Optional[AgentContext]:
        """从 WorkingMemory 恢复 AgentContext"""
        try:
            from src.core.memory.working_memory import WorkingMemoryService
            wm = WorkingMemoryService()
            await wm.ensure_initialized()
            if wm.redis and self.session_id:
                state = await wm.get_agent_state(self.session_id, agent_name)
                if state:
                    return AgentContext.from_snapshot(state)
        except Exception as e:
            logger.warning(f"恢复 AgentContext 失败: {e}")
        return None
    
    async def save_message_pool(self, pool: MessagePool):
        """消息池状态同步到 shared_variables"""
        try:
            from src.core.memory.working_memory import WorkingMemoryService
            wm = WorkingMemoryService()
            await wm.ensure_initialized()
            if wm.redis and self.session_id:
                await wm.set_shared_variable(
                    self.session_id,
                    f"message_pool:{self.task_id}",
                    pool.to_dict(),
                )
        except Exception as e:
            logger.warning(f"保存 MessagePool 失败: {e}")
    
    # === L2 情景记忆：Agent 执行中按需查询历史经验 ===
    async def query_similar_experience(self, agent_name: str, sub_task: str) -> List[dict]:
        """查询与当前子任务相似的历史经验"""
        try:
            from src.services.episodic_memory_service import episodic_memory
            results = await episodic_memory.retrieve_similar_cases(
                f"Agent:{agent_name} 任务:{sub_task}",
                top_k=3,
            )
            return results or []
        except Exception as e:
            logger.warning(f"情景记忆查询失败: {e}")
            return []
    
    # === L3 跨层检索：Agent 执行中增强知识 ===
    async def enhance_agent_knowledge(self, agent_name: str, query: str) -> dict:
        """通过三层记忆增强 Agent 的知识基础"""
        result = {
            "similar_cases": [],
            "legal_knowledge": [],
            "session_context": {},
        }
        
        # L2: 情景记忆
        try:
            from src.services.episodic_memory_service import episodic_memory
            result["similar_cases"] = await episodic_memory.retrieve_similar_cases(query, top_k=2) or []
        except Exception as e:
            logger.debug(f"情景记忆检索失败: {e}")
        
        # L3: 语义记忆
        try:
            from src.core.memory.semantic_memory import SemanticMemoryService
            sm = SemanticMemoryService()
            result["legal_knowledge"] = await sm.search(query, top_k=3) or []
        except Exception as e:
            logger.debug(f"语义记忆检索失败: {e}")
        
        # L1: 工作记忆（当前会话上下文）
        try:
            from src.core.memory.working_memory import WorkingMemoryService
            wm = WorkingMemoryService()
            await wm.ensure_initialized()
            if wm.redis and self.session_id:
                ctx = await wm.get_context(self.session_id)
                result["session_context"] = ctx or {}
        except Exception as e:
            logger.debug(f"工作记忆检索失败: {e}")
        
        return result
    
    # === 任务完成后：写入情景记忆 ===
    async def commit_task_memory(
        self,
        task_desc: str,
        plan: list,
        result: dict,
        agent_contexts: Dict[str, AgentContext],
    ):
        """将完整执行轨迹写入情景记忆"""
        try:
            import json as _json
            from src.services.episodic_memory_service import episodic_memory
            
            # 构建增强的结果（包含各 Agent 推理链和重试次数）
            enhanced_result = dict(result)
            enhanced_result["agent_traces"] = {
                name: {
                    "reasoning_chain": ctx.reasoning_chain,
                    "retry_count": ctx.retry_count,
                    "status": ctx.status,
                }
                for name, ctx in agent_contexts.items()
            }
            
            # 清理 plan：执行过程中 plan 字典会被注入 dependent_results（包含不可序列化的
            # AgentResponse 对象），这里做深拷贝并过滤掉不可序列化的字段
            safe_plan = []
            for step in plan:
                safe_step = {}
                for k, v in step.items():
                    if k == "dependent_results":
                        # 跳过包含 AgentResponse 对象的依赖结果
                        continue
                    try:
                        _json.dumps(v, ensure_ascii=False)
                        safe_step[k] = v
                    except (TypeError, ValueError):
                        safe_step[k] = str(v)
                safe_plan.append(safe_step)
            
            memory_id = await episodic_memory.add_memory(
                task_description=task_desc,
                plan=safe_plan,
                final_result=enhanced_result,
            )
            return memory_id
        except Exception as e:
            logger.warning(f"情景记忆写入失败: {e}")
            return None


# ========== 5. DAG 执行保护常量（从 config.py 统一读取） ==========

MAX_DAG_ROUNDS = settings.AGENT_MAX_DAG_ROUNDS           # DAG 最大执行轮次（默认 30）
GLOBAL_TASK_TIMEOUT = settings.AGENT_GLOBAL_TIMEOUT      # 全局任务超时（默认 600s = 10 分钟）
