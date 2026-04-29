/**
 * 移动端 10 个 user-facing persona 的元信息注册表（V3 P17-C）。
 *
 * 来源：与 backend/src/agents/personas/registry.py + docs/v3/AGENT_PERSONAS.md 对齐。
 *
 * 这里写死，避免冷启动等 API；实际 API 上线后由 personasApi.list() 覆盖
 * （只用 registry 作为离线 fallback / sample question 来源）。
 */

export type PersonaId =
  | 'anxin_assistant'
  | 'legal_advisor'
  | 'contract_steward'
  | 'due_diligence_expert'
  | 'tax_finance_advisor'
  | 'operations_manager'
  | 'market_researcher'
  | 'lead_hunter'
  | 'content_director'
  | 'ecommerce_assistant'

export type PersonaDomain = '综合协调' | '合规经营' | '增长获客' | '出海跨境'

export interface PersonaCapability {
  id: string
  label: string
  /** 用户点击触发时附带的 sample prompt */
  prompt: string
}

export interface PersonaMeta {
  persona_id: PersonaId
  display_name: string
  emoji: string
  /** 一句话定位 */
  tagline: string
  /** 详细描述（用于详情页） */
  description: string
  domain: PersonaDomain
  /** 是否已有后端实装（决定 chat 是否走真实 endpoint） */
  is_implemented: boolean
  capabilities: PersonaCapability[]
  /** 工作台首屏的快速提问示例 */
  sample_questions: string[]
  /** 后端 specialized agent 列表（参考） */
  backed_by_agents: string[]
  /** 已支持的集成应用 */
  supported_apps: string[]
}

