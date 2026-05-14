// -*- coding: utf-8 -*-
/**
 * capabilities.mock — 移动端能力中心统一 Mock 数据 + 类型契约 (P17-D)
 *
 * 与前端 web 版 (frontend/src/lib/api/{skills,appAuthorizations,imChannels,imPairing}.ts)
 * 的类型 1:1 对齐。P17-A 真业务 API 完成后,这里的 mock 调用将被替换为真实 fetch。
 *
 * 用法:
 *   import {
 *     skillsApi, appAuthApi, imChannelsApi, pairingApi,
 *     scheduledTasksApi, pluginsApi,
 *     type Skill, type AppProvider, ...
 *   } from '@/lib/api/__mocks__/capabilities.mock'
 *
 * 所有 API 都返回 Promise + 模拟 ~300ms 延迟,以触发 RN 加载状态 UI。
 */

// ============================================================================
// 类型契约 (与 frontend/src/lib/api/* 对齐)
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

export type SkillType = 'tool' | 'workflow' | 'agent'

export interface Skill {
  name: string
  display_name: string
  description: string
  version: string
  category: SkillCategory
  type: SkillType
  author: string
  triggers: string[]
  personas: string[]
  requires_apps: string[]
  dependencies: string[]
  keywords: string[]
  enabled: boolean
  icon?: string
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

export type AppAuthorizationStatus =
  | 'connected'
  | 'expired'
  | 'revoked'
  | 'error'

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
  user_id: string
  provider_id: string
  status: AppAuthorizationStatus
  scopes: string[]
  connected_at: string
  last_refresh_at: string | null
  error_message: string | null
  account_label?: string
}

// ----- IM Channels -----
export type IMChannelType =
  | 'feishu'
  | 'wechat'
  | 'dingtalk'
  | 'telegram'
  | 'discord'
  | 'slack'

export type IMChannelStatus =
  | 'unconfigured'
  | 'connecting'
  | 'connected'
  | 'error'

export interface IMChannelStats {
  bound_users: number
  bound_groups: number
  pending_pairings: number
}

export interface IMChannel {
  id: string
  channel_type: IMChannelType
  name: string
  config: Record<string, unknown>
  enabled: boolean
  status: IMChannelStatus
  bound_agent_persona: string | null
  stats: IMChannelStats
  created_at: string
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
  external_user_avatar?: string
  external_group_name?: string
  status: PairingStatus
  expires_at: string
  created_at: string
  approved_at: string | null
  approved_by: string | null
  rejection_reason: string | null
}

// ----- Scheduled Tasks (沿用 P17-A 草拟契约) -----
export type ScheduleKind =
  | 'contract_expiry_alert'
  | 'case_status_daily'
  | 'sentiment_weekly'
  | 'compliance_monthly'

export type ScheduleStatus = 'active' | 'paused' | 'failed'

export interface ScheduledTask {
  id: string
  name: string
  kind: ScheduleKind
  cron: string
  cron_human: string
  status: ScheduleStatus
  last_run_at: string | null
  next_run_at: string
  last_run_ok: boolean | null
  agent_persona: string
}

// ----- Plugins -----
export type PluginSource = 'official' | 'private' | 'mcp'
export type PluginStatus = 'enabled' | 'disabled' | 'pending_review'

export interface Plugin {
  id: string
  name: string
  display_name: string
  source: PluginSource
  status: PluginStatus
  description: string
  publisher: string
  icon?: string
}

// ============================================================================
// Mock 数据
// ============================================================================

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms))
}

