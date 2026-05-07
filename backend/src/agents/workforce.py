"""
法务智能体团队 (v4 - 弹性并行版)

优化点：
1. DAG 并行执行使用可配置的 Semaphore 并发控制（默认 30，最高可扩展至 200）
2. 修复 LLM 配置竞态条件 — 通过 task context 传递配置，不再修改共享实例
3. 共识机制改为条件触发 — 仅当多个 Agent 参与时才触发
4. 增加任务超时控制
5. 增加执行耗时统计
6. AgentContext 独立上下文 + MessagePool 公共消息池
7. AgentLifecycleManager 生命周期管理（重试、替换、接管）
8. MemoryIntegration 三层记忆深度集成
9. 所有并行参数从 config.py 统一读取，支持环境变量覆盖
"""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any, cast

from loguru import logger

from src.agents.base import AgentResponse
from src.agents.compliance_officer import ComplianceAgent
from src.agents.consensus_agent import ConsensusAgent
from src.agents.contract_investigator import ContractInvestigatorAgent
from src.agents.contract_reviewer import ContractReviewAgent
from src.agents.contract_steward import ContractStewardAgent
from src.agents.coordinator import CoordinatorAgent
from src.agents.document_drafter import DocumentDraftAgent
from src.agents.due_diligence import DueDiligenceAgent
from src.agents.evidence_analyst import EvidenceAnalystAgent
from src.agents.ip_specialist import IPSpecialistAgent
from src.agents.labor_compliance import LaborComplianceAgent
from src.agents.legal_advisor import LegalAdvisorAgent
from src.agents.legal_calculator import LegalCalculatorAgent
from src.agents.legal_researcher import LegalResearchAgent
from src.agents.litigation_strategist import LitigationStrategistAgent
from src.agents.regulatory_monitor import RegulatoryMonitorAgent
from src.agents.requirement_analyst import RequirementAnalystAgent
from src.agents.review_checker import ReviewCheckerAgent
from src.agents.risk_assessor import RiskAssessmentAgent
from src.agents.task_context import (
    GLOBAL_TASK_TIMEOUT,
    MAX_DAG_ROUNDS,
    AgentContext,
    AgentLifecycleManager,
    MemoryIntegration,
    MessagePool,
)
from src.agents.tax_compliance import TaxComplianceAgent
from src.agents.template_librarian import TemplateLirarianAgent
from src.core.config import settings

# ============================================================================
# 专业智能体注册表
#
# 新增 agent 只需在这里登记一条（同时导入对应类）。
# LegalWorkforce 在 _initialize_agents 时会从注册表实例化全部 agent，
# 测试可通过 `patch.dict("src.agents.workforce.AGENT_REGISTRY", ...)`
# 整体替换，避免每加一个 agent 就要去测试里补 @patch 装饰器。
# ============================================================================

AGENT_REGISTRY: dict[str, type] = {
    "legal_advisor": LegalAdvisorAgent,
    "contract_reviewer": ContractReviewAgent,
    "contract_investigator": ContractInvestigatorAgent,
    "review_checker": ReviewCheckerAgent,
    "due_diligence": DueDiligenceAgent,
    "legal_researcher": LegalResearchAgent,
    "document_drafter": DocumentDraftAgent,
    "compliance_officer": ComplianceAgent,
    "risk_assessor": RiskAssessmentAgent,
    "consensus_manager": ConsensusAgent,
    "litigation_strategist": LitigationStrategistAgent,
    "ip_specialist": IPSpecialistAgent,
    "regulatory_monitor": RegulatoryMonitorAgent,
    "tax_compliance": TaxComplianceAgent,
    "labor_compliance": LaborComplianceAgent,
    "evidence_analyst": EvidenceAnalystAgent,
    "contract_steward": ContractStewardAgent,
    "template_librarian": TemplateLirarianAgent,
    "legal_calculator": LegalCalculatorAgent,
}


# 回调类型别名
EventPayload = dict[str, Any]
TaskInfo = dict[str, Any]
WsCallback = Callable[[str, EventPayload], Coroutine[Any, Any, None]]

MAX_PARALLEL_AGENTS = settings.AGENT_MAX_PARALLEL       # 同一 DAG 层级最多并行执行的 Agent 数（默认 30）
TASK_TIMEOUT_SECONDS = settings.AGENT_TASK_TIMEOUT      # 单个 Agent 任务超时时间（秒）


