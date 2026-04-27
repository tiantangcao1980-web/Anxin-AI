/**
 * Skills Mock 适配层（V3 P5-F）
 *
 * 在 VITE_SKILLS_MOCK=true 时启用，覆盖后端 P5-A skills 接口的 6 个 endpoint。
 *
 * 内置 50+ skill，跨 13 域：
 *   legal · tax_finance · operations · research · marketing · content · design
 *   office · ecommerce · sales · intelligence · decision · system
 *
 * 重点字段：
 *   - triggers / personas / category：用于 trigger 匹配 + persona 过滤 + 域分组
 *   - body / body_excerpt：用于详情抽屉的 markdown 渲染
 *
 * 与文档对齐：详见 docs/v3/SKILLS_INVENTORY.md
 */

import type {
  ListSkillsParams,
  Skill,
  SkillExecuteResult,
  SkillUploadResult,
} from '../skills'

// ===== 工具函数 =====

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

function excerpt(body: string, max = 200): string {
  const s = body.replace(/\s+/g, ' ').trim()
  return s.length > max ? `${s.slice(0, max)}…` : s
}

function md(title: string, lines: string[]): string {
  return `# ${title}\n\n${lines.join('\n')}\n`
}

interface SeedInput
  extends Omit<Skill, 'body' | 'body_excerpt' | 'enabled' | 'version' | 'author'> {
  body: string
  enabled?: boolean
  version?: string
  author?: string
}

function makeSkill(input: SeedInput): Skill {
  return {
    name: input.name,
    display_name: input.display_name,
    description: input.description,
    version: input.version ?? '0.1.0',
    category: input.category,
    type: input.type,
    author: input.author ?? '安心智能助手 · 内置',
    triggers: input.triggers,
    personas: input.personas,
    requires_apps: input.requires_apps,
    dependencies: input.dependencies,
    keywords: input.keywords,
    enabled: input.enabled ?? false,
    icon: input.icon,
    body: input.body,
    body_excerpt: excerpt(input.body),
  }
}

// ===== Skill 种子（按 13 域分组） =====

