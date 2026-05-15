"""
Skill 执行器服务模块（P5-A）

将 ``SkillRegistry`` 中的 ``Skill`` 当作运行时可执行单元：

    1. 拉取 SKILL body（系统提示）
    2. 注入 ``ExecutionContext``（user_id / persona / app_authorizations）
    3. 拼成 prompt 调 LLM（默认走 ``llm_callable`` 抽象，便于 mock）
    4. 返回 ``SkillResult`` + 写入 ``SkillExecutionLog``

未来扩展点：
    - tool call / 子 agent 编排
    - Python sandbox 直接执行（cowork docx/pptx 风格）
    - 引入并发 + 超时
"""

from src.services.skill_executor.decorators import requires_skill
from src.services.skill_executor.executor import SkillExecutor
from src.services.skill_executor.models import (
    ExecutionContext,
    SkillExecutionLog,
    SkillExecutionStatus,
    SkillResult,
)

__all__ = [
    "SkillExecutor",
    "ExecutionContext",
    "SkillResult",
    "SkillExecutionLog",
    "SkillExecutionStatus",
    "requires_skill",
]