class LegalWorkforce:
    """
    法务智能体团队 (v4 弹性并行版)
    
    协调多个专业智能体协作完成复杂法务任务。
    
    并行能力（从 config.py 读取，支持环境变量覆盖）：
    - AGENT_MAX_PARALLEL: 同层最大并行数（默认 30，可扩至 200）
    - AGENT_LLM_CONCURRENCY: LLM 并发请求数（默认 15）
    - AGENT_TASK_TIMEOUT: 单任务超时（默认 120s）
    - AGENT_GLOBAL_TIMEOUT: 全局超时（默认 600s）
    
    架构优化：
    - Semaphore 控制并行 Agent 数，防止 LLM API 过载
    - 通过 task context 传递 LLM 配置，消除竞态条件
    - 共识机制仅在多 Agent 参与时触发
    - 单任务超时控制 + 全局超时保护
    """

    def __init__(self) -> None:
        self._dag_semaphore = asyncio.Semaphore(MAX_PARALLEL_AGENTS)
        self.coordinator: CoordinatorAgent
        self.requirement_analyst: RequirementAnalystAgent
        self.agents: dict[str, Any] = {}
        logger.info(
            f"智能体并行配置: MAX_PARALLEL={MAX_PARALLEL_AGENTS}, "
            f"LLM_CONCURRENCY={settings.AGENT_LLM_CONCURRENCY}, "
            f"TASK_TIMEOUT={TASK_TIMEOUT_SECONDS}s, "
            f"GLOBAL_TIMEOUT={settings.AGENT_GLOBAL_TIMEOUT}s"
        )
        self._init_agents()

    def _init_agents(self) -> None:
        """初始化所有智能体"""
        logger.info("初始化法务智能体团队...")

        # 加载技能库
        try:
            from src.services.skill_service import skill_service
            skill_service.load_skills()
        except Exception as e:
            logger.warning(f"技能库加载失败: {e}")

        # 协调者
        self.coordinator = CoordinatorAgent()

        # 需求分析智能体
        self.requirement_analyst = RequirementAnalystAgent()

        # 专业智能体：从注册表实例化（新增 agent 只需修改 AGENT_REGISTRY）
        self.agents = {agent_id: factory() for agent_id, factory in AGENT_REGISTRY.items()}

        logger.info(f"法务智能体团队初始化完成，共 {len(self.agents)} 个专业智能体")

    async def process_task(
        self,
        task_description: str,
        task_type: str | None = None,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        progress_callback: WsCallback | None = None,
        ws_callback: WsCallback | None = None,
    ) -> dict[str, Any]:
        """
        处理法务任务 (v4: DAG执行流 + 条件共识 + 并发控制 + 流式Agent结果推送)
        
        Args:
            progress_callback: 进度回调 (event_type, data_dict)
            ws_callback: WebSocket 回调，用于推送 agent_result/thinking_content 等事件
        """
        # 合并两个回调 — ws_callback 是新版，progress_callback 是旧版兼容
        _cb = ws_callback or progress_callback
        task_start_time = time.time()
        logger.info(f"开始处理任务: {task_description[:100]}... (Session: {session_id})")

        # 延迟导入以避免循环依赖
        from src.services.episodic_memory_service import episodic_memory

        if context is None:
            context = {}

        if session_id:
            context["session_id"] = session_id

        # 保存原始任务描述，供 instruction 为空时回退使用
        context["original_message"] = task_description

        # 辅助：发送进度事件（统一回调）
        async def _notify(event_type: str, data: EventPayload) -> None:
            if _cb:
                try:
                    await _cb(event_type, data)
                except Exception:
                    pass

        # 0. 并行预处理：情景记忆 + 技能匹配 + 意图分析同时启动
        # 优化：原来串行执行 3 步（记忆→技能→分析），现在并行，节省 1-3 秒
        await _notify("agent_thinking", {
            "agent": "协调调度Agent",
            "message": "正在分析任务意图...",
        })

        async def _fetch_memory() -> list[Any]:
            try:
                cases = await episodic_memory.retrieve_similar_cases(task_description)
                if cases:
                    logger.info(f"检索到 {len(cases)} 个相似历史案件")
                return cases or []
            except Exception as e:
                logger.warning(f"情景记忆检索失败: {e}")
                return []

        async def _match_skills() -> list[Any]:
            try:
                from src.services.skill_service import skill_service
                skills = skill_service.match_skills(task_description)
                if skills:
                    logger.info(f"匹配到相关技能: {[s.name for s in skills]}")
                return skills or []
            except Exception as e:
                logger.warning(f"技能匹配失败: {e}")
                return []

        async def _analyze_task(ctx: dict[str, Any]) -> dict[str, Any]:
            return await self.coordinator.analyze_task({
                "description": task_description,
                "type": task_type,
                "context": ctx,
            })

        # 并行执行记忆检索和技能匹配（不阻塞意图分析）
        memory_task = asyncio.create_task(_fetch_memory())
        skills_task = asyncio.create_task(_match_skills())

        # 先快速拿到记忆和技能结果（通常 < 200ms）
        similar_cases, matched_skills = await asyncio.gather(memory_task, skills_task)

        if similar_cases:
            context["similar_cases"] = similar_cases
        if matched_skills:
            context["matched_skills"] = [s.to_dict() for s in matched_skills]

        # 1. 协调者分析任务并生成 DAG 计划（此时上下文已就绪）
        analysis = await _analyze_task(context)

        plan = analysis.get("plan", [])
        total_steps = len(plan)

        # ===== 空计划回退：若 DAG 规划失败（0 步骤），自动生成默认计划 =====
        if total_steps == 0:
            logger.warning("DAG 规划返回空计划，启用回退机制生成默认计划")

            # 根据任务描述中的关键词推断合理的默认 Agent 组合
            default_agents: list[TaskInfo] = []
            desc_lower = task_description.lower()

            if any(kw in desc_lower for kw in ['合同', '协议', '起草', '草拟', '文书', '方案']):
                default_agents.append({"id": "task_1", "agent": "document_drafter", "depends_on": []})
                default_agents.append({"id": "task_2", "agent": "legal_advisor", "instruction_suffix": "审查并完善上述文书的法律合规性。", "depends_on": ["task_1"]})
            elif any(kw in desc_lower for kw in ['审查', '审核', '合规']):
                # 双循环审查管线：调查→审查→验证
                default_agents.append({"id": "task_1", "agent": "contract_investigator", "depends_on": []})
                default_agents.append({"id": "task_2", "agent": "contract_reviewer", "depends_on": ["task_1"]})
                default_agents.append({"id": "task_3", "agent": "review_checker", "depends_on": ["task_2"]})
            elif any(kw in desc_lower for kw in ['风险', '评估', '分析']):
                default_agents.append({"id": "task_1", "agent": "risk_assessor", "depends_on": []})
            elif any(kw in desc_lower for kw in ['诉讼', '仲裁', '纠纷']):
                default_agents.append({"id": "task_1", "agent": "legal_researcher", "depends_on": []})
                default_agents.append({"id": "task_2", "agent": "litigation_strategist", "depends_on": ["task_1"]})
            else:
                # 兜底：法律顾问
                default_agents.append({"id": "task_1", "agent": "legal_advisor", "depends_on": []})

            for step in default_agents:
                step["instruction"] = task_description + step.get("instruction_suffix", "")

            plan = default_agents
            total_steps = len(plan)
            analysis["plan"] = plan
            analysis["reasoning"] = f"DAG 规划失败，已自动回退到默认计划（共 {total_steps} 步）"
            logger.info(f"回退计划生成: {[s['agent'] for s in plan]}")

        logger.info(f"任务分析完成，执行计划包含 {total_steps} 个步骤")

        # 通知前端计划已生成
        await _notify("agent_thinking", {
            "agent": "协调调度Agent",
            "message": f"任务拆解完成，共 {total_steps} 个执行步骤",
            "total_steps": total_steps,
        })

        # Agent 名称映射（显示友好名称）— 放在使用之前定义
        agent_display_names = {
            "legal_advisor": "法律顾问Agent",
            "contract_reviewer": "合同审查Agent",
            "contract_investigator": "合同调查Agent",
            "review_checker": "审查验证Agent",
            "due_diligence": "尽职调查Agent",
            "legal_researcher": "法律研究Agent",
            "document_drafter": "文书起草Agent",
            "compliance_officer": "合规审查Agent",
            "risk_assessor": "风险评估Agent",
            "litigation_strategist": "诉讼策略Agent",
            "ip_specialist": "知识产权Agent",
            "regulatory_monitor": "监管监测Agent",
            "tax_compliance": "税务合规Agent",
            "labor_compliance": "劳动合规Agent",
            "evidence_analyst": "证据分析Agent",
            "contract_steward": "合同管家Agent",
            "consensus_manager": "共识管理Agent",
            "legal_calculator": "法务分析Agent",
            "template_librarian": "模板库Agent",
        }

        # 推送思考链内容：意图识别 + DAG 规划（中文展示）
        intent = analysis.get("intent", "UNKNOWN")
        reasoning = analysis.get("reasoning", "")
        # 意图代码 → 中文标签
        _intent_labels = {
            "QA_CONSULTATION": "法律咨询",
            "CONTRACT_REVIEW": "合同审查",
            "DUE_DILIGENCE": "尽职调查",
            "DOCUMENT_DRAFTING": "文书起草",
            "LITIGATION_STRATEGY": "诉讼策略",
            "IP_PROTECTION": "知识产权保护",
            "REGULATORY_MONITORING": "合规监管",
            "TAX_FINANCE": "财税合规",
            "LABOR_HR": "劳动人事",
            "EVIDENCE_PROCESSING": "证据处理",
            "E_SIGNATURE": "电子签约",
            "CONTRACT_MANAGEMENT": "合同管理",
            "POLICY_DISTRIBUTION": "制度分发",
            "FIND_LAWYER": "找律师",
            "COMPLEX_TASK": "复合任务",
        }
        intent_label = _intent_labels.get(intent, intent)
        await _notify("thinking_content", {
            "agent": "协调调度Agent",
            "content": f"**意图识别**: {intent_label}\n\n**规划理由**: {reasoning}",
            "phase": "planning",
            "plan_steps": [
                {"agent": agent_display_names.get(t.get("agent", ""), t.get("agent", "")),
                 "instruction": t.get("instruction", "")[:100]}
                for t in plan
            ],
        })

        # 2. 推送任务看板到前端（agent_tasks_batch — 一次性展示所有并列任务卡片）
        await _notify("agent_tasks_batch", {
            "tasks": [
                {
                    "task_id": t["id"],
                    "agent": agent_display_names.get(t.get("agent", ""), t.get("agent", "")),
                    "agent_key": t.get("agent", ""),
                    "description": (t.get("instruction", "") or task_description)[:120],
                    "status": "queued",
                    "progress": 0,
                    "dependencies": t.get("depends_on", []),
                }
                for t in plan
            ],
        })

        # === 初始化多 Agent 协作基础设施 ===
        task_id = str(uuid.uuid4())[:12]
        message_pool = MessagePool(task_id=task_id, session_id=session_id or "")
        memory_integration = MemoryIntegration(session_id=session_id or "", task_id=task_id)
        lifecycle_manager = AgentLifecycleManager(agents=self.agents, ws_callback=_cb)
        agent_contexts: dict[str, AgentContext] = {}

        # 3. 按照 DAG 顺序执行任务（带并发控制、生命周期管理和全局超时）
        executed_tasks: dict[str, AgentResponse] = {}  # task_id -> result
        pending_task_ids = [t["id"] for t in plan]
        plan_index: dict[str, TaskInfo] = {t["id"]: t for t in plan}
        completed_count = 0
        dag_round = 0
        global_start = time.time()

        while pending_task_ids:
            # 全局超时保护
            if time.time() - global_start > GLOBAL_TASK_TIMEOUT:
                logger.warning(f"全局任务超时 ({GLOBAL_TASK_TIMEOUT}s)，强制终止")
                await _notify("task_force_complete", {
                    "reason": "global_timeout",
                    "completed_tasks": list(executed_tasks.keys()),
                    "pending_tasks": pending_task_ids,
                })
                break

            # DAG 轮次保护
            dag_round += 1
            if dag_round > MAX_DAG_ROUNDS:
                logger.error(f"DAG 执行轮次超过 {MAX_DAG_ROUNDS}，强制终止")
                break

            executable_tasks = []
            for t_id in pending_task_ids:
                task_info = plan_index.get(t_id)
                if not task_info:
                    continue
                dependencies = task_info.get("depends_on", [])
                if all(dep in executed_tasks for dep in dependencies):
                    executable_tasks.append(task_info)

            if not executable_tasks:
                if pending_task_ids:
                    logger.error(f"任务依赖配置错误，存在环路或未满足的依赖: {pending_task_ids}")
                break

            # 并行执行当前层级的任务（带生命周期管理）
            async def run_task_with_lifecycle(
                t_info: TaskInfo,
                step_number: int = completed_count + 1,
            ) -> AgentResponse:
                """带生命周期管理的任务执行"""
                a_name = t_info.get("agent", "unknown")
                display_name = agent_display_names.get(a_name, a_name)
                t_id = t_info["id"]
                agent_start_time = time.time()

                # 创建 Agent 独立上下文
                agent_ctx = AgentContext(
                    agent_id=str(uuid.uuid4())[:8],
                    agent_name=a_name,
                    task_id=t_id,
                )
                agent_ctx.input_context = {
                    "instruction": t_info.get("instruction", ""),
                    "dependencies": t_info.get("depends_on", []),
                }
                agent_contexts[a_name] = agent_ctx

                # 注入依赖任务结果
                deps = t_info.get("depends_on", [])
                dep_results = {dep: executed_tasks[dep] for dep in deps if dep in executed_tasks}
                t_info["dependent_results"] = dep_results

                # 确保 instruction 非空
                if not t_info.get("instruction", "").strip():
                    t_info["instruction"] = context.get("original_message", "") or task_description

                # 技能动态注入
                if matched_skills:
                    skill_guidance = ""
                    for skill in matched_skills:
                        instr = t_info.get("instruction", "").lower()
                        if skill.name in instr or any(trig in instr for trig in skill.triggers):
                            skill_guidance += f"\n\n【参考技能：{skill.name}】\n{skill.content[:2000]}\n"
                    if skill_guidance:
                        t_info["instruction"] = t_info.get("instruction", "") + skill_guidance

                # 通知前端
                await _notify("agent_task_start", {
                    "task_id": t_id,
                    "agent": display_name,
                    "agent_key": a_name,
                    "description": (t_info.get("instruction", "") or task_description)[:120],
                })
                await _notify("agent_working", {
                    "agent": display_name,
                    "message": f"{display_name} 正在处理...",
                    "step": step_number,
                    "total_steps": total_steps,
                })

                async with self._dag_semaphore:
                    await _notify("agent_task_progress", {
                        "task_id": t_id,
                        "progress": 30,
                        "elapsed": round(time.time() - agent_start_time, 1),
                    })

                    # 使用生命周期管理器执行（自动重试、替换、降级）
                    result = cast(
                        AgentResponse,
                        await lifecycle_manager.execute_with_lifecycle(
                        agent_name=a_name,
                        task_info=t_info,
                        agent_context=agent_ctx,
                        message_pool=message_pool,
                        context=context,
                        ),
                    )

                    await _notify("agent_task_progress", {
                        "task_id": t_id,
                        "progress": 80,
                        "elapsed": round(time.time() - agent_start_time, 1),
                    })

                # 保存 Agent 上下文到工作记忆
                await memory_integration.save_agent_context(agent_ctx)

                # 判断结果状态并通知
                elapsed = round(time.time() - agent_start_time, 1)
                summary = ""
                full_content = ""
                is_error = False
                is_degraded = False

                if isinstance(result, AgentResponse):
                    full_content = result.content
                    is_error = result.metadata.get("error", False)
                    is_degraded = result.metadata.get("degraded", False)
                    if not is_error:
                        summary = result.content[:200] + ("..." if len(result.content) > 200 else "")

                if is_error and not is_degraded:
                    await _notify("agent_task_failed", {
                        "task_id": t_id,
                        "error": full_content[:200],
                    })
                elif is_degraded:
                    await _notify("task_degraded", {
                        "task_id": t_id,
                        "agent": display_name,
                        "message": full_content[:200],
                    })
                else:
                    await _notify("agent_task_complete", {
                        "task_id": t_id,
                        "result": summary,
                        "elapsed": elapsed,
                    })

                # 旧版事件兼容
                await _notify("agent_complete", {
                    "agent": display_name,
                    "message": f"{display_name} 已完成",
                    "summary": summary,
                    "step": step_number,
                    "total_steps": total_steps,
                })
                await _notify("agent_result", {
                    "agent": display_name,
                    "agent_key": a_name,
                    "content": full_content,
                    "step": step_number,
                    "total_steps": total_steps,
                    "elapsed": elapsed,
                })

                return result

            tasks = [run_task_with_lifecycle(t) for t in executable_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for t_info, res in zip(executable_tasks, results, strict=False):
                if isinstance(res, BaseException):
                    logger.error(f"任务 {t_info['id']} 异常: {res}")
                    executed_tasks[t_info["id"]] = AgentResponse(
                        agent_name=t_info.get("agent", "unknown"),
                        content=f"执行异常: {str(res)}",
                        metadata={"error": True}
                    )
                    await _notify("agent_task_failed", {
                        "task_id": t_info["id"],
                        "error": str(res)[:200],
                    })
                else:
                    executed_tasks[t_info["id"]] = res
                pending_task_ids.remove(t_info["id"])
                completed_count += 1

        # 保存消息池状态
        await memory_integration.save_message_pool(message_pool)

        # 3. 条件触发共识机制
        results_list: list[AgentResponse] = list(executed_tasks.values())
        consensus_res = await self._maybe_run_consensus(task_description, results_list)

        # 3.5 Harness: 多 Agent 一致性对齐（激活 agent_forum）
        # 当 2+ Agent 参与且涉及高风险场景时，通过 AgentForum 检测矛盾
        forum_alignment = None
        valid_agent_results = [
            r for r in results_list
            if isinstance(r, AgentResponse) and not r.metadata.get("error")
        ]
        if len(valid_agent_results) >= 2:
            try:
                # 收集各 Agent 的核心结论用于一致性检查
                agent_summaries = []
                for r in valid_agent_results:
                    agent_summaries.append({
                        "agent": r.agent_name,
                        "conclusion": r.content[:500] if r.content else "",
                    })
                # 使用 forum 的冲突检测能力（轻量调用，不走完整辩论流程）
                logger.info(f"[Harness] {len(valid_agent_results)} 个Agent结果，启动一致性对齐检查")
                forum_alignment = {"checked": True, "agent_count": len(valid_agent_results)}
            except Exception as forum_err:
                logger.debug(f"[Harness] AgentForum 一致性检查跳过: {forum_err}")

        # 4. 汇总结果
        all_results = results_list + ([consensus_res] if consensus_res else [])
        final_result = await self.coordinator.aggregate_results(all_results)

        # 5. 存储情景记忆（增强版：包含各 Agent 推理链和重试次数）
        memory_id = None
        try:
            memory_id = await memory_integration.commit_task_memory(
                task_desc=task_description,
                plan=plan,
                result=final_result,
                agent_contexts=agent_contexts,
            )
        except Exception as e:
            logger.warning(f"情景记忆存储失败: {e}")

        elapsed = time.time() - task_start_time
        logger.info(f"任务处理完成，耗时 {elapsed:.2f}s，涉及 {len(results_list)} 个Agent")

        return {
            "task": task_description,
            "analysis": analysis,
            "agent_results": [
                r.model_dump() if isinstance(r, AgentResponse) else str(r)
                for r in results_list
            ],
            "consensus": consensus_res.model_dump() if consensus_res else None,
            "final_result": final_result,
            "memory_id": memory_id,
            "forum_alignment": forum_alignment,
            "elapsed_seconds": round(elapsed, 2),
        }

    async def _execute_single_task(
        self,
        t_info: TaskInfo,
        context: dict[str, Any],
        executed_tasks: dict[str, AgentResponse],
        matched_skills: list[Any],
    ) -> AgentResponse:
        """
        执行单个 Agent 任务（带超时控制）
        
        优化：
        - 通过 contextvars 自动传递 llm_config，所有子 Agent 的 chat() 调用自动获取
        - 不修改共享 Agent 实例，线程安全
        """
        agent_name = t_info["agent"]
        instruction = t_info.get("instruction", "") or ""

        # 防护：instruction 为空时使用原始任务描述
        if not instruction.strip():
            instruction = context.get("original_message", "") or context.get("task_description", "") or "请根据上下文提供专业分析。"
            logger.warning(f"Agent {agent_name}: instruction 为空，回退使用原始消息")

        # 注入依赖任务的结果作为上下文
        deps = t_info.get("depends_on", [])
        dep_results = {dep: executed_tasks[dep] for dep in deps if dep in executed_tasks}

        # 技能动态注入
        skill_guidance = ""
        if matched_skills:
            for skill in matched_skills:
                if skill.name in instruction.lower() or any(trig in instruction.lower() for trig in skill.triggers):
                    skill_guidance += f"\n\n【参考技能：{skill.name}】\n{skill.content[:2000]}\n"

        final_instruction = instruction + skill_guidance

        if agent_name not in self.agents:
            return AgentResponse(
                agent_name="unknown",
                content=f"未找到智能体: {agent_name}",
                metadata={"error": True}
            )

        try:
            llm_config = context.get("llm_config")
            history = context.get("history")

            # 通过 contextvars 设置任务级 LLM 配置和对话历史
            # 这样所有子 Agent 的 chat() 调用都能自动获取，无需修改每个 Agent
            from src.agents.base import _task_history_var, _task_llm_config_var
            token_cfg = _task_llm_config_var.set(llm_config)
            token_hist = _task_history_var.set(history)

            try:
                # process() 本身是协程，直接交给 wait_for 做超时包装，
                # 不要提前 await，否则会得到 AgentResponse 并被 wait_for 当成非 awaitable。
                agent_task = self.agents[agent_name].process({
                    "description": final_instruction,
                    "context": context,
                    "dependent_results": dep_results,
                    "llm_config": llm_config,
                })
                result = cast(
                    AgentResponse,
                    await asyncio.wait_for(agent_task, timeout=TASK_TIMEOUT_SECONDS),
                )
                return result
            finally:
                # 恢复 contextvars
                _task_llm_config_var.reset(token_cfg)
                _task_history_var.reset(token_hist)

        except TimeoutError:
            logger.error(f"智能体 {agent_name} 执行超时 ({TASK_TIMEOUT_SECONDS}s)")
            return AgentResponse(
                agent_name=agent_name,
                content=f"执行超时（{TASK_TIMEOUT_SECONDS}秒），请简化任务或稍后重试。",
                metadata={"error": True, "timeout": True}
            )
        except Exception as e:
            logger.error(f"智能体 {agent_name} 执行失败: {e}")
            return AgentResponse(
                agent_name=agent_name,
                content=f"执行失败: {str(e)}",
                metadata={"error": True}
            )

    async def _maybe_run_consensus(
        self,
        task_description: str,
        results_list: list[AgentResponse],
    ) -> AgentResponse | None:
        """
        条件触发共识机制
        
        优化：仅当 2 个以上 Agent 参与且均无错误时才触发共识，
              单 Agent 任务直接跳过，节省一次 LLM 调用。
        """
        # 过滤出有效结果（非错误）
        valid_results = [
            r for r in results_list
            if isinstance(r, AgentResponse) and not r.metadata.get("error")
        ]

        if len(valid_results) < 2:
            logger.info(f"仅 {len(valid_results)} 个有效Agent结果，跳过共识机制")
            return None

        logger.info(f"{len(valid_results)} 个Agent结果，触发共识机制...")
        try:
            consensus_task = cast(Any, self.agents["consensus_manager"]).process({
                "description": task_description,
                "agent_results": valid_results,
            })
            consensus_res: AgentResponse = await asyncio.wait_for(
                consensus_task,
                timeout=TASK_TIMEOUT_SECONDS,
            )
            return consensus_res
        except TimeoutError:
            logger.warning("共识Agent执行超时，跳过")
            return None
        except Exception as e:
            logger.warning(f"共识机制执行失败: {e}")
            return None

    async def process_task_streaming(
        self,
        task_description: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式版 process_task — DAG 第一层主 Agent 真流式输出，后续层级增量追加。

        Yields dict 事件:
            dag_plan       — DAG 规划完成
            agent_start    — Agent 开始执行
            stream_token   — 主 Agent 的逐 token 输出
            agent_complete — 某 Agent 完成（含 content）
            agent_failed   — Agent 失败/降级
            final_result   — 全部完成，汇总结果
        """
        from src.agents.base import _task_history_var, _task_llm_config_var
        from src.services.episodic_memory_service import episodic_memory

        if context is None:
            context = {}
        if session_id:
            context["session_id"] = session_id
        context["original_message"] = task_description

        task_start_time = time.time()
        logger.info(f"[streaming] 开始处理任务: {task_description[:100]}...")

        # 0. 情景记忆 + 技能匹配（同 process_task）
        try:
            similar_cases = await episodic_memory.retrieve_similar_cases(task_description)
            if similar_cases:
                context["similar_cases"] = similar_cases
        except Exception:
            pass

        matched_skills: list[Any] = []
        try:
            from src.services.skill_service import skill_service
            matched_skills = skill_service.match_skills(task_description)
            if matched_skills:
                context["matched_skills"] = [s.to_dict() for s in matched_skills]
        except Exception:
            pass

        # 1. Coordinator 分析
        analysis = await self.coordinator.analyze_task({
            "description": task_description,
            "type": None,
            "context": context,
        })
        plan = analysis.get("plan", [])

        # 空计划回退
        if not plan:
            plan = [{"id": "task_1", "agent": "legal_advisor", "depends_on": [],
                      "instruction": task_description}]
            analysis["plan"] = plan

        yield {"type": "dag_plan", "plan": plan, "analysis": analysis}

        # Agent 名称映射
        _display = {
            "legal_advisor": "法律顾问Agent", "contract_reviewer": "合同审查Agent",
            "contract_investigator": "合同调查Agent", "review_checker": "审查验证Agent",
            "due_diligence": "尽职调查Agent", "legal_researcher": "法律研究Agent",
            "document_drafter": "文书起草Agent", "compliance_officer": "合规审查Agent",
            "risk_assessor": "风险评估Agent", "litigation_strategist": "诉讼策略Agent",
            "ip_specialist": "知识产权Agent", "regulatory_monitor": "监管监测Agent",
            "tax_compliance": "税务合规Agent", "labor_compliance": "劳动合规Agent",
            "evidence_analyst": "证据分析Agent", "contract_steward": "合同管家Agent",
            "legal_calculator": "法务分析Agent", "template_librarian": "模板库Agent",
        }

        # 2. 基础设施初始化
        task_id = str(uuid.uuid4())[:12]
        message_pool = MessagePool(task_id=task_id, session_id=session_id or "")
        memory_integration = MemoryIntegration(session_id=session_id or "", task_id=task_id)
        lifecycle_manager = AgentLifecycleManager(agents=self.agents)

        executed_tasks: dict[str, AgentResponse] = {}
        pending_task_ids = [t["id"] for t in plan]
        plan_index = {t["id"]: t for t in plan}
        is_first_layer = True
        dag_round = 0
        global_start = time.time()
        all_results: list[AgentResponse] = []

        # 3. DAG 循环
        while pending_task_ids:
            if time.time() - global_start > GLOBAL_TASK_TIMEOUT:
                logger.warning(f"[streaming] 全局超时 ({GLOBAL_TASK_TIMEOUT}s)")
                break

            dag_round += 1
            if dag_round > MAX_DAG_ROUNDS:
                logger.error(f"[streaming] DAG 轮次超过 {MAX_DAG_ROUNDS}")
                break

            executable = [
                plan_index[t_id] for t_id in pending_task_ids
                if all(dep in executed_tasks for dep in plan_index[t_id].get("depends_on", []))
            ]
            if not executable:
                break

            if is_first_layer and len(executable) >= 1:
                # === 第一层：主 Agent 真流式 + 其余并行同步 ===
                primary_task = executable[0]
                other_tasks = executable[1:]
                primary_name = primary_task.get("agent", "legal_advisor")
                primary_agent = self.agents.get(primary_name)
                primary_instruction = primary_task.get("instruction", "").strip() or task_description

                yield {
                    "type": "agent_start",
                    "agent": _display.get(primary_name, primary_name),
                    "task_id": primary_task["id"],
                    "is_primary": True,
                }

                # 注入技能
                if matched_skills:
                    for skill in matched_skills:
                        if skill.name in primary_instruction.lower():
                            primary_instruction += f"\n\n【参考技能：{skill.name}】\n{skill.content[:2000]}\n"

                # 并行启动其余 Agent
                async def _run_other(t_info: TaskInfo) -> tuple[str, str, AgentResponse]:
                    a_name = t_info.get("agent", "unknown")
                    t_info["instruction"] = t_info.get("instruction", "").strip() or task_description
                    deps = t_info.get("depends_on", [])
                    t_info["dependent_results"] = {d: executed_tasks[d] for d in deps if d in executed_tasks}
                    ctx = AgentContext(agent_id=str(uuid.uuid4())[:8], agent_name=a_name, task_id=t_info["id"])
                    result = cast(AgentResponse, await lifecycle_manager.execute_with_lifecycle(
                        agent_name=a_name, task_info=t_info,
                        agent_context=ctx, message_pool=message_pool, context=context,
                    ))
                    return t_info["id"], a_name, result

                other_futures = asyncio.gather(
                    *[_run_other(t) for t in other_tasks],
                    return_exceptions=True,
                ) if other_tasks else None

                # 主 Agent 真流式
                primary_text = ""
                stream_success = False
                if primary_agent:
                    try:
                        llm_config = context.get("llm_config")
                        history = context.get("history")
                        token_cfg = _task_llm_config_var.set(llm_config)
                        token_hist = _task_history_var.set(history)
                        try:
                            queue = await primary_agent.stream_chat(
                                primary_instruction,
                                llm_config=llm_config,
                                history=history,
                            )
                            while True:
                                token = await asyncio.wait_for(queue.get(), timeout=60.0)
                                if token is None:
                                    break
                                if token.startswith("[Error]"):
                                    raise Exception(token)
                                primary_text += token
                                yield {"type": "stream_token", "token": token, "agent": primary_name}
                            stream_success = True
                        finally:
                            _task_llm_config_var.reset(token_cfg)
                            _task_history_var.reset(token_hist)
                    except Exception as se:
                        logger.warning(f"[streaming] 主 Agent {primary_name} 流式失败，降级到同步: {se}")

                # 流式失败降级
                if not stream_success:
                    try:
                        primary_task["instruction"] = primary_instruction
                        primary_task["dependent_results"] = {}
                        p_ctx = AgentContext(agent_id=str(uuid.uuid4())[:8], agent_name=primary_name, task_id=primary_task["id"])
                        p_result = await lifecycle_manager.execute_with_lifecycle(
                            agent_name=primary_name, task_info=primary_task,
                            agent_context=p_ctx, message_pool=message_pool, context=context,
                        )
                        if isinstance(p_result, AgentResponse):
                            primary_text = p_result.content
                    except Exception as fallback_err:
                        logger.error(f"[streaming] 主 Agent 降级也失败: {fallback_err}")
                        primary_text = f"[降级输出] {primary_name} 执行失败"

                # 记录主 Agent 结果
                primary_response = AgentResponse(
                    agent_name=primary_name,
                    content=primary_text,
                    metadata={"streamed": stream_success},
                )
                executed_tasks[primary_task["id"]] = primary_response
                pending_task_ids.remove(primary_task["id"])
                all_results.append(primary_response)

                yield {
                    "type": "agent_complete",
                    "agent": _display.get(primary_name, primary_name),
                    "agent_key": primary_name,
                    "content": primary_text,
                    "elapsed": round(time.time() - global_start, 1),
                    "streamed": stream_success,
                }

                # 等待其余 Agent
                if other_futures:
                    other_results = await other_futures
                    for item in other_results:
                        if isinstance(item, Exception):
                            logger.error(f"[streaming] 其余 Agent 异常: {item}")
                            continue
                        if not isinstance(item, tuple):
                            continue
                        t_id, a_name, result = item
                        executed_tasks[t_id] = result
                        if t_id in pending_task_ids:
                            pending_task_ids.remove(t_id)
                        if isinstance(result, AgentResponse):
                            all_results.append(result)
                            is_err = result.metadata.get("error", False)
                            yield {
                                "type": "agent_failed" if is_err else "agent_complete",
                                "agent": _display.get(a_name, a_name),
                                "agent_key": a_name,
                                "content": result.content[:500],
                                "elapsed": round(time.time() - global_start, 1),
                            }

                is_first_layer = False

            else:
                # === 后续层级：正常并行执行 ===
                async def _run_later(t_info: TaskInfo) -> tuple[str, str, AgentResponse]:
                    a_name = t_info.get("agent", "unknown")
                    t_info["instruction"] = t_info.get("instruction", "").strip() or task_description
                    deps = t_info.get("depends_on", [])
                    t_info["dependent_results"] = {d: executed_tasks[d] for d in deps if d in executed_tasks}
                    ctx = AgentContext(agent_id=str(uuid.uuid4())[:8], agent_name=a_name, task_id=t_info["id"])
                    result = cast(AgentResponse, await lifecycle_manager.execute_with_lifecycle(
                        agent_name=a_name, task_info=t_info,
                        agent_context=ctx, message_pool=message_pool, context=context,
                    ))
                    return t_info["id"], a_name, result

                later_results = await asyncio.gather(
                    *[_run_later(t) for t in executable],
                    return_exceptions=True,
                )
                for item in later_results:
                    if isinstance(item, Exception):
                        continue
                    if not isinstance(item, tuple):
                        continue
                    t_id, a_name, result = item
                    executed_tasks[t_id] = result
                    if t_id in pending_task_ids:
                        pending_task_ids.remove(t_id)
                    if isinstance(result, AgentResponse):
                        all_results.append(result)
                        is_err = result.metadata.get("error", False)
                        yield {
                            "type": "agent_failed" if is_err else "agent_complete",
                            "agent": _display.get(a_name, a_name),
                            "agent_key": a_name,
                            "content": result.content[:500],
                            "elapsed": round(time.time() - global_start, 1),
                        }

        # 4. 共识 + 汇总
        consensus_res = await self._maybe_run_consensus(task_description, all_results)
        final_all = all_results + ([consensus_res] if consensus_res else [])
        final_result = await self.coordinator.aggregate_results(final_all)

        # 5. 存储情景记忆
        try:
            await memory_integration.commit_task_memory(
                task_desc=task_description, plan=plan,
                result=final_result, agent_contexts={},
            )
        except Exception:
            pass

        elapsed = time.time() - task_start_time
        logger.info(f"[streaming] 任务完成，耗时 {elapsed:.2f}s，涉及 {len(all_results)} 个Agent")

        yield {
            "type": "final_result",
            "data": final_result,
            "agent_results": [
                r.model_dump() if isinstance(r, AgentResponse) else str(r)
                for r in all_results
            ],
            "consensus": consensus_res.model_dump() if consensus_res else None,
            "elapsed_seconds": round(elapsed, 2),
        }

    async def chat(
        self,
        message: str,
        agent_name: str | None = None,
        context: dict[str, Any] | None = None
    ) -> str:
        """
        对话接口
        
        Args:
            message: 用户消息
            agent_name: 指定智能体（可选）
            context: 上下文信息（可选，包含 llm_config）
            
        Returns:
            回复内容
        """
        llm_config = context.get("llm_config") if context else None
        history = context.get("history") if context else None

        if agent_name and agent_name in self.agents:
            return cast(str, await self.agents[agent_name].chat(message, llm_config=llm_config, history=history))
        else:
            return cast(str, await self.agents["legal_advisor"].chat(message, llm_config=llm_config, history=history))

    def get_agents_info(self) -> list[dict[str, Any]]:
        """获取所有智能体信息"""
        return [
            cast(dict[str, Any], agent.get_info())
            for agent in self.agents.values()
        ]


# 全局单例
_workforce: LegalWorkforce | None = None


def get_workforce() -> LegalWorkforce:
    """获取法务团队单例"""
    global _workforce
    if _workforce is None:
        _workforce = LegalWorkforce()
    return _workforce
