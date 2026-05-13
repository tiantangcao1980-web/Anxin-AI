// -*- coding: utf-8 -*-
/**
 * 能力中心统一 Mock 数据 + 类型契约 (P21-D 小程序)
 *
 * 与 web (frontend/src/lib/api/*) / mobile (mobile/src/lib/api/__mocks__/capabilities.mock.ts)
 * 类型 1:1 对齐，便于 P21-A 真业务 API 落地后批量替换。
 *
 * 所有 API 都是 Promise + 模拟 ~250-300ms 延迟，配合小程序的 loading 态。
 */

// ============================================================================
// 类型契约
// ============================================================================

// ----- Skills -----
export type SkillCategory =
  | 'legal'
  | 'tax_finance'
  | 'operations'
  | 'research'
  | 'marketing'
  | 'content'
  | 'design'
  | 'office'
  | 'ecommerce'
  | 'sales'
  | 'intelligence'
  | 'decision'
  | 'system'

export interface Skill {
  name: string
  display_name: string
  description: string
  category: SkillCategory
  enabled: boolean
  triggers: string[]
  requires_apps: string[]
}

// ----- App Authorizations -----
export type AppCategory =
  | 'office'
  | 'office_storage'
  | 'crm'
  | 'ecommerce'
  | 'info_source'
  | 'design'
  | 'compliance'
  | 'finance'

export type AppAuthorizationStatus = 'connected' | 'expired' | 'revoked' | 'error'

export interface AppProvider {
  provider_id: string
  display_name: string
  description: string
  category: AppCategory
  icon_url: string | null
  default_scopes: string[]
}

export interface AppAuthorization {
  id: string
  provider_id: string
  status: AppAuthorizationStatus
  scopes: string[]
  connected_at: string
  account_label?: string
}

// ----- IM Channels -----
export type IMChannelType = 'feishu' | 'wechat' | 'dingtalk' | 'telegram' | 'discord'
export type IMChannelStatus = 'unconfigured' | 'connecting' | 'connected' | 'error'

export interface IMChannelStats {
  bound_users: number
  bound_groups: number
  pending_pairings: number
}

export interface IMChannel {
  id: string
  channel_type: IMChannelType
  name: string
  enabled: boolean
  status: IMChannelStatus
  bound_agent_persona: string | null
  stats: IMChannelStats
}

// ----- Pairing -----
export type PairingStatus = 'pending' | 'approved' | 'rejected' | 'expired'

export interface PairingRequest {
  id: string
  channel_id: string
  channel_type: IMChannelType
  channel_name: string
  external_user_id: string
  external_user_name: string
  external_group_name?: string
  status: PairingStatus
  expires_at: string
  created_at: string
  approved_at: string | null
}

// ----- Scheduled Tasks -----
export type ScheduleKind = 'daily' | 'monitor' | 'report' | 'automation'
export type ScheduleStatus = 'active' | 'paused' | 'failed'

export interface ScheduledTask {
  id: string
  name: string
  description: string
  kind: ScheduleKind
  cron: string
  cron_human: string
  status: ScheduleStatus
  icon: string
  agent_persona: string
}

// ----- Plugins -----
export type PluginStatus = 'enabled' | 'disabled' | 'pending_review'

export interface Plugin {
  id: string
  name: string
  display_name: string
  description: string
  status: PluginStatus
  publisher: string
  skill_count: number
  icon: string
}

// ============================================================================
// Mock 数据
// ============================================================================

function delay<T>(value: T, ms = 280): Promise<T> {
  return new Promise((r) => setTimeout(() => r(value), ms))
}

