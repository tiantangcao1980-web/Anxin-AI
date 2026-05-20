"""
法律文书质量验证器

自动检查生成的法律文书质量：
1. 结构完整性（标题/编号/签署区）
2. 内容充实度（字数/条款数）
3. 法条引用准确性
4. 必备条款覆盖率
5. 格式规范性
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationIssue:
    """验证问题"""

    level: str  # critical / warning / info
    category: str  # structure / content / citation / format
    message: str
    suggestion: str = ""


@dataclass
class ValidationResult:
    """验证结果"""

    passed: bool
    score: float  # 0.0-1.0
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 2),
            "issues": [
                {
                    "level": i.level,
                    "category": i.category,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "stats": self.stats,
        }


class DocumentValidator:
    """法律文书质量验证器"""

    # 合同必备条款关键词
    REQUIRED_CONTRACT_CLAUSES = {
        "合同标的": ["标的", "标的物", "服务内容", "合同内容"],
        "价款/报酬": ["价款", "报酬", "金额", "费用", "租金", "工资"],
        "履行期限": ["期限", "有效期", "起始", "终止", "截止"],
        "违约责任": ["违约", "违约金", "赔偿"],
        "争议解决": ["争议", "诉讼", "仲裁", "管辖"],
    }

    # 可选但建议有的条款
    RECOMMENDED_CLAUSES = {
        "保密条款": ["保密", "商业秘密", "机密"],
        "不可抗力": ["不可抗力", "不能预见", "不能避免"],
        "通知送达": ["通知", "送达", "书面通知"],
        "合同变更": ["变更", "修改", "补充协议"],
    }

    @staticmethod
    def normalize_doc_type(doc_type: str) -> str:
        value = (doc_type or "").lower()
        if any(token in value for token in ["合同", "协议", "contract"]):
            return "contract"
        if any(token in value for token in ["起诉", "诉状", "答辩", "申请书"]):
            return "lawsuit"
        if any(token in value for token in ["律师函", "催告函", "通知函"]):
            return "lawyer_letter"
        if any(token in value for token in ["法律意见", "尽调", "尽职调查"]):
            return "legal_opinion"
        return "generic"

    @classmethod
    def validate_document(cls, text: str, doc_type: str) -> ValidationResult:
        normalized = cls.normalize_doc_type(doc_type)
        if normalized == "contract":
            return cls.validate_contract(text, doc_type)
        if normalized == "lawsuit":
            return cls.validate_lawsuit(text)
        if normalized == "lawyer_letter":
            return cls.validate_lawyer_letter(text)
        if normalized == "legal_opinion":
            return cls.validate_legal_opinion(text)
        return cls.validate_generic_document(text, doc_type)

    @classmethod
    def _finalize_result(
        cls, issues: list[ValidationIssue], stats: dict[str, Any]
    ) -> ValidationResult:
        critical_count = sum(1 for issue in issues if issue.level == "critical")
        warning_count = sum(1 for issue in issues if issue.level == "warning")
        score = 1.0
        score -= critical_count * 0.18
        score -= warning_count * 0.06
        score = max(0.0, min(1.0, score))
        return ValidationResult(
            passed=critical_count == 0 and score >= 0.7,
            score=score,
            issues=issues,
            stats=stats,
        )

    @classmethod
    def validate_contract(cls, text: str, contract_type: str = "") -> ValidationResult:
        """
        验证合同文书质量

        Returns:
            ValidationResult with score and issues
        """
        issues: list[ValidationIssue] = []
        stats: dict[str, Any] = {}

        # === 1. 基础统计 ===
        char_count = len(text)
        word_count = len(text.replace(" ", "").replace("\n", ""))
        line_count = len(text.split("\n"))
        stats["char_count"] = char_count
        stats["word_count"] = word_count
        stats["line_count"] = line_count

        if word_count < 1200:
            issues.append(
                ValidationIssue(
                    level="critical",
                    category="content",
                    message=f"合同内容过短（{word_count}字），不足以构成可交付草案",
                    suggestion="补充完整的权利义务、履行、违约责任、争议解决、签署区等条款",
                )
            )
        elif word_count < 2500:
            issues.append(
                ValidationIssue(
                    level="warning",
                    category="content",
                    message=f"合同内容仍偏短（{word_count}字），建议继续充实具体条件与责任",
                    suggestion="增加付款节点、验收标准、违约计算方式、通知送达等细节",
                )
            )

        has_h1 = bool(re.search(r"^#\s+.+", text, re.MULTILINE))
        if not has_h1:
            issues.append(
                ValidationIssue(
                    level="warning",
                    category="structure",
                    message="缺少合同标题（一级标题）",
                    suggestion="在合同开头添加 # 合同名称",
                )
            )

        clause_pattern = r"(?:第[一二三四五六七八九十百零\d]+条|##\s+第.*?条)"
        clause_matches = re.findall(clause_pattern, text)
        clause_count = len(clause_matches)
        stats["clause_count"] = clause_count

        if clause_count < 8:
            issues.append(
                ValidationIssue(
                    level="critical",
                    category="structure",
                    message=f"条款数量不足（仅{clause_count}条），不足以构成专业合同草案",
                    suggestion="至少补齐标的、价款、履行期限、验收、违约责任、争议解决、通知送达、附则等章节",
                )
            )

        has_parties = bool(re.search(r"甲方|乙方|出租方|承租方|买方|卖方|委托方|受托方", text))
        if not has_parties:
            issues.append(
                ValidationIssue(
                    level="critical",
                    category="structure",
                    message="缺少当事方信息（甲方/乙方）",
                    suggestion="在合同开头添加甲乙双方的名称、地址、联系方式等信息",
                )
            )

        has_signature = bool(re.search(r"签字|盖章|签章|签名.*日期|日期.*签名", text))
        if not has_signature:
            issues.append(
                ValidationIssue(
                    level="warning",
                    category="structure",
                    message="缺少签署区（盖章/签字/日期）",
                    suggestion="在合同末尾添加甲乙双方盖章、签字和日期的区域",
                )
            )

        covered_clauses = []
        missing_clauses = []

        for clause_name, keywords in cls.REQUIRED_CONTRACT_CLAUSES.items():
            found = any(kw in text for kw in keywords)
            if found:
                covered_clauses.append(clause_name)
            else:
                missing_clauses.append(clause_name)
                issues.append(
                    ValidationIssue(
                        level="critical",
                        category="content",
                        message=f"缺少必备条款：{clause_name}",
                        suggestion=f"根据民法典第470条，合同应包含{clause_name}相关约定",
                    )
                )

        for clause_name, keywords in cls.RECOMMENDED_CLAUSES.items():
            if not any(kw in text for kw in keywords):
                issues.append(
                    ValidationIssue(
                        level="info",
                        category="content",
                        message=f"建议增加：{clause_name}",
                        suggestion=f"添加{clause_name}可以更好地保护双方权益",
                    )
                )

        coverage = len(covered_clauses) / max(len(cls.REQUIRED_CONTRACT_CLAUSES), 1)
        stats["required_coverage"] = round(coverage, 2)
        stats["covered_clauses"] = covered_clauses
        stats["missing_clauses"] = missing_clauses

        citation_pattern = r"《[^》]+》第\d+条"
        citations = re.findall(citation_pattern, text)
        stats["citation_count"] = len(citations)

        if len(citations) == 0 and word_count > 1000:
            issues.append(
                ValidationIssue(
                    level="info",
                    category="citation",
                    message="合同中未引用具体法律条文",
                    suggestion="在关键条款处引用法律依据可增强合同的法律效力说服力",
                )
            )

        placeholder_count = len(re.findall(r"【[^】]*】|______", text))
        stats["placeholder_count"] = placeholder_count

        has_amount = bool(re.search(r"[人民币RMB￥¥]\s*[\d,]+", text))
        has_chinese_amount = bool(re.search(r"[壹贰叁肆伍陆柒捌玖拾佰仟万亿]", text))
        if has_amount and not has_chinese_amount:
            issues.append(
                ValidationIssue(
                    level="info",
                    category="format",
                    message="合同金额缺少大写中文",
                    suggestion="正式合同中金额应同时标注阿拉伯数字和大写中文",
                )
            )

        return cls._finalize_result(issues, stats)

    @classmethod
    def validate_lawsuit(cls, text: str) -> ValidationResult:
        """验证诉讼文书质量"""
        issues: list[ValidationIssue] = []
        stats: dict[str, Any] = {"word_count": len(text.replace(" ", ""))}

        # 原告/被告信息
        if not re.search(r"原告", text):
            issues.append(ValidationIssue("critical", "structure", "缺少原告信息"))
        if not re.search(r"被告", text):
            issues.append(ValidationIssue("critical", "structure", "缺少被告信息"))

        # 诉讼请求
        if not re.search(r"诉讼请求|请求.*法院", text):
            issues.append(ValidationIssue("critical", "structure", "缺少诉讼请求"))

        # 事实与理由
        if not re.search(r"事实.*理由|事实与理由", text):
            issues.append(ValidationIssue("warning", "structure", "缺少事实与理由部分"))

        # 此致xx法院
        if not re.search(r"此致|人民法院", text):
            issues.append(ValidationIssue("warning", "structure", "缺少结尾格式（此致XX人民法院）"))

        return cls._finalize_result(issues, stats)

    @classmethod
    def validate_lawyer_letter(cls, text: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        stats: dict[str, Any] = {"word_count": len(text.replace(" ", ""))}
        if not re.search(r"致[:：]", text):
            issues.append(ValidationIssue("critical", "structure", "缺少致函对象"))
        if not re.search(r"委托|受.*委托", text):
            issues.append(ValidationIssue("critical", "structure", "缺少委托说明"))
        if not re.search(r"要求|函告|请贵方", text):
            issues.append(ValidationIssue("critical", "content", "缺少明确履行要求"))
        if not re.search(r"\d+\s*日内|期限|收到本函之日起", text):
            issues.append(ValidationIssue("critical", "content", "缺少履行期限"))
        if not re.search(r"法律后果|诉讼|仲裁", text):
            issues.append(ValidationIssue("warning", "content", "缺少后果警示"))
        return cls._finalize_result(issues, stats)

    @classmethod
    def validate_legal_opinion(cls, text: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        stats: dict[str, Any] = {"word_count": len(text.replace(" ", ""))}
        if not re.search(r"致[:：]", text):
            issues.append(ValidationIssue("warning", "structure", "缺少致送对象"))
        if not re.search(r"引言|委托事项|委托范围", text):
            issues.append(ValidationIssue("critical", "structure", "缺少引言或委托范围说明"))
        if not re.search(r"事实概述|基本事实", text):
            issues.append(ValidationIssue("critical", "structure", "缺少事实前提"))
        if not re.search(r"法律分析|分析意见", text):
            issues.append(ValidationIssue("critical", "structure", "缺少法律分析框架"))
        if not re.search(r"四[、.]法律意见|四[、.]结论|结论意见|综上所述", text):
            issues.append(ValidationIssue("critical", "content", "缺少法律意见结论"))
        if not re.search(r"特别说明|保留意见|适用限制", text):
            issues.append(ValidationIssue("warning", "content", "缺少特别说明或适用限制"))
        return cls._finalize_result(issues, stats)

    @classmethod
    def validate_generic_document(cls, text: str, doc_type: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        stats: dict[str, Any] = {
            "word_count": len(text.replace(" ", "")),
            "doc_type": doc_type,
        }
        if not re.search(r"^#\s+.+", text, re.MULTILINE):
            issues.append(ValidationIssue("warning", "structure", "缺少文书标题"))
        if len(text.replace(" ", "").replace("\n", "")) < 500:
            issues.append(ValidationIssue("critical", "content", "文书内容过短"))
        return cls._finalize_result(issues, stats)
