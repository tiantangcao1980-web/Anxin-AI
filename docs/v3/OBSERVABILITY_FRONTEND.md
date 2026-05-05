# V3 三端前端可观测层（P19-B）

> 范围：Web (React/Vite) · Mobile (Expo/RN) · Mini-Program (Taro)
> 时间：2026-04 启动；与 P19-A 后端 monitoring + P19-C Prometheus/Grafana + P19-D CI 联动。

---

## 1. 总览

| 端 | 错误捕获 | 性能采集 | Session Replay | 业务事件 |
|---|---|---|---|---|
| Web | Sentry React + ErrorBoundary | web-vitals (LCP/FID/INP/CLS/TTFB) | Sentry Replay (10%) | `customMetrics.ts` × 10 helper |
| Mobile | sentry-expo + ErrorUtils | sentry-expo native trace | 不启用 | 复用 helper（按需） |
| Mini-Program | Taro.onError + onUnhandledRejection 自实装 | Taro.getPerformance | 不可用 | `error-reporter.trackEvent` |

所有三端**额外**走自实装聚合通道：`POST /api/v1/client-errors`，由 P19-A 后端 `error_classifier` 计算同一份 fingerprint hash，确保跨端聚类。

---

## 2. Sentry 配置 SOP

### 2.1 Web

```bash
# .env / .env.production
VITE_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/yyy
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_TRACES_SAMPLE_RATE=0.1
VITE_SENTRY_REPLAYS_SAMPLE_RATE=0.1
```

启动入口（`frontend/src/main.tsx`）已自动调用 `initSentry()` + `initWebVitals()`。
**DSN 留空时整套监控自动关闭**，不影响开发体验。

### 2.2 Mobile (Expo)

```bash
EXPO_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/yyy
EXPO_PUBLIC_SENTRY_ENVIRONMENT=production
EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.1
```

启动入口（`mobile/app/_layout.tsx`）已自动调用 `initSentry()` + `setupCrashReporting()`。
sentry-expo 通过动态 require 加载，未安装时**降级到 console + 自实装通道**。

### 2.3 Mini-Program

无 Sentry 官方 SDK，直接用自实装上报：
- `Taro.onError` → POST `/api/v1/client-errors`（type=`crash`）
- `Taro.onUnhandledRejection` → 同上（type=`unhandled_rejection`）
- `Taro.getPerformance` → 同上（type=`perf`）

**配置零成本** —— 启动时由 `setupErrorReporter()` + `setupPerfReporter()` 自动接管。

---

## 3. Web Vitals 上报字段

```ts
{
  source: 'web',
  type: 'web-vital',
  name: 'LCP' | 'FID' | 'INP' | 'CLS' | 'TTFB',
  value: number,                                    // 单位：ms（CLS 为无单位 score）
  rating: 'good' | 'needs-improvement' | 'poor',
  id: string,                                       // 同一指标的多次重发可去重
  navigationType: 'navigate' | 'reload' | 'back-forward' | 'prerender',
  url: string,                                      // window.location.pathname
  ts: number                                        // Date.now()
}
```

性能基线（Core Web Vitals 2024 Google 推荐）：

| 指标 | Good | Needs Improvement | Poor |
|---|---|---|---|
| **LCP** | ≤ 2.5 s | ≤ 4.0 s | > 4.0 s |
| **FID** | ≤ 100 ms | ≤ 300 ms | > 300 ms |
| **INP** | ≤ 200 ms | ≤ 500 ms | > 500 ms |
| **CLS** | ≤ 0.1 | ≤ 0.25 | > 0.25 |
| **TTFB** | ≤ 0.8 s | ≤ 1.8 s | > 1.8 s |

P19-D 在 CI 中跑 Lighthouse + 上述阈值做 PR gate。

---

## 4. 业务自定义事件清单（10 个关键路径）

| Helper | 触发位置（建议） | context 字段 |
|---|---|---|
| `trackPersonaChatMessageSent` | `frontend/src/components/chat/ChatInput.tsx` `onSend` | `personaId, messageId` |
| `trackPersonaChatMessageReceived` | `frontend/src/lib/api/persona-stream.ts` 流结束 | `personaId, messageId, durationMs, tokens?` |
| `trackAgentTaskCreated` | `components/agent-tasks/CreateTaskDialog` `onSubmit` | `taskId, type` |
| `trackAgentTaskCompleted` | `lib/api/agent-tasks.ts` ws `task.completed` | `taskId, status, durationMs` |
| `trackOAuthAuthorizeStarted` | `pages/oauth/AuthorizePage` 点击「授权」 | `provider, scope?` |
| `trackOAuthAuthorizeCompleted` | `pages/oauth/AuthorizePage` 回调成功 | `provider, appId?` |
| `trackOAuthAuthorizeFailed` | 同上 catch 分支 | `provider, reason` |
| `trackSkillExecuted` | `lib/api/skills.ts` execute 完成 | `skillId, status, durationMs` |
| `trackFetchRequestSent` | `lib/api/fetch.ts` 发起前 | `url, method` |
| `trackPairingRequestApproved` | `pages/im-pairing/*` 同意时 | `pairingId, appId` |

