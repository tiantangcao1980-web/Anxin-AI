---
name: 常见陷阱
description: 提交前必查的"不要这样做"清单
audience: AI agents · 提交前必读
last_updated: 2026-05-14
---

# 07 · 常见陷阱

> 提交前最后扫一眼。这些坑都是真实踩过的。

---

## 🚫 品牌 / 命名

| 陷阱 | 正确做法 |
|---|---|
| 新代码用"安心法务" / "Anxin Smart Legal Services" | 用"安心智能助手 / Anxin AI"；"安心法务"仅在 v1/v2 历史叙事中合法 |
| 引用 `anxinfawu.com` 作目标域名 | 用 `anxinai.com`（目标）；`anxinfawu.com` 仅在 nginx.conf 部署项 + ADR 历史 |
| 新建 Python 模块文件名带 `-` | Python 用 `snake_case`；只有 `.md` / 目录用 kebab-case |

---

## 🚫 依赖 / 导入

| 陷阱 | 正确做法 |
|---|---|
| `import camel` / `from camel_ai import X` | CAMEL-AI 已剥离；用 `backend/src/harness/` 自研模块 |
| `from camel import CamelModel` | 用 `from src.core.schemas import APIModel`（`CamelModel` 是向后兼容别名） |
| 前端 `import { X } from 'lucide-react'` | 统一 `import { icons } from '@/lib/icons'` + `<icons.X />` (T1 已 100% 收口, ESLint `no-restricted-imports` 防回归; 仅 `src/components/ui/**` shadcn 原文件可直接 import) |
| `from src.harness.output_validator import output_validator` | 用 `from src.harness.enforcement import run_validation`（H1 入口） |

---

## 🚫 数据库 / 迁移

| 陷阱 | 正确做法 |
|---|---|
| 加新 alembic migration 不接当前 head | ✅ 当前是单一 head `047_user_token_usage` (Phase A T5-prep + T5 主体已合并 028/030/044 多 head). 新 migration `down_revision='047_user_token_usage'` 即可 |
| 用 SQLAlchemy 1.x 同步 API（`session.query`） | 用 2.0 async：`async with` + `select() + await session.execute()` |
| 跨租户查询不带 `tenant_id` 过滤 | 必查多租户隔离，见 `docs/standards/database-standard.md` §多租户 |
| 直接写 raw SQL 字符串 | 用参数化查询；SQLi 风险见 `docs/standards/security-standard.md` |

---

## 🚫 API 设计

| 陷阱 | 正确做法 |
|---|---|
| 新加 `/api/...` 路由（不带版本） | 用 `/api/v3/...`；V3 已冻结路由结构 |
| 直接修改 `ChatResponse` schema | H1 已扩展 `harness: dict \| None`；前端依赖此字段，改之前看 [chat.py](../../backend/src/api/routes/chat.py) |
| 不验证 tool call 权限 | 必经 `_check_mcp_tool_policy`（在 `backend/src/agents/base.py`）；P0 待统一到 `harness/policy_engine.py` |
| 同步阻塞调用 LLM | 用 Celery 异步：`POST /agent_tasks/submit` + 轮询/SSE |

---

## 🚫 测试 / 验证

| 陷阱 | 正确做法 |
|---|---|
| `python -c "..."` 直接跑（没 PATH） | 用 `cd backend && uv run --no-sync python -c "..."` |
| 跑全量 `pytest`（10+ 分钟） | 改 H1 相关只跑 `tests/test_chat.py tests/test_harness*.py`（2 秒，89 用例） |
| Mock 数据库 | 测试用真 PG 或 SQLite；mock 容易掩盖迁移 bug |
| 改 Agent 行为不更新 eval baseline | 必跑 `backend/evals/` 25 case；下降 ≥ 5% 阻断 PR |
| 前端改 UI 不跑视觉回归 | 见 `docs/audit/ui-ux-audit-2026-05-08.md`；用 preview_screenshot 验证 |

