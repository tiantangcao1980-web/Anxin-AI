/**
 * Personas Mock 适配层（V3 P8-C）
 *
 * 在 VITE_PERSONAS_MOCK=true 时启用，覆盖后端 personas 通用 endpoint。
 *
 * 内置 10 个 user-facing persona，与 docs/v3/AGENT_PERSONAS.md 对齐：
 *   1. 🤖 安心助理       (anxin_assistant)        — 法务规划中
 *   2. ⚖️ 法律顾问       (legal_advisor)          — 法务规划中
 *   3. 📜 合同管家       (contract_steward)       — 法务规划中
 *   4. 🔍 尽调专家       (due_diligence_expert)   — 法务规划中
 *   5. 💰 财税顾问       (tax_finance_advisor)    — 法务规划中
 *   6. 📋 流程管家       (operations_manager)     — P7-A ✅
 *   7. 📊 市场研究员     (market_researcher)      — P7-B ✅
 *   8. 🎯 获客猎手       (lead_hunter)            — P7-C ✅
 *   9. ✍️ 内容总监       (content_director)       — P7-D ✅
 *  10. 🌍 跨境电商助手   (ecommerce_assistant)    — P7-E ✅
 */

import type {
  ChatRequest,
  ChatResponse,
  Persona,
  PersonaDetail,
} from '../personas'

// ===== 工具函数 =====

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

interface PersonaSeed extends Persona {
  /** 详情页 system prompt 摘要 */
  system_prompt_excerpt?: string
  /** 后端调用的 specialized agents */
  backed_by_agents?: string[]
}

function seed(p: PersonaSeed): PersonaSeed {
  return { enabled: true, ...p }
}

// ===== 10 persona 种子 =====

