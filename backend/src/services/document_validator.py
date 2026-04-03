# -*- coding: utf-8 -*-
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
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class ValidationIssue:
    """验证问题"""
    level: str          # critical / warning / info
    category: str       # structure / content / citation / format
    message: str
    suggestion: str = ""


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    score: float                    # 0.0-1.0
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": round(self.score, 2),
            "issues": [
                {"level": i.level, "category": i.category, "message": i.message, "suggestion": i.suggestion}
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

    @classmethod
    def validate_contract(cls, text: str, contract_type: str = "") -> ValidationResult:
        """
        验证合同文书质量

        Returns:
            ValidationResult with score and issues
        """
        issues: List[ValidationIssue] = []
        stats: Dict[str, Any] = {}

        # === 1. 基础统计 ===
        char_count = len(text)
        word_count = len(text.replace(" ", "").replace("\n", ""))
        line_count = len(text.split("\n"))
        stats["char_count"] = char_count
        stats["word_count"] = word_count
        stats["line_count"] = line_count

        # === 2. 字数检查 ===
        if word_count < 500:
            issues.append(ValidationIssue(
                level="critical", category="content",
                message=f"合同内容过短（{word_count}字），不像正式合同文本",
                suggestion="合同正文建议不少于3000字，至少包含10个以上条款",
            ))
        elif word_count < 1500:
            issues.append(ValidationIssue(
                level="warning", category="content",
                message=f"合同内容较短（{word_count}字），可能条款不够详细",
                suggestion="建议补充违约责任、保密条款、争议解决等重要条款",
            ))

        # === 3. 结构检查 ===
        # 标题
        has_h1 = bool(re.search(r'^#\s+.+', text, re.MULTILINE))
        if not has_h1:
            issues.append(ValidationIssue(
                level="warning", category="structure",
                message="缺少合同标题（一级标题）",
                suggestion="在合同开头添加 # 合同名称",
            ))

        # 条款编号
        clause_pattern = r'(?:第[一二三四五六七八九十百零\d]+条|##\s+第.*?条)'
        clause_matches = re.findall(clause_pattern, text)
        clause_count = len(clause_matches)
        stats["clause_count"] = clause_count

        if clause_count < 5:
            issues.append(ValidationIssue(
                level="critical" if clause_count < 3 else "warning",
                category="structure",
                message=f"条款数量不足（仅{clause_count}条），不符合专业合同标准",
                suggestion="专业合同通常包含10条以上条款，建议补充标的、价款、履行、违约责任、争议解决等",
            ))

        # 当事方信息
        has_parties = bool(re.search(r'甲方|乙方|出租方|承租方|买方|卖方|委托方|受托方', text))
        if not has_parties:
            issues.append(ValidationIssue(
                level="critical", category="structure",
                message="缺少当事方信息（甲方/乙方）",
                suggestion="在合同开头添加甲乙双方的名称、地址、联系方式等信息",
            ))

        # 签署区
        has_signature = bool(re.search(r'签字|盖章|签章|签名.*日期|日期.*签名', text))
        if not has_signature:
            issues.append(ValidationIssue(
                level="warning", category="structure",
                message="缺少签署区（盖章/签字/日期）",
                suggestion="在合同末尾添加甲乙双方盖章、签字和日期的区域",
            ))

        # === 4. 必备条款检查 ===
        covered_clauses = []
        missing_clauses = []

        for clause_name, keywords in cls.REQUIRED_CONTRACT_CLAUSES.items():
            found = any(kw in text for kw in keywords)
            if found:
                covered_clauses.append(clause_name)
            else:
                missing_clauses.append(clause_name)
                issues.append(ValidationIssue(
                    level="critical", category="content",
                    message=f"缺少必备条款：{clause_name}",
                    suggestion=f"根据民法典第470条，合同应包含{clause_name}相关约定",
                ))

        # 推荐条款
        for clause_name, keywords in cls.RECOMMENDED_CLAUSES.items():
            if not any(kw in text for kw in keywords):
                issues.append(ValidationIssue(
                    level="info", category="content",
                    message=f"建议增加：{clause_name}",
                    suggestion=f"添加{clause_name}可以更好地保护双方权益",
                ))

        coverage = len(covered_clauses) / max(len(cls.REQUIRED_CONTRACT_CLAUSES), 1)
        stats["required_coverage"] = round(coverage, 2)
        stats["covered_clauses"] = covered_clauses
        stats["missing_clauses"] = missing_clauses

        # === 5. 法条引用检查 ===
        citation_pattern = r'《[^》]+》第\d+条'
        citations = re.findall(citation_pattern, text)
        stats["citation_count"] = len(citations)

        if len(citations) == 0 and word_count > 1000:
            issues.append(ValidationIssue(
                level="info", category="citation",
                message="合同中未引用具体法律条文",
                suggestion="在关键条款处引用法律依据可增强合同的法律效力说服力",
            ))

        # === 6. 格式检查 ===
        # 检查空白占位符
        placeholder_count = len(re.findall(r'【[^】]*】|______', text))
        stats["placeholder_count"] = placeholder_count

        # 检查金额格式（应有大写）
        has_amount = bool(re.search(r'[人民币RMB￥¥]\s*[\d,]+', text))
        has_chinese_amount = bool(re.search(r'[壹贰叁肆伍陆柒捌玖拾佰仟万亿]', text))
        if has_amount and not has_chinese_amount:
            issues.append(ValidationIssue(
                level="info", category="format",
                message="合同金额缺少大写中文",
                suggestion="正式合同中金额应同时标注阿拉伯数字和大写中文",
            ))

        # === 7. 计算总分 ===
        critical_count = sum(1 for i in issues if i.level == "critical")
        warning_count = sum(1 for i in issues if i.level == "warning")

        score = 1.0
        score -= critical_count * 0.15
        score -= warning_count * 0.05
        score = max(0.0, min(1.0, score))

        passed = critical_count == 0 and score >= 0.6

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues,
            stats=stats,
        )

    @classmethod
    def validate_lawsuit(cls, text: str) -> ValidationResult:
        """验证诉讼文书质量"""
        issues: List[ValidationIssue] = []
        stats: Dict[str, Any] = {"word_count": len(text.replace(" ", ""))}

        # 原告/被告信息
        if not re.search(r'原告', text):
            issues.append(ValidationIssue("critical", "structure", "缺少原告信息"))
        if not re.search(r'被告', text):
            issues.append(ValidationIssue("critical", "structure", "缺少被告信息"))

        # 诉讼请求
        if not re.search(r'诉讼请求|请求.*法院', text):
            issues.append(ValidationIssue("critical", "structure", "缺少诉讼请求"))

        # 事实与理由
        if not re.search(r'事实.*理由|事实与理由', text):
            issues.append(ValidationIssue("warning", "structure", "缺少事实与理由部分"))

        # 此致xx法院
        if not re.search(r'此致|人民法院', text):
            issues.append(ValidationIssue("warning", "structure", "缺少结尾格式（此致XX人民法院）"))

        critical_count = sum(1 for i in issues if i.level == "critical")
        score = max(0.0, 1.0 - critical_count * 0.2 - sum(1 for i in issues if i.level == "warning") * 0.05)

        return ValidationResult(passed=critical_count == 0, score=score, issues=issues, stats=stats)