> **本次 P19-B 只提供 helper**，不动业务页代码。后续 PR 在对应位置插入一行 `import + call`，保持改动最小。

事件载荷统一为：

```ts
{ source: 'web', type: 'event', name: <EventName>, context: {...}, url, ts }
```

---

## 5. 错误聚类策略（与 P19-A 后端对齐）

### 5.1 Fingerprint 三元组

三端在客户端先按 `[client_source, module, errType, function]` 构造 fingerprint：

| 端 | client_source | module | errType | function |
|---|---|---|---|---|
| Web | `frontend-web` | stack 最末帧 `module` 或 `filename` | exception type | 最末帧 `function` |
| Mobile | `mobile` | 同上（RN frame） | 同上 | 同上 |
| Mini-Program | `miniprogram` | `Taro.getCurrentPages()` 顶页 `route` | 从 `Error: xxx` 解析 | stack 第一行（截断 120） |

### 5.2 后端归一化 hash

`backend/src/api/routes/client_errors.py` 接收后调用：

```python
from src.services.error_classifier import compute_fingerprint  # P19-A
hash = compute_fingerprint(source, error_type, module, message)
```

若 P19-A 还未落地，则用 `MD5(source|type|fingerprint|name|error)` 兜底，**字段集与 P19-A 完全一致**，未来无缝切换不丢历史。

Grafana 看板按 `fingerprint_hash` 维度聚类，跨端共用一个面板：
- `client_source` 维度切片：Web vs Mobile vs MP
- 同一 hash 跨端出现 → 可能是后端契约问题，反向推动 P19-A 修复

---

## 6. 数据流

```
┌──────────┐  Sentry SDK   ┌──────────────────┐
│ Web/Mobile│ ───────────▶ │ Sentry Cloud/SaaS│
└─────┬────┘               └──────────────────┘
      │
      │  /api/v1/client-errors  (web-vital + event + 兜底 crash)
      ▼
┌────────────────────┐    ┌──────────────────┐    ┌─────────┐
│ FastAPI rate-limit │ ─▶ │ error_classifier │ ─▶ │ Loki    │ ─▶ Grafana
│ (100/min/IP)       │    │ (P19-A hash)     │    │ ClientError 表 (可选) │
└────────────────────┘    └──────────────────┘    └─────────┘

Mini-Program ─── Taro.request ──┘  (与 Web 同源端点)
```

---

## 7. 性能基线 & SLO

| 指标 | 目标 | Alert 阈值（P19-C Grafana） |
|---|---|---|
| Web LCP p75 | < 2.5 s | > 4.0 s 持续 5 min |
| Web INP p75 | < 200 ms | > 500 ms 持续 5 min |
| Web CLS p75 | < 0.1 | > 0.25 持续 5 min |
| Mobile JS crash rate | < 0.5% sessions | > 2% / 1h |
| MP onError rate | < 0.3% sessions | > 1% / 1h |
| client-errors 上报失败率 | < 1% | > 5% / 5min（后端 5xx 异常） |

---

## 8. FAQ / 排查

- **DSN 没配置 → 监控失效？** 是的，这是 by design。开发态默认关闭，避免 Sentry 配额浪费。
- **mini-program 域名白名单？** 后端域名（如 `api.anxinagent.com`）必须在「微信公众平台 → 开发设置 → request 合法域名」中加白。
- **如何本地验证 client-errors 端点？** `curl -X POST http://localhost:8001/api/v1/client-errors -H 'Content-Type: application/json' -d '{"source":"web","type":"crash","error":"test"}'`，预期返回 `code: 202`。
- **rate limit 触发？** 默认 100/min/IP，被限流时返回 429。前端不应重试，丢弃即可（事件本身就是 best-effort）。

---

## 9. 后续工作（不在 P19-B 范围）

- [ ] 业务页插入 helper 调用（10 处，单独 PR）
- [ ] P19-A `error_classifier.compute_fingerprint` 落地（与本端点对齐）
- [ ] P19-C Grafana 面板：跨端 fingerprint_hash 维度聚合
- [ ] P19-D CI：Lighthouse 阈值 gate + PR Sentry release 自动上传 sourcemap
- [ ] ClientError 表 model + alembic 迁移（可选，仅在需要离线分析时）
