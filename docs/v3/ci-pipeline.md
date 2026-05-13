# V3 CI Pipeline (P19-D)

> 5 端 GitHub Actions 流水线 + Nightly Smoke + Bundle Size Guard。
> Borrowed methodology: `harness-engineering` + `deployment-patterns` + `e2e-testing`.

## 设计原则

1. **谁改谁触发**：每端 workflow 用 `paths` 过滤，只在自己目录变更时跑（PR 不会因为后端改动而触发前端构建）。
2. **快速失败**：lint → typecheck → test → build → bundle 顺序，前阶段失败立刻终止，不浪费 CI 分钟。
3. **bundle size 是产品质量的硬约束**：每端有限额，超阈值 fail。
4. **monitor 桥**：CI fail 自动开 issue（`labels: ci, p19-d, nightly-failure`），P19-A/B/C 监控告警可以通过订阅这个 label 跳过去（避免重复告警）。

## 5 端 Workflow 清单

### 1. `backend.yml`

| 项 | 值 |
|---|---|
| Trigger | PR + push to main, paths: `backend/**` / `pyproject.toml` |
| Jobs | lint (ruff + black) → typecheck (mypy) + test (pytest --cov >= 80%) + security (pip-audit) |
| 通过标准 | 所有 job green；coverage >= 80% |
| 已知豁免 | `GHSA-xqmj-j6mv-4862`（litellm，受 camel-ai 锁，详见 `docs/v3/P16_DEPENDENCY_UPGRADE.md`） |
| 上传 | coverage.xml -> Codecov（`flags=backend`） |

### 2. `frontend.yml`

| 项 | 值 |
|---|---|
| Trigger | PR + push to main, paths: `frontend/**` |
| Jobs | install → lint (eslint --max-warnings=0) + typecheck (tsc --noEmit) + test (vitest) → build (vite) → e2e-mock (Playwright) |
| 通过标准 | 0 eslint warning；tsc 无错误；build 成功；bundle size 通过；E2E `@v3 / harness / persona / navigation` subset 通过 |
| 限额 | main chunk < 1024 KB，dist 总 < 5120 KB（见 `scripts/ci/check-bundle-sizes.sh`） |
| 上传 | `frontend-dist` artifact + `playwright-report` |

### 3. `mobile.yml`

| 项 | 值 |
|---|---|
| Trigger | PR + push to main, paths: `mobile/**` |
| Jobs | install + tsc --noEmit + vitest → eas dry-run + expo config 校验 |
| 通过标准 | typecheck 0 错；EAS dry-run 不 crash |
| 已知不做 | 真 APK 构建（需 EXPO_TOKEN + 时间长，跳） |

### 4. `mini-program.yml`

| 项 | 值 |
|---|---|
| Trigger | PR + push to main, paths: `mini-program/**` |
| Jobs | build:weapp + 主包/分包 size 校验 / build:h5（含 postbuild check-bundle-size.js） |
| 通过标准 | weapp 主包 < 1.5 MB，总 < 8 MB；H5 entrypoint < 430 KB |
| 上传 | `mini-program-dist` artifact |

### 5. `tauri-desktop.yml`

| 项 | 值 |
|---|---|
| Trigger | PR + push to main, paths: `desktop/**` 或 `frontend/**` |
| Jobs | frontend-build-gate（前端必须先 build 成功）→ cargo check + clippy + cargo test (macos-latest) |
| 通过标准 | cargo check 通过；clippy 没有 deny warning（暂 soft-fail）；test 通过（暂 soft-fail） |
| 平台 | macos-latest（Windows/Linux 在 release tag 时由 build-clients.yml 处理） |

### 6. `all-smoke.yml` (统一 smoke)

| 项 | 值 |
|---|---|
| Trigger | `workflow_dispatch` + nightly cron `0 2 * * *`（北京时间 10:00） |
| Jobs | smoke-backend / smoke-frontend / smoke-mobile / smoke-mini-program / smoke-desktop → aggregate |
| 输出 | GH Step Summary 表格 |
| 失败 | 自动开 issue（`labels: ci, p19-d, nightly-failure`） |

## 失败诊断流程图

```
PR / push
   │
   ▼
┌──────────────┐
│  Lint fail?  │──Yes──> ruff/eslint 提示行号 → 本地 `npm run lint -- --fix` / `uv run ruff check --fix` → push
└──────┬───────┘
       │ No
       ▼
┌──────────────┐
│  Type fail?  │──Yes──> tsc/mypy 提示类型错 → 本地复现：`npx tsc --noEmit` / `uv run mypy src/`
└──────┬───────┘
       │ No
       ▼
┌──────────────┐
│  Test fail?  │──Yes──> 看具体 test name → 本地 `npm test -- <pattern>` / `uv run pytest -k <name> -v`
└──────┬───────┘        ├─ flaky? rerun 1 次（FE 有 retries=2）
       │ No             └─ real? 修代码 / 修测试
       ▼
┌──────────────┐
│  Build fail? │──Yes──> 通常是 import 错 / 配置错 → 本地 `npm run build` / `uv build`
└──────┬───────┘
       │ No
       ▼
┌──────────────┐
│  Size fail?  │──Yes──> `bash scripts/ci/check-bundle-sizes.sh <端>` 本地复现
└──────┬───────┘        ├─ 真膨胀：分析 chunk（`vite build --report` / `taro inspect`）→ 拆包 / 懒加载
       │ No             └─ 限额过紧：评估后调 `scripts/ci/check-bundle-sizes.sh` 阈值（需 P19 lead approve）
       ▼
   ✅ Green
```