// ----- Scheduled Tasks (16 个，4 类) -----
const SCHEDULED_TASKS: ScheduledTask[] = [
  // 日常 (4)
  { id: 'st-d1', name: '晨间简报', description: '每日 09:00 推送昨日要闻摘要', kind: 'daily', cron: '0 9 * * *', cron_human: '每天 09:00', status: 'active', icon: '🌅', agent_persona: 'office' },
  { id: 'st-d2', name: '日终总结', description: '每日 18:00 汇总当日工作产出', kind: 'daily', cron: '0 18 * * *', cron_human: '每天 18:00', status: 'active', icon: '🌇', agent_persona: 'office' },
  { id: 'st-d3', name: '站会准备', description: '工作日 09:30 整理站会要点', kind: 'daily', cron: '30 9 * * 1-5', cron_human: '工作日 09:30', status: 'paused', icon: '👥', agent_persona: 'office' },
  { id: 'st-d4', name: '邮件分拣', description: '每 2 小时分类未读邮件', kind: 'daily', cron: '0 */2 * * *', cron_human: '每 2 小时', status: 'active', icon: '📧', agent_persona: 'office' },
  // 监控 (4)
  { id: 'st-m1', name: '竞品动态', description: '每小时扫描竞品新闻与产品更新', kind: 'monitor', cron: '0 * * * *', cron_human: '每小时', status: 'active', icon: '🔭', agent_persona: 'intelligence' },
  { id: 'st-m2', name: '热点追踪', description: '每 30 分钟跟踪行业热点', kind: 'monitor', cron: '*/30 * * * *', cron_human: '每 30 分钟', status: 'active', icon: '🔥', agent_persona: 'intelligence' },
  { id: 'st-m3', name: '技术雷达', description: '每天 08:00 扫描新技术动向', kind: 'monitor', cron: '0 8 * * *', cron_human: '每天 08:00', status: 'failed', icon: '📡', agent_persona: 'research' },
  { id: 'st-m4', name: '依赖检查', description: '每周一 03:00 检查依赖漏洞', kind: 'monitor', cron: '0 3 * * 1', cron_human: '每周一 03:00', status: 'active', icon: '🛡️', agent_persona: 'system' },
  // 报告 (4)
  { id: 'st-r1', name: '周度回顾', description: '每周五 17:00 生成周报', kind: 'report', cron: '0 17 * * 5', cron_human: '每周五 17:00', status: 'active', icon: '📊', agent_persona: 'office' },
  { id: 'st-r2', name: '代码质量报告', description: '每周日 22:00 输出代码质量趋势', kind: 'report', cron: '0 22 * * 0', cron_human: '每周日 22:00', status: 'paused', icon: '🧪', agent_persona: 'system' },
  { id: 'st-r3', name: 'Git 活动概览', description: '每天 19:00 汇总仓库活动', kind: 'report', cron: '0 19 * * *', cron_human: '每天 19:00', status: 'active', icon: '🌿', agent_persona: 'system' },
  { id: 'st-r4', name: '用户反馈摘要', description: '每周一 10:00 提炼上周用户反馈', kind: 'report', cron: '0 10 * * 1', cron_human: '每周一 10:00', status: 'active', icon: '💬', agent_persona: 'research' },
  // 自动化 (4)
  { id: 'st-a1', name: '阻塞发现', description: '每 4 小时扫描进度阻塞项', kind: 'automation', cron: '0 */4 * * *', cron_human: '每 4 小时', status: 'active', icon: '🚧', agent_persona: 'office' },
  { id: 'st-a2', name: '项目状态报告', description: '每天 09:00 推送项目健康度', kind: 'automation', cron: '0 9 * * *', cron_human: '每天 09:00', status: 'active', icon: '📈', agent_persona: 'office' },
  { id: 'st-a3', name: '变更日志生成', description: 'PR 合入后自动生成 CHANGELOG', kind: 'automation', cron: '@event:pr-merged', cron_human: 'PR 合入触发', status: 'active', icon: '📝', agent_persona: 'system' },
  { id: 'st-a4', name: '待办提取', description: '每 1 小时从聊天/会议纪要抽取 todo', kind: 'automation', cron: '0 * * * *', cron_human: '每小时', status: 'paused', icon: '✅', agent_persona: 'office' },
]

