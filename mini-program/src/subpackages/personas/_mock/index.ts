/**
 * P21-C 小程序 personas mock 数据 + 假流式 helper
 *
 * 与 frontend/src/lib/api/__mocks__/personas.mock.ts 对齐：
 *   - 10 个 user-facing persona（emoji + 名称 + 描述 + capabilities + skills + supported_apps）
 *   - 每 persona 3 个示例对话
 *   - chatWithPersona mock：根据 persona type 返回不同假回复
 *   - 假流式 helper（小程序无 SSE，逐字推送 chunk）
 */

export type PersonaDomain = '综合协调' | '合规经营' | '增长获客' | '出海跨境'

export interface Persona {
  persona_id: string
  display_name: string
  emoji: string
  description: string
  domain: PersonaDomain
  is_implemented: boolean
  capabilities: string[]
  backed_by_skills: string[]
  backed_by_agents: string[]
  supported_apps: string[]
  /** 示例对话（detail 页 / 空 chat 提示用） */
  sample_dialogs: Array<{ q: string; a: string }>
}

// ===== 10 personas 完整种子 =====

export const PERSONAS: Persona[] = [
  {
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
    supported_apps: ['feishu', 'dingtalk', 'wecom', '桌面通知', '移动推送'],
    sample_dialogs: [
      { q: '我下周要见一个新客户，需要做什么准备？', a: '我帮你拆三步：1) 让尽调专家拉客户家底 2) 让法律顾问看历史风险 3) 让获客猎手出谈判要点。' },
      { q: '帮我整理本周所有 persona 的进度', a: '已聚合 5 个 persona 任务：流程管家 3 项 / 内容总监 2 项 / 跨境助手 1 项 ……' },
      { q: '我有个新业务想做，但不知道找谁', a: '描述给我，我会路由到正确的 persona 组合，并生成执行 DAG。' },
    ],
  },
  {
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
    backed_by_agents: ['legal_advisor', 'legal_researcher', 'risk_assessor', 'compliance_officer'],
    supported_apps: ['北大法宝', '威科先行', '国务院政策库', 'feishu', 'dingtalk'],
    sample_dialogs: [
      { q: '员工离职后违反竞业协议，公司能要回多少违约金？', a: '依《劳动合同法》第 23-24 条……（4 步分析 + 类案 3 篇）' },
      { q: '帮我查 2026 年新公司法注册资本五年实缴细则', a: '已检索 12 条法规 + 3 条释义，核心条款：……（带源链接）' },
      { q: '这单业务有什么合规红线？', a: '我帮你做 5 级风险评估，请告诉我业务场景……' },
    ],
  },
  {
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
    ],
    backed_by_agents: ['contract_reviewer', 'contract_steward', 'review_checker', 'document_drafter'],
    supported_apps: ['法大大', 'e签宝', 'feishu_doc', 'notion', 'outlook'],
    sample_dialogs: [
      { q: '帮我起草一份服务合同，金额 50 万，6 个月', a: '我从模板库选「IT 服务合同 v3」，已自动填好金额 / 期限 / 验收 / 付款节奏，请确认……' },
      { q: '这份采购合同有什么风险？', a: '已逐条审查 23 条款，标记 4 处红色风险 / 6 处黄色提示，并给出 redline 建议……' },
      { q: '本月哪些合同要到期？', a: '本月到期 7 份，建议续约 3 份 / 重新谈判 2 份 / 终止 2 份，详情见列表。' },
    ],
  },
  {
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
      'office/pdf-report-gen',
    ],
    backed_by_agents: ['due_diligence', 'evidence_analyst', 'sentiment_agent', 'legal_researcher'],
    supported_apps: ['企查查', '天眼查', '启信宝', '中国裁判文书网', '信用中国', 'linkedin'],
    sample_dialogs: [
      { q: '查一下深圳 XX 科技有限公司的家底', a: '已聚合工商 / 涉诉 / 舆情 3 维报告：注册资本 500 万实缴 100 万，5 年涉诉 12 起……' },
      { q: '这家供应商靠不靠谱？', a: '风险等级：黄色（中）。要点：经营异常 1 次 / 行政处罚 2 起 / 失信被执行人无……' },
      { q: '我要做一份 A 轮投资尽调报告', a: '请上传被投方信息，我会出具投资级 PDF（约 30-50 页，含 6 大模块）。' },
    ],
  },
  {
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
    sample_dialogs: [
      { q: '员工工作 5 年被裁，N+1 是多少？', a: '依据 2025 年北京社平工资上限，N+1 = 6 × 月薪（封顶 35,283 元/月）= ……' },
      { q: '帮我看看本月增值税申报有没有问题', a: '已对账 23 笔：3 笔进项缺票 / 2 笔税率有误 / 余 18 笔正常，建议优先补……' },
      { q: '小规模和一般纳税人哪个更划算？', a: '基于你的年营收 280 万 + 主要客户类型，建议保持小规模，年节税约 8.4 万……' },
    ],
  },
  {
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
    ],
    backed_by_agents: ['requirement_analyst', 'coordinator', 'okr_agent', 'meeting_minutes_agent'],
    supported_apps: ['feishu', 'dingtalk', 'wecom', 'notion', 'google_calendar', 'outlook'],
    sample_dialogs: [
      { q: '帮我拆解 Q2 OKR：营收提升 30%', a: '已拆 3 个 KR：新客户 +50 / 客单价 +15% / 流失率 -8%，每个 KR 又拆 4-6 个 task……' },
      { q: '今天会议给我做个纪要', a: '请上传录音或粘贴文字。我会输出 3 段：决策 / 待办（带 owner + DDL）/ 风险。' },
      { q: '本周周报', a: '已聚合 3 平台：OKR 完成 65%，关键进展 4 项，阻塞 1 项，下周计划 5 项。' },
    ],
  },
  {
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
    ],
    backed_by_agents: ['legal_researcher', 'evidence_analyst', 'sentiment_agent', 'market_agent'],
    supported_apps: ['reddit', 'x', 'linkedin', 'youtube', 'tiktok', 'headlessx'],
    sample_dialogs: [
      { q: '帮我深读这份 50 页行业报告', a: '已用 DeepTutor 模式：5 个核心结论 / 12 张关键图 / 8 条引文，推荐先看第 3 章……' },
      { q: '监控竞品 X 公司本月动态', a: '本月 6 条信号：发布会 1 / 新岗招聘 8 / 媒体提及 23，异动等级：黄色。' },
      { q: '小红书"AI 法务"话题正在火吗？', a: '近 30 天提及 +124%，热门角度 3 个，潜在切入机会 2 个，建议布局……' },
    ],
  },
  {
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
    ],
    backed_by_agents: ['sentiment_agent', 'consensus_agent', 'lead_agent', 'vibe_seller'],
    supported_apps: ['salesforce', 'hubspot', 'zoho', 'pipedrive', 'feishu', 'wecom', 'linkedin'],
    sample_dialogs: [
      { q: '帮我挖一批"近期 A 轮融资 + 在招法务"的潜在客户', a: '已找到 47 家：高优 12 / 中优 23 / 低优 12，带决策人 + 联系方式 + 切入话术。' },
      { q: '这条客户回复"再考虑下"，我下一步该做什么？', a: '基于对话情绪（保留型）+ 客户阶段（评估期），建议 3 天内发竞品对比卡片。' },
      { q: '本周巨量引擎广告该加预算吗？', a: '多 agent 投票：加 +20%（4/5 agent 同意），ROI 趋势向上，关键词 2 条建议替换。' },
    ],
  },
  {
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
      'content/video-script',
      'content/remotion-render',
    ],
    backed_by_agents: ['content_agent', 'design_agent', 'video_agent', 'evidence_analyst'],
    supported_apps: ['canvas-design', 'figma', 'canva', 'higgsfield', 'remotion', '微信公众号', '抖音'],
    sample_dialogs: [
      { q: '帮我写一篇关于"中小企业法务困境"的小红书爆款', a: '已生成 5 个钩子标题 + 正文 600 字 + 9 张分镜配图脚本，预估完播率 ≥ 40%。' },
      { q: '生成一张活动海报', a: '请告诉我主题 / 受众 / 风格关键词，我会用 canvas-design 出 3 个方案。' },
      { q: '把这篇产品文做成 60 秒短视频', a: '已拆分镜 12 段 / 配音 / BGM / 字幕，Remotion 自动渲染中，预计 2 分钟产出。' },
    ],
  },
  {
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
    ],
    backed_by_agents: ['ecommerce_agent', 'selection_agent', 'oversea_compliance_agent', 'tax_compliance'],
    supported_apps: ['shopify', 'shopee', 'tiktok_shop', 'amazon_sp_api', '1688', 'stripe', 'paypal'],
    sample_dialogs: [
      { q: '我想做美区 TikTok Shop，选品建议？', a: '基于近 30 天数据，3 个高潜赛道：宠物配件 / 厨房小物 / 美妆工具，含 12 个 SKU 候选。' },
      { q: '欧盟 GDPR 我需要做什么？', a: '6 步合规清单：DPO / Cookie 弹窗 / 隐私政策 / 数据导出 / 跨境传输 SCC / 删除请求流程。' },
      { q: '帮我搭一个 Shopify 独立站', a: '主题已选 Dawn，正在配置：商品页 5 个 / 落地页 2 个 / 支付（Stripe）/ 物流（4PX）。' },
    ],
  },
]

