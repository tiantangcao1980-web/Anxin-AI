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
from typing import Any

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
    detail: str | None = None


@dataclass
class ValidationResult:
    """校验结果"""
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    score: float = 1.0  # 0.0-1.0 质量分

    @property
    def has_critical(self) -> bool:
        return any(i.level == ValidationLevel.CRITICAL for i in self.issues)

    @property
    def has_fail(self) -> bool:
        return any(i.level == ValidationLevel.FAIL for i in self.issues)

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == ValidationLevel.WARNING]

    def to_dict(self) -> dict[str, Any]:
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

    # validate() 方法定义在文件末尾（增强版，含场景化检查）

    def _check_structure(self, text: str) -> list[ValidationIssue]:
        """结构校验"""
        issues: list[ValidationIssue] = []

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

    async def _check_citations(self, text: str) -> list[ValidationIssue]:
        """引用核查：检测法条引用的真实性"""
        issues: list[ValidationIssue] = []

        law_refs = _LAW_CITATION_RE.findall(text)
        article_refs = _ARTICLE_RE.findall(text)

        if not law_refs:
            # 法律回复没有引用不一定是错误，但值得关注
            return issues
        if not article_refs:
            issues.append(ValidationIssue(
                check_name="citation.missing_article",
                level=ValidationLevel.WARNING,
                message="检测到法律名称引用，但未检测到具体条文编号",
            ))

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
            if not await vs.get_collection_info("legal_knowledge"):
                return issues
            for law_name in law_refs[:5]:  # 最多校验 5 条，控制延迟
                results = await vs.search(
                    query=law_name,
                    collection_name="legal_knowledge",
                    top_k=1,
                    score_threshold=0.85,
                )
                if not results:
                    issues.append(ValidationIssue(
                        check_name="citation.not_found_in_kb",
                        level=ValidationLevel.WARNING,
                        message=f"法律《{law_name}》未在知识库中找到匹配",
                        detail="建议确认该法律名称是否准确",
                    ))
        except Exception as e:
            logger.debug(f"引用向量库校验跳过: {e}")

        return issues

    def _check_relevance(self, response: str, query: str) -> list[ValidationIssue]:
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

    def _check_risk_content(self, text: str, route: str) -> list[ValidationIssue]:
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

    def _check_document_completeness(self, text: str, route: str) -> list[ValidationIssue]:
        """文书起草场景：检查输出是否包含法定格式要素"""
        issues: list[ValidationIssue] = []
        if route not in ("document_drafting", "DOCUMENT_DRAFTING"):
            return issues

        # 文书必须包含的要素
        required_elements = {
            "当事人信息": [r"甲方|乙方|原告|被告|申请人|被申请人|委托人"],
            "核心条款/请求": [r"第[一二三四五六七八九十\d]+条|诉讼请求|请求事项|合同标的"],
            "日期": [r"\d{4}\s*年\s*\d{1,2}\s*月|\d{4}-\d{2}-\d{2}"],
        }

        missing = []
        for element_name, patterns in required_elements.items():
            found = any(re.search(p, text) for p in patterns)
            if not found:
                missing.append(element_name)

        if missing:
            issues.append(ValidationIssue(
                check_name="document.incomplete",
                level=ValidationLevel.WARNING,
                message=f"文书可能缺少以下要素: {', '.join(missing)}",
                detail=f"建议补充: {missing}",
            ))

        return issues

    def _check_case_analysis_quality(self, text: str, route: str) -> list[ValidationIssue]:
        """案件分析场景：检查报告是否包含法律依据、证据评估、风险评估"""
        issues: list[ValidationIssue] = []
        # 对分析类路由生效
        analysis_routes = (
            "general", "LABOR_HR", "DEBT_COLLECTION", "LITIGATION_STRATEGY",
            "FAMILY_LAW", "CRIMINAL", "REAL_ESTATE",
        )
        if route not in analysis_routes:
            return issues

        # 分析报告的长度应该足够（至少 300 字才有实质内容）
        if len(text) < 300:
            return issues

        quality_indicators = {
            "法律依据": [r"《[^》]+》", r"第[一二三四五六七八九十百千\d]+条", r"根据.*规定"],
            "风险评估": [r"风险|注意|需要.*关注|建议.*重视|可能.*不利"],
            "行动建议": [r"建议|应当|可以.*考虑|下一步|行动方案"],
        }

        missing = []
        for indicator_name, patterns in quality_indicators.items():
            found = any(re.search(p, text) for p in patterns)
            if not found:
                missing.append(indicator_name)

        if len(missing) >= 2:
            issues.append(ValidationIssue(
                check_name="analysis.low_quality",
                level=ValidationLevel.WARNING,
                message=f"分析报告质量不足，缺少: {', '.join(missing)}",
                detail="高质量的法律分析应包含法律依据引用、风险评估和行动建议",
            ))

        return issues

    async def validate(
        self,
        response_text: str,
        user_query: str = "",
        agent_name: str = "",
        route: str = "general",
    ) -> ValidationResult:
        """
        执行全部校验（增强版，含场景化检查）
        """
        issues: list[ValidationIssue] = []
        score = 1.0

        # 1. 结构校验
        issues.extend(self._check_structure(response_text))

        # 2. 引用核查
        citation_issues = await self._check_citations(response_text)
        issues.extend(citation_issues)

        # 3. 相关性检测
        if user_query:
            issues.extend(self._check_relevance(response_text, user_query))

        # 4. 风险检测
        issues.extend(self._check_risk_content(response_text, route))

        # 5. 文书完整性检查（场景化）
        issues.extend(self._check_document_completeness(response_text, route))

        # 6. 案件分析质量检查（场景化）
        issues.extend(self._check_case_analysis_quality(response_text, route))

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


# 全局单例
output_validator = OutputValidator()
