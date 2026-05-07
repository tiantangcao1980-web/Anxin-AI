# 发版体检清单 — 2026-04-18

本文件是一份可执行的发版前健康检查表。每次发版前按此清单逐项执行，
所有项目必须 ✅ 绿色才能进入上线动作。

## 一、代码层门槛

| 层级 | 命令 | 期望结果 | 上次结果 |
|---|---|---|---|
| Backend 关键子集 | `cd backend && ./.venv/bin/pytest -q tests/test_workforce.py tests/test_chat_history_propagation.py tests/test_auth_roles_permissions.py tests/test_auth_surface_hardening.py tests/test_case_service.py tests/test_performance_benchmark.py` | 69 passed | ✅ 69 passed / 8.56s |
| Backend 完整回归 | `cd backend && ./.venv/bin/pytest -q tests` | 273 passed / 0 failed | ✅ 273 passed / 13:32 |
| Frontend 类型+构建 | `cd frontend && npm run build` | exit 0 | ✅ built in ~14s |
| Frontend lint | `cd frontend && npm run lint` | 0 warnings | ✅ |
| Frontend 单测 | `cd frontend && npm run test` | 2 files / 3 tests | ✅ |
| Frontend E2E | `cd frontend && npx playwright test` | 108 passed / 0 failed | ✅ 108/0/46 skipped |
| Desktop | `cd desktop && cargo check` | exit 0 | ✅ |
| Mobile 单测 | `cd mobile && npm test` | 5 files / 10 tests | ✅ |
| Mini-program H5 + size guard | `cd mini-program && npm run build:h5` | ✅ 所有尺寸指标在阈值内 | ✅ app.js 21.2 KiB / entry 411.4 KiB |

## 二、性能与尺寸指标

| 维度 | 阈值 | 当前 | 状态 |
|---|---|---|---|
| Backend 完整回归耗时 | ≤ 25 min | 13:32 | ✅ |
| Frontend build 时间 | ≤ 20s | ~14s | ✅ |
| Mini-program 业务代码 `app.js` | ≤ 40 KiB | 21.2 KiB | ✅ |
| Mini-program 首次加载总量 | ≤ 430 KiB | 411.4 KiB | ✅ |
| Playwright E2E 全跑时间 | ≤ 2 min | ~42s | ✅ |

## 三、依赖矩阵

| 组件 | 服务端版本 | 客户端版本 | 匹配 |
|---|---|---|---|
| PostgreSQL | (配置中) | asyncpg >= 0.29 | ✅ |
| Redis | (配置中) | redis >= 5.0 | ✅ |
| **Qdrant** | **v1.12.1** | **qdrant-client 1.12.2（pin 1.12.x）** | ✅ |
| Neo4j | (配置中) | neo4j >= 5.15 | ✅ |
| MinIO | (配置中) | minio >= 7.2 | ✅ |

## 四、关键测试覆盖

### 认证链（P0 回归）
- ✅ test_register_assigns_initial_role_by_user_type × 4（企业 / 个人 / 律师 / 机构）
- ✅ test_login_locks_account_after_repeated_failures
- ✅ test_forgot_password_rate_limited
- ✅ CAPTCHA 环境隔离（conftest autouse）

### 智能体编排（P0 回归）
- ✅ test_workforce_initialization（19 个 agent）
- ✅ test_get_agents_info
- ✅ test_execute_single_task_sets_history_contextvar（无双重 await）

### 文档工作台（E2E 深度）
- ✅ 所有 entryMode 默认展开右侧面板
- ✅ WorkbenchSidebar 三段切换（文档工作台 / 协作模板）
- ✅ 示例文档分组（Markdown / PDF / 通用）
- ✅ 知识库资源选择器（全部 / 知识库 / 模板）
- ✅ AI 缺项补写闭环（插入建议 / 生成补写段落 / 历史 / 锚点定位）

### 路由与信息架构
- ✅ 顶部四大业务域：AI法务 / 智能协作 / 智能调查 / 法律智库
- ✅ 旧路由兼容：`/tasks → /case-center?tab=tasks` 等全部带 tab
- ✅ 合同「完整审查」不再循环重定向

## 五、发版阻断项（必须为 0）

| 阻断项 | 当前 |
|---|---|
| Backend 测试失败 | 0 |
| Frontend 构建错误 | 0 |
| Frontend Lint 警告 | 0 |
| Playwright E2E 失败 | 0 |
| 小程序尺寸超阈值 | 0 |
| Qdrant 版本不匹配警告 | 0 |

## 六、发版后立即执行

- [ ] 查看线上 API `/health` 端点返回 200
- [ ] 查看线上 Qdrant 客户端兼容性日志无警告
- [ ] 查看前端首屏 TTI（应 ≤ 3s）
- [ ] 查看小程序 H5 首屏加载（应 ≤ 2s）
- [ ] 查看后端 workforce 日志无 "double await" 类异常
- [ ] 查看新建账户注册流程（无 CAPTCHA 测试环境污染）

## 七、已知风险与监控

| 风险 | 缓解 |
|---|---|
| Qdrant 客户端 1.12 不支持最新特性 | 已 pin；升级前先升服务端到 1.16+ |
| right-panel.spec 50ms 时序测试 flaky | 已配 local retries=1 + CI retries=2 |
| Mini-program entrypoint 首次加载 411 KiB | gzip 后约 140 KiB；vendor 长缓存生效 |
| workforce agent 清单硬编码 | TODO：改注册表（下一个 Sprint） |

---

**签发条件**：上述所有"期望结果"与"当前"一致，且第五节所有阻断项为 0。
