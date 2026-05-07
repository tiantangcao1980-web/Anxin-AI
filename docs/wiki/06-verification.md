# 验证与质量基线

## 当前已实际运行过的检查

本 Wiki 生成前，已运行并观察到以下结果：

| 区域 | 命令 | 结果 |
|---|---|---|
| Web lint | `cd frontend && npm run lint` | 通过 |
| Web build | `cd frontend && npm run build` | 通过，有构建告警 |
| 后端抽样测试 | `pytest` 关键切片 32 项 | 32 passed，6 warnings |
| 桌面 Rust | `cd desktop && cargo check` | 通过 |
| 移动/小程序本地门禁 | `bash scripts/mobile-device-smoke.sh` | 通过：mobile Vitest 7 files / 17 tests passed；mobile tsc、Expo doctor 17/17、mobile production npm audit、小程序 tsc/build、WeChat DevTools CLI project smoke、refresh auth guard、fake fallback guard、mini-program design token guard 均为 exit 0 |
| 小程序 H5 | `cd mini-program && npm run build:h5` | 历史通过，1 个 webpack warning；当前发布基线以 `build:weapp` 为准 |

## Web build 告警

已知告警：

- `lottie-web` 使用 `eval`
- 部分 chunk 超过 500KB
- `api.ts` / `api-adapter.ts` 动静态 import 混用，影响代码分割

这些不是当前构建阻断，但会影响生产安全和性能。

## 后端测试

最近记录过后端全量 pytest：

```text
467 passed, 1 skipped, 17 warnings
```

但注意：商业候选发布前必须基于最终提交重新跑全量：

```bash
cd backend
./.venv/bin/python -m pytest -q tests
```

## 前端测试

推荐发布前至少跑：

```bash
cd frontend
npm run lint
npm run build
npm run test
npm run test:e2e -- role-access.spec.ts
npm run test:e2e -- business-actions.spec.ts
```

如果浏览器权限或 Playwright 环境异常，需要记录为发布风险。

## 移动端测试

当前本地代码级门禁已通过，但真机/官方工具验收仍未完成。发布前至少复跑：

```bash
cd mobile
npm test
npx tsc --noEmit --module esnext
```

统一入口：

```bash
bash scripts/mobile-device-smoke.sh
```

该脚本覆盖移动 Vitest、移动 tsc、Expo config/SDK guard、Expo doctor、mobile production npm audit、小程序 tsc/build、WeChat DevTools CLI project smoke、refresh auth guard、fake fallback guard 与小程序设计 token guard。它不能替代 iOS、Android、交互式微信开发者工具或真机 transcript。

## GitNexus 风险信号

GitNexus `detect_changes(scope=all)` 曾在大规模未提交交付面上报告：

| 指标 | 值 |
|---|---:|
| changed files | 105 |
| changed symbols | 1126 |
| affected processes | 68 |
| risk level | critical |

这说明历史交付面改动很广，发布前不应只跑单点测试。当前已提交后应以 `.gitnexus/meta.json`、`gitnexus status` 和 `detect-changes` 的最新结果为准。