## 如何加新检查

1. **新 lint 规则**：改 `frontend/.eslintrc` 或 `backend/pyproject.toml [tool.ruff.lint]`，CI 自动跑。
2. **新 test**：放到 `backend/tests/` 或 `frontend/src/**/*.test.ts`，CI 自动跑。
3. **新 bundle size 限额**：编辑 `scripts/ci/check-bundle-sizes.sh` 的 `check_*` 函数，加 `check_size_limit`。
4. **新 workflow**：在 `.github/workflows/` 下新建 yml；务必加 `paths:` 过滤；务必在本文档表格里增行。
5. **接入 P19-A/B/C 监控告警**：监控侧订阅 GH issue label `ci`，命中则跳过当次告警（避免「CI 自己挂了」当作生产告警）。

## 如何本地调试 GHA

### 方式 1：act（推荐）

```bash
# 安装
brew install act  # macOS
# Linux: see https://github.com/nektos/act

# 跑单个 workflow
act -W .github/workflows/backend.yml --container-architecture linux/amd64

# 跑特定 job
act -j lint -W .github/workflows/backend.yml
```

### 方式 2：本地 smoke 脚本

```bash
# 全部 5 端
bash scripts/ci/run-smoke.sh

# 跳过慢的 desktop
bash scripts/ci/run-smoke.sh fast

# 单端
bash scripts/ci/run-smoke.sh frontend
```

### 方式 3：actionlint（语法校验）

```bash
brew install actionlint
actionlint .github/workflows/*.yml
```

## 与 P19-A / P19-B / P19-C 衔接

| P19-X | 职责 | CI 桥接点 |
|---|---|---|
| P19-A 后端监控 | Prometheus metrics + Sentry | `backend.yml` test 失败时上报 metrics `ci_test_failure_total{layer=backend}` |
| P19-B 前端监控 | Sentry browser + RUM | `frontend.yml` build 失败时上报 release（用 Sentry CLI） |
| P19-C Prometheus/Grafana | 统一面板 | `all-smoke.yml` 的 aggregate job 推 `nightly_smoke_status{layer=…}` 到 Pushgateway |
| **P19-D（本）** | **5 端 CI gate** | **失败开 issue → P19-A/B/C 告警跳过这条避免重复** |

> CI 失败 ≠ 生产事故。监控侧应过滤 `label:ci OR label:nightly-failure` 的 issue 不触发 oncall。

## CI 状态徽章（贴到 README）

```markdown
[![Backend CI](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/backend.yml/badge.svg)](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/frontend.yml/badge.svg)](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/frontend.yml)
[![Mobile CI](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/mobile.yml/badge.svg)](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/mobile.yml)
[![Mini Program CI](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/mini-program.yml/badge.svg)](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/mini-program.yml)
[![Tauri Desktop CI](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/tauri-desktop.yml/badge.svg)](https://github.com/tiantangcao1980-web/Anxin-Smart-Assistant/actions/workflows/tauri-desktop.yml)
[![codecov](https://codecov.io/gh/tiantangcao1980-web/Anxin-Smart-Assistant/branch/main/graph/badge.svg)](https://codecov.io/gh/tiantangcao1980-web/Anxin-Smart-Assistant)
```

## Bundle Size 限额一览

| 端 | 项 | 限额 | 来源 |
|---|---|---|---|
| frontend | main chunk | 1024 KB (1 MB) | `scripts/ci/check-bundle-sizes.sh` |
| frontend | dist 总 | 5120 KB (5 MB) | 同上 |
| mini-program | weapp 主包 | 1536 KB (1.5 MB) | 同上（微信硬限 2 MB） |
| mini-program | weapp 总包 | 8192 KB (8 MB) | 同上（微信硬限 20 MB） |
| mini-program | h5 entrypoint | 430 KB | `mini-program/scripts/check-bundle-size.js`（postbuild） |
| mobile | expo dist | 6144 KB (6 MB) | `scripts/ci/check-bundle-sizes.sh`（仅当 dist 存在） |
| desktop | tauri release | — | 不在 CI 检查（platform-specific binary） |

---

**版本**：P19-D 初版 / 2026-05-01
**维护**：CI 失败请优先按上方流程图自查，不要直接 disable workflow。
