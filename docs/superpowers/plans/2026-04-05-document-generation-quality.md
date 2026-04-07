# Document Generation Quality Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将智能对话中的法律文书生成从极简文本升级为可继续交付使用的专业草案，支持成稿/高可用草案/结构化草稿三态输出，并统一聊天链路与独立文档生成链路的质量标准。

**Architecture:** 先在 `DocumentValidator` 中收紧并分类化质量闸门，再在 `DocumentDraftAgent` 中加入文书类型归一化、信息完整度评估、三态输出与定向补写逻辑。最后抽出共享的文书生成服务，让 `/documents/generate` 与聊天中的 `document_drafter` 复用同一条高质量流水线。

**Tech Stack:** Python 3.11、FastAPI、Pydantic、SQLAlchemy Async、pytest、pytest-asyncio、unittest.mock

---

## 文件结构

- Create: `backend/tests/test_document_validator_quality.py`
  - 覆盖合同、律师函、法律意见书的质量闸门
- Create: `backend/tests/test_document_drafter_quality.py`
  - 覆盖三态输出、Prompt 组装、定向补写
- Create: `backend/tests/test_document_generation_api.py`
  - 覆盖 `/api/v1/documents/generate` 复用共享流水线
- Create: `backend/src/services/document_generation_service.py`
  - 统一文书生成入口，供聊天链路与独立文档接口共用
- Modify: `backend/src/services/document_validator.py`
  - 从简单字数/结构检查扩展为分类型质量校验
- Modify: `backend/src/agents/document_drafter.py`
  - 引入完整度评估、生成模式决策、补写闭环
- Modify: `backend/src/prompts/agents/document_drafter.txt`
  - 从静态规范说明升级为任务驱动的系统提示
- Modify: `backend/src/api/routes/documents.py`
  - 独立文档生成接口改为复用共享文书生成服务

> 说明：按当前用户要求，本计划不包含 git commit 步骤。

---

### Task 1: 收紧并分类化文书质量闸门

**Files:**
- Create: `backend/tests/test_document_validator_quality.py`
- Modify: `backend/src/services/document_validator.py`

- [ ] **Step 1: 先写失败的质量测试**

创建 `backend/tests/test_document_validator_quality.py`，先用三个最能暴露“极简但被放行”的场景把当前行为卡住。

```python
import pytest

from src.services.document_validator import DocumentValidator


def test_contract_short_text_fails_quality_gate():
    text = """# 服务合同

甲方：甲公司
乙方：乙公司

## 第一条 合同标的
乙方向甲方提供服务。

## 第二条 价款
服务费为人民币10000元。
"""

    result = DocumentValidator.validate_contract(text, "服务合同")

    assert result.passed is False
    assert result.score < 0.6
    assert any(issue.level == "critical" for issue in result.issues)
    assert any("条款数量不足" in issue.message or "合同内容过短" in issue.message for issue in result.issues)


def test_lawyer_letter_without_deadline_fails():
    text = """# 律师函

致：某供应商

一、基本事实
贵方存在迟延付款情形。

二、法律分析
贵方行为已构成违约。

三、律师意见
请及时履行付款义务。
"""

    result = DocumentValidator.validate_document(text, "律师函")

    assert result.passed is False
    assert any("履行要求" in issue.message or "期限" in issue.message for issue in result.issues)


def test_legal_opinion_without_conclusion_fails():
    text = """# 法律意见书

致：某公司

## 一、引言
受贵司委托，就本次交易出具法律意见。

## 二、事实概述
交易双方已签署框架协议。

## 三、法律分析
本次交易涉及公司法与民法典相关规则。
"""

    result = DocumentValidator.validate_document(text, "法律意见书")

    assert result.passed is False
    assert any("结论" in issue.message or "法律意见" in issue.message for issue in result.issues)
```

- [ ] **Step 2: 运行定向测试，确认当前实现先失败**

Run:

```bash
cd backend && pytest tests/test_document_validator_quality.py -q
```

