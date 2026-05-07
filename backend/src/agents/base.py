"""
基础智能体类 (v3 - 弹性并行版)

优化点：
1. 共享 httpx 连接池，消除每次请求重建客户端的开销
2. chat() 支持 system_prompt_override，避免重建 Agent 来切换 Prompt
3. 反思机制改为条件触发（通过 enable_reflection 参数控制）
4. 增加 LLM 调用重试机制（指数退避）
5. Tool Calling 支持并行执行
6. LLM 信号量和连接池参数从 config.py 统一读取，支持弹性扩展
"""

import asyncio
import contextvars
import json
from abc import ABC, abstractmethod
from typing import Any

import httpx
from camel.agents import ChatAgent  # noqa: F401 - legacy patch target for tests
from camel.models import ModelFactory  # noqa: F401 - legacy patch target for tests
from camel.types import ModelPlatformType, ModelType
from loguru import logger
from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.llm_helper import get_llm_config_sync

JSONDict = dict[str, Any]
ChatMessage = dict[str, Any]

# 任务级 LLM 配置上下文变量（线程安全，用于 DAG 执行时自动传递配置）
_task_llm_config_var: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "task_llm_config",
    default=None,
)

# 任务级对话历史上下文变量（线程安全，用于 DAG 执行时自动传递历史给子 Agent）
_task_history_var: contextvars.ContextVar[list[ChatMessage] | None] = contextvars.ContextVar(
    "task_history",
    default=None,
)


class AgentConfig(BaseModel):
    """智能体配置"""
    name: str
    role: str
    description: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    """智能体响应"""
    agent_name: str
    content: str
    reasoning: str | None = None
    citations: list[JSONDict] = Field(default_factory=list)
    actions: list[JSONDict] = Field(default_factory=list)
    metadata: JSONDict = Field(default_factory=dict)