const seeds: PersonaSeed[] = [
  // ----- 1. 🤖 安心助理 -----
  seed({
    persona_id: 'anxin_assistant',
    display_name: '安心助理',
    emoji: '🤖',
    description: '通用入口 + 任务编排，不知道找谁就找它',
    domain: '综合协调',
    is_implemented: false,
    capabilities: [
      '意图识别（自然语言路由到正确 persona）',
      '任务拆解（复杂请求 → 多 persona 协作 DAG）',
      '多 agent 协商（分歧时 consensus_agent 投票）',
      '统一收件箱（聚合所有 persona 进度 / 结果）',
      '上下文续接（跨 persona 共享会话）',
    ],
    backed_by_skills: [
      'system/intent-router',
      'system/task-graph',
      'system/consensus',
      'intelligence/cross-search',
      'decision/multi-agent-vote',
    ],
    backed_by_agents: ['coordinator', 'workforce', 'requirement_analyst', 'consensus_agent'],
    supported_apps: ['feishu', 'dingtalk', 'wecom', '桌面通知中心', '移动推送'],
    system_prompt_excerpt:
      '你是安心智能助手的总管入口。你不直接做事，你听用户说一句话后，把它路由到正确的 persona 或拆成多 persona 协作图……',
  }),
  // ----- 2. ⚖️ 法律顾问 -----
  seed({
    persona_id: 'legal_advisor',
    display_name: '法律顾问',
    emoji: '⚖️',
    description: '你的随身法律大脑，问法条、判例、风险，全靠我',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      '法规检索（北大法宝 / 威科 / 国务院政策库，带源链接）',
      '法律咨询（基于业务上下文给可执行建议）',
      '风险评估（5 级风险分级 + 量化评分）',
      '法规监测（自动追踪相关法规变更并推送）',
      '判例检索（33,102 条文书库 + 类案推送）',
    ],
    backed_by_skills: [
      'legal/regulation-search',
      'legal/case-search',
      'legal/risk-grade',
      'legal/compliance-check',
      'intelligence/citation-trace',
      'research/deeptutor-mode',
    ],
    backed_by_agents: [
      'legal_advisor',
      'legal_researcher',
      'risk_assessor',
      'compliance_officer',
      'regulatory_monitor',
      'litigation_strategist',
    ],
    supported_apps: ['北大法宝', '威科先行', '国务院政策库', 'feishu', 'dingtalk'],
  }),
  // ----- 3. 📜 合同管家 -----
  seed({
    persona_id: 'contract_steward',
    display_name: '合同管家',
    emoji: '📜',
    description: '从起草、审查、谈判、签署到归档，每一份合同我帮你盯',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      '合同起草（200+ 模板库 + 智能填空 + 行业定制）',
      '合同审查（逐条审查 + 风险标注 + 修改建议）',
      '合同谈判（让步空间分析 + 替代条款建议）',
      '合同管理（到期提醒 / 续约 / 归档 / 检索）',
      '合规校验（内部审批流 + 法务红线）',
    ],
    backed_by_skills: [
      'legal/contract-draft',
      'legal/contract-review',
      'legal/clause-extract',
      'legal/redline-suggest',
      'office/docx-track-changes',
      'legal/template-match',
    ],
    backed_by_agents: [
      'contract_reviewer',
      'contract_steward',
      'contract_investigator',
      'review_checker',
      'document_drafter',
      'template_librarian',
    ],
    supported_apps: ['法大大', 'e签宝', 'feishu_doc', 'notion', 'outlook'],
  }),
  // ----- 4. 🔍 尽调专家 -----
  seed({
    persona_id: 'due_diligence_expert',
    display_name: '尽调专家',
    emoji: '🔍',
    description: '见客户 / 投资 / 收购前，先让我看看对方家底',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      '工商尽调（股权 / 实控人 / 关联 / 变更）',
      '法律尽调（诉讼 / 仲裁 / 行政处罚 / 失信）',
      '财务尽调（年报 / 经营异常 / 税务等级）',
      '舆情尽调（新闻 / 社媒 / 维权 / 监管处罚）',
      '专项报告（投资级 / 客户级 / 供应商级 PDF 导出）',
    ],
    backed_by_skills: [
      'intelligence/company-profile',
      'intelligence/litigation-search',
      'intelligence/news-aggregate',
      'intelligence/sentiment-score',
      'research/deeptutor-mode',
      'office/pdf-report-gen',
    ],
    backed_by_agents: [
      'due_diligence',
      'evidence_analyst',
      'sentiment_agent',
      'legal_researcher',
      'risk_assessor',
      'contract_investigator',
    ],
    supported_apps: ['企查查', '天眼查', '启信宝', '中国裁判文书网', '信用中国', 'linkedin'],
  }),
  // ----- 5. 💰 财税顾问 -----
  seed({
    persona_id: 'tax_finance_advisor',
    display_name: '财税顾问',
    emoji: '💰',
    description: '节税合规 + 财务健康，老板和会计的最佳搭档',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      '税务合规（增值税 / 企业所得税 / 个税申报检查）',
      '节税筹划（合规节税方案 + 风险等级）',
      '法律计算（经济补偿金 / 加班费 / 工伤赔偿 / 利息）',
      '财务分析（现金流 / 资产负债 / 利润 关键指标）',
      '稽查预警（高频稽查指标自检）',
    ],
    backed_by_skills: [
      'tax_finance/tax-plan',
      'tax_finance/tax-check',
      'tax_finance/legal-calc',
      'tax_finance/financial-analysis',
      'tax_finance/audit-warning',
    ],
    backed_by_agents: ['tax_compliance', 'legal_calculator', 'compliance_officer'],
    supported_apps: ['金蝶', '用友', 'xero', 'quickbooks', '国家税务总局'],
  }),
  // ----- 6. 📋 流程管家 (P7-A) -----
  seed({
    persona_id: 'operations_manager',
    display_name: '流程管家',
    emoji: '📋',
    description: '公司过程管理小助手，OKR 到周报都帮你梳',
    domain: '合规经营',
    is_implemented: true,
    capabilities: [
      'OKR 管理（制定 / 拆解 / 跟进 / 复盘）',
      '审批流程（报销 / 请假 / 采购 智能审批）',
      '会议纪要（录音 → 转写 → 提炼 → 分发待办）',
      '周报 / 月报（OKR + 飞书 + 日历 自动聚合）',
      '日程协调（多人会议时间协调 + 议程起草）',
    ],
    backed_by_skills: [
      'operations/okr-plan',
      'operations/approval-flow',
      'operations/meeting-minutes',
      'operations/weekly-report',
      'office/calendar-coordinate',
      'office/transcribe',
    ],
    backed_by_agents: ['requirement_analyst', 'coordinator', 'okr_agent', 'meeting_minutes_agent'],
    supported_apps: ['feishu', 'dingtalk', 'wecom', 'notion', 'google_calendar', 'outlook'],
  }),
  // ----- 7. 📊 市场研究员 (P7-B) -----
  seed({
    persona_id: 'market_researcher',
    display_name: '市场研究员',
    emoji: '📊',
    description: '想了解一个行业 / 一个对手 / 一个趋势，我做你的研究员',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      '行业研究（DeepTutor 模式深度阅读多份报告）',
      '竞品监控（定时抓取竞品动态 + 异动报警）',
      '趋势挖掘（从舆情 / 社媒 / 招聘 信号识别趋势）',
      'PDF 深读（RAG-Anything + MinerU 解析图表 / 公式）',
      '客户洞察（客户公司画像 + 决策链分析）',
    ],
    backed_by_skills: [
      'research/deeptutor-mode',
      'research/multi-source-synthesize',
      'research/citation-trace',
      'research/competitive-monitor',
      'intelligence/news-aggregate',
      'intelligence/social-listen',
    ],
    backed_by_agents: ['legal_researcher', 'evidence_analyst', 'sentiment_agent', 'market_agent'],
    supported_apps: ['reddit', 'x', 'linkedin', 'youtube', 'tiktok', 'headlessx'],
  }),
  // ----- 8. 🎯 获客猎手 (P7-C) -----
  seed({
    persona_id: 'lead_hunter',
    display_name: '获客猎手',
    emoji: '🎯',
    description: '把陌生人变成客户，把客户变成朋友',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      '线索挖掘（基于行业 / 招聘 / 工商信号识别潜客）',
      'Vibe Selling（基于客户语境调整销售话术）',
      '跟进策略（基于客户阶段推送下一步行动）',
      '投放决策（AI-Trader 范式，多 agent 协商出价）',
      '客户分层（RFM + 行为评分 + 优先级）',
    ],
    backed_by_skills: [
      'sales/lead-mining',
      'sales/vibe-selling',
      'sales/follow-up',
      'sales/quotation-draft',
      'decision/multi-agent-vote',
      'marketing/ad-optimize',
      'marketing/audience-target',
    ],
    backed_by_agents: ['sentiment_agent', 'consensus_agent', 'lead_agent', 'vibe_seller'],
    supported_apps: ['salesforce', 'hubspot', 'zoho', 'pipedrive', 'feishu', 'wecom', 'linkedin', '巨量引擎', '腾讯广告'],
  }),
  // ----- 9. ✍️ 内容总监 (P7-D) -----
  seed({
    persona_id: 'content_director',
    display_name: '内容总监',
    emoji: '✍️',
    description: '从一句话灵感到一支成片，全链路内容生产',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      '图文创作（公众号 / 知乎 / 小红书 / 头条 多平台适配）',
      '视觉设计（海报 / 封面 / Banner via canvas-design）',
      '短视频脚本 + 成片（脚本 → 分镜 → Remotion 自动剪辑）',
      '落地页生成（web-artifacts-builder 一键生成产品页）',
      '文案矩阵（标题 / 钩子 / 卖点 多版本 A/B）',
    ],
    backed_by_skills: [
      'content/article-write',
      'content/headline-generate',
      'content/seo',
      'design/poster',
      'design/canvas-design',
      'design/web-artifacts-builder',
      'content/video-script',
      'content/remotion-render',
    ],
    backed_by_agents: ['content_agent', 'design_agent', 'video_agent', 'evidence_analyst'],
    supported_apps: ['canvas-design', 'web-artifacts-builder', 'figma', 'canva', 'higgsfield', 'remotion', '微信公众号', '抖音', '视频号'],
  }),
  // ----- 10. 🌍 跨境电商助手 (P7-E) -----
  seed({
    persona_id: 'ecommerce_assistant',
    display_name: '跨境电商助手',
    emoji: '🌍',
    description: '从想做出海到第一笔订单，每个坑我帮你避',
    domain: '出海跨境',
    is_implemented: true,
    capabilities: [
      '选品分析（跨平台数据 + 社媒信号 + 趋势识别）',
      '独立站搭建（Shopify 主题定制 / 商品页 / 落地页）',
      '平台接入（Amazon / Shopee / TikTok Shop / 1688）',
      '物流 + 收款（跨境物流方案 + Stripe / PayPal 接入）',
      '海外推广（Google / Meta / TikTok 广告策略）',
      '出海合规（GDPR / CCPA / VAT / 商标 / 海关）',
    ],
    backed_by_skills: [
      'ecommerce/product-selection',
      'ecommerce/keyword-research',
      'ecommerce/store-setup',
      'ecommerce/listing-optimize',
      'ecommerce/oversea-compliance',
      'ecommerce/logistics-plan',
      'marketing/ad-optimize',
      'decision/multi-agent-vote',
    ],
    backed_by_agents: [
      'ecommerce_agent',
      'selection_agent',
      'oversea_compliance_agent',
      'legal_researcher',
      'risk_assessor',
      'tax_compliance',
    ],
    supported_apps: [
      'shopify',
      'shopee',
      'tiktok_shop',
      'amazon_sp_api',
      '1688',
      'stripe',
      'paypal',
      'meta_ads',
      'google_ads',
      'tiktok_ads',
    ],
  }),
]