Expected:

```text
FAILED tests/test_document_validator_quality.py::test_lawyer_letter_without_deadline_fails
AttributeError: type object 'DocumentValidator' has no attribute 'validate_document'
```

- [ ] **Step 3: 在 `DocumentValidator` 中加入统一分发与分类规则**

在 `backend/src/services/document_validator.py` 中新增统一入口、文书类型归一化和律师函/法律意见书专项检查。先保留现有 `validate_contract` 与 `validate_lawsuit`，再叠加新的调度层，避免影响已有调用方。

```python
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
def validate_lawyer_letter(cls, text: str) -> ValidationResult:
    issues = []
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
    return cls._finalize_result(issues, {"word_count": len(text.replace(" ", ""))})
```

- [ ] **Step 4: 收紧合同闸门，避免“短而空”的合同通过**

把 `validate_contract()` 的低门槛提升到能反映真实可交付性。

```python
if word_count < 1200:
    issues.append(ValidationIssue(
        level="critical",
        category="content",
        message=f"合同内容过短（{word_count}字），不足以构成可交付草案",
        suggestion="补充完整的权利义务、履行、违约责任、争议解决、签署区等条款",
    ))
elif word_count < 2500:
    issues.append(ValidationIssue(
        level="warning",
        category="content",
        message=f"合同内容仍偏短（{word_count}字），建议继续充实具体条件与责任",
        suggestion="增加付款节点、验收标准、违约计算方式、通知送达等细节",
    ))

if clause_count < 8:
    issues.append(ValidationIssue(
        level="critical",
        category="structure",
        message=f"条款数量不足（仅{clause_count}条），不足以构成专业合同草案",
        suggestion="至少补齐标的、价款、履行期限、验收、违约责任、争议解决、通知送达、附则等章节",
    ))
```

- [ ] **Step 5: 为通用收尾逻辑新增 `_finalize_result()`**

避免律师函、法律意见书、诉状等不同校验函数重复写打分逻辑。

```python
@classmethod
def _finalize_result(cls, issues: list[ValidationIssue], stats: dict[str, Any]) -> ValidationResult:
    critical_count = sum(1 for item in issues if item.level == "critical")
    warning_count = sum(1 for item in issues if item.level == "warning")

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
```

- [ ] **Step 6: 运行测试，确认质量闸门生效**

Run:

```bash
cd backend && pytest tests/test_document_validator_quality.py -q
```

Expected:

```text
3 passed
```

---

### Task 2: 为文书起草 Agent 加入三态输出与定向补写

**Files:**
- Create: `backend/tests/test_document_drafter_quality.py`
- Modify: `backend/src/agents/document_drafter.py`
- Modify: `backend/src/prompts/agents/document_drafter.txt`

- [ ] **Step 1: 先写失败的 Agent 行为测试**

创建 `backend/tests/test_document_drafter_quality.py`，先定义两个关键行为：信息不完整时进入“高可用草案”，质量不达标时触发定向补写。

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.document_drafter import DocumentDraftAgent


def _make_llm_config_mock():
    return MagicMock(
        provider="openai",
        model_name="gpt-4o",
        temperature=0.7,
        max_tokens=4096,
        api_key="test-key",
        api_base_url=None,
        source="env",
    )


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_uses_high_usability_draft_mode_when_key_info_missing(mock_model_factory, mock_llm_config):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    with patch.object(agent, "chat", new_callable=AsyncMock, return_value="# 服务合同\n\n## 第一条 合同标的\n..."):
        task = {
            "description": "起草一份服务合同",
            "context": {
                "doc_type": "服务合同",
                "scenario": "甲方委托乙方提供年度运维服务",
                "requirements": {
                    "client": "甲公司",
                    "target": "乙公司",
                    "details": "未提供金额和付款节点",
                },
            },
        }

        result = await agent.process(task)

    assert "待确认事项" in result.content or "起草说明" in result.content
    assert "高可用草案" in result.reasoning


