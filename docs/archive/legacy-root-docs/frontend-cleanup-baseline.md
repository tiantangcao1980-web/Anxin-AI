# 前端清理基线清单

> 目的：在 UI/UX 升级执行前，先清理旧的、冗余的、未引用的样式、资源和代码，避免新旧系统长期并存。

## 1. 清理原则

- 先盘点，再删除。
- 删除前确认：是否仍被路由、动态导入、测试、脚本或文档使用。
- 清理优先级高于局部美化；如果一个模块已被新实现替代，应先去旧再做样式统一。
- 所有“候选未使用项”都要标记为 `confirmed-unused` 后再真正移除。

## 2. 当前候选遗留项

### 2.1 第一批分类结果

#### confirmed-unused（已完成第一批删除）

- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/components/dashboard/Dashboard.tsx`
- `frontend/src/pages/Experts.tsx`
- `frontend/src/pages/Knowledge.tsx`
- `frontend/src/pages/Search.tsx`
- `frontend/src/pages/AgentWorkflow.tsx`
- `frontend/src/pages/ConversationInsights.tsx`
- `frontend/src/pages/AIAssistantSettings.tsx`
- `frontend/src/pages/Approvals.tsx`
- `frontend/src/pages/FirmManagement.tsx`

说明：
- 已被重定向入口替代，或仅剩无效懒加载残留。
- 删除后不会影响当前主路由。
- 该批次已执行完成；当前代码库中这些文件已移除。

#### keep-for-now（暂不删除）

- `frontend/src/pages/News.tsx`

说明：
- 当前路由已注释，但文件明确标注为后续版本启用，先保留，避免误删规划内功能。

### 2.2 候选资源问题

- `frontend/src/assets/animations/*.json` 当前都有引用，但引用强度很低，且存在远程 Lottie URL 与本地 JSON 并存的问题。
- 需要核查是否保留“双轨动画体系”，还是统一到本地资源或统一到远程策略。

### 2.3 候选样式遗留

- 页面和组件里存在大量直接 `rounded-*`、`shadow-[...]`、硬编码颜色和局部按钮样式。
- 这些不一定是“未引用”，但属于“旧系统残留实现”，必须在阶段改造中逐步回收。

## 3. 清理类型

### A. 彻底删除
- 已无路由入口
- 已无导入引用
- 已被新模块完全替代

### B. 合并替换
- 仍有行为价值，但视觉和交互实现已过时
- 应迁移到统一组件后再删除旧实现

### C. 保留归档
- 暂时不删，但明确标记为历史兼容、实验性或待迁移

## 4. 清理执行顺序

1. 跑 `npm run audit:cleanup`
2. 标记候选项为：
   - `confirmed-unused`
   - `needs-migration`
   - `keep-for-now`
3. 先删页面级休眠入口与废弃资源
4. 再回收旧样式、旧组件私有实现
5. 最后再做 UI 统一改造

## 5. 清理验收标准

- 没有“旧页面文件仍在、但新页面已接管”的双轨状态
- 没有“同一功能两套样式/两套资源/两套组件”
- 资产目录没有明显孤儿资源
- 路由、导航、设计文档、测试说明指向同一套当前实现