class BaseLegalAgent(ABC):
    """
    法务智能体基类 (v2 性能优化版)
    
    所有法务智能体都继承此类，提供统一的接口和基础功能。
    
    v2 优化：
    - 类级别共享 httpx 连接池，避免每次 chat() 重建连接
    - chat() 新增 system_prompt_override / enable_reflection 参数
    - LLM 调用增加指数退避重试
    - Tool Calling 支持并行执行
    """

    # ========== 类级别共享资源 ==========
    _shared_http_client: httpx.AsyncClient | None = None
    _client_lock: asyncio.Lock = asyncio.Lock()

    # LLM 调用重试配置（从 settings 读取，支持环境变量覆盖）
    MAX_RETRIES = settings.AGENT_LLM_MAX_RETRIES
    RETRY_BASE_DELAY = settings.AGENT_LLM_RETRY_BASE_DELAY  # 秒
    RETRY_MAX_DELAY = settings.AGENT_LLM_RETRY_MAX_DELAY  # 秒

    # DAG 并行执行信号量（限制并发 LLM 请求数，从配置读取）
    _llm_semaphore: asyncio.Semaphore = asyncio.Semaphore(settings.AGENT_LLM_CONCURRENCY)

    @classmethod
    async def get_http_client(cls) -> httpx.AsyncClient:
        """获取类级别共享的 httpx 客户端（带连接池）"""
        # 注意：始终在基类上读写 _shared_http_client，避免每个子类各创建一个连接池
        if BaseLegalAgent._shared_http_client is None or BaseLegalAgent._shared_http_client.is_closed:
            async with BaseLegalAgent._client_lock:
                # 双重检查锁
                if BaseLegalAgent._shared_http_client is None or BaseLegalAgent._shared_http_client.is_closed:
                    _max_conn = settings.AGENT_HTTP_MAX_CONNECTIONS
                    _keepalive_conn = settings.AGENT_HTTP_KEEPALIVE_CONNECTIONS
                    BaseLegalAgent._shared_http_client = httpx.AsyncClient(
                        timeout=httpx.Timeout(
                            settings.AGENT_LLM_TIMEOUT,
                            connect=settings.AGENT_LLM_CONNECT_TIMEOUT,
                        ),
                        limits=httpx.Limits(
                            max_connections=_max_conn,
                            max_keepalive_connections=_keepalive_conn,
                            keepalive_expiry=30.0,
                        ),
                    )
                    logger.info(
                        f"已创建共享 httpx 连接池 "
                        f"(max_conn={_max_conn}, keepalive={_keepalive_conn}, "
                        f"llm_concurrency={settings.AGENT_LLM_CONCURRENCY})"
                    )
        return BaseLegalAgent._shared_http_client

    @classmethod
    async def close_http_client(cls) -> None:
        """关闭共享 httpx 客户端（应用关闭时调用）"""
        if BaseLegalAgent._shared_http_client and not BaseLegalAgent._shared_http_client.is_closed:
            await BaseLegalAgent._shared_http_client.aclose()
            BaseLegalAgent._shared_http_client = None
            logger.info("共享 httpx 连接池已关闭")

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.name = config.name
        self.role = config.role
        self.system_prompt = config.system_prompt
        self.client: Any | None = None
        self.agent: Any | None = None  # Deprecated camel agent
        self.llm_config: Any | None = None
        self.model_name: str | None = None
        self._init_agent()

    def _init_agent(self) -> None:
        """初始化 LLM 配置（仅获取配置，不创建 httpx 客户端）"""
        try:
            llm_config = get_llm_config_sync("llm")
            self.llm_config = llm_config
            self.model_name = llm_config.model_name

            logger.info(
                f"智能体 {self.name} 初始化成功 "
                f"(provider: {llm_config.provider}, model: {llm_config.model_name})"
            )

        except Exception as e:
            logger.error(f"智能体 {self.name} 初始化失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.llm_config = None
            self.model_name = None

    def _get_platform_type(self, provider: str) -> ModelPlatformType:
        """根据提供商获取CAMEL平台类型 (Unused, 保留兼容)"""
        platform_map = {
            "openai": ModelPlatformType.OPENAI,
            "anthropic": ModelPlatformType.ANTHROPIC,
        }
        return platform_map.get(provider, ModelPlatformType.OPENAI)

    def _get_model_type(self, provider: str, model_name: str) -> ModelType:
        """根据提供商和模型名称获取CAMEL模型类型 (Unused, 保留兼容)"""
        return ModelType.GPT_4O

    @abstractmethod
    async def process(self, task: dict[str, Any]) -> AgentResponse:
        """
        处理任务
        
        Args:
            task: 任务信息，可包含 llm_config 用于动态配置
            
        Returns:
            AgentResponse: 处理结果
        """
        pass

    def _is_local_model_api(self, api_base_url: str) -> bool:
        """判断是否为本地模型服务（非 OpenAI 兼容格式）"""
        if not api_base_url:
            return False
        # 本地模型服务特征：URL 以 /api/v1/chat 结尾
        return "/api/v1/chat" in api_base_url

    def _prepare_llm_request(self, active_config: Any) -> tuple[str, dict[str, str], str | None]:
        """
        准备 LLM 请求参数（提取公共逻辑）

        Returns:
            (url, headers, model_name) 元组
        """
        api_key = str(getattr(active_config, "api_key", "") or "")
        api_base_url = str(getattr(active_config, "api_base_url", "") or "")
        model_name = getattr(active_config, "model_name", self.model_name)

        # 解密 API Key (如果需要)
        if api_key and not api_key.startswith("sk-") and len(api_key) > 20:
            try:
                from src.services.llm_service import LLMService
                api_key = LLMService.decrypt_api_key(api_key)
            except Exception:
                pass

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        base_url = api_base_url.rstrip("/")

        # 本地模型服务：URL 已包含完整路径，不拼接 /chat/completions
        if self._is_local_model_api(base_url):
            url = base_url
        elif not base_url.endswith("/chat/completions") and not base_url.endswith("/v1"):
            url = f"{base_url}/chat/completions"
        elif base_url.endswith("/v1"):
            url = f"{base_url}/chat/completions"
        else:
            url = base_url

        return url, headers, model_name

    @staticmethod
    def _normalize_history_messages(history: list[ChatMessage] | None) -> list[ChatMessage]:
        """规范化历史消息，过滤空内容和重复 system 消息"""
        normalized: list[ChatMessage] = []
        for item in history or []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()
            if not role or not content or role == "system":
                continue
            normalized.append({"role": role, "content": content})
        return normalized

    def _build_llm_messages(
        self,
        system_prompt: str,
        message: str,
        history: list[ChatMessage] | None = None,
    ) -> list[ChatMessage]:
        """构建发给 LLM 的消息列表，保留最近的对话历史"""
        return [
            {"role": "system", "content": system_prompt},
            *self._normalize_history_messages(history),
            {"role": "user", "content": message},
        ]

    @staticmethod
    def _has_valid_api_key(active_config: Any | None) -> bool:
        """检查配置是否包含可用 API Key"""
        api_key = getattr(active_config, "api_key", "") if active_config else ""
        return bool(api_key and api_key != "sk-dummy-key" and "dummy" not in str(api_key))

    async def _resolve_active_llm_config(self, llm_config: Any | None = None) -> Any | None:
        """统一解析热路径中的有效 LLM 配置，必要时走缓存化自愈"""
        from src.services.llm_service import LLMService

        active_config = llm_config or _task_llm_config_var.get(None) or self.llm_config
        if self._has_valid_api_key(active_config):
            return active_config

        preview = getattr(active_config, "api_key", "") if active_config else ""
        logger.warning(
            f"Agent {self.name}: 当前配置无效 "
            f"(key={preview[:8] if preview else 'None'}...)，尝试从缓存/数据库加载"
        )

        try:
            cached_config = await LLMService.get_cached_effective_config("llm")
            if self._has_valid_api_key(cached_config):
                logger.info(
                    f"Agent {self.name}: 已加载有效 LLM 配置 "
                    f"({getattr(cached_config, 'provider', 'unknown')}/"
                    f"{getattr(cached_config, 'model_name', 'unknown')})"
                )
                return cached_config
        except Exception as db_err:
            logger.warning(f"Agent {self.name}: 加载 LLM 配置失败: {db_err}")

        return active_config

    async def _call_llm_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        payload: JSONDict,
        stream: bool = False,
    ) -> JSONDict:
        """
        带指数退避重试的 LLM 调用
        
        Args:
            url: API 端点
            headers: 请求头
            payload: 请求体
            stream: 是否使用流式模式
            
        Returns:
            API 响应 JSON
            
        Raises:
            Exception: 所有重试失败后抛出
        """
        from tenacity import (
            AsyncRetrying,
            retry_if_exception_type,
            stop_after_attempt,
            wait_exponential,
        )

        client = await self.get_http_client()

        def should_retry(e: BaseException) -> bool:
            # 认证错误不重试
            error_str = str(e)
            if "401" in error_str or "认证" in error_str:
                return False
            return True

        retryer = AsyncRetrying(
            stop=stop_after_attempt(self.MAX_RETRIES),
            wait=wait_exponential(multiplier=self.RETRY_BASE_DELAY, min=1, max=self.RETRY_MAX_DELAY),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                try:
                    async with self._llm_semaphore:
                        if stream:
                            resp = await client.post(url, headers=headers, json=payload)
                        else:
                            resp = await client.post(url, headers=headers, json=payload)

                    if resp.status_code == 200:
                        result = resp.json()
                        if isinstance(result, dict):
                            return result
                        return {"response": result}
                    elif resp.status_code == 401:
                        raise Exception(f"API认证失败 (401): {resp.text}")
                    elif resp.status_code == 429:
                        raise Exception(f"API速率限制 (429): {resp.text}")
                    else:
                        raise Exception(f"API返回 {resp.status_code}: {resp.text}")

                except Exception as e:
                    if not should_retry(e):
                        raise  # Reraise immediately, bypass tenacity retry

                    logger.warning(f"API调用异常: {e}，正在尝试重试 (当前尝试 {attempt.retry_state.attempt_number}/{self.MAX_RETRIES})")
                    raise  # Reraise so tenacity catches it and retries

        raise RuntimeError("API调用失败：重试器未返回结果")

    @staticmethod
    def _extract_tool_name(tool: JSONDict) -> str | None:
        function_def = tool.get("function")
        if isinstance(function_def, dict):
            name = function_def.get("name")
            return str(name) if name else None
        return None

    def _check_mcp_tool_policy(self, tool_name: str) -> Any:
        from src.harness.policy_engine import policy_engine

        return policy_engine.check_tool_access(self.name, tool_name)

    def _filter_mcp_tools_for_policy(self, tools: list[JSONDict]) -> list[JSONDict]:
        from src.harness.policy_engine import PolicyDecision

        allowed_tools: list[JSONDict] = []
        for tool in tools:
            tool_name = self._extract_tool_name(tool)
            if not tool_name:
                logger.warning(f"Agent {self.name}: 跳过无名称 MCP 工具")
                continue
            decision = self._check_mcp_tool_policy(tool_name)
            if decision.decision == PolicyDecision.ALLOW:
                allowed_tools.append(tool)
            else:
                logger.warning(
                    f"Agent {self.name}: MCP 工具 {tool_name} 被策略拒绝: {decision.reason}"
                )
        return allowed_tools

    @staticmethod
    def _tool_policy_denial(tool_name: str, reason: str) -> str:
        return (
            f"[工具调用被拒绝] {tool_name}: {reason}。"
            "请基于已有信息回答，不要尝试绕过工具权限。"
        )

    async def chat(
        self,
        message: str,
        user_id: str | None = None,
        llm_config: Any | None = None,
        system_prompt_override: str | None = None,
        enable_reflection: bool = False,
        max_tokens: int | None = None,
        history: list[ChatMessage] | None = None,
    ) -> str:
        """
        对话接口 (v2 优化版)
        
        优化点：
        1. 新增 system_prompt_override 参数，避免重建客户端切换 Prompt
        2. 新增 enable_reflection 参数，默认关闭反思（仅复杂任务开启）
        3. 使用共享连接池，不再每次创建新 httpx.AsyncClient
        4. Tool Calling 支持并行执行
        5. 增加指数退避重试
        
        Args:
            message: 用户消息
            user_id: 用户ID（可选，用于加载偏好）
            llm_config: 动态 LLM 配置（可选）
            system_prompt_override: 临时覆盖 system prompt（不修改实例状态）
            enable_reflection: 是否启用反思机制（默认关闭）
            max_tokens: 最大输出 token 数（可选，用于限制响应长度）
        """
        try:
            # 广播思考状态
            await self.broadcast_status("thinking", f"{self.name} 正在思考...", {"message_preview": message[:50]})

            # 确定 system prompt（优先使用 override，不修改实例状态）
            system_prompt = system_prompt_override or self.system_prompt

            # 动态注入用户偏好 (Long-term Memory)
            if user_id:
                try:
                    from src.services.preference_service import preference_service
                    suffix = await preference_service.get_agent_system_prompt_suffix(user_id)
                    system_prompt += suffix
                except Exception as e:
                    logger.warning(f"无法获取用户偏好: {e}")

            # ===== Harness: RAG 法律知识自动注入（所有 Agent 共享）=====
            # 从知识库检索相关法条，注入到 system_prompt 中
            try:
                from src.services.agent_rag_service import AgentRAGService
                rag_context = await AgentRAGService.get_legal_context(
                    query=message[:1000],
                    max_articles=5,
                )
                if rag_context:
                    rag_section = AgentRAGService.build_rag_prompt_section(rag_context, task_type="general")
                    system_prompt += f"\n\n{rag_section}"
                    logger.debug(f"[Harness] RAG 注入 {len(rag_context)} 条法律知识到 {self.name}")
            except Exception as rag_err:
                logger.debug(f"[Harness] RAG 注入跳过: {rag_err}")

            # ===== Harness: 做梦洞察注入（越用越懂用户）=====
            # 如果 auto_dream 产生了针对该用户的洞察，注入到 prompt 中
            if user_id:
                try:
                    from src.services.experience_engine import experience_engine
                    exp_ctx = experience_engine.build_experience_context(user_id, message, max_tokens=200)
                    if exp_ctx:
                        system_prompt += f"\n\n[用户历史偏好与经验]\n{exp_ctx}"
                except Exception:
                    pass

            # 防护：确保 user 消息不为空（API 会拒绝空消息）
            if not message or not message.strip():
                logger.warning(f"Agent {self.name}: 收到空的用户消息，使用默认提示")
                message = "请根据上下文提供分析和建议。"

            # 使用传入的 history > contextvars 任务历史（DAG 执行时自动透传）
            effective_history = history or _task_history_var.get(None)
            messages = self._build_llm_messages(system_prompt, message, effective_history)

            # 导入 MCP 服务
            from src.services.mcp_client_service import mcp_client_service

            # 使用传入的配置 > contextvars 任务配置 > 默认配置
            active_config = await self._resolve_active_llm_config(llm_config)

            # 最终校验：如果仍然无效，返回提示
            _final_key = getattr(active_config, 'api_key', '') if active_config else ''
            if not self._has_valid_api_key(active_config):
                logger.warning(f"Agent {self.name}: 没有有效的 API Key，请在设置页面配置 LLM 模型")
                return ("尚未配置有效的大语言模型 API Key。\n\n"
                        "请按以下步骤操作：\n"
                        "1. 点击左侧菜单 **设置**\n"
                        "2. 进入 **模型配置 (LLM)** 标签\n"
                        "3. 编辑您的模型配置，输入有效的 API Key\n"
                        "4. 保存后重新发送消息即可")

            # Debug logging — 不记录任何密钥片段
            provider = getattr(active_config, 'provider', 'N/A')
            base_url_str = getattr(active_config, 'api_base_url', 'N/A')
            logger.info(f"Agent {self.name} using config: Provider={provider}, API Base={base_url_str}, Key={'configured' if _final_key else 'missing'}")

            # 准备请求参数
            url, headers, model_name = self._prepare_llm_request(active_config)

            # --- MCP Tools Integration ---
            try:
                available_tools = await mcp_client_service.get_all_tools()
            except Exception as e:
                logger.warning(f"获取 MCP 工具失败: {e}")
                available_tools = []
            available_tools = self._filter_mcp_tools_for_policy(available_tools)

            max_turns = 5  # Prevent infinite loops
            current_turn = 0
            reflection_done = False  # 标记是否已完成反思

            # 检测是否为本地模型 API
            api_base_url = getattr(active_config, "api_base_url", "")
            is_local_api = self._is_local_model_api(api_base_url)

            while current_turn < max_turns:
                current_turn += 1

                # 某些模型对 temperature 有严格限制（如 kimi-k2.5 只允许 temperature=1）
                temperature = getattr(active_config, 'temperature', None) or self.config.temperature or 0.7
                if model_name and ("k2" in model_name or "thinking" in model_name or "o1" in model_name or "o3" in model_name):
                    temperature = 1.0  # 推理型模型强制 temperature=1

                if is_local_api:
                    # 本地模型服务格式：将 messages 转为单个 input 字符串
                    input_text = ""
                    for msg in messages:
                        role = msg.get("role", "")
                        msg_content = msg.get("content", "")
                        if role == "system":
                            input_text += f"[系统指令] {msg_content}\n\n"
                        elif role == "user":
                            input_text += f"{msg_content}\n"
                        elif role == "assistant":
                            input_text += f"[助手回复] {msg_content}\n"
                    payload: JSONDict = {
                        "model": model_name,
                        "input": input_text.strip(),
                        "stream": False,
                    }
                else:
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": temperature,
                    }

                    if max_tokens:
                        payload["max_tokens"] = max_tokens

                    if available_tools:
                        payload["tools"] = available_tools
                        payload["tool_choice"] = "auto"

                logger.info(f"API Call to {url} (Turn {current_turn})")

                # 使用带重试的 LLM 调用
                data = await self._call_llm_with_retry(url, headers, payload)

                # ===== Harness: 捕获 token 用量并记录成本 =====
                try:
                    usage = data.get("usage")
                    if usage:
                        from src.harness.cost_tracker import cost_tracker
                        cost_tracker.record(
                            model=model_name or "unknown",
                            provider=provider or "unknown",
                            prompt_tokens=usage.get("prompt_tokens", 0),
                            completion_tokens=usage.get("completion_tokens", 0),
                            agent_name=self.name,
                            operation=f"agent.{self.name}.chat.turn_{current_turn}",
                        )
                except Exception as _cost_err:
                    logger.debug(f"成本追踪跳过: {_cost_err}")  # 不影响主流程但记录日志

                # 解析响应：兼容本地模型 API 和 OpenAI 格式
                if is_local_api:
                    # 本地模型响应格式: {"output": [{"type": "message", "content": "..."}], ...}
                    output_list = data.get("output", [])
                    content = ""
                    for item in output_list:
                        if isinstance(item, dict) and item.get("content"):
                            content += item["content"]
                    if not content or not content.strip():
                        logger.warning(f"本地模型返回空响应: {str(data)[:200]}")
                        content = "抱歉，模型未能生成有效回复，请重试或切换模型。"
                    tool_calls = None  # 本地模型暂不支持 tool calls
                    resp_msg: ChatMessage = {"role": "assistant", "content": content}
                else:
                    choice = data["choices"][0]
                    resp_msg = choice["message"]
                    raw_content = resp_msg.get("content")
                    # 兼容 content 为数组的情况，如 [{"type":"text","text":"..."}]
                    if isinstance(raw_content, list):
                        content = "".join(
                            item.get("text", str(item)) if isinstance(item, dict) else str(item)
                            for item in raw_content
                        )
                        resp_msg["content"] = content
                    else:
                        content = str(raw_content) if raw_content is not None else ""
                    tool_calls = resp_msg.get("tool_calls")

                # 空响应防护
                if not content and not tool_calls:
                    logger.warning(f"LLM 返回空内容: model={model_name}, turn={current_turn}")
                    content = "抱歉，AI 暂时无法生成回复，请稍后重试。"
                    resp_msg["content"] = content

                # Update messages with assistant response
                messages.append(resp_msg)

                if tool_calls:
                    logger.info(f"Executing {len(tool_calls)} tool calls...")
                    await self.broadcast_status("tool_use", f"{self.name} 正在使用工具...", {"tool_count": len(tool_calls)})

                    # 并行执行所有 Tool Calls
                    async def _execute_tool(tc: JSONDict) -> ChatMessage:
                        call_id = tc["id"]
                        fn = tc["function"]
                        fn_name = fn["name"]
                        fn_args_str = fn["arguments"]
                        try:
                            from src.harness.policy_engine import PolicyDecision

                            decision = self._check_mcp_tool_policy(fn_name)
                            if decision.decision != PolicyDecision.ALLOW:
                                tool_output = self._tool_policy_denial(fn_name, decision.reason)
                                logger.warning(
                                    f"Tool execution denied for {fn_name}: {decision.reason}"
                                )
                                return {
                                    "role": "tool",
                                    "tool_call_id": call_id,
                                    "content": tool_output,
                                }
                            fn_args = json.loads(fn_args_str)
                            result = await mcp_client_service.call_tool(fn_name, fn_args)
                            tool_output = str(result)
                            logger.info(f"Tool {fn_name} executed successfully")
                        except Exception as e:
                            logger.error(f"Tool execution failed for {fn_name}: {e}")
                            tool_output = f"[工具调用失败] {fn_name}: {str(e)}。请基于已有信息回答，不要编造数据。"
                        return {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": tool_output
                        }

                    tool_results = await asyncio.gather(
                        *[_execute_tool(tc) for tc in tool_calls],
                        return_exceptions=True
                    )

                    for tr in tool_results:
                        if isinstance(tr, BaseException):
                            messages.append({
                                "role": "tool",
                                "tool_call_id": "error",
                                "content": f"Tool execution error: {str(tr)}"
                            })
                        else:
                            messages.append(tr)

                    # Loop back to send tool outputs to LLM
                    continue
                else:
                    # 条件触发反思机制（仅在 enable_reflection=True 且尚未反思时）
                    if (enable_reflection
                            and not reflection_done
                            and current_turn == 1
                            and len(str(content)) > 200):
                        reflection_done = True
                        reflection_prompt = (
                            f"请检查上述回答。如果你是{self.role}，你认为这个回答在法律专业性、"
                            f"风险提示或完整性上有什么遗漏吗？如果没有，请直接复述原回答；如果有，请修正。"
                        )
                        messages.append({"role": "user", "content": reflection_prompt})
                        await self.broadcast_status("reflection", f"{self.name} 正在反思...", {"reason": "Self-Correction"})
                        continue

                    # Final response
                    await self.broadcast_status("finished", f"{self.name} 回复完成", {"response_preview": str(content)[:50]})
                    return content

            return "Task limit reached without final answer."

        except Exception as e:
            # MOCK MODE
            error_str = str(e)
            is_auth_error = "Incorrect API key provided" in error_str or "401" in error_str or "认证" in error_str
            is_conn_error = "ConnectError" in error_str or "Timeout" in error_str or "timed out" in error_str or "Connection refused" in error_str

            active_config = llm_config or _task_llm_config_var.get(None) or self.llm_config
            api_key = getattr(active_config, "api_key", "") if active_config else ""
            api_base_url = getattr(active_config, "api_base_url", "") if active_config else ""

            is_dummy_key = "dummy" in api_key or not api_key

            if is_auth_error or (is_conn_error and is_dummy_key) or (is_dummy_key and "api.openai.com" in api_base_url):
                logger.warning(f"API调用失败或使用测试Key ({error_str})，使用模拟响应 (Mock Mode) - Agent: {self.name}")
                return self._get_mock_response(message)

            logger.error(f"对话失败: {e}")
            await self.broadcast_status("error", f"{self.name} 发生错误: {str(e)}")
            return f"处理失败: {str(e)}"

    async def stream_chat(
        self,
        message: str,
        llm_config: Any | None = None,
        system_prompt_override: str | None = None,
        history: list[ChatMessage] | None = None,
        max_tokens: int | None = None,
    ) -> asyncio.Queue[str | None]:
        """
        流式对话接口 — 真正的 token-by-token 流式输出
        
        返回一个 asyncio.Queue，调用方可以从中逐步读取 token。
        队列中的特殊值 None 表示流结束。
        
        Args:
            message: 用户消息
            llm_config: 动态 LLM 配置
            system_prompt_override: 临时覆盖 system prompt
            
        Returns:
            asyncio.Queue: token 队列
        """
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def _stream_worker() -> None:
            try:
                system_prompt = system_prompt_override or self.system_prompt
                active_config = await self._resolve_active_llm_config(llm_config)
                if not self._has_valid_api_key(active_config):
                    await queue.put(
                        "尚未配置有效的大语言模型 API Key。请前往设置 > 模型配置 (LLM) 完成配置后再试。"
                    )
                    await queue.put(None)
                    return

                url, headers, model_name = self._prepare_llm_request(active_config)

                # 推理型模型强制 temperature=1
                temperature = getattr(active_config, 'temperature', None) or self.config.temperature or 0.7
                if model_name and ("k2" in model_name or "thinking" in model_name or "o1" in model_name or "o3" in model_name):
                    temperature = 1.0

                # 防护：确保 user 消息不为空
                # 注意：不能对闭包变量 message 赋值，否则 Python 会将其视为局部变量
                # 导致 UnboundLocalError
                user_message = message
                if not user_message or not user_message.strip():
                    logger.warning(f"Agent {self.name}: stream_chat 收到空的用户消息，使用默认提示")
                    user_message = "请根据上下文提供分析和建议。"

                # 使用传入的 history > contextvars 任务历史
                effective_history = history or _task_history_var.get(None)
                messages = self._build_llm_messages(system_prompt, user_message, effective_history)

                # 检测是否为本地模型 API
                _api_base = getattr(active_config, "api_base_url", "")
                _is_local = self._is_local_model_api(_api_base)

                if _is_local:
                    # 本地模型服务：使用非流式调用，一次性返回结果
                    input_text = ""
                    for msg in messages:
                        role = msg.get("role", "")
                        msg_content = msg.get("content", "")
                        if role == "system":
                            input_text += f"[系统指令] {msg_content}\n\n"
                        elif role == "user":
                            input_text += f"{msg_content}\n"
                        elif role == "assistant":
                            input_text += f"[助手回复] {msg_content}\n"
                    payload: JSONDict = {
                        "model": model_name,
                        "input": input_text.strip(),
                        "stream": False,
                    }

                    client = await self.get_http_client()
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code != 200:
                        await queue.put(f"[Error] API returned {resp.status_code}")
                        await queue.put(None)
                        return

                    data = resp.json()
                    output_list = data.get("output", [])
                    content = ""
                    for item in output_list:
                        if isinstance(item, dict) and item.get("content"):
                            content += item["content"]
                    if not content:
                        content = str(data)
                    # 模拟流式输出：按句分块推送
                    import re
                    chunks = re.split(r'(?<=[。！？\n])', content)
                    for chunk in chunks:
                        if chunk:
                            await queue.put(chunk)
                else:
                    payload = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "stream": True,
                    }
                    if max_tokens:
                        payload["max_tokens"] = max_tokens

                    client = await self.get_http_client()

                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        if resp.status_code != 200:
                            await resp.aread()
                            await queue.put(f"[Error] API returned {resp.status_code}")
                            await queue.put(None)
                            return

                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]":
                                    break
                                try:
                                    data = json.loads(data_str)
                                    delta = data["choices"][0].get("delta", {})
                                    token = delta.get("content", "")
                                    if token:
                                        await queue.put(token)
                                except (json.JSONDecodeError, KeyError, IndexError):
                                    continue

                await queue.put(None)  # 流结束信号

            except Exception as e:
                logger.error(f"流式对话失败: {e}")
                await queue.put(f"[Error] {str(e)}")
                await queue.put(None)

        # 在后台启动流式 worker
        asyncio.create_task(_stream_worker())
        return queue

    def _get_mock_response(self, message: str) -> str:
        """生成模拟响应"""
        msg_lower = message.lower()

        # 1. 劳动法相关
        if "辞退" in msg_lower or "试用期" in msg_lower:
            return """根据《劳动合同法》第39条规定，劳动者在试用期间被证明不符合录用条件的，用人单位可以解除劳动合同，且无需支付经济补偿金。
            
            建议：
            1. 确保已有明确的录用条件确认书。
            2. 收集员工不符合录用条件的具体证据。
            3. 书面通知员工解除劳动合同。
            """

        # 2. 知识产权相关
        if "抄袭" in msg_lower or "侵权" in msg_lower:
            return """判定著作权侵权通常遵循"接触 + 实质性相似"原则。
            
            分析：
            1. **接触**：侵权人是否有机会接触到您的作品。
            2. **实质性相似**：两部作品在核心表达上是否构成实质性相似。
            
            建议保留创作底稿，进行侵权对比分析。
            """

        # 3. 共识 Agent (JSON 格式)
        if "共识" in self.name or "仲裁" in self.role or "conflicts" in self.system_prompt:
            return """```json
{
  "conflicts": [
    {
      "point": "法律适用条款",
      "positions": [
        {"agent": "LegalAdvisor", "view": "适用劳动合同法第39条", "score": 9, "reason": "法律依据准确"},
        {"agent": "RiskAssessor", "view": "建议支付N+1以降低风险", "score": 7, "reason": "出于实务风险考虑"}
      ],
      "winner": "LegalAdvisor"
    }
  ],
  "debate_summary": "法律顾问强调法定免赔情形，风险专家关注实际操作中的举证难度。",
  "final_decision": "在证据充分的情况下，依据第39条解除合同且无需赔偿；若证据不足，建议协商解除。",
  "reasoning": "法律规定明确，关键在于举证责任。",
  "risk_level": "medium",
  "is_consensus_reached": true
}
```"""

        # 4. 通用回复
        return f"【Mock响应】我已收到您的问题：{message}。由于正在使用测试API Key，无法调用真实模型进行回答。请配置有效的OPENAI_API_KEY。"


    async def broadcast_status(
        self,
        status: str,
        message: str,
        payload: JSONDict | None = None,
    ) -> None:
        """广播Agent状态到事件总线"""
        try:
            from src.services.event_bus import event_bus
            event_data = {
                "agent": self.name,
                "status": status,
                "message": message,
                "payload": payload or {}
            }
            await event_bus.publish("agent_events", event_data)
        except Exception as e:
            logger.warning(f"状态广播失败: {e}")

    def get_info(self) -> dict[str, Any]:
        """获取Agent信息"""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.config.description,
            "tools": self.config.tools
        }