@pytest.mark.asyncio
@patch("src.agents.base.get_llm_config_sync")
@patch("src.agents.base.ModelFactory.create")
async def test_process_retries_with_targeted_repair_when_validation_fails(mock_model_factory, mock_llm_config):
    mock_llm_config.return_value = _make_llm_config_mock()
    mock_model_factory.return_value = MagicMock()
    agent = DocumentDraftAgent()

    first_output = "# 服务合同\n\n甲方：甲公司\n乙方：乙公司"
    repaired_output = "# 服务合同\n\n## 第一条 定义与解释\n1.1 ..."

    with patch.object(agent, "chat", new_callable=AsyncMock, side_effect=[first_output, repaired_output]) as mock_chat:
        result = await agent.process(
            {"description": "起草一份服务合同", "context": {"doc_type": "服务合同", "requirements": {"client": "甲公司", "target": "乙公司"}}}
        )

    assert result.content == repaired_output
    assert mock_chat.await_count == 2
```

- [ ] **Step 2: 运行定向测试，确认当前实现不满足**

Run:

```bash
cd backend && pytest tests/test_document_drafter_quality.py -q
```

Expected:

```text
FAILED tests/test_document_drafter_quality.py::test_process_uses_high_usability_draft_mode_when_key_info_missing
AssertionError: assert '高可用草案' in result.reasoning
```

- [ ] **Step 3: 在 `DocumentDraftAgent` 中加入完整度评估与模式决策**

新增轻量级规划对象和完整度评分，让 `process()` 先做判断再组 Prompt。

```python
from dataclasses import dataclass


@dataclass
class DraftPlan:
    normalized_doc_type: str
    draft_mode: str
    missing_fields: list[str]
    completeness_score: float


def _assess_draft_plan(
    self,
    doc_type: str,
    description: str,
    requirements: Dict[str, Any],
    scenario: str,
) -> DraftPlan:
    normalized = self._normalize_doc_type(doc_type)
    facts = {
        "parties": any(key in requirements for key in ["client", "target", "plaintiff", "defendant"]),
        "amount": "amount" in requirements,
        "details": bool(requirements.get("details") or scenario or description),
        "timeline": any(token in f"{scenario} {description}" for token in ["期限", "日期", "时间", "交付", "付款"]),
    }
    missing = [name for name, present in facts.items() if not present]
    score = round(sum(1 for present in facts.values() if present) / len(facts), 2)
    if score >= 0.85:
        mode = "成稿"
    elif score >= 0.45:
        mode = "高可用草案"
    else:
        mode = "结构化草稿"
    return DraftPlan(normalized, mode, missing, score)
```

- [ ] **Step 4: 用任务驱动 Prompt 替换当前“一次性长指令”**

把 `process()` 的 Prompt 拼装改成明确的任务单，并在正文后固定追加附加区块。

```python
prompt = f"""请根据以下任务单起草法律文书。

【文书类型】{doc_type}
【输出模式】{draft_plan.draft_mode}
【场景背景】{scenario or description}
【已知信息】
{self._format_requirements(requirements)}
【缺失信息】
{self._format_missing_fields(draft_plan.missing_fields)}
【结构要求】
{structure_guide}
{rag_context}

【输出要求】
1. 输出完整 Markdown 文书正文，不得只写原则性说明
2. 信息完整时按成稿标准写满关键条款
3. 信息不完整时保留专业占位，不得写“请按实际情况补充”
4. 文末必须包含：
---
## 起草说明
## 待确认事项
## 使用提示
"""
```

- [ ] **Step 5: 将“泛化补充”改成“定向补写”**

把验证失败后的二次调用改成根据缺失问题生成修复任务，而不是只说“请补充修正”。

```python
def _build_repair_prompt(self, original_output: str, issues: list[str], draft_plan: DraftPlan, structure_guide: str) -> str:
    joined_issues = "\n".join(f"- {item}" for item in issues)
    return f"""你刚才生成的法律文书未达到可交付标准，请基于下列问题重新输出完整文书：

【当前输出模式】{draft_plan.draft_mode}
【必须修复的问题】
{joined_issues}

【保留要求】
1. 保留原文中已正确的当事方和场景事实
2. 补齐缺失的核心条款、结构和结尾部分
3. 仍然输出完整正文，不要输出修订说明

【结构要求】
{structure_guide}

【原始文书】
{original_output}
"""
```

- [ ] **Step 6: 更新系统 Prompt，使其与三态输出一致**

把 `backend/src/prompts/agents/document_drafter.txt` 中“只强调专业”改成“强调模式感知 + 不得伪装定稿”。新增以下关键段落并保留现有文书结构模板。

```text
## 起草策略

