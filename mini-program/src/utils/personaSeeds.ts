// -*- coding: utf-8 -*-
/**
 * 10 personas 静态种子（与 frontend personas.mock.ts 对齐）
 *
 * Home 首屏在网络空闲 / 未登录时即可渲染，避免空白。
 * 登录后由 personasApi.list() 拉真数据替换。
 */

import type { Persona, PersonaDomain } from '../types/persona'

export interface SeededPersona extends Persona {
  domain: PersonaDomain
  is_implemented: boolean
}

export const PERSONA_SEEDS: SeededPersona[] = [
  {
    persona_id: 'anxin_assistant',
    display_name: '安心助理',
    emoji: '🤖',
    description: '通用入口 + 任务编排，不知道找谁就找它',
    domain: '综合协调',
    is_implemented: false,
    capabilities: ['意图识别', '任务拆解', '多 agent 协商'],
    backed_by_skills: ['system/intent-router', 'system/task-graph'],
    supported_apps: ['feishu', 'wecom', '桌面通知'],
    enabled: true,
  },
  {
    persona_id: 'legal_advisor',
    display_name: '法律顾问',
    emoji: '⚖️',
    description: '你的随身法律大脑，问法条、判例、风险',
    domain: '合规经营',
    is_implemented: false,
    capabilities: ['法规检索', '判例分析', '合规自检'],
    backed_by_skills: ['legal/regulation-search', 'legal/case-mining'],
    supported_apps: ['anxin', 'wecom'],
    enabled: true,
  },
  {
    persona_id: 'contract_steward',
    display_name: '合同管家',
    emoji: '📜',
    description: '起草、审查、协商、归档全流程',
    domain: '合规经营',
    is_implemented: false,
    capabilities: ['合同起草', '风险审查', '版本对比'],
    backed_by_skills: ['legal/contract-draft', 'legal/contract-review'],
    supported_apps: ['anxin', 'wecom', 'feishu'],
    enabled: true,
  },
  {
    persona_id: 'due_diligence_expert',
    display_name: '尽调专家',
    emoji: '🔍',
    description: '工商 / 司法 / 经营 360° 尽调',
    domain: '合规经营',
    is_implemented: false,
    capabilities: ['企业画像', '风险扫描', '股权图谱'],
    backed_by_skills: ['legal/dd-firm-search', 'legal/dd-risk-scan'],
    supported_apps: ['anxin'],
    enabled: true,
  },
  {
    persona_id: 'tax_finance_advisor',
    display_name: '财税顾问',
    emoji: '💰',
    description: '税筹、做账、票据、稽查应对',
    domain: '合规经营',
    is_implemented: false,
    capabilities: ['税收筹划', '票据校验', '财报分析'],
    backed_by_skills: ['finance/tax-plan', 'finance/invoice-check'],
    supported_apps: ['anxin', 'wecom'],
    enabled: true,
  },
  {
    persona_id: 'operations_manager',
    display_name: '流程管家',
    emoji: '📋',
    description: 'OKR、SOP、会议纪要、流程优化',
    domain: '综合协调',
    is_implemented: true,
    capabilities: ['OKR 推进', 'SOP 设计', '会议纪要'],
    backed_by_skills: ['ops/okr', 'ops/sop', 'ops/meeting'],
    supported_apps: ['feishu', 'dingtalk', 'wecom'],
    enabled: true,
  },
  {
    persona_id: 'market_researcher',
    display_name: '市场研究员',
    emoji: '📊',
    description: '行业、竞品、用户、政策深度调研',
    domain: '增长获客',
    is_implemented: true,
    capabilities: ['行业研究', '竞品分析', '调研报告'],
    backed_by_skills: ['research/industry', 'research/competitor'],
    supported_apps: ['anxin', 'feishu'],
    enabled: true,
  },
  {
    persona_id: 'lead_hunter',
    display_name: '获客猎手',
    emoji: '🎯',
    description: '客户线索挖掘 / 触达 / 跟进',
    domain: '增长获客',
    is_implemented: true,
    capabilities: ['线索挖掘', '画像分析', '触达节奏'],
    backed_by_skills: ['sales/lead-mining', 'sales/outreach'],
    supported_apps: ['wecom', 'dingtalk'],
    enabled: true,
  },
  {
    persona_id: 'content_director',
    display_name: '内容总监',
    emoji: '✍️',
    description: '公众号 / 视频号 / 小红书全平台内容生产',
    domain: '增长获客',
    is_implemented: true,
    capabilities: ['爆款选题', '多平台改写', '日历排期'],
    backed_by_skills: ['content/topic', 'content/multiplatform'],
    supported_apps: ['anxin'],
    enabled: true,
  },
  {
    persona_id: 'ecommerce_assistant',
    display_name: '跨境电商助手',
    emoji: '🌍',
    description: 'Shopify / Amazon / TikTok 出海运营',
    domain: '出海跨境',
    is_implemented: true,
    capabilities: ['选品研究', '广告投放', '物流合规'],
    backed_by_skills: ['ecommerce/listing', 'ecommerce/ads'],
    supported_apps: ['anxin'],
    enabled: true,
  },
]

/** 4 个业务域 → 默认查询入口 */
export const DOMAIN_LIST: Array<{
  domain: PersonaDomain
  emoji: string
  description: string
}> = [
  { domain: '合规经营', emoji: '⚖️', description: '法/税/财/合同' },
  { domain: '出海跨境', emoji: '🌍', description: '跨境电商运营' },
  { domain: '增长获客', emoji: '🎯', description: '调研/获客/内容' },
  { domain: '综合协调', emoji: '🤖', description: '助理/流程' },
]

/** Home 推荐场景 chips（点了直接发起 chat） */
export const RECOMMENDED_PROMPTS: Array<{
  text: string
  persona_id: string
}> = [
  { text: '调研一下竞品', persona_id: 'market_researcher' },
  { text: '起草采购合同', persona_id: 'contract_steward' },
  { text: '本月 OKR 进度', persona_id: 'operations_manager' },
  { text: '挖掘新客户线索', persona_id: 'lead_hunter' },
  { text: '改写公众号文章', persona_id: 'content_director' },
  { text: '查这家公司风险', persona_id: 'due_diligence_expert' },
]
