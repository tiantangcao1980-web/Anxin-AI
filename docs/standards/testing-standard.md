# 测试规范

> 强制规范。覆盖单元 / 集成 / E2E 三级测试。

## 1. 测试金字塔

```
        E2E (Playwright)       ← 慢 / 少 / 关键用户旅程
       ▲▲▲▲
      集成测试                  ← 中速 / 中量 / 端到端 API
     ▲▲▲▲▲▲▲▲▲▲
    单元测试                    ← 快 / 多 / 函数/组件级
   ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
```

| 层级 | 占比 | 速度 |
|---|---|---|
| 单元 | 70% | ms 级 |
| 集成 | 20% | 秒级 |
| E2E | 10% | 分钟级 |

## 2. 后端测试（pytest）

### 2.1 目录

```
backend/tests/
├── unit/                单元测试（service / agent / 工具函数）
├── integration/         集成测试（routes / DB）
├── e2e/                 端到端（@pytest.mark.live）
├── eval/                AI 质量评测
├── conftest.py          全局 fixture
└── factories/           对象工厂
```

### 2.2 命名

`test_<被测对象>_<场景>_<期望>.py`：

```python
# ✅ 正确
test_contract_service_create_with_duplicate_title_raises_exception
test_chat_route_send_without_auth_returns_401
test_rag_query_with_empty_kb_returns_empty_result

# ❌ 模糊
test_contract_1
test_works
test_create
```

### 2.3 结构（Arrange-Act-Assert）

```python
async def test_contract_service_create_returns_contract(db_session, user):
    # Arrange
    req = ContractCreateRequest(title="测试合同", party_a="甲", party_b="乙", content="...")

    # Act
    contract = await contract_service.create(req, user, db_session)

    # Assert
    assert contract.id is not None
    assert contract.title == "测试合同"
    assert contract.user_id == user.id
```

### 2.4 Fixture（conftest.py）

| Fixture | 用途 |
|---|---|
| `db_session` | 独立事务 DB session（每测试自动回滚） |
| `client` | httpx AsyncClient |
| `auth_headers` | 已登录用户 token |
| `admin_headers` | 管理员 token |
| `user_factory` | 用户工厂 |
| `contract_factory` | 合同工厂 |
| `mock_llm` | LLM mock |

### 2.5 Mock 与外部依赖

| 依赖 | Mock 方式 |
|---|---|
| LLM | `pytest-vcr` 录制真实响应 / fixture mock |
| 第三方 API | `respx` |
| Redis | `fakeredis` |
| 文件系统 | `tmp_path` |
| 时间 | `freezegun` |

**禁止**：测试中直连真实付费 API、网络爬虫、邮件发送等。

### 2.6 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_something(): ...
```

`pytest.ini` 已配置 `asyncio_mode = auto`，新测试默认 async。

### 2.7 标记

```python
@pytest.mark.live          # 需真实外部资源
@pytest.mark.slow          # 慢测试（>5s）
@pytest.mark.flaky         # 已知 flaky
@pytest.mark.security      # 安全相关
@pytest.mark.integration   # 集成
```

CI 默认跑：`pytest -m "not live and not slow"`

### 2.8 覆盖率目标

| 模块 | 覆盖率目标 |
|---|---|
| 核心业务（auth / payment / persona） | ≥ 80% |
| Service 层 | ≥ 70% |
| Route 层 | ≥ 60%（含集成） |
| Agent | 关键路径必有 |

```bash
cd backend
pytest --cov=src --cov-report=term --cov-fail-under=70
```

## 3. 前端测试

### 3.1 单元（Vitest）

#### 位置

就近：`<Component>.test.tsx` 或 `<util>.test.ts`

#### 工具

```ts
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('ChatBubble', () => {
  it('显示消息内容', () => {
    render(<ChatBubble message={{ role: 'user', content: '你好' }} />);
    expect(screen.getByText('你好')).toBeInTheDocument();
  });

  it('点击重试调用 onRetry', () => {
    const onRetry = vi.fn();
    render(<ChatBubble message={errorMsg} onRetry={onRetry} />);
    fireEvent.click(screen.getByRole('button', { name: /重试/ }));
    expect(onRetry).toHaveBeenCalled();
  });
});
```

#### 范围

- 组件渲染 + 交互
- 自定义 Hook
- 工具函数
- API 客户端层

### 3.2 E2E（Playwright）

#### 位置

`frontend/e2e/<feature>.spec.ts`

#### 命名

`<feature>-<scenario>.spec.ts`：

```
auth.spec.ts
contract-lifecycle.spec.ts
document-flows.spec.ts
role-access.spec.ts
business-actions.spec.ts
```

#### 示例

```ts
import { test, expect } from '@playwright/test';