1. 先判断当前任务属于“成稿”“高可用草案”还是“结构化草稿”
2. 成稿：直接输出可交付律师或业务方继续审阅的完整文书
3. 高可用草案：输出完整正文，并在必要位置保留专业占位
4. 结构化草稿：输出完整结构、核心条款方向和待确认事项，不得用空泛套话冒充定稿

## 严格禁止

- 只输出极简提纲或几条原则性建议
- 使用“请根据实际情况补充”代替正文
- 在缺少关键信息时伪装成已经完全定稿
```

- [ ] **Step 7: 运行 Agent 测试，确认三态输出与补写闭环通过**

Run:

```bash
cd backend && pytest tests/test_document_drafter_quality.py -q
```

Expected:

```text
2 passed
```

---

### Task 3: 抽出共享文书生成服务并接入独立文档生成接口

**Files:**
- Create: `backend/src/services/document_generation_service.py`
- Create: `backend/tests/test_document_generation_api.py`
- Modify: `backend/src/api/routes/documents.py`

- [ ] **Step 1: 先写失败的接口回归测试**

创建 `backend/tests/test_document_generation_api.py`，验证 `/api/v1/documents/generate` 不再自行拼 Prompt，而是走共享服务并保存生成结果。

```python
from unittest.mock import AsyncMock

import pytest

from .conftest import create_auth_headers


