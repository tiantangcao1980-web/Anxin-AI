# 发布门禁 — 单一真相源

> **状态**：本文是商业发布门禁的**单一权威来源**。
> **版本**：2026-05-14
> **历史来源**：合并自 `docs/release/commercial-delivery-readiness.md` + `docs/openspec/02-commercial-delivery-test-spec.md` + `docs/release/48-hour-commercial-delivery-plan.md`。原文归档到 [docs/archive/legacy-spine-sources/](archive/legacy-spine-sources/)。
> **更新规则**：证据状态变更时更新（预期商业冲刺期每天）。

---

## 目录

1. [发布判定标准（5 维度）](#1-发布判定标准5-维度)
2. [各 Lane 必跑测试与证据](#2-各-lane-必跑测试与证据)
3. [商业门禁命令集](#3-商业门禁命令集)
4. [证据清单与 Go/No-Go](#4-证据清单与-gono-go)
5. [已知阻断项跟踪](#5-已知阻断项跟踪)

---

## 1. 发布判定标准（5 维度）

商业候选版必须**5 维度全过**：

### 1.1 后端完成度

| 项 | 状态 |
|---|---|
| 61 v3 API endpoint 全通 | ✅ |
| pytest 543+ 用例 | ✅ |
| ruff + mypy 干净 | ✅ |
| alembic upgrade head | ⚠️ 双 head |
| OpenAPI 生成无错 | ✅ |

### 1.2 前端完成度

| 项 | 状态 |
|---|---|
| ESLint 全过 | ✅ |
| tsc 类型干净 | ✅ |
| vitest 全过 | ✅ |
| `npm run build` 成功 | ✅ |
| 图标体系一致性 100% | 🚧 47% |
| UI/UX P0 假成功修复 | 🚧 |

### 1.3 桌面完成度

| 项 | 状态 |
|---|---|
| cargo clippy 干净 | ✅ |
| cargo test 全过 | ✅ |
| unsigned runtime smoke | ✅ |
| **macOS 签名 + 公证** | 🚫 |
| **Windows 代码签名** | 🚫 |
| 同步引擎实装 | 🚧 |

### 1.4 移动 / 小程序完成度

| 项 | 状态 |
|---|---|
| RN typecheck + test | ✅ |
| Expo build smoke | ✅ |
| Taro 小程序 build | ✅ |
| **iOS 真机 transcript** | 🚫 |
| **Android 真机 transcript** | 🚫 |
| 微信小程序审核预提交 | 🚧 |

### 1.5 外部资源与证据

| 项 | 状态 |
|---|---|
| trufflehog secret scan | ✅ |
| npm audit prod | ✅ |
| Bandit | ✅ |
| AI Review 4 reviewer | ✅ |
| Eval baseline 25 case | ✅ |
| **RAG full50 baseline** | 🚧 |
| **支付沙箱 preflight + live** | ⏬ 降 P3 (商业化阶段, 2026-05-14) |
| **电签沙箱 preflight + live** | ⏬ 降 P3 (商业化阶段) |
| **政务签章 GDCA / 粤企签 placeholder** | ✅ (代码就位, 商务待启动) |
| Agent governance smoke | ✅ |

---

## 2. 各 Lane 必跑测试与证据

### 2.1 Lane 1 — 政务签章 / 商业化支付电签 (2026-05-14 调整)

**产品策略**: 核心功能 PMF 验证优先, 签约场景接入政务平台 (GDCA / 粤企签), 商业化支付电签降为 PMF 后阶段。

```bash
# 后端回归 — 签章 / 支付 services 单元测试 (Mock provider 默认)
cd backend && uv run --no-sync pytest tests/test_payment* tests/test_esign*

# Preflight (不需要真凭证, 验证 mock + 配置合法性)
python3 scripts/payment/preflight.py
python3 scripts/esign/preflight.py

# 政务签章接入 (待业务方启动 — 见 docs/integrations/guangdong-gov-signature.md)
ESIGN_PROVIDER=gdca       # 广东 GDCA 政务签
# 或
ESIGN_PROVIDER=yueqishang  # 粤企签 / 粤商通

# 商业化 Live 采集 (PMF 后启动, 当前不阻断)
python3 scripts/payment/live_smoke.py --provider {wechat|alipay|stripe}
python3 scripts/esign/live_smoke.py --provider {esign|fadada}
```

证据落点: `docs/release/evidence/artifacts/payment-sandbox-preflight-*.json` 等。
政务签章接入计划: [docs/integrations/guangdong-gov-signature.md](integrations/guangdong-gov-signature.md)

### 2.2 Lane 2 — 桌面

```bash
# 静态门禁
cd desktop && cargo clippy --all-targets -- -D warnings
cd desktop && cargo test

# Runtime smoke（unsigned）
bash scripts/desktop/runtime-smoke.sh --unsigned

# 签名 / 公证（需要凭证，阻断）
bash scripts/desktop/sign-macos.sh
bash scripts/desktop/sign-windows.sh
```

证据落点：`docs/release/evidence/artifacts/desktop-*.json`。

### 2.3 Lane 3 — RAG / 案件 / 律师市场

```bash
# 单元 + 集成
cd backend && uv run --no-sync pytest tests/test_rag* tests/test_case_* tests/test_lawyer_market*

# RAG full50 baseline
cd backend && uv run --no-sync pytest evals/rag_full50.py

# Eval baseline 5 法务 persona（P9 后）
cd backend && uv run --no-sync pytest evals/legal/
```

证据落点：`docs/release/evidence/artifacts/rag-full50-*.json`。

### 2.4 Lane 4 — 移动 / 小程序

```bash
# Mobile (Expo)
cd mobile && npm run typecheck && npm run test
cd mobile && npm run build -- --platform=ios
cd mobile && npm run build -- --platform=android

# Mini-program (Taro)
cd mini-program && npm run build:weapp

# UniApp
cd apps/uni-mobile && npm run build:h5
```

证据落点：`docs/release/evidence/artifacts/mobile-*.json`, `uni-mobile-*.json`, `mini-*.json`。

### 2.5 Lane 5 — 发布门禁

```bash
bash scripts/commercial-readiness-gate.sh --quick
bash scripts/commercial-readiness-gate.sh --with-local-tests
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown
node scripts/validate-commercial-delivery-checklist.cjs
node scripts/validate-commercial-delivery-lanes.cjs
bash scripts/release-evidence-secret-scan.sh
```

### 2.6 Lane 6 — UI/UX

```bash
# 前端
cd frontend && npm run lint
cd frontend && npm run build  # 含 tsc
cd frontend && npm run test

# 图标体系一致性（待 lint 规则实装）
grep -r "from 'lucide-react'" frontend/src/  # 应为空

# 视觉回归（preview tools，本地）
# preview_screenshot 关键页面
```

---

## 3. 商业门禁命令集

### 3.1 全门禁（Go/No-Go 前必跑）

```bash
# 1. 工作树清点
python3 scripts/release-worktree-inventory.py --json --fail-on-unknown

# 2. 密钥扫描
bash scripts/release-evidence-secret-scan.sh

# 3. 发布清单 + Lane 配置
node scripts/validate-commercial-delivery-checklist.cjs
node scripts/validate-commercial-delivery-lanes.cjs

# 4. 后端全回归
cd backend && uv run --no-sync pytest --maxfail=10

# 5. 前端验证
cd frontend && npm run lint && npm run build && npm run test

# 6. 桌面验证
cd desktop && cargo clippy --all-targets -- -D warnings && cargo test

# 7. 移动验证
cd mobile && npm run typecheck && npm run test

# 8. Eval baseline
cd backend && uv run --no-sync pytest evals/

# 9. 商业候选版门禁
bash scripts/commercial-readiness-gate.sh --quick
```

### 3.2 商业候选版门禁（with-local-tests）

```bash
bash scripts/commercial-readiness-gate.sh --with-local-tests
```

包括但不限于：
- 上述 9 项
- RAG full50 baseline 完整跑通
- 桌面 unsigned runtime smoke
- 移动 build smoke
- 小程序 build smoke
- 支付 / 电签 preflight

### 3.3 快速门禁（Quick — 日常）

```bash
bash scripts/commercial-readiness-gate.sh --quick
```

包括：1-3 项（worktree / secret scan / checklist） + 后端简化测试。

---

## 4. 证据清单与 Go/No-Go

### 4.1 证据清单（必出）

| 证据项 | 路径 | 状态 |
|---|---|---|
| `worktree-inventory-clean` | `release-worktree-inventory.py` output | ✅ |
| `secret-scan-pass` | `release-evidence-secret-scan.sh` output | ✅ |
| `backend-pytest-full` | pytest output | ✅ |
| `frontend-build-clean` | `npm run build` output | ✅ |
| `desktop-clippy-clean` | `desktop-clippy-gate-*.json` | ✅ |
| `desktop-unsigned-smoke` | `desktop-runtime-code-smoke-*.json` | ✅ |
| `desktop-signed-package` | (未生成 — 阻断) | 🚫 |
| `desktop-notarization` | (未生成 — 阻断) | 🚫 |
| `mobile-ios-real-device` | (未生成 — 阻断) | 🚫 |
| `mobile-android-real-device` | (未生成 — 阻断) | 🚫 |
| `mini-program-build` | `mobile-mini-code-smoke-*.json` | ✅ |
| `payment-sandbox-preflight` | `payment-sandbox-preflight-*.json` | ✅ |
| `payment-live` | (未生成 — 阻断) | 🚫 |
| `esign-sandbox-preflight` | `esign-sandbox-preflight-*.json` | ✅ |
| `esign-live` | (未生成 — 阻断) | 🚫 |
| `rag-full50-baseline` | `rag-full50-built-in-*.json` | 🚧 |
| `eval-baseline-25-case` | `evals/baseline/` | ✅ |
| `agent-governance-smoke` | `agent-governance-code-smoke-*.json` | ✅ |
| `cross-device-continuation` | `cross-device-continuation-code-smoke-*.json` | ✅ |

详见 [docs/release/commercial-delivery-checklist.json](release/commercial-delivery-checklist.json)。

### 4.2 Go/No-Go 判定

#### Go 条件（必须全部满足）

- [ ] 5 维度全 ✅
- [ ] 上表 18 项证据全部生成（含 8 项当前阻断的）
- [ ] `commercial-readiness-gate.sh --with-local-tests` 全过
- [ ] 无 P0 / P1 阻断
- [ ] 风险登记册无未缓解高风险项

#### No-Go 条件（任一即触发）

- 🚫 任一阻断项未解除
- 🚫 任一证据缺失
- 🚫 Eval baseline 下降 ≥ 5%
- 🚫 RAG full50 准确率不达阈值
- 🚫 真机 transcript 缺
- 🚫 桌面包未签名

### 4.3 当前判定（2026-05-14）

```
状态：🚫 No-Go

原因：
- 桌面签名 / 公证 缺（阻断）
- 支付 / 电签 live 证据 缺（阻断）
- 真机 transcript 缺（阻断）
- 图标体系一致性 47%（P0 task in progress）
```

---

## 5. 已知阻断项跟踪

| 阻断 | 影响 Lane | 何时解除 | 当前状态 |
|---|---|---|---|
| Apple Developer 账号 | Lane 2 | 行政申请通过 | 🚧 跟踪中 |
| Windows 代码签名证书 | Lane 2 | 证书购置 | 🚧 跟踪中 |
| GDCA 政务签 测试凭据 | Lane 1 (政务版) | GDCA 商务对接 (NDA + 商务合同) | 🟡 待业务方启动 |
| 粤企签 / 粤商通 开发者权限 | Lane 1 (政务版) | 数字广东审批 (企业实名 + 法人认证) | 🟡 待业务方启动 |
| 支付沙箱凭证（微信 / 支付宝 / Stripe） | Lane 1 (商业化) | 渠道方审批 — ⏬ 2026-05-14 降级, PMF 后启动 | ⏸ 暂停跟踪 |
| 电签沙箱凭证（e签宝 / 法大大） | Lane 1 (商业化) | 渠道方审批 — ⏬ 2026-05-14 降级, PMF 后启动 | ⏸ 暂停跟踪 |
| 真机预约（iOS / Android） | Lane 4 | 行政预约 | 🚧 跟踪中 |
| RAG corpus 准备 | Lane 3 | 内部数据准备 | 🚧 内部 |
| Alembic 三 head 合并 | 全 Lane（数据库） | T2 完成后 | 🚧 计划中 |

详见 [docs/release/external-resource-handoff.md](release/external-resource-handoff.md) + [docs/release/external-inputs-checklist.md](release/external-inputs-checklist.md)。

---

## 附录 · 归档与原文

- **原 docs/release/commercial-delivery-readiness.md（193 行）**：[docs/archive/legacy-spine-sources/release/](archive/legacy-spine-sources/release/)
- **原 docs/openspec/02-commercial-delivery-test-spec.md（312 行）**：[docs/archive/legacy-spine-sources/openspec/](archive/legacy-spine-sources/openspec/)
- **原 docs/release/48-hour-commercial-delivery-plan.md（99 行）**：[docs/archive/legacy-spine-sources/release/](archive/legacy-spine-sources/release/)
- **完整发布清单**：[docs/release/commercial-delivery-checklist.json](release/commercial-delivery-checklist.json)
- **并行 Lane 配置**：[docs/release/commercial-delivery-lanes.json](release/commercial-delivery-lanes.json)
- **回滚 Runbook**：[docs/release/rollback-runbook.md](release/rollback-runbook.md)
- **证据采集 Runbook**：[docs/release/evidence-collection-runbook.md](release/evidence-collection-runbook.md)

---

> **维护提示**：证据状态变化（任一 🚫 → ✅）必须更新本文 + 同步 [docs/wiki/03-current-state.md](wiki/03-current-state.md)。