test.describe('合同生命周期', () => {
  test('用户可创建并签署合同', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name=email]', 'test@example.com');
    await page.fill('[name=password]', 'password');
    await page.click('button[type=submit]');

    await page.goto('/contracts');
    await page.click('text=新建合同');
    await page.fill('[name=title]', '测试合同');
    // ...
    await expect(page.locator('.status')).toHaveText('已签署');
  });
});
```

#### 覆盖范围

V3 主用户旅程：

- 登录 / 注册
- 10 personas 入口与基础对话
- 合同创建 / 审查 / 签署
- 案件管理流程
- 找律师 / 案源市场
- 桌面同步
- 移动端关键路径

## 4. AI 质量评测

### 4.1 RAG 评测

`eval/` 目录：

```
eval/
├── rag_quality.py                综合评测
├── rag_live_qdrant_smoke.py      烟测
├── rag_live_qdrant_full50.py     50 条黄金集
├── legal_full50_corpus.jsonl     语料
└── golden.jsonl                  黄金标注
```

```bash
python eval/rag_live_qdrant_smoke.py
python eval/rag_live_qdrant_full50.py
```

### 4.2 指标

- Recall@k
- Citation accuracy
- Latency (P95)

### 4.3 改 RAG / Embedding / Reranker 必跑

每次改动必须跑 full50 对比 baseline，记录在 `docs/release/evidence/rag-full50-live-baseline.md`。

## 5. 性能测试

### 5.1 后端基线

`scripts/static-quality-baseline.sh` 输出：

- 单元测试 pass 数 / 时长
- Lint / mypy 0 警告
- Build 通过

### 5.2 桌面端

- `scripts/desktop-runtime-smoke.sh` runtime 烟测
- `scripts/desktop-sqlite-security-gate.sh` SQLCipher 门禁
- 性能基线：100 / 500 行同步 < 2s

### 5.3 移动端

- `scripts/mobile-device-smoke.sh` 代码级 smoke
- 真机：需 iOS / Android device + 手动 transcript

## 6. 安全测试

| 类型 | 工具 |
|---|---|
| 密钥扫描 | `scripts/release-evidence-secret-scan.sh` |
| 依赖 CVE | `pip-audit` / `npm audit` / `cargo audit` |
| 越权回归 | `backend/tests/test_*_authorization_guards.py` |
| Webhook 签名 | `backend/tests/test_official_webhook_security.py` |
| LLM 注入 | `backend/tests/test_prompt_injection_*.py` |

## 7. CI 必跑（每个 PR）

| 检查 | 工具 |
|---|---|
| Backend lint | `ruff check` |
| Backend type | `mypy` |
| Backend unit + integration | `pytest -m "not live and not slow"` |
| Frontend lint | `eslint --max-warnings 0` |
| Frontend type | `tsc --noEmit` |
| Frontend unit | `vitest run` |
| Frontend build | `vite build` |
| Frontend E2E（关键 spec） | `playwright test role-access business-actions` |
| Mobile typecheck | `tsc --noEmit` |
| Mobile unit | `vitest run` |
| Desktop check | `cargo clippy --all-targets` + `cargo test` |
| 安全扫描 | `release-evidence-secret-scan.sh` |

## 8. 发布前必跑

```bash
# 完整门禁
bash scripts/commercial-readiness-gate.sh --with-local-tests

# 桌面 release smoke
bash scripts/desktop-release-package.sh
bash scripts/desktop-release-preflight.sh

# 移动 device smoke
bash scripts/mobile-device-smoke.sh

# RAG full50
python eval/rag_live_qdrant_full50.py
```

## 9. 测试反模式

| ❌ 反模式 | ✅ 改进 |
|---|---|
| 一个 test 测多个无关功能 | 拆为多个独立 test |
| 强依赖测试顺序 | 每个 test 独立可运行 |
| 直接修改生产 fixture | 用 `factory_boy` / `pytest-factoryboy` |
| Mock 一切（包括被测对象） | 只 mock 外部边界 |
| 测试中 `time.sleep()` | 用事件等待或 mock 时间 |
| 不断 try/except 把错误吞掉测过 | assertRaises / pytest.raises |

## 10. 测试维护

- 测试失败优先修测试，不修被测代码（除非确认被测错）
- Flaky 测试加 `@pytest.mark.flaky` 标记，限时修复
- 测试运行慢于 5s 标 `@pytest.mark.slow`
- 删除测试需在 PR 说明理由