@pytest.mark.asyncio
async def test_generate_document_uses_shared_generation_service(client, test_user, monkeypatch):
    generated = {
        "content": "# 服务合同\n\n## 第一条 定义与解释\n1.1 ...\n\n---\n## 起草说明\n...",
        "draft_mode": "高可用草案",
        "validation_score": 0.86,
    }

    service = AsyncMock()
    service.generate.return_value = generated
    monkeypatch.setattr("src.api.routes.documents.DocumentGenerationService", lambda db: service)

    response = await client.post(
        "/api/v1/documents/generate",
        headers=create_auth_headers(test_user),
        json={
            "doc_type": "服务合同",
            "scenario": "甲方委托乙方提供驻场运维服务",
            "requirements": {
                "client": "甲公司",
                "target": "乙公司",
                "details": "需要约定驻场服务、响应时效、付款节点",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 200
    assert payload["data"]["name"].endswith(".md")
    assert service.generate.await_count == 1
```

- [ ] **Step 2: 运行定向测试，确认当前接口还未接入共享服务**

Run:

```bash
cd backend && pytest tests/test_document_generation_api.py -q
```

Expected:

```text
FAILED tests/test_document_generation_api.py::test_generate_document_uses_shared_generation_service
AttributeError: module 'src.api.routes.documents' has no attribute 'DocumentGenerationService'
```

- [ ] **Step 3: 新建共享文书生成服务**

创建 `backend/src/services/document_generation_service.py`，把“组织任务 -> 调用 `DocumentDraftAgent.process()` -> 返回正文与元信息”聚到一处。

```python
from typing import Any

from src.agents.document_drafter import DocumentDraftAgent
from src.services.document_validator import DocumentValidator


class DocumentGenerationService:
    def __init__(self, db):
        self.db = db
        self.agent = DocumentDraftAgent()

    async def generate(
        self,
        *,
        doc_type: str,
        scenario: str,
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        task = {
            "description": scenario or f"起草一份{doc_type}",
            "context": {
                "doc_type": doc_type,
                "scenario": scenario,
                "requirements": requirements,
            },
        }
        response = await self.agent.process(task)
        validation = DocumentValidator.validate_document(response.content, doc_type)
        return {
            "content": response.content,
            "draft_mode": self._extract_draft_mode(response.reasoning),
            "validation_score": validation.score,
            "reasoning": response.reasoning,
        }
```

- [ ] **Step 4: 让 `/documents/generate` 复用共享服务**

修改 `backend/src/api/routes/documents.py`，删除手写 Prompt，直接调用 `DocumentGenerationService`。

```python
from src.services.document_generation_service import DocumentGenerationService


@router.post("/generate", response_model=UnifiedResponse)
async def generate_document(
    request: DocumentGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = DocumentGenerationService(db)
    generated = await service.generate(
        doc_type=request.doc_type,
        scenario=request.scenario,
        requirements=request.requirements or {},
    )

    document_service = DocumentService(db)
    doc_name = f"{request.doc_type}_{datetime.now().strftime('%Y%m%d%H%M')}.md"
    document = await document_service.create_text_document(
        name=doc_name,
        content=generated["content"],
        doc_type="contract" if "合同" in request.doc_type else "legal_opinion",
        org_id=user.org_id,
        case_id=request.case_id,
        created_by=user.id,
        description=f"AI自动生成（{generated['draft_mode']}）: {request.scenario[:50]}...",
        tags=["AI生成", request.doc_type, generated["draft_mode"]],
    )
```

- [ ] **Step 5: 运行接口测试，确认独立文档链路复用成功**

Run:

```bash
cd backend && pytest tests/test_document_generation_api.py -q
```

Expected:

```text
1 passed
```

---

### Task 4: 端到端回归文书质量基线

**Files:**
- Modify: `backend/tests/test_document_drafter_quality.py`
- Modify: `backend/tests/test_document_generation_api.py`
- Modify: `backend/tests/test_document_validator_quality.py`

- [ ] **Step 1: 给合同与律师函各补一个“信息不足但不能退化成极简文本”的回归断言**

在 `backend/tests/test_document_drafter_quality.py` 中补两个回归断言：结果必须包含正文结构和附加区块。

```python
assert "# 服务合同" in result.content
assert "## 第一条" in result.content or "## 一、" in result.content
assert "## 待确认事项" in result.content
assert "## 使用提示" in result.content
```

- [ ] **Step 2: 给接口测试补“文档已落库”的断言**

在 `backend/tests/test_document_generation_api.py` 中补充数据库侧结果校验，确保生成内容不是只返回给接口而未保存。

```python
assert "data" in payload
assert payload["data"]["extracted_text"].startswith("# 服务合同")
assert "高可用草案" in payload["data"]["description"]
```

- [ ] **Step 3: 运行后端定向回归集**

Run:

```bash
cd backend && pytest \
  tests/test_document_validator_quality.py \
  tests/test_document_drafter_quality.py \
  tests/test_document_generation_api.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 4: 运行已有聊天与文档接口回归，确认未误伤主流程**

Run:

```bash
cd backend && pytest \
  tests/test_chat.py \
  tests/test_document_authorization_api.py -q
```

Expected:

```text
passed
```

- [ ] **Step 5: 运行基础静态检查**

Run:

```bash
cd backend && ruff check src tests
```

Expected:

```text
All checks passed!
```

---

## 自检

- 规格覆盖：
  - 三态输出：Task 2
  - 分类质量闸门：Task 1
  - 定向补写：Task 2
  - 统一聊天与独立文档接口质量逻辑：Task 3
  - 回归验证：Task 4
- 占位符扫描：
  - 无 `TODO`、`TBD`、`implement later`
- 类型一致性：
  - `validate_document()`、`DocumentGenerationService.generate()`、`DraftPlan` 在各任务中名称一致