// ----- Scheduled Tasks (12 个,4 类预设) -----
const SCHEDULED_TASKS: ScheduledTask[] = [
  // 合同到期提醒 (4 个)
  {
    id: 'st-001',
    name: '采购合同 30 天到期提醒',
    kind: 'contract_expiry_alert',
    cron: '0 9 * * *',
    cron_human: '每天 09:00',
    status: 'active',
    last_run_at: '2026-04-29T01:00:00Z',
    next_run_at: '2026-04-30T01:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  {
    id: 'st-002',
    name: '租赁合同到期 60 天预警',
    kind: 'contract_expiry_alert',
    cron: '0 9 * * 1',
    cron_human: '每周一 09:00',
    status: 'active',
    last_run_at: '2026-04-28T01:00:00Z',
    next_run_at: '2026-05-05T01:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  {
    id: 'st-003',
    name: '保密协议 NDA 续签提示',
    kind: 'contract_expiry_alert',
    cron: '0 10 1 * *',
    cron_human: '每月 1 日 10:00',
    status: 'paused',
    last_run_at: '2026-04-01T02:00:00Z',
    next_run_at: '2026-05-01T02:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  {
    id: 'st-004',
    name: '供应商主合同年度续签',
    kind: 'contract_expiry_alert',
    cron: '0 10 1 1 *',
    cron_human: '每年 1 月 1 日 10:00',
    status: 'active',
    last_run_at: null,
    next_run_at: '2027-01-01T02:00:00Z',
    last_run_ok: null,
    agent_persona: 'legal',
  },
  // 案件状态日报 (3 个)
  {
    id: 'st-005',
    name: '诉讼案件每日进度日报',
    kind: 'case_status_daily',
    cron: '0 18 * * 1-5',
    cron_human: '工作日 18:00',
    status: 'active',
    last_run_at: '2026-04-28T10:00:00Z',
    next_run_at: '2026-04-29T10:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  {
    id: 'st-006',
    name: '仲裁案件每日跟进',
    kind: 'case_status_daily',
    cron: '0 18 * * *',
    cron_human: '每天 18:00',
    status: 'active',
    last_run_at: '2026-04-28T10:00:00Z',
    next_run_at: '2026-04-29T10:00:00Z',
    last_run_ok: false,
    agent_persona: 'legal',
  },
  {
    id: 'st-007',
    name: '执行案款回收周报',
    kind: 'case_status_daily',
    cron: '0 18 * * 5',
    cron_human: '每周五 18:00',
    status: 'paused',
    last_run_at: '2026-04-25T10:00:00Z',
    next_run_at: '2026-05-02T10:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  // 舆情周报 (3 个)
  {
    id: 'st-008',
    name: '品牌舆情周报',
    kind: 'sentiment_weekly',
    cron: '0 9 * * 1',
    cron_human: '每周一 09:00',
    status: 'active',
    last_run_at: '2026-04-22T01:00:00Z',
    next_run_at: '2026-05-05T01:00:00Z',
    last_run_ok: true,
    agent_persona: 'intelligence',
  },
  {
    id: 'st-009',
    name: '竞品动态周报',
    kind: 'sentiment_weekly',
    cron: '0 9 * * 1',
    cron_human: '每周一 09:00',
    status: 'active',
    last_run_at: '2026-04-22T01:00:00Z',
    next_run_at: '2026-05-05T01:00:00Z',
    last_run_ok: true,
    agent_persona: 'research',
  },
  {
    id: 'st-010',
    name: '行业政策每日扫描',
    kind: 'sentiment_weekly',
    cron: '0 8 * * *',
    cron_human: '每天 08:00',
    status: 'failed',
    last_run_at: '2026-04-29T00:00:00Z',
    next_run_at: '2026-04-30T00:00:00Z',
    last_run_ok: false,
    agent_persona: 'research',
  },
  // 月度合规巡检 (2 个)
  {
    id: 'st-011',
    name: '数据合规月度自查',
    kind: 'compliance_monthly',
    cron: '0 10 1 * *',
    cron_human: '每月 1 日 10:00',
    status: 'active',
    last_run_at: '2026-04-01T02:00:00Z',
    next_run_at: '2026-05-01T02:00:00Z',
    last_run_ok: true,
    agent_persona: 'legal',
  },
  {
    id: 'st-012',
    name: '财税申报月度提醒',
    kind: 'compliance_monthly',
    cron: '0 9 25 * *',
    cron_human: '每月 25 日 09:00',
    status: 'active',
    last_run_at: '2026-03-25T01:00:00Z',
    next_run_at: '2026-04-25T01:00:00Z',
    last_run_ok: true,
    agent_persona: 'tax_finance',
  },
]

// ----- App Providers (30 个,5 已连接) -----
const APP_PROVIDERS: AppProvider[] = [
  { provider_id: 'feishu', display_name: '飞书', description: '字节系协作 OA', category: 'office', icon_url: null, default_scopes: ['contact:user.id:read'] },
  { provider_id: 'dingtalk', display_name: '钉钉', description: '阿里系协作 OA', category: 'office', icon_url: null, default_scopes: ['Contact.User.Read'] },
  { provider_id: 'wecom', display_name: '企业微信', description: '腾讯系企业 IM', category: 'office', icon_url: null, default_scopes: ['snsapi_base'] },
  { provider_id: 'lark', display_name: 'Lark', description: '飞书海外版', category: 'office', icon_url: null, default_scopes: [] },
  { provider_id: 'slack', display_name: 'Slack', description: '海外团队 IM', category: 'office', icon_url: null, default_scopes: ['chat:read'] },

  { provider_id: 'notion', display_name: 'Notion', description: '团队知识库', category: 'office_storage', icon_url: null, default_scopes: ['read_content'] },
  { provider_id: 'feishu_doc', display_name: '飞书云文档', description: '在线文档', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'dingtalk_drive', display_name: '钉盘', description: '钉钉云盘', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'google_drive', display_name: 'Google Drive', description: '谷歌云盘', category: 'office_storage', icon_url: null, default_scopes: [] },
  { provider_id: 'onedrive', display_name: 'OneDrive', description: '微软云盘', category: 'office_storage', icon_url: null, default_scopes: [] },

  { provider_id: 'salesforce', display_name: 'Salesforce', description: '海外 CRM 标杆', category: 'crm', icon_url: null, default_scopes: ['api'] },
  { provider_id: 'hubspot', display_name: 'HubSpot', description: '集客营销 CRM', category: 'crm', icon_url: null, default_scopes: [] },
  { provider_id: 'fxiaoke', display_name: '纷享销客', description: '国内 SaaS CRM', category: 'crm', icon_url: null, default_scopes: [] },
  { provider_id: 'xiaoshouyi', display_name: '销售易', description: '国内 PaaS CRM', category: 'crm', icon_url: null, default_scopes: [] },

  { provider_id: 'shopify', display_name: 'Shopify', description: '跨境独立站', category: 'ecommerce', icon_url: null, default_scopes: ['read_orders'] },
  { provider_id: 'amazon_seller', display_name: 'Amazon Seller', description: '亚马逊卖家中心', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'taobao_open', display_name: '淘宝开放平台', description: '阿里电商', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'jd_open', display_name: '京东开放平台', description: '京东商家', category: 'ecommerce', icon_url: null, default_scopes: [] },
  { provider_id: 'douyin_open', display_name: '抖店', description: '抖音电商', category: 'ecommerce', icon_url: null, default_scopes: [] },

  { provider_id: 'qichacha', display_name: '企查查', description: '工商信息', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'tianyancha', display_name: '天眼查', description: '企业信用', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'wenshu', display_name: '裁判文书网', description: '司法文书', category: 'info_source', icon_url: null, default_scopes: [] },
  { provider_id: 'beidafabao', display_name: '北大法宝', description: '法规数据库', category: 'info_source', icon_url: null, default_scopes: [] },

  { provider_id: 'figma', display_name: 'Figma', description: 'UI 设计协作', category: 'design', icon_url: null, default_scopes: ['files:read'] },
  { provider_id: 'jianying', display_name: '剪映', description: '短视频创作', category: 'design', icon_url: null, default_scopes: [] },
  { provider_id: 'canva', display_name: 'Canva', description: '海报快速创作', category: 'design', icon_url: null, default_scopes: [] },

  { provider_id: 'compliance_gov', display_name: '国家企业信用信息系统', description: '官方信用查询', category: 'compliance', icon_url: null, default_scopes: [] },
  { provider_id: 'creditchina', display_name: '信用中国', description: '失信名单', category: 'compliance', icon_url: null, default_scopes: [] },

  { provider_id: 'kingdee', display_name: '金蝶云', description: 'ERP/财务', category: 'finance', icon_url: null, default_scopes: [] },
  { provider_id: 'yongyou', display_name: '用友 U8', description: 'ERP/财务', category: 'finance', icon_url: null, default_scopes: [] },
]

// 5 个已连接 (飞书、Notion、Salesforce、Figma、金蝶云)
const APP_AUTHORIZATIONS: AppAuthorization[] = [
  {
    id: 'auth-feishu-1',
    user_id: 'u-001',
    provider_id: 'feishu',
    status: 'connected',
    scopes: ['contact:user.id:read'],
    connected_at: '2026-04-10T03:22:00Z',
    last_refresh_at: '2026-04-28T03:22:00Z',
    error_message: null,
    account_label: 'wenyu@anxinagent.com',
  },
  {
    id: 'auth-notion-1',
    user_id: 'u-001',
    provider_id: 'notion',
    status: 'connected',
    scopes: ['read_content'],
    connected_at: '2026-04-12T09:00:00Z',
    last_refresh_at: '2026-04-26T09:00:00Z',
    error_message: null,
    account_label: 'workspace: 安心智能助手',
  },
  {
    id: 'auth-salesforce-1',
    user_id: 'u-001',
    provider_id: 'salesforce',
    status: 'expired',
    scopes: ['api'],
    connected_at: '2026-03-01T00:00:00Z',
    last_refresh_at: '2026-04-01T00:00:00Z',
    error_message: 'refresh_token expired',
    account_label: 'sales@anxin-agent.com',
  },
  {
    id: 'auth-figma-1',
    user_id: 'u-001',
    provider_id: 'figma',
    status: 'connected',
    scopes: ['files:read'],
    connected_at: '2026-04-20T05:00:00Z',
    last_refresh_at: '2026-04-27T05:00:00Z',
    error_message: null,
    account_label: 'designer@anxin-agent.com',
  },
  {
    id: 'auth-kingdee-1',
    user_id: 'u-001',
    provider_id: 'kingdee',
    status: 'connected',
    scopes: [],
    connected_at: '2026-04-22T08:00:00Z',
    last_refresh_at: '2026-04-28T08:00:00Z',
    error_message: null,
    account_label: '财务部账套-001',
  },
]

// ----- Skills (50 个,跨 13 域) -----
function buildSkill(
  name: string,
  display_name: string,
  category: SkillCategory,
  enabled: boolean,
  description: string,
  triggers: string[] = [],
  requires_apps: string[] = [],
): Skill {
  return {
    name,
    display_name,
    description,
    version: '1.0.0',
    category,
    type: 'tool',
    author: 'Anxin Team',
    triggers,
    personas: [category],
    requires_apps,
    dependencies: [],
    keywords: triggers,
    enabled,
  }
}

const SKILLS: Skill[] = [
  // legal (6)
  buildSkill('legal/contract-review', '合同审查', 'legal', true, '识别合同风险条款', ['合同审查', '合同风险']),
  buildSkill('legal/clause-extract', '条款提取', 'legal', true, '从合同中抽取关键条款'),
  buildSkill('legal/case-search', '案例检索', 'legal', true, '裁判文书检索', ['类案检索'], ['wenshu']),
  buildSkill('legal/regulation-lookup', '法规查询', 'legal', true, '法规库精确检索', [], ['beidafabao']),
  buildSkill('legal/litigation-strategy', '诉讼策略', 'legal', false, '辅助诉讼方案设计'),
  buildSkill('legal/compliance-check', '合规检查', 'legal', true, '业务合规扫描'),
  // tax_finance (4)
  buildSkill('tax/invoice-recognize', '发票识别', 'tax_finance', true, 'OCR 识别发票要素'),
  buildSkill('tax/tax-calc', '税额测算', 'tax_finance', true, '增值税/所得税计算'),
  buildSkill('finance/cash-flow', '现金流分析', 'tax_finance', false, '现金流预测', [], ['kingdee']),
  buildSkill('finance/budget-plan', '预算编制', 'tax_finance', false, '年度预算辅助'),
  // operations (3)
  buildSkill('ops/sop-generate', 'SOP 生成', 'operations', true, '业务流程文档化'),
  buildSkill('ops/risk-matrix', '风险矩阵', 'operations', false, '运营风险评估'),
  buildSkill('ops/process-mining', '流程挖掘', 'operations', false, '从日志推导流程'),
  // research (4)
  buildSkill('research/market-scan', '市场扫描', 'research', true, '行业研究报告生成'),
  buildSkill('research/competitor', '竞品分析', 'research', true, '竞争对手画像'),
  buildSkill('research/survey', '问卷设计', 'research', false, '调研问卷生成'),
  buildSkill('research/data-clean', '数据清洗', 'research', false, '调研数据预处理'),
  // marketing (4)
  buildSkill('marketing/lead-score', '线索评分', 'marketing', true, '销售线索打分'),
  buildSkill('marketing/email-campaign', '邮件营销', 'marketing', false, 'EDM 文案生成'),
  buildSkill('marketing/social-post', '社媒发布', 'marketing', false, '多平台同步'),
  buildSkill('marketing/seo-keyword', 'SEO 关键词', 'marketing', false, '关键词研究'),
  // content (4)
  buildSkill('content/article-write', '文章撰写', 'content', true, '长文创作'),
  buildSkill('content/short-video', '短视频脚本', 'content', false, '抖音/小红书脚本'),
  buildSkill('content/translate', '多语翻译', 'content', true, '中英日韩互译'),
  buildSkill('content/proofread', '校对润色', 'content', true, '错别字/语法'),
  // design (3)
  buildSkill('design/poster-gen', '海报生成', 'design', false, 'AI 海报', [], ['canva']),
  buildSkill('design/figma-handoff', 'Figma 切图', 'design', false, '设计稿标注', [], ['figma']),
  buildSkill('design/icon-design', '图标设计', 'design', false, 'SVG 图标生成'),
  // office (5)
  buildSkill('office/docx', 'Word 文档', 'office', true, '生成 docx'),
  buildSkill('office/xlsx', 'Excel 表格', 'office', true, '生成 xlsx + 公式'),
  buildSkill('office/pptx', 'PPT 幻灯片', 'office', true, '生成 pptx'),
  buildSkill('office/pdf', 'PDF 处理', 'office', true, '解析/合并/拆分'),
  buildSkill('office/email-draft', '邮件起草', 'office', false, '商务邮件'),
  // ecommerce (4)
  buildSkill('ecom/listing-optimize', 'Listing 优化', 'ecommerce', false, 'Amazon Listing', [], ['amazon_seller']),
  buildSkill('ecom/review-analyze', '评价分析', 'ecommerce', false, '差评归因', [], ['shopify']),
  buildSkill('ecom/keyword-mining', '选品关键词', 'ecommerce', false, '蓝海词挖掘'),
  buildSkill('ecom/cross-border-tax', '跨境税务', 'ecommerce', false, 'VAT/IOSS 计算'),
  // sales (3)
  buildSkill('sales/cold-call-script', '电销话术', 'sales', false, '陌拜话术生成'),
  buildSkill('sales/proposal-gen', '商务提案', 'sales', true, '客户方案书'),
  buildSkill('sales/quote-calc', '报价测算', 'sales', false, '阶梯报价'),
  // intelligence (4)
  buildSkill('intel/news-monitor', '新闻监控', 'intelligence', true, '实时舆情'),
  buildSkill('intel/risk-radar', '风险雷达', 'intelligence', true, '黑天鹅预警'),
  buildSkill('intel/competitor-watch', '竞争情报', 'intelligence', false, '友商动态'),
  buildSkill('intel/policy-track', '政策跟踪', 'intelligence', true, '法规政策更新'),
  // decision (3)
  buildSkill('decision/swot', 'SWOT 分析', 'decision', false, '战略框架'),
  buildSkill('decision/scenario', '情景规划', 'decision', false, '多场景推演'),
  buildSkill('decision/decision-tree', '决策树', 'decision', false, '量化决策'),
  // system (3)
  buildSkill('system/log-search', '日志检索', 'system', true, '内部 trace'),
  buildSkill('system/api-call', 'API 调用', 'system', true, '通用 HTTP'),
  buildSkill('system/cron-edit', '定时编排', 'system', true, '编辑 cron'),
]

// ----- IM Channels (5 平台) -----
const IM_CHANNELS: IMChannel[] = [
  {
    id: 'imc-feishu',
    channel_type: 'feishu',
    name: '安心智能助手团队飞书',
    config: { app_id: 'cli_a***', verification_token: '***' },
    enabled: true,
    status: 'connected',
    bound_agent_persona: 'legal',
    stats: { bound_users: 18, bound_groups: 4, pending_pairings: 3 },
    created_at: '2026-04-15T08:00:00Z',
  },
  {
    id: 'imc-wechat',
    channel_type: 'wechat',
    name: '微信(占位)',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: '2026-04-15T08:00:00Z',
  },
  {
    id: 'imc-dingtalk',
    channel_type: 'dingtalk',
    name: '钉钉(占位)',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: '2026-04-15T08:00:00Z',
  },
  {
    id: 'imc-telegram',
    channel_type: 'telegram',
    name: 'Telegram(占位)',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: '2026-04-15T08:00:00Z',
  },
  {
    id: 'imc-discord',
    channel_type: 'discord',
    name: 'Discord(占位)',
    config: {},
    enabled: false,
    status: 'unconfigured',
    bound_agent_persona: null,
    stats: { bound_users: 0, bound_groups: 0, pending_pairings: 0 },
    created_at: '2026-04-15T08:00:00Z',
  },
]

// ----- Pairing Requests (3 待审批) -----
function expiresInHours(hours: number): string {
  return new Date(Date.now() + hours * 3600 * 1000).toISOString()
}

const PAIRING_REQUESTS: PairingRequest[] = [
  {
    id: 'pr-001',
    channel_id: 'imc-feishu',
    channel_type: 'feishu',
    channel_name: '安心智能助手团队飞书',
    external_user_id: 'fs-uu-001',
    external_user_name: '王晓明',
    external_user_avatar: undefined,
    status: 'pending',
    expires_at: expiresInHours(20),
    created_at: new Date(Date.now() - 4 * 3600 * 1000).toISOString(),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
  {
    id: 'pr-002',
    channel_id: 'imc-feishu',
    channel_type: 'feishu',
    channel_name: '安心智能助手团队飞书',
    external_user_id: 'fs-uu-002',
    external_user_name: '李静',
    external_group_name: '法务-合规专项群',
    status: 'pending',
    expires_at: expiresInHours(8),
    created_at: new Date(Date.now() - 16 * 3600 * 1000).toISOString(),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
  {
    id: 'pr-003',
    channel_id: 'imc-feishu',
    channel_type: 'feishu',
    channel_name: '安心智能助手团队飞书',
    external_user_id: 'fs-uu-003',
    external_user_name: 'Tom Chen',
    status: 'pending',
    expires_at: expiresInHours(2),
    created_at: new Date(Date.now() - 22 * 3600 * 1000).toISOString(),
    approved_at: null,
    approved_by: null,
    rejection_reason: null,
  },
]

// ----- Plugins (8 个) -----
const PLUGINS: Plugin[] = [
  { id: 'pl-001', name: 'beidafabao', display_name: '北大法宝', source: 'official', status: 'enabled', description: '法规与案例数据库', publisher: '北大英华' },
  { id: 'pl-002', name: 'westlaw', display_name: 'Westlaw', source: 'official', status: 'disabled', description: '海外法规数据库', publisher: 'Thomson Reuters' },
  { id: 'pl-003', name: 'qichacha', display_name: '企查查', source: 'official', status: 'enabled', description: '工商信息查询', publisher: '企查查科技' },
  { id: 'pl-004', name: 'gov-credit', display_name: '国家企业信用信息系统', source: 'official', status: 'enabled', description: '官方信用查询', publisher: '市监总局' },
  { id: 'pl-005', name: 'mcp-filesystem', display_name: 'MCP File System', source: 'mcp', status: 'enabled', description: '本地文件系统访问', publisher: 'Anthropic' },
  { id: 'pl-006', name: 'mcp-postgres', display_name: 'MCP Postgres', source: 'mcp', status: 'disabled', description: '数据库查询', publisher: 'Anthropic' },
  { id: 'pl-007', name: 'private-erp', display_name: '内部 ERP 接入', source: 'private', status: 'pending_review', description: '通过 Webhook 接入企业 ERP', publisher: '研发部' },
  { id: 'pl-008', name: 'private-hr', display_name: '内部 HR 系统', source: 'private', status: 'enabled', description: '员工档案查询', publisher: '研发部' },
]

// ============================================================================
// API 接口 (mimic frontend skillsApi / appAuthApi / imChannelsApi / pairingApi)
// ============================================================================

export const skillsApi = {
  list(): Promise<Skill[]> {
    return delay([...SKILLS])
  },
  toggle(name: string, enabled: boolean): Promise<Skill> {
    const idx = SKILLS.findIndex((s) => s.name === name)
    if (idx >= 0) {
      SKILLS[idx] = { ...SKILLS[idx], enabled }
      return delay(SKILLS[idx], 250)
    }
    return Promise.reject(new Error(`skill not found: ${name}`))
  },
}

export const appAuthApi = {
  listProviders(): Promise<AppProvider[]> {
    return delay([...APP_PROVIDERS])
  },
  listAuthorizations(): Promise<AppAuthorization[]> {
    return delay([...APP_AUTHORIZATIONS])
  },
  startConnect(providerId: string): Promise<{ authorize_url: string; state: string }> {
    return delay({
      authorize_url: `https://mock-oauth.anxinagent.com/${providerId}?state=mock-state`,
      state: 'mock-state',
    })
  },
  // mock OAuth callback —— 1.5s 后落表
  completeConnect(providerId: string): Promise<AppAuthorization> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const existing = APP_AUTHORIZATIONS.find((a) => a.provider_id === providerId)
        if (existing) {
          existing.status = 'connected'
          existing.error_message = null
          resolve(existing)
          return
        }
        const fresh: AppAuthorization = {
          id: `auth-${providerId}-${Date.now()}`,
          user_id: 'u-001',
          provider_id: providerId,
          status: 'connected',
          scopes: APP_PROVIDERS.find((p) => p.provider_id === providerId)?.default_scopes ?? [],
          connected_at: new Date().toISOString(),
          last_refresh_at: new Date().toISOString(),
          error_message: null,
          account_label: '已连接账户',
        }
        APP_AUTHORIZATIONS.push(fresh)
        resolve(fresh)
      }, 1500)
    })
  },
  disconnect(id: string): Promise<void> {
    const idx = APP_AUTHORIZATIONS.findIndex((a) => a.id === id)
    if (idx >= 0) APP_AUTHORIZATIONS.splice(idx, 1)
    return delay(undefined, 200)
  },
}