// ===== 公共 API（mock） =====

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

export async function listPersonas(): Promise<Persona[]> {
  await sleep(120)
  return PERSONAS
}

export async function getPersona(personaId: string): Promise<Persona | undefined> {
  await sleep(80)
  return PERSONAS.find((p) => p.persona_id === personaId)
}

export interface ChatRequest {
  message: string
  history?: Array<{ role: 'user' | 'assistant'; content: string }>
}

export interface ChatResponse {
  persona_id: string
  content: string
  is_implemented: boolean
  display_name: string
  emoji: string
}

export async function chatWithPersona(
  personaId: string,
  body: ChatRequest,
): Promise<ChatResponse> {
  await sleep(280)
  const found = PERSONAS.find((p) => p.persona_id === personaId)
  if (!found) {
    throw new Error(`mock: persona 不存在 ${personaId}`)
  }
  const head = found.is_implemented
    ? `${found.emoji} ${found.display_name}：收到「${body.message.slice(0, 60)}」。`
    : `${found.emoji} ${found.display_name}（规划中 · mock 占位）：「${body.message.slice(0, 60)}」`
  const detail = found.is_implemented
    ? `我可以帮你做：${found.capabilities.slice(0, 3).join(' / ')}……（共 ${found.capabilities.length} 项能力）`
    : `本 persona 后端尚未实装，当前为前端 mock 应答；正式上线后可调用：${found.capabilities.slice(0, 2).join(' / ')}……`
  const tail = `背后调用 ${found.backed_by_skills.length} 个技能 / ${found.backed_by_agents.length} 个 specialized agent。`
  return {
    persona_id: personaId,
    content: [head, '', detail, '', tail].join('\n'),
    is_implemented: found.is_implemented,
    display_name: found.display_name,
    emoji: found.emoji,
  }
}

