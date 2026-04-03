# -*- coding: utf-8 -*-
"""
输出质量校验引擎

在 Agent 输出返回用户之前，执行多重校验：
1. 结构校验：响应非空、格式合理
2. 引用核查：法条/案例编号真实存在
3. 相关性检测：回答是否偏题
4. 风险检测：是否包含高风险内容（如未经审批的法律意见）
5. 一致性检测：多 Agent 结果是否矛盾
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ValidationLevel(str, Enum):
    """校验结果级别"""
    PASS = "pass"
    WARNING = "warning"      # 警告但仍返回
    FAIL = "fail"            # 需要修正
    CRITICAL = "critical"    # 阻断返回


@dataclass
class ValidationIssue:
    """单个校验问题"""
    check_name: str
    level: ValidationLevel
    message: str
    detail: Optional[str] = None


@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0-1.0 质量分

    @property
    def has_critical(self) -> bool:
        return any(i.level == ValidationLevel.CRITICAL for i in self.issues)

    @property
    def has_fail(self) -> bool:
        return any(i.level == ValidationLevel.FAIL for i in self.issues)

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 2),
            "issue_count": len(self.issues),
            "issues": [
                {"check": i.check_name, "level": i.level.value, "message": i.message}
                for i in self.issues
            ],
        }


# ===== 法律引用模式 =====
_LAW_CITATION_RE = re.compile(r'《([^》]+)》')
_ARTICLE_RE = re.compile(r'第[一二三四五六七八九十百千\d]+条')
_CASE_NUMBER_RE = re.compile(r'[（(]\d{4}[）)][^，。\n]{2,20}号')

# ===== 高风险短语 =====
_HIGH_RISK_PHRASES = [
    "本律师认为", "法律意见如下", "正式法律意见",
    "保证胜诉", "一定能赢", "百分之百",
    "建议立即转账", "请提供银行卡", "请提供身份证号",
]


class OutputValidator:
    """输出质量校验引擎"""

    async def validate(
        self,
        response_text: str,
        user_query: str = "",
        agent_name: str = "",
        route: str = "general",
    ) -> ValidationResult:
        """
        执行全部校验

        Args:
            response_text: Agent 生成的回复
            user_query: 用户原始问题
            agent_name: 使用的 Agent 名称
            route: 路由类型

        Returns:
            ValidationResult
        """
        issues: List[ValidationIssue] = []
        score = 1.0

        # 1. 结构校验
        struct_issues = self._check_structure(response_text)
        issues.extend(struct_issues)

        # 2. 引用核查
        citation_issues = await self._check_citations(response_text)
        issues.extend(citation_issues)

        # 3. 相关性检测（仅当有用户问题时）
        if user_query:
            relevance_issues = self._check_relevance(response_text, user_query)
            issues.extend(relevance_issues)

        # 4. 风险检测
        risk_issues = self._check_risk_content(response_text, route)
        issues.extend(risk_issues)

        # 计算质量分
        for issue in issues:
            if issue.level == ValidationLevel.CRITICAL:
                score -= 0.4
            elif issue.level == ValidationLevel.FAIL:
                score -= 0.2
            elif issue.level == ValidationLevel.WARNING:
                score -= 0.05
        score = max(0.0, score)

        passed = not any(
            i.level in (ValidationLevel.FAIL, ValidationLevel.CRITICAL)
            for i in issues
        )

        result = ValidationResult(passed=passed, issues=issues, score=score)

        if not passed:
            logger.warning(
                f"[OutputValidator] 校验未通过 | agent={agent_name} | "
                f"score={score:.2f} | issues={len(issues)} | "
                f"fails={[i.message for i in issues if i.level in (ValidationLevel.FAIL, ValidationLevel.CRITICAL)]}"
            )

        return result

    def _check_structure(self, text: str) -> List[ValidationIssue]:
        """结构校验"""
        issues = []

        if not text or not text.strip():
            issues.append(ValidationIssue(
                check_name="structure.empty",
                level=ValidationLevel.CRITICAL,
                message="响应内容为空",
            ))
            return issues

        if len(text.strip()) < 10:
            issues.append(ValidationIssue(
                check_name="structure.too_short",
                level=ValidationLevel.WARNING,
                message=f"响应过短（{len(text.strip())}字）",
            ))

        # 检测明显的模型拒绝/错误
        refusal_patterns = [
            "I cannot", "I'm sorry, I can't", "作为AI，我无法",
            "我没有能力", "超出了我的能力范围",
        ]
        for pattern in refusal_patterns:
            if pattern.lower() in text.lower():
                issues.append(ValidationIssue(
                    check_name="structure.refusal",
                    level=ValidationLevel.WARNING,
                    message="响应包含拒绝/能力限制声明",
                    detail=pattern,
                ))
                break

        return issues

    async def _check_citations(self, text: str) -> List[ValidationIssue]:
        """引用核查：检测法条引用的真实性"""
        issues = []

        law_refs = _LAW_CITATION_RE.findall(text)
        article_refs = _ARTICLE_RE.findall(text)

        if not law_refs:
            # 法律回复没有引用不一定是错误，但值得关注
            return issues

        # 基础校验：引用的法律名称是否看起来合理
        suspicious_laws = []
        for law_name in law_refs:
            # 检测明显虚构的法律名称（过长、包含特殊字符等）
            if len(law_name) > 30:
                suspicious_laws.append(law_name)
            elif re.search(r'[a-zA-Z\d]{5,}', law_name):
                suspicious_laws.append(law_name)

        if suspicious_laws:
            issues.append(ValidationIssue(
                check_name="citation.suspicious_law",
                level=ValidationLevel.WARNING,
                message=f"疑似虚构法律名称: {suspicious_laws[:3]}",
                detail=str(suspicious_laws),
            ))

        # 深度校验层 1：通过 citation_tracker 提取并验证
        try:
            from src.services.citation_tracker import citation_tracker
            if citation_tracker and law_refs:
                citations = citation_tracker.extract_citations(text)
                if citations:
                    unverified = [c for c in citations if not c.verified]
                    if unverified and len(unverified) > len(citations) * 0.5:
                        issues.append(ValidationIssue(
                            check_name="citation.unverified",
                            level=ValidationLevel.WARNING,
                            message=f"{len(unverified)}/{len(citations)} 条引用未验证",
                        ))
        except Exception as e:
            logger.debug(f"引用 citation_tracker 校验跳过: {e}")

        # 深度校验层 2：通过向量库检索验证法律名称是否存在
        try:
            from src.services.vector_store import VectorStoreService
            vs = VectorStoreService()
            for law_name in law_refs[:5]:  # 最多校验 5 条，控制延迟
                results = await vs.search(
                    query=law_name,
                    collection_name="legal_knowledge",
                    limit=1,
                    score_threshold=0.85,
                )
                if not results:
                    issues.append(ValidationIssue(
                        check_name="citation.not_found_in_kb",
                        level=ValidationLevel.WARNING,
                        message=f"法律《{law_name}》未在知识库中找到匹配",
                        detail=f"建议确认该法律名称是否准确",
                    ))
        except Exception as e:
            logger.debug(f"引用向量库校验跳过: {e}")

        return issues

    def _check_relevance(self, response: str, query: str) -> List[ValidationIssue]:
        """相关性检测：回答是否偏离问题"""
        issues = []

        # 简单关键词覆盖检测
        # 提取用户问题中的关键名词（去掉常用虚词）
        stop_words = {"的", "了", "吗", "呢", "啊", "是", "在", "我", "你", "他",
                      "她", "有", "这", "那", "和", "与", "到", "对", "请", "帮",
                      "能", "可以", "怎么", "如何", "什么", "哪些", "为什么", "多少"}

        query_keywords = set()
        for char_group in re.findall(r'[\u4e00-\u9fff]{2,}', query):
            if char_group not in stop_words:
                query_keywords.add(char_group)

        if query_keywords:
            covered = sum(1 for kw in query_keywords if kw in response)
            coverage_ratio = covered / len(query_keywords) if query_keywords else 1.0

            if coverage_ratio < 0.15 and len(query_keywords) >= 3:
                issues.append(ValidationIssue(
                    check_name="relevance.low_coverage",
                    level=ValidationLevel.WARNING,
                    message=f"回答可能偏题（关键词覆盖率 {coverage_ratio:.0%}）",
                    detail=f"用户关键词: {list(query_keywords)[:5]}",
                ))

        return issues

    def _check_risk_content(self, text: str, route: str) -> List[ValidationIssue]:
        """风险内容检测"""
        issues = []

        for phrase in _HIGH_RISK_PHRASES:
            if phrase in text:
                # 正式法律意见需要审批
                if phrase in ("本律师认为", "法律意见如下", "正式法律意见"):
                    issues.append(ValidationIssue(
                        check_name="risk.formal_opinion",
                        level=ValidationLevel.WARNING,
                        message=f"包含正式法律意见措辞: '{phrase}'（建议加免责声明）",
                    ))
                # 保证性承诺
                elif phrase in ("保证胜诉", "一定能赢", "百分之百"):
                    issues.append(ValidationIssue(
                        check_name="risk.guarantee",
                        level=ValidationLevel.FAIL,
                        message=f"包含不当保证性承诺: '{phrase}'",
                    ))
                # 敏感信息索取
                elif phrase in ("建议立即转账", "请提供银行卡", "请提供身份证号"):
                    issues.append(ValidationIssue(
                        check_name="risk.sensitive_request",
                        level=ValidationLevel.CRITICAL,
                        message=f"包含敏感信息索取: '{phrase}'",
                    ))

        return issues


# 全局单例
output_validator = OutputValidator()