export const imChannelsApi = {
  list(): Promise<IMChannel[]> {
    return delay([...IM_CHANNELS])
  },
}

export const pairingApi = {
  listPending(): Promise<PairingRequest[]> {
    return delay(PAIRING_REQUESTS.filter((r) => r.status === 'pending').map((r) => ({ ...r })))
  },
  approve(id: string): Promise<PairingRequest> {
    const r = PAIRING_REQUESTS.find((p) => p.id === id)
    if (!r) return Promise.reject(new Error('not found'))
    r.status = 'approved'
    r.approved_at = new Date().toISOString()
    r.approved_by = 'u-001'
    return delay({ ...r }, 250)
  },
  reject(id: string, reason: string): Promise<PairingRequest> {
    const r = PAIRING_REQUESTS.find((p) => p.id === id)
    if (!r) return Promise.reject(new Error('not found'))
    r.status = 'rejected'
    r.rejection_reason = reason
    return delay({ ...r }, 250)
  },
}

export const scheduledTasksApi = {
  list(): Promise<ScheduledTask[]> {
    return delay([...SCHEDULED_TASKS])
  },
  toggle(id: string, status: ScheduleStatus): Promise<ScheduledTask> {
    const t = SCHEDULED_TASKS.find((x) => x.id === id)
    if (!t) return Promise.reject(new Error('not found'))
    t.status = status
    return delay({ ...t }, 200)
  },
}

export const pluginsApi = {
  list(): Promise<Plugin[]> {
    return delay([...PLUGINS])
  },
  toggle(id: string, enabled: boolean): Promise<Plugin> {
    const p = PLUGINS.find((x) => x.id === id)
    if (!p) return Promise.reject(new Error('not found'))
    p.status = enabled ? 'enabled' : 'disabled'
    return delay({ ...p }, 200)
  },
}