// ===== 公共 API =====

export async function mockListPersonas(): Promise<Persona[]> {
  await sleep(120)
  // 拷贝并去掉 detail-only 字段
  return seeds.map(({ system_prompt_excerpt: _sp, backed_by_agents: _bba, ...p }) => p)
}

export async function mockGetPersona(personaId: string): Promise<PersonaDetail> {
  await sleep(120)
  const found = seeds.find((p) => p.persona_id === personaId)
  if (!found) {
    throw new Error(`mock: persona 不存在 ${personaId}`)
  }
  return {
    ...found,
    system_prompt_excerpt:
      found.system_prompt_excerpt ??
      `你是「${found.display_name}」persona — ${found.description}。在 mock 环境中，详情来自前端 mock 种子。`,
    backed_by_agents: found.backed_by_agents ?? [],
  }
}

export async function mockChatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  await sleep(400)
  const found = seeds.find((p) => p.persona_id === personaId)
  if (!found) {
    throw new Error(`mock: persona 不存在 ${personaId}`)
  }
  const prefix = found.is_implemented
    ? `${found.emoji} **${found.display_name}**：收到「${body.message.slice(0, 60)}」。`
    : `${found.emoji} **${found.display_name}**（规划中 · mock 占位）：「${body.message.slice(0, 60)}」`
  const lines = [
    prefix,
    '',
    found.is_implemented
      ? `我可以帮你做：${found.capabilities.slice(0, 3).join(' / ')}……（共 ${found.capabilities.length} 项能力）`
      : `本 persona 后端尚未实装，当前为前端 mock 应答；正式上线后可调用：${found.capabilities.slice(0, 2).join(' / ')}……`,
    '',
    `_背后调用 ${found.backed_by_skills.length} 个技能 / ${(found.backed_by_agents ?? []).length} 个 specialized agent_`,
  ]
  return {
    persona_id: personaId,
    content: lines.join('\n'),
    metadata: {
      mock: true,
      is_implemented: !!found.is_implemented,
      capabilities: found.capabilities,
      display_name: found.display_name,
    },
  }
}