// ----- App Providers (30 个，8 分类) -----
const APP_PROVIDERS: AppProvider[] = [
  // office (5)
  { provider_id: 'feishu', display_name: '飞书', description: '字节系协作 OA', category: 'office', icon_url: null, default_scopes: ['contact:user.id:read'] },
  { provider_id: 'dingtalk', display_name: '钉钉', description: '阿里系协作 OA', category: 'office', icon_url: null, default_scopes: ['Contact.User.Read'] },
  { provider_id: 'wecom', display_name: '企业微信', description: '腾讯系企业 IM', category: 'office', icon_url: null, default_scopes: ['snsapi_base'] },
  { provider_id: 'lark', display_name: 'Lark', description: '飞书海外版', category: 'office', icon_url: null, default_scopes: [] },
  { provider_id: 'slack', display_name: 'Slack', description: '海外团队 IM', category: 'office', icon_url: null, default_scopes: ['chat:read'] },
  // office_storage (5)
  { provider_id: 'notion', display_name: 'Notion', description: '团队知识库', category: 'office_storage', icon_url: null, default_scopes: ['read_content'] },
  { provider_id: 'feishu_doc', display_name: '飞书云文档', description: '在线文档', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'dingtalk_drive', display_name: '钉盘', description: '钉钉云盘', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'google_drive', display_name: 'Google Drive', description: '谷歌云盘', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'onedrive', display_name: 'OneDrive', description: '微软云盘', category: 'office_storage', icon_url: null, default_scopes: [] },
  // crm (4)
  { provider_id: 'salesforce', display_name: 'Salesforce', description: '海外 CRM 标杆', category: 'crm', icon_url: null, default_scopes: ['api'] },
  { provider_id: 'hubspot', display_name: 'HubSpot', description: '集客营销 CRM', category: 'crm', icon_url: null, default_scopes: [] },
  { provider_id: 'fxiaoke', display_name: '纷享销客', description: '国内 SaaS CRM', category: 'crm', icon_url: null, default_scopes: [] },
  { provider_id: 'xiaoshouyi', display_name: '销售易', description: '国内 PaaS CRM', category: 'crm', icon_url: null, default_scopes: [] },
  // ecommerce (5)
  { provider_id: 'shopify', display_name: 'Shopify', description: '跨境独立站', category: 'ecommerce', icon_url: null, default_scopes: ['read_orders'] },
  { provider_id: 'amazon_seller', display_name: 'Amazon Seller', description: '亚马逊卖家中心', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'taobao_open', display_name: '淘宝开放平台', description: '阿里电商', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'jd_open', display_name: '京东开放平台', description: '京东商家', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'douyin_open', display_name: '抖店', description: '抖音电商', category: 'ecommerce', icon_url: null, default_scopes: [] },
  // info_source (4)
  { provider_id: 'qichacha', display_name: '企查查', description: '工商信息', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'tianyancha', display_name: '天眼查', description: '企业信用', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'wenshu', display_name: '裁判文书网', description: '司法文书', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'beidafabao', display_name: '北大法宝', description: '法规数据库', category: 'info_source', icon_url: null, default_scopes: [] },
  // design (3)
  { provider_id: 'figma', display_name: 'Figma', description: 'UI 设计协作', category: 'design', icon_url: null, default_scopes: ['files:read'] },
  { provider_id: 'jianying', display_name: '剪映', description: '短视频创作', category: 'design', icon_url: null, default_scopes: [] },
  { provider_id: 'canva', display_name: 'Canva', description: '海报快速创作', category: 'design', icon_url: null, default_scopes: [] },
  // compliance (2)
  { provider_id: 'compliance_gov', display_name: '国家企业信用信息系统', description: '官方信用查询', category: 'compliance', icon_url: null, default_scopes: [] },
  { provider_id: 'creditchina', display_name: '信用中国', description: '失信名单', category: 'compliance', icon_url: null, default_scopes: [] },
  // finance (2)
  { provider_id: 'kingdee', display_name: '金蝶云', description: 'ERP/财务', category: 'finance', icon_url: null, default_scopes: [] },
  { provider_id: 'yongyou', display_name: '用友 U8', description: 'ERP/财务', category: 'finance', icon_url: null, default_scopes: [] },
]

// 已连接：飞书 / Notion / Salesforce(过期) / Figma / 金蝶云
const APP_AUTHORIZATIONS: AppAuthorization[] = [
  { id: 'auth-feishu-1', provider_id: 'feishu', status: 'connected', scopes: ['contact:user.id:read'], connected_at: '2026-04-10T03:22:00Z', account_label: 'wenyu@anxinagent.com' },
  { id: 'auth-notion-1', provider_id: 'notion', status: 'connected', scopes: ['read_content'], connected_at: '2026-04-12T09:00:00Z', account_label: 'workspace: 安心智能助手' },
  { id: 'auth-salesforce-1', provider_id: 'salesforce', status: 'expired', scopes: ['api'], connected_at: '2026-03-01T00:00:00Z', account_label: 'sales@anxin-agent.com' },
  { id: 'auth-figma-1', provider_id: 'figma', status: 'connected', scopes: ['files:read'], connected_at: '2026-04-20T05:00:00Z', account_label: 'designer@anxin-agent.com' },
  { id: 'auth-kingdee-1', provider_id: 'kingdee', status: 'connected', scopes: [], connected_at: '2026-04-22T08:00:00Z', account_label: '财务部账套-001' },
]

