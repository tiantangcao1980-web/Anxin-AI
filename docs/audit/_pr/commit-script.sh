#!/usr/bin/env bash
# 波次 1（V2 守卫加固 + LLM 隔离 + 尽调模式守卫）拆分 commit 脚本
#
# 目的：把当前所有改动拆为 3 个 commit，便于回滚与 review
# 用法：
#   1. 确认 git status 与本脚本预期一致
#   2. 逐个执行 commit（不要 push）
#   3. 用户审完后再 push
#
# 警告：本脚本不 push、不 force、不 amend。仅 add + commit。

set -euo pipefail

cd /Users/pengchengkeji/Documents/GitHub/Anxin-Smart-Legal-Services

echo "=== 当前 git status ==="
git status -sb
echo ""
read -p "确认看起来对吗？回车继续，Ctrl+C 退出 " _

# ============================================================
# Commit 1：审计文档（无代码风险）
# ============================================================
echo ""
echo "=== Commit 1：审计文档 ==="
git add docs/audit/

git commit -m "$(cat <<'EOF'
docs(audit): 加入 V2 实质就绪度审计计划与任务提示词

本次新增 docs/audit/ 完整目录，包含：
- PLAN.md 主计划书（修订版，融合 18 处代码点位实测）
- 00-platform/ 任务 0 全部产出（PRD vs 现实差分、密钥治理 SOP、
  横切系统缺口、CI 安全扫描方案、followups）
- _tasks/ 15 份独立任务提示词（TASK-01..12）
- 09-risk/PROPOSAL-mode-guard.md 调研提案
- _pr/ PR 描述模板

不改代码，仅文档落地。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"

# ============================================================
# Commit 2：V2 守卫层 + LLM 组织隔离
# ============================================================
echo ""
echo "=== Commit 2：V2 守卫层 + LLM 隔离 ==="
git add backend/src/api/routes/llm.py
git add backend/src/services/llm_service.py
git add backend/tests/test_llm_org_isolation.py
git add frontend/src/components/auth/ProtectedRoute.tsx
git add frontend/src/App.tsx
git add frontend/src/components/pro/ProLayout.tsx
git add frontend/src/components/mode/ModeGate.tsx
git add frontend/src/context/PrivacyContext.tsx
git add frontend/e2e/role-access.spec.ts
git add frontend/e2e/helpers/session.ts

git commit -m "$(cat <<'EOF'
fix(v2,security): V2 守卫层加固 + LLM 多租户隔离 fail-closed

收口 PROJECT_STATUS Phase 1-5 中实质未完工的 V2 守卫缺口：

前端
- ProtectedRoute 加 requirePrimaryClient 参数；老用户字段为空时按 role 推断
- /pro 路由加 requirePrimaryClient="provider"；index 重定向 BUG（指向
  /lawyer-dashboard 根路径）修为 /pro/dashboard
- ProLayout 12 个导航 path 全部加 /pro/ 前缀（修复死代码：进入 /pro 后
  点击导航会跳出 /pro 树）
- ModeGate 移除 setMode(HYBRID) 一键绕过，改为 navigate('/settings?tab=privacy')
  引导用户走 requestModeSwitch（带订阅检查）
- PrivacyContext 三处 fail-open 全部改 fail-closed：
  * `?? true` 默认放行 → `?? false`
  * catch 块 setMode 自动切换 → 不切并标记 subscriptionRequired
  * 非 2xx 响应放行 → 拒绝
- 默认 API 端口 8003 → 8001 与项目其他位置统一

后端
- LLMService.list_configs 加 require_org_filter=True 默认 fail-closed；
  org_id=None 直接返回空（不再走"无过滤"分支）
- if org_id: → if org_id is not None: 修复 falsy bug（S-104 历史修复
  在 None 时被短路，等价于无过滤查询）
- LLM 路由层超管 require_org_filter=False / 普通用户 True

测试
- 5 个 LLM org 隔离回归测试（含默认 fail-closed 用例）
- 4 个 V2 e2e case：needer 访问 /pro/* 被拦 / provider 通行 /
  /pro 重定向 BUG 修复 / 老用户 role 推断
- seedAuthState 加 primary_client 可选字段

测试结果：278 passed（baseline 273 + 5 新增，0 退化）
PR 描述：docs/audit/_pr/wave-1-batch-1-2.md

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"

# ============================================================
# Commit 3：尽调模式守卫（TASK-09 P0-1）
# ============================================================
echo ""
echo "=== Commit 3：尽调模式守卫 ==="
git add backend/src/core/mode_deps.py
git add backend/src/api/routes/due_diligence.py
git add backend/tests/test_mode_subscription_guards.py

git commit -m "$(cat <<'EOF'
feat(security,due-diligence): 新建 mode_deps + 尽调路由加 require_mode 守卫

收口 TASK-09 P0-1：尽调路由历史仅挂 get_current_user_required，
缺少模式（hybrid_or_cloud）和订阅（due_diligence）守卫。

新增 backend/src/core/mode_deps.py 提供两个 FastAPI 依赖工厂：
- require_mode(allow=["hybrid","cloud"])：
  * 读 X-Privacy-Mode 头比对 + 订阅 allowed_modes 双重校验
  * 老客户端无头时按订阅 allowed_modes[0] 推断（fail-safe）
  * 超级管理员直接放行
  * 不在 allow 列表 → 403；订阅不允许 → 402
- require_subscription_feature(feature_key)：
  * SubscriptionService.can_access_feature 返回 False → 402
  * 超级管理员直接放行

due_diligence.py 10 个写入路由全部挂上双守卫：
- POST /company /company/stream /company/orchestrated-stream /company/deep-investigate
- POST /investigations/{id}/report /report/generate /report/generate/stream
- POST /simulate /simulate/stream
- POST /memory/dream

只读路由（profile/risks/litigation/graph/snapshots/cache/preferences/memory）
本批未动，下批可考虑加 require_subscription_feature 但不挂 require_mode。

测试覆盖（8 个新增 pytest case）：
- 超管放行（mode + feature 双守卫）
- 免费用户无头降级 local → 403
- 付费用户带 hybrid 头 → 通过
- 付费用户但前端选 local → 403
- 非法头按缺失处理
- 免费用户 due_diligence → 402
- 付费用户 due_diligence → 通过

测试结果：286 passed（baseline 273 + 13 新增，0 退化）
方案文档：docs/audit/09-risk/PROPOSAL-mode-guard.md

后续配套：
- 前端 axios 拦截器加 X-Privacy-Mode 头（独立 PR，依赖
  PrivacyContext 持久化重构）
- 只读路由加 require_subscription_feature

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"

echo ""
echo "=== 全部完成 ==="
git log --oneline -3
echo ""
echo "下一步建议："
echo "  1. git diff main HEAD 复查整体变更"
echo "  2. ./.venv/bin/pytest tests/ -q 复跑后端验证"
echo "  3. cd frontend && npm run build && npm run lint"
echo "  4. 确认无问题后再 git push origin <branch>"
echo ""
echo "如果要回滚某个 commit：git reset --soft HEAD~1（保留改动到工作区）"