---

## 🚫 Git / 工作流

| 陷阱 | 正确做法 |
|---|---|
| `git push --force` 到 main / 共享分支 | **从来不要**；要回滚改用 `git revert` |
| `git commit --no-verify` | 不要绕过 hooks；hook 失败说明有问题，先修 |
| `git rebase -i` / `git add -i` | 这些是交互式，CLI 环境不支持 |
| 合并不写 commit type | 用 conventional commits：`feat / fix / chore / docs / refactor / test` |
| Commit 描述用英文 | type 英文 + 描述中文：`feat(harness): 引入六层框架基线` |
| 一个 commit 跨 5+ 文件且 5 个不同主题 | 拆 commit；每个 commit 单一主题 |

---

## 🚫 安全 / 隐私

| 陷阱 | 正确做法 |
|---|---|
| 把 token / API key 提交到 git | 走 `.env` + KMS 加密；commit 前 `bash scripts/release-evidence-secret-scan.sh` |
| 桌面本地数据不加密 | SQLCipher 必经；OS Keyring 存密钥 |
| 跨设备同步带 PII 不脱敏 | 必经 `privacy_context` 8 类 scrub |
| 接受 user input 不校验直接喂 LLM | Prompt Injection 风险；用 `output_validator` |
| 工具调用结果不审计 | trace_sink 必落盘 |

---

## 🚫 文档 / 沟通

| 陷阱 | 正确做法 |
|---|---|
| 把决策记录写在 commit message 里就完事 | 重要架构决策追加到 [06-decision-log.md](06-decision-log.md) |
| 改 README.md 不改 AGENTS.md / Wiki | 三层文档要同步：README（人门面）+ AGENTS（Agent 行为）+ Wiki（AI 入口） |
| 在多个 .md 复制粘贴同一段内容 | 用引用链接 `[详见 Spine §X](path)`，避免 sync 漂移 |
| 写文档不写 frontmatter | Wiki 文件需 `name / description / audience / last_updated` |

---

## 🚫 部署 / 发布

| 陷阱 | 正确做法 |
|---|---|
| 商业发布前不跑 gate | 必跑 `bash scripts/commercial-readiness-gate.sh --quick` |
| 桌面包不签名直接发 | macOS 需 Apple Developer + 公证；Windows 需代码签名证书 |
| RAG 上线不跑 full50 baseline | 必跑 `backend/evals/rag_full50.py`；准确率下降阻断发布 |
| 改 Agent 行为不跑 eval baseline | 25 case + 4 维度；下降 ≥ 5% PR 阻断 |

---

## 🚫 风格 / 噪音

| 陷阱 | 正确做法 |
|---|---|
| 没必要的 try/except 包一切 | 只在边界（用户输入 / 外部 API）；内部 trust framework |
| 写 docstring 解释 "What" | "What" 由函数名 + 类型签名说清；docstring 只写"Why"或非显然约束 |
| 加 emoji 到代码 | 用户没明确要求时不加 |
| 加 backwards-compat 兼容层（未发布的代码） | 直接改；只有 public API 才需兼容 |
| 提前做"未来可能需要"的抽象 | YAGNI；3 个相似实现再抽象 |

---

## ⚠️ 容易漏的检查项

提交前快速过：

```bash
# 1. 工作树干净？
git status

# 2. 无密钥泄漏？
bash scripts/release-evidence-secret-scan.sh

# 3. 无未知文件？
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown

# 4. 测试通过？
cd backend && uv run --no-sync pytest <相关测试>

# 5. 类型干净？
cd backend && uv run --no-sync mypy src/  # 若改了 backend
cd frontend && npm run build              # 若改了 frontend

# 6. AGENTS.md / Wiki 是否需要同步？
# 若改了：persona 行为 / 工具策略 / 架构布局 → 是

# 7. 决策是否需要记录？
# 若是"架构决策"或"破坏性变更" → 追加到 06-decision-log.md
```