// ----- Skills (50+ 跨 13 域) -----
function s(name: string, display_name: string, category: SkillCategory, enabled: boolean, description: string, triggers: string[] = [], requires_apps: string[] = []): Skill {
  return { name, display_name, description, category, enabled, triggers, requires_apps }
}

const SKILLS: Skill[] = [
  // legal (6)
  s('legal/contract-review', '合同审查', 'legal', true, '识别合同风险条款', ['合同审查']),
  s('legal/clause-extract', '条款提取', 'legal', true, '从合同中抽取关键条款'),
  s('legal/case-search', '案例检索', 'legal', true, '裁判文书检索', ['类案'], ['wenshu']),
  s('legal/regulation-lookup', '法规查询', 'legal', true, '法规库精确检索', [], ['beidafabao']),
  s('legal/litigation-strategy', '诉讼策略', 'legal', false, '辅助诉讼方案设计'),
  s('legal/compliance-check', '合规检查', 'legal', true, '业务合规扫描'),
  // tax_finance (4)
  s('tax/invoice-recognize', '发票识别', 'tax_finance', true, 'OCR 识别发票要素'),
  s('tax/tax-calc', '税额测算', 'tax_finance', true, '增值税/所得税计算'),
  s('finance/cash-flow', '现金流分析', 'tax_finance', false, '现金流预测', [], ['kingdee']),
  s('finance/budget-plan', '预算编制', 'tax_finance', false, '年度预算辅助'),
  // operations (3)
  s('ops/sop-generate', 'SOP 生成', 'operations', true, '业务流程文档化'),
  s('ops/risk-matrix', '风险矩阵', 'operations', false, '运营风险评估'),
  s('ops/process-mining', '流程挖掘', 'operations', false, '从日志推导流程'),
  // research (4)
  s('research/market-scan', '市场扫描', 'research', true, '行业研究报告生成'),
  s('research/competitor', '竞品分析', 'research', true, '竞争对手画像'),
  s('research/survey', '问卷设计', 'research', false, '调研问卷生成'),
  s('research/data-clean', '数据清洗', 'research', false, '调研数据预处理'),
  // marketing (4)
  s('marketing/lead-score', '线索评分', 'marketing', true, '销售线索打分'),
  s('marketing/email-campaign', '邮件营销', 'marketing', false, 'EDM 文案生成'),
  s('marketing/social-post', '社媒发布', 'marketing', false, '多平台同步'),
  s('marketing/seo-keyword', 'SEO 关键词', 'marketing', false, '关键词研究'),
  // content (4)
  s('content/article-write', '文章撰写', 'content', true, '长文创作'),
  s('content/short-video', '短视频脚本', 'content', false, '抖音/小红书脚本'),
  s('content/translate', '多语翻译', 'content', true, '中英日韩互译'),
  s('content/proofread', '校对润色', 'content', true, '错别字/语法'),
  // design (3)
  s('design/poster-gen', '海报生成', 'design', false, 'AI 海报', [], ['canva']),
  s('design/figma-handoff', 'Figma 切图', 'design', false, '设计稿标注', [], ['figma']),
  s('design/icon-design', '图标设计', 'design', false, 'SVG 图标生成'),
  // office (5)
  s('office/docx', 'Word 文档', 'office', true, '生成 docx'),
  s('office/xlsx', 'Excel 表格', 'office', true, '生成 xlsx + 公式'),
  s('office/pptx', 'PPT 幻灯片', 'office', true, '生成 pptx'),
  s('office/pdf', 'PDF 处理', 'office', true, '解析/合并/拆分'),
  s('office/email-draft', '邮件起草', 'office', false, '商务邮件'),
  // ecommerce (4)
  s('ecom/listing-optimize', 'Listing 优化', 'ecommerce', false, 'Amazon Listing', [], ['amazon_seller']),
  s('ecom/review-analyze', '评价分析', 'ecommerce', false, '差评归因', [], ['shopify']),
  s('ecom/keyword-mining', '选品关键词', 'ecommerce', false, '蓝海词挖掘'),
  s('ecom/cross-border-tax', '跨境税务', 'ecommerce', false, 'VAT/IOSS 计算'),
  // sales (3)
  s('sales/cold-call-script', '电销话术', 'sales', false, '陌拜话术生成'),
  s('sales/proposal-gen', '商务提案', 'sales', true, '客户方案书'),
  s('sales/quote-calc', '报价测算', 'sales', false, '阶梯报价'),
  // intelligence (4)
  s('intel/news-monitor', '新闻监控', 'intelligence', true, '实时舆情'),
  s('intel/risk-radar', '风险雷达', 'intelligence', true, '黑天鹅预警'),
  s('intel/competitor-watch', '竞争情报', 'intelligence', false, '友商动态'),
  s('intel/policy-track', '政策跟踪', 'intelligence', true, '法规政策更新'),
  // decision (3)
  s('decision/swot', 'SWOT 分析', 'decision', false, '战略框架'),
  s('decision/scenario', '情景规划', 'decision', false, '多场景推演'),
  s('decision/decision-tree', '决策树', 'decision', false, '量化决策'),
  // system (3)
  s('system/log-search', '日志检索', 'system', true, '内部 trace'),
  s('system/api-call', 'API 调用', 'system', true, '通用 HTTP'),
  s('system/cron-edit', '定时编排', 'system', true, '编辑 cron'),
]