export const PERSONAS: PersonaMeta[] = [
  {
    persona_id: 'anxin_assistant',
    display_name: '安心助理',
    emoji: '🤖',
    tagline: '通用入口 + 任务编排，不知道找谁就找它',
    description:
      '你的智能办公总管。自然语言路由 + 任务拆解 + 多智能体协作，让你只用一句话就能调动 9 个专家协同工作。',
    domain: '综合协调',
    is_implemented: false,
    capabilities: [
      { id: 'intent_route', label: '意图识别 / 路由', prompt: '我下周一要给客户做提案,你帮我安排一下' },
      { id: 'task_breakdown', label: '任务拆解', prompt: '帮我准备下周三去深圳见新供应商的全套材料' },
      { id: 'multi_agent', label: '多智能体协商', prompt: '让市场和销售两位针对这个新品方案各给一份意见' },
      { id: 'inbox', label: '统一收件箱', prompt: '汇总所有 persona 今天给我的进度' },
    ],
    sample_questions: [
      '帮我看看这个供应商靠不靠谱',
      '下周一要给客户做提案,怎么搞',
      '这份合同有点复杂,你看看（附 PDF）',
    ],
    backed_by_agents: ['coordinator', 'workforce', 'requirement_analyst', 'consensus_agent'],
    supported_apps: ['飞书', '钉钉', '企业微信', '桌面通知'],
  },
  {
    persona_id: 'legal_advisor',
    display_name: '法律顾问',
    emoji: '⚖️',
    tagline: '法律咨询 + 法规检索 + 风险评估',
    description:
      '你的随身法律大脑。对接北大法宝 / 威科 / 国务院政策库，结合公司业务上下文给出可执行建议（非泛泛而谈），带源链接 + 量化风险。',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      { id: 'reg_search', label: '法规检索', prompt: '《劳动合同法》关于竞业限制的条款' },
      { id: 'consult', label: '法律咨询', prompt: '员工拒绝签竞业协议,我能强制要求吗?' },
      { id: 'risk_grade', label: '风险评估', prompt: '客户要在合同里加最惠待遇条款,有什么风险?' },
      { id: 'reg_monitor', label: '法规监测', prompt: '上月监管局发布的办法对我们公司有什么影响?' },
      { id: 'case_search', label: '判例检索', prompt: '查一下最高法关于竞业限制的指导案例' },
    ],
    sample_questions: [
      '员工提交辞职申请后当天就要走,可以吗?依据是什么?',
      '客户要在合同里加最惠待遇条款,有什么风险?',
      '我们要在英国注册子公司做 SaaS 业务,要注意什么',
    ],
    backed_by_agents: [
      'legal_advisor',
      'legal_researcher',
      'risk_assessor',
      'compliance_officer',
      'regulatory_monitor',
      'litigation_strategist',
    ],
    supported_apps: ['北大法宝', '威科先行', '国务院政策库', '飞书', '钉钉'],
  },
  {
    persona_id: 'contract_steward',
    display_name: '合同管家',
    emoji: '📜',
    tagline: '合同全生命周期，从起草到归档',
    description:
      '从起草、审查、谈判、签署到归档，每一份合同我帮你盯。200+ 模板库 + 智能填空 + 轨道修订 + 到期提醒。',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      { id: 'draft', label: '合同起草', prompt: '帮我起草一份 OEM 合同,客户在深圳,标的 200 万' },
      { id: 'review', label: '合同审查', prompt: '客户发来的采购框架协议,看看哪里要改（附 PDF）' },
      { id: 'negotiate', label: '合同谈判', prompt: '违约金条款让步空间分析' },
      { id: 'lifecycle', label: '到期提醒', prompt: '3 月 15 日前到期的合同有哪些?提醒我下' },
      { id: 'compliance', label: '合规校验', prompt: '这份合同符合我们内部红线吗?' },
    ],
    sample_questions: [
      '客户发来采购框架协议,看看哪里要改',
      '帮我起草一份保密协议',
      '3 月 15 日前到期的合同有哪些?',
    ],
    backed_by_agents: [
      'contract_reviewer',
      'contract_steward',
      'contract_investigator',
      'review_checker',
      'document_drafter',
      'template_librarian',
    ],
    supported_apps: ['法大大', 'e签宝', '飞书文档', 'Notion', 'Outlook'],
  },
  {
    persona_id: 'due_diligence_expert',
    display_name: '尽调专家',
    emoji: '🔍',
    tagline: '公司 / 项目 / 客户 360° 尽调',
    description:
      '见客户 / 投资 / 收购前，先让我看看对方家底。工商 + 法律 + 财务 + 舆情 四路并行，6 分钟出综合简报。',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      { id: 'company', label: '工商尽调', prompt: '查 XX 制造有限公司的股权和实控人' },
      { id: 'legal_dd', label: '法律尽调', prompt: '查这家公司的诉讼和失信记录' },
      { id: 'finance_dd', label: '财务尽调', prompt: '看下他们的年报和纳税等级' },
      { id: 'sentiment', label: '舆情尽调', prompt: '近 6 个月有什么负面新闻或维权事件?' },
      { id: 'report', label: '专项报告', prompt: '给 XX 公司做一个客户级尽调报告' },
    ],
    sample_questions: [
      'XX 制造有限公司,深圳的,给我做个客户尽调',
      '我要收购一家精密五金厂,预算 3000 万,做投资级尽调',
      '查一下这位老板有没有失信被执行记录',
    ],
    backed_by_agents: [
      'due_diligence',
      'evidence_analyst',
      'sentiment_agent',
      'legal_researcher',
      'risk_assessor',
      'contract_investigator',
    ],
    supported_apps: ['企查查', '天眼查', '启信宝', '裁判文书网', '信用中国'],
  },
  {
    persona_id: 'tax_finance_advisor',
    display_name: '财税顾问',
    emoji: '💰',
    tagline: '税务合规 + 财务分析 + 法律计算',
    description:
      '节税合规 + 财务健康，老板和会计的最佳搭档。增值税 / 企业所得税 / 个税合规检查 + 经济补偿金 / 加班费 / 工伤赔偿等专项计算。',
    domain: '合规经营',
    is_implemented: false,
    capabilities: [
      { id: 'tax_check', label: '税务合规检查', prompt: '帮我看看上季度的增值税申报有没有问题' },
      { id: 'tax_plan', label: '节税筹划', prompt: '年底要发 500 万奖金,怎么发最省税?' },
      { id: 'legal_calc', label: '法律计算', prompt: '员工月薪 2 万,干了 3 年 7 个月,N+1 协商离职赔多少?' },
      { id: 'fin_analysis', label: '财务分析', prompt: '帮我分析一下本季度的现金流' },
      { id: 'audit_warn', label: '稽查预警', prompt: '我们公司目前有哪些高频稽查指标在异常区间?' },
    ],
    sample_questions: [
      '员工月薪 2 万,干了 3 年 7 个月,N+1 协商离职赔多少?',
      '年底要发 500 万奖金,全公司怎么发最省税?',
      '帮我看下上季度增值税申报有没有合规风险',
    ],
    backed_by_agents: ['tax_compliance', 'legal_calculator', 'compliance_officer'],
    supported_apps: ['金蝶', '用友', 'Xero', 'QuickBooks', '税务总局公告'],
  },
  {
    persona_id: 'operations_manager',
    display_name: '流程管家',
    emoji: '📋',
    tagline: 'OKR / 审批 / 会议 / 周报全流程',
    description:
      '公司过程管理小助手。OKR 制定 + 审批智能流转 + 会议纪要自动生成 + 周报自动起草，把零散过程串成闭环。',
    domain: '合规经营',
    is_implemented: true,
    capabilities: [
      { id: 'okr_dashboard', label: 'OKR 看板', prompt: '给我看下本季度 OKR 进度' },
      { id: 'weekly_report', label: '周报起草', prompt: '帮我起草本周周报' },
      { id: 'meeting_minutes', label: '会议纪要', prompt: '上周二下午的产品评审会纪要给我下' },
      { id: 'extract_todos', label: '待办抽取', prompt: '从这份会议录音里抽出待办分配给责任人' },
      { id: 'approval_flow', label: '审批流程', prompt: '这笔报销该走什么流程?' },
    ],
    sample_questions: [
      '上周的产品评审会纪要给我下',
      '帮我起草本周周报',
      '给我看下本季度 OKR 进度',
    ],
    backed_by_agents: ['requirement_analyst', 'coordinator'],
    supported_apps: ['飞书', '钉钉', '企业微信', 'Notion', 'Google Calendar', 'Outlook'],
  },
  {
    persona_id: 'market_researcher',
    display_name: '市场研究员',
    emoji: '📊',
    tagline: '调研 / 竞品 / 趋势 / 行业洞察',
    description:
      '想了解一个行业 / 一个对手 / 一个趋势,我做你的研究员。DeepResearch 迭代 + RAG-Anything PDF 深读 + 跨平台社媒抓取。',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      { id: 'investigate_company', label: '公司调研', prompt: '调研一下 XX 公司的业务和团队' },
      { id: 'competitor_monitor', label: '竞品监控', prompt: '监控 5 家竞品的官网和公众号,周二早上汇总' },
      { id: 'industry_trends', label: '行业趋势', prompt: 'LED 封装赛道接下来 3 年怎么看?' },
      { id: 'deep_research', label: 'DeepResearch 深读', prompt: '把这 5 份行业报告 PDF 提炼成 1 页要点' },
      { id: 'reports', label: '研究报告库', prompt: '查看我之前生成的所有研究报告' },
    ],
    sample_questions: [
      'LED 封装赛道接下来 3 年怎么看?',
      '监控 5 家竞品的官网 + 公众号,每周二 9 点给我汇总',
      '把这 5 份行业报告提炼成 1 页要点',
    ],
    backed_by_agents: ['legal_researcher', 'evidence_analyst', 'sentiment_agent'],
    supported_apps: ['Reddit', 'X', 'LinkedIn', 'YouTube', 'TikTok', '艾瑞', '易观'],
  },
  {
    persona_id: 'lead_hunter',
    display_name: '获客猎手',
    emoji: '🎯',
    tagline: '销售线索 + 推广 + Vibe Selling',
    description:
      '把陌生人变成客户,把客户变成朋友。线索挖掘 + LeadScoring + Vibe Selling 话术 + 多 Agent 投放决策。',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      { id: 'discover_leads', label: '线索挖掘', prompt: '挖 200 个珠三角精密五金行业的潜客线索' },
      { id: 'draft_email', label: '销售邮件', prompt: '客户回了再考虑下,帮我起草跟进邮件' },
      { id: 'generate_quote', label: '报价单生成', prompt: '生成一份注塑机报价单' },
      { id: 'sync_crm', label: 'CRM 同步', prompt: '把今天的线索同步到 HubSpot' },
      { id: 'linkedin_outreach', label: 'LinkedIn 触达', prompt: '给这位欧洲采购总监设计一套 LinkedIn 触达策略' },
    ],
    sample_questions: [
      '客户回了再考虑下,怎么办?',
      '上个月广告 ROI 不行,看看怎么调',
      '挖 200 个精密五金行业的潜客线索',
    ],
    backed_by_agents: ['sentiment_agent', 'consensus_agent'],
    supported_apps: ['Salesforce', 'HubSpot', 'Zoho', 'Pipedrive', 'LinkedIn Sales Navigator'],
  },
  {
    persona_id: 'content_director',
    display_name: '内容总监',
    emoji: '✍️',
    tagline: '公众号 / 短视频 / 海报 / 落地页',
    description:
      '从一句话灵感到一支成片,全链路内容生产。多平台适配 + canvas-design 海报 + Remotion 视频 + 多语言改写。',
    domain: '增长获客',
    is_implemented: true,
    capabilities: [
      { id: 'wechat_article', label: '公众号长文', prompt: '写一篇我们新一代精密注塑机发布的公众号' },
      { id: 'video_script', label: '短视频脚本', prompt: '产品演讲剪成 3 条 30 秒短视频' },
      { id: 'poster_copy', label: '海报文案', prompt: '春节活动海报,主题回家过年送好礼' },
      { id: 'brand_check', label: '品牌一致性校验', prompt: '看这版文案符不符合我们品牌调性' },
      { id: 'localize', label: '多语言改写', prompt: '把这篇产品页改成英文 + 日文版本' },
    ],
    sample_questions: [
      '写一篇我们新品发布的公众号,调性专业但不枯燥',
      '春节活动海报,主题是回家过年送好礼',
      '把这段产品演讲剪成 3 条 30 秒短视频',
    ],
    backed_by_agents: ['evidence_analyst'],
    supported_apps: ['canvas-design', 'web-artifacts-builder', 'Figma', 'Canva', 'Remotion'],
  },
  {
    persona_id: 'ecommerce_assistant',
    display_name: '跨境电商助手',
    emoji: '🌍',
    tagline: '选品 / 独立站 / 出海全链路',
    description:
      '从想做出海到第一笔订单,每个坑我帮你避。选品分析 + 独立站搭建 + 多平台 listing + AI 议价 + VAT 合规。',
    domain: '出海跨境',
    is_implemented: true,
    capabilities: [
      { id: 'analyze_niche', label: '选品分析', prompt: '最近 TikTok 上可折叠桌很火,要不要选?' },
      { id: 'verify_supplier', label: '供应商核验', prompt: '帮我核实一下这家 1688 供应商靠不靠谱' },
      { id: 'negotiate', label: 'AI 议价', prompt: '帮我跟阿里供应商砍价,目标 -15%' },
      { id: 'setup_store', label: '独立站搭建', prompt: '帮我开 Shopify 独立站,卖精密五金' },
      { id: 'list_to_platforms', label: '多平台上架', prompt: '把这个 SKU 同步上架 Amazon + Shopee + TikTok Shop' },
      { id: 'vat_guidance', label: 'VAT 合规', prompt: '英国子公司 VAT 阈值是多少?要怎么注册?' },
      { id: 'dashboard', label: '运营总览', prompt: '本周出海运营总览' },
    ],
    sample_questions: [
      '我们做精密五金,想做出海,从哪开始?',
      '最近 TikTok 上可折叠桌很火,要不要选品?',
      '英国子公司 VAT 阈值多少?',
    ],
    backed_by_agents: ['legal_researcher', 'risk_assessor', 'tax_compliance'],
    supported_apps: [
      'Shopify',
      'Shopee',
      'TikTok Shop',
      'Amazon SP-API',
      '1688',
      'Stripe',
      'PayPal',
      'Meta Ads',
      'Google Ads',
    ],
  },
]

export const DOMAIN_COLOR: Record<PersonaDomain, string> = {
  综合协调: '#0EA5E9',
  合规经营: '#8B5CF6',
  增长获客: '#F97316',
  出海跨境: '#10B981',
}

export function getPersonaMeta(personaId: string): PersonaMeta | undefined {
  return PERSONAS.find((p) => p.persona_id === personaId)
}
