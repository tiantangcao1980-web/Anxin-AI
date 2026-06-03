# -*- coding: utf-8 -*-
"""
Harness 输出强制接入（H1）

H0 体检发现：chat_service 中 output_validator 是软接入：
- try/except 把异常吞成 debug
- 失败仅 log warning，回答原样发出

本模块把"如何根据校验结果处理响应"集中到一个函数，让 chat_service 调用一行即可。

语义（动作枚举 action）：
    pass            校验通过，原样返回
    warned          WARNING：在末尾追加免责声明
    retry           FAIL：调用方应触发单次重试，并在响应里带 _harness.validation_failed
    rejected        CRITICAL：直接替换为统一拒绝消息（**禁止**保留原回答）
    validator_error validator 自身异常：视同 rejected（保守默认）

关联：
- AGENTS.md §3.4 输出约定
- docs/audit/harness/00-integration-matrix.md 中 P0：output_validator 软接入
"""

from __future__ import annotations

from loguru import logger

from src.harness.output_validator import (
    ValidationLevel,
    ValidationResult,
    output_validator,
)

# ===== 统一文案 =====

REJECTION_TEXT = (
    "抱歉，本次回答未通过质量校验，已被拦截。\n\n"
    "可能原因：检测到高风险表述、敏感信息请求或引用不可验证。\n"
    "建议您：①换一种描述重新提问；②如紧急，建议直接联系执业律师。"
)

DISCLAIMER_TEXT = (
    "\n\n⚠️ 本回答仅供参考，不构成正式法律意见。如需专业法律服务，请咨询执业律师。"
)


# ===== 同步：根据校验结果决定动作（纯函数，便于单测） =====

def enforce_output(original_text: str, result: ValidationResult) -> tuple[str, str]:
    """根据校验结果决定最终响应文本和动作"""
    if result.has_critical:
        logger.warning(
            f"[Harness] 输出被拒绝(CRITICAL) | issues={[i.message for i in result.issues if i.level == ValidationLevel.CRITICAL]}"
        )
        return REJECTION_TEXT, "rejected"

    if result.has_fail:
        logger.warning(
            f"[Harness] 输出待重试(FAIL) | score={result.score:.2f} | issues={[i.message for i in result.issues if i.level == ValidationLevel.FAIL]}"
        )
        # 文本暂保留，调用方可在重试后覆盖
        return original_text, "retry"

    if result.warnings:
        logger.info(
            f"[Harness] 输出附加免责声明(WARNING) | score={result.score:.2f} | warnings={len(result.warnings)}"
        )
        return original_text + DISCLAIMER_TEXT, "warned"

    return original_text, "pass"


# ===== 异步：包装 validator 调用 + 兜底 =====

# 抽成模块级变量，便于测试替换
_validator_call = output_validator.validate


async def run_validation(
    *,
    response_text: str,
    user_query: str,
    agent_name: str | None = None,
    route: str | None = None,
) -> tuple[str, str]:
    """运行 validator 并应用强制策略。

    返回 (final_text, action)。action ∈ {pass, warned, retry, rejected, validator_error}
    """
    try:
        result: ValidationResult = await _validator_call(
            response_text=response_text,
            user_query=user_query,
            agent_name=agent_name or "",
            route=route or "general",
        )
    except Exception as e:  # noqa: BLE001
        # 关键：必须 ERROR 级别，不能 debug 吞掉
        logger.error(f"[Harness] output_validator 调用失败: {e}", exc_info=True)
        return REJECTION_TEXT, "validator_error"

    return enforce_output(response_text, result)