// ----- IM Channels (5 平台) -----
const IM_CHANNELS: IMChannel[] = [
  { id: 'imc-feishu', channel_type: 'feishu', name: '飞书', enabled: true, status: 'connected', bound_agent_persona: 'legal', stats: { bound_users: 18, bound_groups: 4, pending_pairings: 3 } },
  { id: 'imc-wechat', channel_type: 'wechat', name: '微信', enabled: false, status: 'unconfigured', bound_agent_persona: null, stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 } },
  { id: 'imc-dingtalk', channel_type: 'dingtalk', name: '钉钉', enabled: false, status: 'unconfigured', bound_agent_persona: null, stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 } },
  { id: 'imc-telegram', channel_type: 'telegram', name: 'Telegram', enabled: false, status: 'unconfigured', bound_agent_persona: null, stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 } },
  { id: 'imc-discord', channel_type: 'discord', name: 'Discord', enabled: false, status: 'unconfigured', bound_agent_persona: null, stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 } },
]

const IM_ICONS: Record<IMChannelType, string> = {
  feishu: '🪶',
  wechat: '💬',
  dingtalk: '🟦',
  telegram: '✈️',
  discord: '🎮',
}

// ----- Pairing Requests (8 待审核 + 12 已授权) -----
function expiresInHours(hours: number): string {
  return new Date(Date.now() + hours * 3600 * 1000).toISOString()
}
function hoursAgo(hours: number): string {
  return new Date(Date.now() - hours * 3600 * 1000).toISOString()
}