const seeds: Skill[] = [
  // ----- legal (8) -----
  makeSkill({
    name: 'legal/contract-review',
    display_name: '合同逐条审查',
    description: '解析合同结构、抽取关键条款、给出 5 级风险评级和修订建议',
    category: 'legal',
    type: 'workflow',
    triggers: ['审一下这份合同', 'contract review', '合同审查', '帮我看看合同风险'],
    personas: ['合同管家', '法律顾问'],
    requires_apps: [],
    dependencies: ['legal/clause-extract', 'legal/risk-grade', 'office/docx'],
    keywords: ['contract', 'review', 'redline', '风险'],
    icon: '📜',
    enabled: true,
    body: md('legal/contract-review — 合同逐条审查', [
      '> 输入：.docx / .pdf 合同 ｜ 输出：风险摘要 + 逐条点评 + redline 建议',
      '',
      '## 流程',
      '1. office/docx 解析正文与结构（条款树）',
      '2. legal/clause-extract 抽取主体、标的、价款、期限、违约、争议解决等关键条款',
      '3. legal/risk-grade 给出 5 级风险评分（1=低 ~ 5=极高）',
      '4. 输出修订建议（轨道修订 .docx）',
      '',
      '## 触发示例',
      '- "帮我审一下这份采购合同的付款条款"',
      '- "标的物条款有没有问题？"',
    ]),
  }),
  makeSkill({
    name: 'legal/clause-extract',
    display_name: '关键条款抽取',
    description: '从合同中抽取主体、标的、价款、期限、违约、争议解决等关键条款',
    category: 'legal',
    type: 'tool',
    triggers: ['抽取条款', '关键条款是什么', 'extract clauses'],
    personas: ['合同管家', '法律顾问'],
    requires_apps: [],
    dependencies: ['office/docx'],
    keywords: ['clause', 'extract', '条款'],
    icon: '🔖',
    enabled: true,
    body: md('legal/clause-extract — 关键条款抽取', [
      '基于 LLM + 模板库，把合同切分为标准条款桶。',
      '',
      '输出 schema：`{ parties, subject, price, term, liability, dispute_resolution, ... }`',
    ]),
  }),
  makeSkill({
    name: 'legal/due-diligence',
    display_name: '法律尽调（公司）',
    description: '工商 / 司法 / 知识产权 / 行政处罚一站式尽调报告',
    category: 'legal',
    type: 'agent',
    triggers: ['查一下这家公司', 'due diligence', '尽调', '查工商', '法律尽调'],
    personas: ['尽调专家', '法律顾问'],
    requires_apps: ['qichacha'],
    dependencies: ['intelligence/web-fetch', 'research/multi-source-synthesize'],
    keywords: ['DD', '尽调', '工商', '裁判文书', '行政处罚'],
    icon: '🏢',
    body: md('legal/due-diligence — 法律尽调', [
      '聚合 8+ 数据源（企查查、天眼查、信用中国、裁判文书网、商标局…）。',
      '',
      '产出 markdown 尽调报告 + 风险红黄绿三色标注。',
    ]),
  }),
  makeSkill({
    name: 'legal/labor-law',
    display_name: '劳动法计算器',
    description: '加班费、经济补偿、工伤赔偿、未签劳动合同 2N 等场景化计算',
    category: 'legal',
    type: 'tool',
    triggers: ['加班费怎么算', '工伤赔偿', '经济补偿 N+1', '解雇赔偿'],
    personas: ['法律顾问', '财税顾问'],
    requires_apps: [],
    dependencies: [],
    keywords: ['劳动法', '加班', '赔偿', 'labor'],
    icon: '⚖️',
    enabled: true,
    body: md('legal/labor-law — 劳动法计算器', [
      '输入：劳动者基本信息（薪资 / 工龄 / 解除原因）',
      '输出：金额 + 法律依据条文 + 案例参考',
    ]),
  }),
  makeSkill({
    name: 'legal/ip-infringement',
    display_name: '知识产权侵权排查',
    description: '商标、专利、著作权侵权风险的批量排查与证据固定',
    category: 'legal',
    type: 'workflow',
    triggers: ['商标侵权', '专利侵权', '版权侵权', 'IP infringement'],
    personas: ['法律顾问'],
    requires_apps: ['cnipa'],
    dependencies: ['intelligence/web-fetch'],
    keywords: ['IP', '商标', '专利', '侵权'],
    icon: '🛡️',
    body: md('legal/ip-infringement — 知识产权侵权排查', [
      '抓取在售 / 在线 / 在案的相似品牌，比对申请优先权。',
    ]),
  }),
  makeSkill({
    name: 'legal/legal-research',
    display_name: '法律法规与判例检索',
    description: '北大法宝 / 威科 / 33,102 条裁判文书 + 全网法规检索',
    category: 'legal',
    type: 'tool',
    triggers: ['查一下法条', '相关判例', 'case search', '法规检索'],
    personas: ['法律顾问', '合同管家', '尽调专家'],
    requires_apps: ['pkulaw'],
    dependencies: [],
    keywords: ['法规', '判例', 'research', '裁判文书'],
    icon: '🔍',
    enabled: true,
    body: md('legal/legal-research — 法律法规与判例检索', [
      '混合检索：BM25 + 向量 + 时效校验（已废止 / 现行有效 / 待施行）。',
    ]),
  }),
  makeSkill({
    name: 'legal/asset-tracing',
    display_name: '资产线索追踪',
    description: '诉前 / 执行阶段的不动产 / 股权 / 银行账户线索梳理',
    category: 'legal',
    type: 'agent',
    triggers: ['查资产', '执行线索', 'asset tracing'],
    personas: ['法律顾问', '尽调专家'],
    requires_apps: ['qichacha'],
    dependencies: ['intelligence/web-fetch'],
    keywords: ['执行', '资产', '股权', '不动产'],
    icon: '🏦',
    body: md('legal/asset-tracing — 资产线索追踪', [
      '聚合工商股权 / 不动产 / 法拍 / 海关 / 出入境记录线索。',
    ]),
  }),
  makeSkill({
    name: 'legal/compliance-check',
    display_name: '行业合规自检',
    description: '按行业 + 区域生成合规自检清单（数据 / 反垄断 / 广告 / 环保等）',
    category: 'legal',
    type: 'workflow',
    triggers: ['合规自检', 'compliance check', '反垄断', '数据合规'],
    personas: ['法律顾问'],
    requires_apps: [],
    dependencies: ['legal/legal-research'],
    keywords: ['compliance', '合规', '自检'],
    icon: '✅',
    body: md('legal/compliance-check — 行业合规自检', [
      '内置 12 行业 × 6 区域合规模板，输出 PDF / Excel 检查表。',
    ]),
  }),

  // ----- tax_finance (4) -----
  makeSkill({
    name: 'tax_finance/tax-compliance',
    display_name: '税务合规自检',
    description: '增值税 / 企业所得税 / 个税常见高频稽查项预警',
    category: 'tax_finance',
    type: 'workflow',
    triggers: ['税务合规', '稽查预警', 'tax compliance'],
    personas: ['财税顾问'],
    requires_apps: [],
    dependencies: [],
    keywords: ['tax', '稽查', 'VAT', 'CIT'],
    icon: '🧾',
    enabled: true,
    body: md('tax_finance/tax-compliance — 税务合规自检', [
      '依据税总最新公告，对发票链 / 进销项 / 异常凭证进行打分。',
    ]),
  }),
  makeSkill({
    name: 'tax_finance/tax-plan',
    display_name: '税务筹划方案对比',
    description: '股权架构 / 业务流程 / 区域优惠的多方案税负对比',
    category: 'tax_finance',
    type: 'workflow',
    triggers: ['税务筹划', '怎么省税', 'tax plan'],
    personas: ['财税顾问'],
    requires_apps: [],
    dependencies: ['tax_finance/tax-compliance'],
    keywords: ['筹划', 'planning', 'tax'],
    icon: '🧮',
    body: md('tax_finance/tax-plan — 税务筹划方案对比', [
      '产出：3 套方案 + 综合税负差额 + 落地成本评估。',
    ]),
  }),
  makeSkill({
    name: 'tax_finance/financial-analysis',
    display_name: '财务报表关键指标解读',
    description: '资产负债表 / 利润表 / 现金流量表关键指标自动解读',
    category: 'tax_finance',
    type: 'tool',
    triggers: ['看一下报表', '财务分析', 'financial analysis'],
    personas: ['财税顾问'],
    requires_apps: ['xero'],
    dependencies: ['office/xlsx'],
    keywords: ['财报', 'finance', 'KPI'],
    icon: '📊',
    body: md('tax_finance/financial-analysis — 财报指标解读', [
      '输出 30+ 关键指标 + 同比 / 环比 + 行业基准对照。',
    ]),
  }),
  makeSkill({
    name: 'tax_finance/cross-border-tax',
    display_name: '跨境税务（VAT / 关税）',
    description: 'EU VAT / UK VAT / 美国销售税 / 关税估算与申报准备',
    category: 'tax_finance',
    type: 'workflow',
    triggers: ['VAT 申报', '跨境税', 'cross border tax'],
    personas: ['跨境电商助手', '财税顾问'],
    requires_apps: ['xero', 'shopify'],
    dependencies: [],
    keywords: ['VAT', 'duty', '跨境', '关税'],
    icon: '🌐',
    body: md('tax_finance/cross-border-tax — 跨境税务', [
      '覆盖 EU OSS / IOSS / UK MTD / 美国 nexus 判定。',
    ]),
  }),

  // ----- operations (5) -----
  makeSkill({
    name: 'operations/okr-tracker',
    display_name: 'OKR 跟踪',
    description: 'OKR 制定 → 拆解 → 周跟进 → 季度复盘全流程',
    category: 'operations',
    type: 'agent',
    triggers: ['OKR', '目标管理', '周跟进'],
    personas: ['流程管家'],
    requires_apps: ['feishu', 'notion'],
    dependencies: ['operations/weekly-report'],
    keywords: ['OKR', '目标', 'tracking'],
    icon: '🎯',
    body: md('operations/okr-tracker — OKR 跟踪', [
      '与飞书 OKR / Notion OKR Database 双向同步。',
    ]),
  }),
  makeSkill({
    name: 'operations/approval-flow',
    display_name: '审批流配置 + 智能预警',
    description: '配置审批流，识别长时间未处理 / 风险审批节点并主动提醒',
    category: 'operations',
    type: 'workflow',
    triggers: ['审批', '审批超时', 'approval flow'],
    personas: ['流程管家'],
    requires_apps: ['feishu', 'dingtalk'],
    dependencies: [],
    keywords: ['approval', '审批', '流程'],
    icon: '🪪',
    body: md('operations/approval-flow — 审批流', [
      '飞书 / 钉钉审批 OpenAPI 双向打通。',
    ]),
  }),
  makeSkill({
    name: 'operations/meeting-minutes',
    display_name: '会议纪要',
    description: '会议录音 → 转写 → 结构化纪要 → 待办分发',
    category: 'operations',
    type: 'workflow',
    triggers: ['会议纪要', '记一下会议', 'meeting minutes'],
    personas: ['流程管家', '安心助理'],
    requires_apps: ['feishu'],
    dependencies: ['intelligence/transcribe'],
    keywords: ['minutes', '纪要', '会议'],
    icon: '📝',
    enabled: true,
    body: md('operations/meeting-minutes — 会议纪要', [
      '输出：议题、决议、待办（带责任人 / 截止时间）、原文锚点。',
    ]),
  }),
  makeSkill({
    name: 'operations/weekly-report',
    display_name: '周报自动起草',
    description: '聚合 OKR / IM / 日历 / Git 数据，自动起草个人 / 团队周报',
    category: 'operations',
    type: 'workflow',
    triggers: ['写周报', '周报', 'weekly report'],
    personas: ['流程管家', '安心助理'],
    requires_apps: ['feishu', 'github'],
    dependencies: ['operations/okr-tracker'],
    keywords: ['weekly', '周报', 'report'],
    icon: '📅',
    body: md('operations/weekly-report — 周报', [
      '默认模板：本周完成 / 下周计划 / 风险阻塞 / 数据指标。',
    ]),
  }),
  makeSkill({
    name: 'operations/calendar-coordinate',
    display_name: '多人日程协调',
    description: '在多人多日历间寻找空闲时段、自动发出邀请',
    category: 'operations',
    type: 'tool',
    triggers: ['约个会议', '日程协调', 'find a time'],
    personas: ['流程管家', '安心助理'],
    requires_apps: ['outlook', 'google_calendar'],
    dependencies: [],
    keywords: ['calendar', '日程', 'schedule'],
    icon: '🗓️',
    body: md('operations/calendar-coordinate — 日程协调', [
      '基于 free-busy API，自动避开个人偏好时段。',
    ]),
  }),

  // ----- research (4) -----
  makeSkill({
    name: 'research/market-research',
    display_name: '市场研究报告',
    description: '市场容量 / 竞争格局 / 用户画像 / 趋势预测一体化报告',
    category: 'research',
    type: 'agent',
    triggers: ['市场研究', '行业报告', 'market research'],
    personas: ['市场研究员'],
    requires_apps: [],
    dependencies: ['intelligence/web-fetch', 'research/multi-source-synthesize'],
    keywords: ['market', 'research', 'TAM', 'SAM', 'SOM'],
    icon: '📈',
    body: md('research/market-research — 市场研究', [
      'TAM / SAM / SOM + Porter 5 力 + SWOT。',
    ]),
  }),
  makeSkill({
    name: 'research/competitor-monitor',
    display_name: '竞品监控',
    description: '官网 / 公众号 / 应用商店 / 招聘的竞品异动监控',
    category: 'research',
    type: 'agent',
    triggers: ['监控竞品', '竞品动态', 'competitor monitor'],
    personas: ['市场研究员', '获客猎手'],
    requires_apps: [],
    dependencies: ['intelligence/web-fetch', 'system/schedule'],
    keywords: ['competitor', '监控', '竞品'],
    icon: '👀',
    enabled: true,
    body: md('research/competitor-monitor — 竞品监控', [
      '日 / 周 / 月维度调度，diff 后推送到 IM。',
    ]),
  }),
  makeSkill({
    name: 'research/industry-trends',
    display_name: '行业趋势识别',
    description: '从研报 / 论文 / 新闻中识别新兴趋势与拐点信号',
    category: 'research',
    type: 'workflow',
    triggers: ['行业趋势', 'industry trends', '趋势识别'],
    personas: ['市场研究员'],
    requires_apps: [],
    dependencies: ['intelligence/web-fetch'],
    keywords: ['trends', '趋势', '行业'],
    icon: '📡',
    body: md('research/industry-trends — 行业趋势', [
      'Embedding + clustering + LLM 解读。',
    ]),
  }),
  makeSkill({
    name: 'research/company-investigation',
    display_name: '公司深度调查',
    description: '客户 / 供应商 / 投资标的的多维信息调查',
    category: 'research',
    type: 'agent',
    triggers: ['查一下这家公司', '公司调查', 'company investigation'],
    personas: ['尽调专家', '获客猎手'],
    requires_apps: ['qichacha'],
    dependencies: ['legal/due-diligence'],
    keywords: ['investigation', '尽调', '公司'],
    icon: '🕵️',
    body: md('research/company-investigation — 公司调查', [
      '整合工商、舆情、招聘、专利、品牌、客户案例。',
    ]),
  }),

  // ----- marketing (4) -----
  makeSkill({
    name: 'marketing/linkedin-outreach',
    display_name: 'LinkedIn 触达',
    description: '生成个性化 LinkedIn 开场白 + 跟进序列',
    category: 'marketing',
    type: 'workflow',
    triggers: ['LinkedIn 触达', '开发信', 'linkedin outreach'],
    personas: ['获客猎手'],
    requires_apps: ['linkedin'],
    dependencies: [],
    keywords: ['outreach', 'linkedin', 'lead'],
    icon: '🤝',
    body: md('marketing/linkedin-outreach — LinkedIn 触达', [
      '基于目标画像生成 3 段式触达序列（首触 / 跟进 / 收口）。',
    ]),
  }),
  makeSkill({
    name: 'marketing/email-campaign',
    display_name: '邮件营销活动',
    description: 'EDM 主题 + 正文 + A/B 变体 + 发送时机建议',
    category: 'marketing',
    type: 'workflow',
    triggers: ['EDM', '邮件营销', 'email campaign'],
    personas: ['获客猎手', '内容总监'],
    requires_apps: ['mailchimp'],
    dependencies: [],
    keywords: ['email', 'EDM', 'campaign'],
    icon: '📧',
    body: md('marketing/email-campaign — EDM', [
      '内置 20+ 行业模板 + GPT 改写。',
    ]),
  }),
  makeSkill({
    name: 'marketing/seo-keyword',
    display_name: 'SEO 关键词研究',
    description: '关键词扩展 / 难度评估 / 内容 brief 建议',
    category: 'marketing',
    type: 'tool',
    triggers: ['SEO', '关键词', 'keyword research'],
    personas: ['获客猎手', '内容总监'],
    requires_apps: ['ahrefs'],
    dependencies: [],
    keywords: ['SEO', 'keyword'],
    icon: '🔑',
    body: md('marketing/seo-keyword — SEO', [
      '聚合 Ahrefs / Semrush / Google Suggest。',
    ]),
  }),
  makeSkill({
    name: 'marketing/ads-analysis',
    display_name: '广告投放分析',
    description: 'Meta / Google / TikTok 广告 ROI 与素材表现分析',
    category: 'marketing',
    type: 'workflow',
    triggers: ['广告投放', '投放复盘', 'ads analysis'],
    personas: ['获客猎手', '跨境电商助手'],
    requires_apps: ['google_ads', 'meta_ads'],
    dependencies: [],
    keywords: ['ads', '投放', 'ROAS'],
    icon: '📣',
    body: md('marketing/ads-analysis — 投放分析', [
      'ROAS / CTR / CVR / CPC + 素材聚类。',
    ]),
  }),

  // ----- content (3) -----
  makeSkill({
    name: 'content/wechat-article',
    display_name: '微信公众号文章',
    description: '选题 → 大纲 → 正文 → 标题 → 配图建议一体化',
    category: 'content',
    type: 'workflow',
    triggers: ['公众号', 'wechat article', '写公众号'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['wechat', '公众号', 'article'],
    icon: '📰',
    enabled: true,
    body: md('content/wechat-article — 公众号文章', [
      '输出 markdown 正文 + 5 个备选标题 + 3 个封面建议。',
    ]),
  }),
  makeSkill({
    name: 'content/video-script',
    display_name: '短视频脚本',
    description: '抖音 / 视频号 / TikTok 脚本（hook + body + CTA）',
    category: 'content',
    type: 'workflow',
    triggers: ['视频脚本', '抖音脚本', 'video script'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['video', 'script', '短视频'],
    icon: '🎬',
    body: md('content/video-script — 短视频脚本', [
      '内置 6 种 hook 模式 + 节奏建议。',
    ]),
  }),
  makeSkill({
    name: 'content/poster-design',
    display_name: '海报文案',
    description: '海报主标 / 副标 / 钩子 / 行动号召文案',
    category: 'content',
    type: 'tool',
    triggers: ['海报文案', 'poster copy'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['poster', 'copy', '海报'],
    icon: '🖼️',
    body: md('content/poster-design — 海报文案', [
      '输出 3 套不同情绪基调（激进 / 专业 / 温和）。',
    ]),
  }),

  // ----- design (3) -----
  makeSkill({
    name: 'design/canvas-design',
    display_name: '画布式视觉设计',
    description: '海报 / KV / 社媒图（PNG / PDF）',
    category: 'design',
    type: 'workflow',
    triggers: ['做一张海报', 'canvas design', 'KV 设计'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['canvas', 'design', 'KV'],
    icon: '🎨',
    body: md('design/canvas-design — 画布设计', [
      '基于 cowork canvas-design skill 二次封装。',
    ]),
  }),
  makeSkill({
    name: 'design/brand-guidelines',
    display_name: '品牌规范应用',
    description: '将企业 VI / 品牌色 / 字体应用到内容产出',
    category: 'design',
    type: 'tool',
    triggers: ['品牌色', '品牌规范', 'brand guidelines'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['brand', 'VI', '品牌'],
    icon: '🏷️',
    body: md('design/brand-guidelines — 品牌规范', [
      '上传一次品牌手册，后续所有产出自动套用。',
    ]),
  }),
  makeSkill({
    name: 'design/theme-factory',
    display_name: '主题样式工厂',
    description: '为 PPT / 文档 / 落地页生成成套配色 + 字体方案',
    category: 'design',
    type: 'tool',
    triggers: ['主题', 'theme factory', '配色'],
    personas: ['内容总监'],
    requires_apps: [],
    dependencies: [],
    keywords: ['theme', '配色', '字体'],
    icon: '🌈',
    body: md('design/theme-factory — 主题工厂', [
      '基于 cowork theme-factory skill 二次封装。',
    ]),
  }),

  // ----- office (5) — cowork 移植 -----
  makeSkill({
    name: 'office/docx',
    display_name: 'Word 文档读写',
    description: '创建 / 读取 / 编辑 .docx，含目录、页码、表格、轨道修订',
    category: 'office',
    type: 'tool',
    triggers: ['写一个 word', '改一下 docx', '生成 word', 'word doc'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['docx', 'word', 'document'],
    icon: '📄',
    enabled: true,
    body: md('office/docx — Word 读写（cowork 移植 P5 Body B）', [
      '基于 anthropic docx skill 移植，提供原生 .docx 操作能力。',
      '',
      '能力清单：',
      '- 创建带页码 / 目录 / 抬头的正式文档',
      '- 提取并重组现有 .docx 内容',
      '- 插入 / 替换图片',
      '- 全文 find-replace',
      '- 轨道修订 / 评论',
    ]),
  }),
  makeSkill({
    name: 'office/xlsx',
    display_name: 'Excel 表格处理',
    description: '读 / 写 / 编辑 .xlsx，含公式、图表、清洗、CSV 互转',
    category: 'office',
    type: 'tool',
    triggers: ['做个表格', '处理 excel', 'open xlsx', 'excel 公式'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['xlsx', 'excel', 'csv'],
    icon: '📊',
    enabled: true,
    body: md('office/xlsx — Excel（cowork 移植 P5 Body C）', [
      '基于 anthropic xlsx skill 移植。',
      '',
      '能力：公式 / 数据透视 / 图表 / 多 sheet / 数据清洗。',
    ]),
  }),
  makeSkill({
    name: 'office/pptx',
    display_name: 'PowerPoint 幻灯片',
    description: '生成 / 读取 / 编辑 .pptx，含模板、备注、布局',
    category: 'office',
    type: 'tool',
    triggers: ['做个 PPT', '幻灯片', 'pptx', 'slide deck'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['pptx', 'ppt', 'slides'],
    icon: '🎞️',
    enabled: true,
    body: md('office/pptx — PowerPoint（cowork 移植 P5 Body D）', [
      '基于 anthropic pptx skill 移植，使用 python-pptx。',
    ]),
  }),
  makeSkill({
    name: 'office/pdf',
    display_name: 'PDF 处理',
    description: '抽取文本 / 表格、合并拆分、加水印、表单填充、OCR',
    category: 'office',
    type: 'tool',
    triggers: ['处理 PDF', '合并 pdf', '提取 pdf', 'pdf ocr'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['pdf', 'ocr'],
    icon: '📑',
    enabled: true,
    body: md('office/pdf — PDF（cowork 移植 P5 Body E）', [
      '基于 anthropic pdf skill 移植。',
    ]),
  }),
  makeSkill({
    name: 'office/doc-coauthoring',
    display_name: '文档协同写作',
    description: '结构化协同：上下文 → 迭代 → 读者验证',
    category: 'office',
    type: 'workflow',
    triggers: ['一起写文档', '协同写', 'doc coauthoring'],
    personas: ['流程管家', '内容总监'],
    requires_apps: [],
    dependencies: ['office/docx'],
    keywords: ['coauthoring', 'doc', '协同'],
    icon: '✍️',
    body: md('office/doc-coauthoring — 协同写作', [
      '基于 anthropic doc-coauthoring skill 移植。',
    ]),
  }),

  // ----- ecommerce (5) -----
  makeSkill({
    name: 'ecommerce/product-sourcing',
    display_name: '选品 / 货源',
    description: '基于趋势 + 利润空间 + 竞争度的智能选品',
    category: 'ecommerce',
    type: 'agent',
    triggers: ['选品', 'product sourcing', '货源'],
    personas: ['跨境电商助手'],
    requires_apps: ['1688', 'alibaba'],
    dependencies: ['research/industry-trends'],
    keywords: ['sourcing', '选品', 'ecommerce'],
    icon: '🛍️',
    body: md('ecommerce/product-sourcing — 选品', [
      '阿里 1688 + Amazon BSR + Google Trends 三角验证。',
    ]),
  }),
  makeSkill({
    name: 'ecommerce/supplier-verify',
    display_name: '供应商背景核验',
    description: '工商 + 海关 + 历史询盘交叉核验供应商',
    category: 'ecommerce',
    type: 'workflow',
    triggers: ['核实供应商', '查供应商', 'supplier verify'],
    personas: ['跨境电商助手'],
    requires_apps: ['qichacha'],
    dependencies: ['legal/due-diligence'],
    keywords: ['supplier', '供应商', '核验'],
    icon: '🏭',
    body: md('ecommerce/supplier-verify — 供应商核验', [
      '输出红黄绿三色推荐 + 风险点列表。',
    ]),
  }),
  makeSkill({
    name: 'ecommerce/ai-bargaining',
    display_name: 'AI 砍价助手',
    description: '基于历史成交价 + 竞品报价的 AI 砍价话术',
    category: 'ecommerce',
    type: 'tool',
    triggers: ['砍价', 'bargaining', '议价'],
    personas: ['跨境电商助手'],
    requires_apps: [],
    dependencies: [],
    keywords: ['bargain', '砍价', '议价'],
    icon: '💬',
    body: md('ecommerce/ai-bargaining — AI 砍价', [
      '6 套谈判节奏（quick / steady / aggressive ...）。',
    ]),
  }),
  makeSkill({
    name: 'ecommerce/store-builder',
    display_name: '独立站搭建',
    description: 'Shopify / WooCommerce 一键开店与主题配置',
    category: 'ecommerce',
    type: 'workflow',
    triggers: ['开店', '独立站', 'store builder', 'shopify'],
    personas: ['跨境电商助手'],
    requires_apps: ['shopify'],
    dependencies: ['design/theme-factory'],
    keywords: ['shopify', 'store', '独立站'],
    icon: '🏬',
    body: md('ecommerce/store-builder — 独立站', [
      '从域名 → 主题 → 商品 → 支付 → 物流一站搭好。',
    ]),
  }),
  makeSkill({
    name: 'ecommerce/vat-tax',
    display_name: '跨境 VAT / 关税申报',
    description: '基于订单数据自动准备 VAT 申报与关税估算',
    category: 'ecommerce',
    type: 'workflow',
    triggers: ['VAT 申报', '关税', 'vat tax'],
    personas: ['跨境电商助手', '财税顾问'],
    requires_apps: ['shopify', 'xero'],
    dependencies: ['tax_finance/cross-border-tax'],
    keywords: ['VAT', 'duty', 'ecommerce'],
    icon: '💸',
    body: md('ecommerce/vat-tax — VAT', [
      '与 tax_finance/cross-border-tax 共享估算引擎。',
    ]),
  }),

  // ----- sales (3) -----
  makeSkill({
    name: 'sales/crm-sync',
    display_name: 'CRM 双向同步',
    description: '客户 / 商机 / 联系人在 IM 与 CRM 之间双向同步',
    category: 'sales',
    type: 'tool',
    triggers: ['CRM', '同步客户', 'crm sync'],
    personas: ['获客猎手'],
    requires_apps: ['salesforce', 'hubspot'],
    dependencies: [],
    keywords: ['CRM', 'sync', 'salesforce'],
    icon: '🔄',
    body: md('sales/crm-sync — CRM 同步', [
      '增量 + 冲突解决（last-write-wins + 字段级 merge）。',
    ]),
  }),
  makeSkill({
    name: 'sales/quote-builder',
    display_name: '报价单生成',
    description: '从产品库 + 折扣策略生成正式报价单 PDF',
    category: 'sales',
    type: 'workflow',
    triggers: ['做个报价', '报价单', 'quote'],
    personas: ['获客猎手'],
    requires_apps: [],
    dependencies: ['office/pdf'],
    keywords: ['quote', '报价', 'PDF'],
    icon: '🧾',
    body: md('sales/quote-builder — 报价单', [
      '内置 8 套行业模板 + 多币种 / 多税率。',
    ]),
  }),
  makeSkill({
    name: 'sales/lead-tracking',
    display_name: '线索跟进',
    description: '从首触 → SQL → 商机 → 成交全链路跟进与提醒',
    category: 'sales',
    type: 'agent',
    triggers: ['线索', '跟进', 'lead tracking'],
    personas: ['获客猎手'],
    requires_apps: ['salesforce'],
    dependencies: ['sales/crm-sync', 'system/schedule'],
    keywords: ['lead', 'pipeline', 'sales'],
    icon: '🧲',
    body: md('sales/lead-tracking — 线索跟进', [
      '基于 SLA 自动提醒，长时无动静自动 nurture。',
    ]),
  }),

  // ----- intelligence (4) -----
  makeSkill({
    name: 'intelligence/web-fetch',
    display_name: '网页抓取（白名单）',
    description: '在合规白名单内抓取网页 / 解析正文 / 截图',
    category: 'intelligence',
    type: 'tool',
    triggers: ['抓一下网页', 'fetch url', 'web scraping'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['fetch', 'scrape', 'web'],
    icon: '🌐',
    enabled: true,
    body: md('intelligence/web-fetch — 网页抓取', [
      'Headless Chromium + 反爬保护，rate limit 1 req/s/domain。',
    ]),
  }),
  makeSkill({
    name: 'intelligence/official-api',
    display_name: '官方 API 数据源',
    description: '工商 / 司法 / 知识产权 / 海关等官方 API 统一封装',
    category: 'intelligence',
    type: 'tool',
    triggers: ['官方数据', 'official api'],
    personas: ['尽调专家', '法律顾问'],
    requires_apps: ['qichacha', 'cnipa'],
    dependencies: [],
    keywords: ['api', '官方', '数据'],
    icon: '🏛️',
    body: md('intelligence/official-api — 官方 API', [
      '统一鉴权 + 限流 + 缓存。',
    ]),
  }),
  makeSkill({
    name: 'intelligence/news-monitor',
    display_name: '新闻舆情监控',
    description: '关键词 / 实体 / 行业的舆情聚合与情绪分析',
    category: 'intelligence',
    type: 'agent',
    triggers: ['舆情', '新闻监控', 'news monitor'],
    personas: ['市场研究员', '法律顾问'],
    requires_apps: [],
    dependencies: ['intelligence/web-fetch', 'system/schedule'],
    keywords: ['news', '舆情', 'monitor'],
    icon: '📡',
    body: md('intelligence/news-monitor — 舆情监控', [
      '分钟 / 小时 / 日级调度，sentiment + topic clustering。',
    ]),
  }),
  makeSkill({
    name: 'intelligence/transcribe',
    display_name: '音视频转写',
    description: '会议 / 直播 / 课程录音转文字 + 时间戳',
    category: 'intelligence',
    type: 'tool',
    triggers: ['转写', 'transcribe'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['transcribe', 'asr'],
    icon: '🎙️',
    body: md('intelligence/transcribe — 转写', [
      'Whisper-large-v3 + 中文标点 + 多说话人分离。',
    ]),
  }),

  // ----- decision (3) -----
  makeSkill({
    name: 'decision/data-dashboard',
    display_name: '数据驾驶舱',
    description: '把多源指标拼成可交互 dashboard',
    category: 'decision',
    type: 'workflow',
    triggers: ['数据看板', 'dashboard', '驾驶舱'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['dashboard', 'BI'],
    icon: '🧭',
    body: md('decision/data-dashboard — 驾驶舱', [
      '内置 12 套常用看板模板。',
    ]),
  }),
  makeSkill({
    name: 'decision/multi-option-compare',
    display_name: '多方案智能对比',
    description: '在多个候选方案间按多维指标加权对比 + 推荐',
    category: 'decision',
    type: 'workflow',
    triggers: ['方案对比', 'compare options'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['compare', 'decision'],
    icon: '🆚',
    body: md('decision/multi-option-compare — 方案对比', [
      'AHP / TOPSIS 加权法。',
    ]),
  }),
  makeSkill({
    name: 'decision/risk-assessment',
    display_name: '风险评估',
    description: '识别 / 量化 / 排序业务风险并给出缓释方案',
    category: 'decision',
    type: 'workflow',
    triggers: ['风险评估', 'risk assessment'],
    personas: ['法律顾问', '尽调专家'],
    requires_apps: [],
    dependencies: [],
    keywords: ['risk', '评估'],
    icon: '⚠️',
    body: md('decision/risk-assessment — 风险评估', [
      '5×5 风险矩阵 + 缓释建议。',
    ]),
  }),

  // ----- system (4) -----
  makeSkill({
    name: 'system/skill-creator',
    display_name: '技能创建器',
    description: '基于自然语言对话，引导用户创建新 skill 并落盘',
    category: 'system',
    type: 'agent',
    triggers: ['创建技能', 'create skill', 'new skill'],
    personas: ['安心助理'],
    requires_apps: [],
    dependencies: [],
    keywords: ['skill', 'creator', 'meta'],
    icon: '🛠️',
    enabled: true,
    body: md('system/skill-creator — 技能创建器', [
      '生成 SKILL.md 草稿 + 触发词 + 示例 payload。',
    ]),
  }),
  makeSkill({
    name: 'system/mcp-builder',
    display_name: 'MCP 服务搭建',
    description: '从 OpenAPI / SDK 自动生成 MCP server 代码',
    category: 'system',
    type: 'workflow',
    triggers: ['MCP', '搭建 MCP', 'mcp builder'],
    personas: ['安心助理'],
    requires_apps: [],
    dependencies: [],
    keywords: ['mcp', 'server'],
    icon: '🔌',
    body: md('system/mcp-builder — MCP', [
      '基于 anthropic mcp-builder skill 移植。',
    ]),
  }),
  makeSkill({
    name: 'system/schedule',
    display_name: '定时调度',
    description: '为 skill / agent 设置 cron / interval / one-shot 调度',
    category: 'system',
    type: 'tool',
    triggers: ['每天', '定时', 'schedule', 'cron'],
    personas: ['全部'],
    requires_apps: [],
    dependencies: [],
    keywords: ['schedule', 'cron', '调度'],
    icon: '⏰',
    enabled: true,
    body: md('system/schedule — 定时调度', [
      '与 P3 ScheduledTasksPage 对接。',
    ]),
  }),
  makeSkill({
    name: 'system/permission-audit',
    display_name: '权限审计',
    description: '审计哪些 skill 在使用哪些 OAuth 权限，最小化授权',
    category: 'system',
    type: 'workflow',
    triggers: ['权限审计', 'permission audit'],
    personas: ['安心助理'],
    requires_apps: [],
    dependencies: [],
    keywords: ['permission', 'audit', 'security'],
    icon: '🔐',
    body: md('system/permission-audit — 权限审计', [
      '生成最小权限建议 + 一键收紧。',
    ]),
  }),
]

// ===== 内存状态 =====

const skillsMap = new Map<string, Skill>()
seeds.forEach((s) => skillsMap.set(s.name, s))

// ===== Mock 实现 =====

export async function mockListSkills(params: ListSkillsParams = {}): Promise<Skill[]> {
  await sleep(120)
  let list = Array.from(skillsMap.values()).map((s) => {
    // list 接口仅返回 body_excerpt，不返回完整 body
    const { body, ...rest } = s
    void body
    return rest as Skill
  })
  if (params.category) {
    list = list.filter((s) => s.category === params.category)
  }
  if (params.persona) {
    list = list.filter(
      (s) => s.personas.includes(params.persona!) || s.personas.includes('全部'),
    )
  }
  if (params.enabled !== undefined) {
    list = list.filter((s) => s.enabled === params.enabled)
  }
  return list
}

export async function mockGetSkill(name: string): Promise<Skill> {
  await sleep(100)
  const s = skillsMap.get(name)
  if (!s) throw new Error(`Skill not found: ${name}`)
  return { ...s }
}

export async function mockToggleSkill(name: string, enabled: boolean): Promise<Skill> {
  await sleep(150)
  const s = skillsMap.get(name)
  if (!s) throw new Error(`Skill not found: ${name}`)
  const updated = { ...s, enabled }
  skillsMap.set(name, updated)
  return updated
}

export async function mockUploadSkill(file: File): Promise<SkillUploadResult> {
  await sleep(400)
  // 简化版 SKILL.md frontmatter 解析（仅 mock 用途）
  const text = await file.text()
  const fmMatch = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/)
  const meta: Record<string, string> = {}
  let body = text
  if (fmMatch) {
    body = fmMatch[2]
    fmMatch[1].split('\n').forEach((line) => {
      const m = line.match(/^([a-zA-Z_]+):\s*(.+)$/)
      if (m) meta[m[1]] = m[2].trim().replace(/^['"]|['"]$/g, '')
    })
  }
  const name = meta.name || `uploaded/${file.name.replace(/\.md$/, '')}`
  const skill: Skill = {
    name,
    display_name: meta.display_name || name,
    description: meta.description || '由用户上传的自定义技能',
    version: meta.version || '0.1.0',
    category: ((meta.category as Skill['category']) || 'system') as Skill['category'],
    type: ((meta.type as Skill['type']) || 'tool') as Skill['type'],
    author: meta.author || '用户上传',
    triggers: (meta.triggers || '').split(',').map((s) => s.trim()).filter(Boolean),
    personas: (meta.personas || '安心助理').split(',').map((s) => s.trim()).filter(Boolean),
    requires_apps: (meta.requires_apps || '').split(',').map((s) => s.trim()).filter(Boolean),
    dependencies: (meta.dependencies || '').split(',').map((s) => s.trim()).filter(Boolean),
    keywords: (meta.keywords || '').split(',').map((s) => s.trim()).filter(Boolean),
    enabled: true,
    icon: meta.icon || '✨',
    body,
    body_excerpt: excerpt(body),
  }
  skillsMap.set(skill.name, skill)
  const warnings: string[] = []
  if (!fmMatch) warnings.push('未检测到 frontmatter，使用默认元数据')
  if (!meta.triggers) warnings.push('triggers 为空，可能无法被自动触发')
  return { skill, warnings }
}

export async function mockExecuteSkill(
  name: string,
  payload: unknown,
): Promise<SkillExecuteResult> {
  await sleep(600)
  const s = skillsMap.get(name)
  if (!s) {
    return {
      ok: false,
      output: null,
      duration_ms: 0,
      error: `Skill not found: ${name}`,
    }
  }
  return {
    ok: true,
    output: {
      message: `[mock] 已模拟执行 ${name}`,
      received_payload: payload,
      skill_summary: s.description,
    },
    duration_ms: 580,
    trace_id: `mock-trace-${Date.now().toString(36)}`,
  }
}

export async function mockMatchTriggers(q: string): Promise<Skill[]> {
  await sleep(80)
  const lower = q.toLowerCase()
  return Array.from(skillsMap.values())
    .filter((s) =>
      s.triggers.some((t) => t.toLowerCase().includes(lower)) ||
      s.keywords.some((k) => k.toLowerCase().includes(lower)) ||
      s.display_name.toLowerCase().includes(lower),
    )
    .slice(0, 10)
}
