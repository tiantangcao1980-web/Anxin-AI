#!/usr/bin/env node

const fs = require('fs');

const checks = [
  {
    path: 'PRODUCT_ROADMAP.md',
    required: [
      '最后更新：2026-05-09',
      '桌面端代码级 MVP 与本地门禁推进中；商业发布仍缺签名/真机/外部 API 证据',
      'Mobile + Mini Program, uni-app',
      '当前代码级能力',
      '不等于商业发布完成',
      'shared-staging/signed runtime 证据待补',
      'Quick Query 独立窗口',
      '真实托盘图标 drop',
      'DCloud App 云打包',
      '代码级 rehearsal',
    ],
    forbidden: [
      '最后更新：2026-04-15',
      'Mobile Edition, Tauri iOS/Android',
      '已完成能力（截至 2026-04-15）',
      '✅ 自动更新（`tauri-plugin-updater`）',
      '✅ 本地 SQLite 数据库（`tauri-plugin-sql`）',
      '✅ 离线任务队列 + 同步引擎（`desktop/src/services/`）',
      'P0-1 ~ P0-3 完成',
      'iOS / Android 移动端 UI 适配',
      'TestFlight / 应用宝 Beta',
    ],
  },
  {
    path: 'PROJECT_STATUS.md',
    required: [
      '2026-05-09 商业交付状态纠偏',
      '尚未达到商业交付完成态',
      'scripts/commercial-readiness-gate.sh --quick',
      '桌面优先',
      'apps/uni-mobile/',
      'DCloud App 云打包/签名',
      'V2 架构核心基础设施已就绪；**不等于商业可上线完成态**',
    ],
    forbidden: [
      'V2 架构核心基础设施已就绪，可部署到生产环境',
      '后续为持续迭代：支付渠道真实对接、跨模式数据同步、企业私有化定制',
    ],
  },
  {
    path: 'docs/audit/00-platform/01-prd-reality-gap.md',
    required: [
      '代码级/unsigned 证据已补，商业同步闭环仍未完成',
      '独立 `/desktop/quick-query` 快问窗口',
      '[~] P0-1',
      '[~] P0-2',
      '[~] P0-3',
      'signed runtime、平台手测、性能、真实 connector/模型和真机证据',
    ],
    forbidden: [
      '快捷键呼出后**没有"快速问答"模式**',
      '当前呼出后跳到主界面',
      '| [ ] P0-1：Tauri 窗口外观优化 | 未实现',
      '| [ ] P0-2：全局快捷键呼出后的"快速问答"模式 | 未实现',
      '| [ ] P0-3：文件拖拽到系统托盘 → 自动分析 | 未实现',
    ],
  },
  {
    path: 'docs/audit/00-platform/03-cross-cutting-gaps.md',
    required: [
      '缺口 A 的底座已落地',
      '缺口 B 的代码级官方协议与幂等/重试底座已落地',
      '缺口 C 已由任务 11b 推进到 SQLCipher/keyring',
      '已完成代码级/unsigned release 本地证据',
      'PROJECT_STATUS.md` → 2026-05-09 已补商业交付状态纠偏',
      'PRODUCT_ROADMAP.md` → 2026-05-09 已把',
    ],
    forbidden: [
      '缺口 C 的修复就是任务 11b 本身',
      '任务 11b 启动时（约 Day 14）',
      '预计 Day 21 完成',
      '骨架已搭，实质未连',
    ],
  },
];

const failures = [];

for (const check of checks) {
  if (!fs.existsSync(check.path)) {
    failures.push(`${check.path}: missing`);
    continue;
  }
  const text = fs.readFileSync(check.path, 'utf8');
  for (const fragment of check.required) {
    if (!text.includes(fragment)) {
      failures.push(`${check.path}: missing required fragment ${JSON.stringify(fragment)}`);
    }
  }
  for (const fragment of check.forbidden) {
    if (text.includes(fragment)) {
      failures.push(`${check.path}: contains stale fragment ${JSON.stringify(fragment)}`);
    }
  }
}

if (failures.length) {
  for (const failure of failures) {
    console.error(`Product status consistency: FAIL: ${failure}`);
  }
  process.exit(1);
}

console.log('Product status consistency: OK');