const PAIRING_REQUESTS: PairingRequest[] = [
  // 8 待审核
  { id: 'pr-001', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-001', external_user_name: '王晓明', status: 'pending', expires_at: expiresInHours(20), created_at: hoursAgo(4), approved_at: null },
  { id: 'pr-002', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-002', external_user_name: '李静', external_group_name: '法务-合规专项群', status: 'pending', expires_at: expiresInHours(8), created_at: hoursAgo(16), approved_at: null },
  { id: 'pr-003', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-003', external_user_name: 'Tom Chen', status: 'pending', expires_at: expiresInHours(2), created_at: hoursAgo(22), approved_at: null },
  { id: 'pr-004', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-004', external_user_name: '赵蓉', external_group_name: '财税咨询群', status: 'pending', expires_at: expiresInHours(18), created_at: hoursAgo(6), approved_at: null },
  { id: 'pr-005', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-005', external_user_name: '黄磊', status: 'pending', expires_at: expiresInHours(12), created_at: hoursAgo(12), approved_at: null },
  { id: 'pr-006', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-006', external_user_name: '周婷', external_group_name: 'IP 运营群', status: 'pending', expires_at: expiresInHours(15), created_at: hoursAgo(9), approved_at: null },
  { id: 'pr-007', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-007', external_user_name: 'Alice Wang', status: 'pending', expires_at: expiresInHours(6), created_at: hoursAgo(18), approved_at: null },
  { id: 'pr-008', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-008', external_user_name: '林伟', external_group_name: '海外销售小组', status: 'pending', expires_at: expiresInHours(23), created_at: hoursAgo(1), approved_at: null },
  // 12 已授权
  { id: 'pa-001', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-101', external_user_name: '陈俊', status: 'approved', expires_at: '', created_at: hoursAgo(72), approved_at: hoursAgo(70) },
  { id: 'pa-002', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-102', external_user_name: '吴敏', status: 'approved', expires_at: '', created_at: hoursAgo(120), approved_at: hoursAgo(119) },
  { id: 'pa-003', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-103', external_user_name: '何旭', external_group_name: '法务-审核群', status: 'approved', expires_at: '', created_at: hoursAgo(160), approved_at: hoursAgo(155) },
  { id: 'pa-004', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-104', external_user_name: 'Sara Liu', status: 'approved', expires_at: '', created_at: hoursAgo(200), approved_at: hoursAgo(196) },
  { id: 'pa-005', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-105', external_user_name: '张浩', status: 'approved', expires_at: '', created_at: hoursAgo(240), approved_at: hoursAgo(238) },
  { id: 'pa-006', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-106', external_user_name: '宋琳', external_group_name: '跨境电商运营', status: 'approved', expires_at: '', created_at: hoursAgo(310), approved_at: hoursAgo(305) },
  { id: 'pa-007', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-107', external_user_name: '刘洋', status: 'approved', expires_at: '', created_at: hoursAgo(380), approved_at: hoursAgo(375) },
  { id: 'pa-008', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-108', external_user_name: 'Kevin Zhao', status: 'approved', expires_at: '', created_at: hoursAgo(420), approved_at: hoursAgo(415) },
  { id: 'pa-009', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-109', external_user_name: '高云', status: 'approved', expires_at: '', created_at: hoursAgo(500), approved_at: hoursAgo(495) },
  { id: 'pa-010', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-110', external_user_name: '魏明', external_group_name: '财税合规群', status: 'approved', expires_at: '', created_at: hoursAgo(560), approved_at: hoursAgo(555) },
  { id: 'pa-011', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-111', external_user_name: 'Linda Sun', status: 'approved', expires_at: '', created_at: hoursAgo(620), approved_at: hoursAgo(615) },
  { id: 'pa-012', channel_id: 'imc-feishu', channel_type: 'feishu', channel_name: '飞书', external_user_id: 'fs-112', external_user_name: '冯伟', status: 'approved', expires_at: '', created_at: hoursAgo(700), approved_at: hoursAgo(695) },
]

// ----- Plugins (6 行业垂直包) -----
const PLUGINS: Plugin[] = [
  { id: 'pl-labor', name: 'labor-law-pack', display_name: '劳动法包', description: '劳动合同/工伤/裁员/竞业全套技能', status: 'enabled', publisher: '安心团队', skill_count: 12, icon: '👷' },
  { id: 'pl-ip', name: 'ip-pack', display_name: 'IP 包', description: '商标/专利/版权/反不正当竞争', status: 'enabled', publisher: '安心团队', skill_count: 9, icon: '🏷️' },
  { id: 'pl-foreign', name: 'foreign-law-pack', display_name: '涉外法包', description: '跨境合规/国际商事仲裁/外汇', status: 'disabled', publisher: '安心团队', skill_count: 8, icon: '🌐' },
  { id: 'pl-family', name: 'family-pack', display_name: '家事包', description: '婚姻/继承/未成年人保护', status: 'disabled', publisher: '安心团队', skill_count: 6, icon: '🏡' },
  { id: 'pl-cross-border', name: 'cross-border-ecom', display_name: '跨境电商包', description: 'VAT/Listing/海外政策/平台规则', status: 'disabled', publisher: '安心团队', skill_count: 10, icon: '🚢' },
  { id: 'pl-sales', name: 'sales-pack', display_name: '销售获客包', description: '陌拜/SOP/CRM 集成/转化追踪', status: 'enabled', publisher: '安心团队', skill_count: 7, icon: '🎯' },
]

// ============================================================================
// API 接口
// ============================================================================

export const scheduledTasksApi = {
  list(): Promise<ScheduledTask[]> { return delay([...SCHEDULED_TASKS]) },
  toggle(id: string, status: ScheduleStatus): Promise<ScheduledTask> {
    const t = SCHEDULED_TASKS.find((x) => x.id === id)
    if (!t) return Promise.reject(new Error('not found'))
    t.status = status
    return delay({ ...t }, 200)
  },
}

export const appAuthApi = {
  listProviders(): Promise<AppProvider[]> { return delay([...APP_PROVIDERS]) },
  listAuthorizations(): Promise<AppAuthorization[]> { return delay([...APP_AUTHORIZATIONS]) },
  startConnect(provider_id: string): Promise<{ authorize_url: string }> {
    return delay({ authorize_url: `https://mock-oauth.anxinagent.com/${provider_id}?state=mock` })
  },
  disconnect(id: string): Promise<void> {
    const i = APP_AUTHORIZATIONS.findIndex((a) => a.id === id)
    if (i >= 0) APP_AUTHORIZATIONS.splice(i, 1)
    return delay(undefined, 200)
  },
}

export const skillsApi = {
  list(): Promise<Skill[]> { return delay([...SKILLS]) },
  toggle(name: string, enabled: boolean): Promise<Skill> {
    const i = SKILLS.findIndex((s) => s.name === name)
    if (i < 0) return Promise.reject(new Error('not found'))
    SKILLS[i] = { ...SKILLS[i], enabled }
    return delay(SKILLS[i], 200)
  },
}

export const pluginsApi = {
  list(): Promise<Plugin[]> { return delay([...PLUGINS]) },
  toggle(id: string, enabled: boolean): Promise<Plugin> {
    const p = PLUGINS.find((x) => x.id === id)
    if (!p) return Promise.reject(new Error('not found'))
    p.status = enabled ? 'enabled' : 'disabled'
    return delay({ ...p }, 200)
  },
}

export const imChannelsApi = {
  list(): Promise<IMChannel[]> { return delay([...IM_CHANNELS]) },
  iconOf(t: IMChannelType): string { return IM_ICONS[t] },
}

export const pairingApi = {
  listPending(): Promise<PairingRequest[]> {
    return delay(PAIRING_REQUESTS.filter((r) => r.status === 'pending').map((r) => ({ ...r })))
  },
  listApproved(): Promise<PairingRequest[]> {
    return delay(PAIRING_REQUESTS.filter((r) => r.status === 'approved').map((r) => ({ ...r })))
  },
  approve(id: string): Promise<PairingRequest> {
    const r = PAIRING_REQUESTS.find((p) => p.id === id)
    if (!r) return Promise.reject(new Error('not found'))
    r.status = 'approved'
    r.approved_at = new Date().toISOString()
    return delay({ ...r }, 200)
  },
  reject(id: string): Promise<PairingRequest> {
    const r = PAIRING_REQUESTS.find((p) => p.id === id)
    if (!r) return Promise.reject(new Error('not found'))
    r.status = 'rejected'
    return delay({ ...r }, 200)
  },
  revoke(id: string): Promise<void> {
    const i = PAIRING_REQUESTS.findIndex((p) => p.id === id)
    if (i >= 0) PAIRING_REQUESTS[i].status = 'rejected'
    return delay(undefined, 200)
  },
}

// 域显示名（用于 SkillsPage 分组标题）
export const DOMAIN_LABELS: Record<SkillCategory, string> = {
  legal: '法律',
  tax_finance: '财税',
  operations: '运营',
  research: '调研',
  marketing: '营销',
  content: '内容',
  design: '设计',
  office: '办公',
  ecommerce: '电商',
  sales: '销售',
  intelligence: '情报',
  decision: '决策',
  system: '系统',
}

export const DOMAIN_ORDER: SkillCategory[] = [
  'legal', 'tax_finance', 'operations', 'research', 'marketing',
  'content', 'design', 'office', 'ecommerce', 'sales',
  'intelligence', 'decision', 'system',
]

export const APP_CATEGORY_LABELS: Record<AppCategory, string> = {
  office: '办公',
  office_storage: '云盘文档',
  crm: 'CRM',
  ecommerce: '电商',
  info_source: '情报源',
  design: '设计',
  compliance: '合规',
  finance: '财务',
}

export const APP_CATEGORY_ORDER: AppCategory[] = [
  'office', 'office_storage', 'crm', 'ecommerce', 'info_source', 'design', 'compliance', 'finance',
]