// ===== 假流式 helper =====
//
// 小程序无 SSE：用 setTimeout 每 50ms 推一个字符 chunk，
// 模拟真实大模型逐字流式体验。
// 调用方传入 onChunk(chunk, fullText, done)。

export interface FakeStreamHandle {
  /** 取消流（用于离开页面 / 重新生成） */
  cancel: () => void
}

export function fakeStream(
  fullText: string,
  onChunk: (chunk: string, fullText: string, done: boolean) => void,
  intervalMs = 50,
): FakeStreamHandle {
  let cancelled = false
  let idx = 0
  let acc = ''

  const tick = () => {
    if (cancelled) return
    if (idx >= fullText.length) {
      onChunk('', acc, true)
      return
    }
    const ch = fullText[idx]
    acc += ch
    idx += 1
    onChunk(ch, acc, false)
    setTimeout(tick, intervalMs)
  }

  setTimeout(tick, intervalMs)

  return {
    cancel: () => {
      cancelled = true
    },
  }
}

// ===== 业务域分组（list 页面用） =====

export interface PersonaGroup {
  domain: PersonaDomain
  /** 人话 label，如「法务合规」 */
  label: string
  personas: Persona[]
}

export function groupPersonas(list: Persona[]): PersonaGroup[] {
  // 按业务域分桶 — 任务要求 4 大组（法务 / 经营 / 增长 / 综合）
  // domain '合规经营' 又细分两类：法律强相关 4 个 + 流程经营 2 个
  const legalIds = new Set([
    'legal_advisor',
    'contract_steward',
    'due_diligence_expert',
    'tax_finance_advisor',
  ])
  const operationIds = new Set(['operations_manager'])
  const overseaIds = new Set(['ecommerce_assistant'])
  const generalIds = new Set(['anxin_assistant'])

  const buckets: Record<string, PersonaGroup> = {
    legal: { domain: '合规经营', label: '法务合规', personas: [] },
    ops: { domain: '合规经营', label: '经营管理', personas: [] },
    growth: { domain: '增长获客', label: '增长获客', personas: [] },
    general: { domain: '综合协调', label: '综合协调', personas: [] },
  }

  list.forEach((p) => {
    if (legalIds.has(p.persona_id)) buckets.legal.personas.push(p)
    else if (operationIds.has(p.persona_id) || overseaIds.has(p.persona_id))
      buckets.ops.personas.push(p)
    else if (p.domain === '增长获客') buckets.growth.personas.push(p)
    else if (generalIds.has(p.persona_id)) buckets.general.personas.push(p)
    else buckets.general.personas.push(p)
  })

  // 输出顺序：法务 → 经营 → 增长 → 综合
  return [buckets.legal, buckets.ops, buckets.growth, buckets.general].filter(
    (g) => g.personas.length > 0,
  )
}
