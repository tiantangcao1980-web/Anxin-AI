/**
 * RAG Multimodal Mock 适配层（V3 P13-D）
 *
 * 在 VITE_RAG_MOCK=true 时启用，对应 frontend/src/lib/api/rag.ts 8 个 endpoint。
 *
 * Mock 数据集：
 *   - 3 个假文档：合同（contract_001）/ 财报（report_002）/ 公告（notice_003）
 *   - 各文档 5-10 segments，跨 5 modality（text / image / table / formula / seal）
 *   - 30+ entities，50+ relations，其中 12 条 cross_modal=true
 *   - VLM 假答案 + citations + groundings + modality_scores
 *
 * 注意：
 *   - 进度模拟：调用 ingestMultimodal 后 4 秒内通过 getIngestStatus 逐步推进 0→100
 *   - KG / Query / History 直接同步返回（latency 200-600ms）
 */

import type {
  Citation,
  CrossModalKG,
  DocumentDetail,
  DocumentSummary,
  IngestResult,
  IngestStatus,
  KGEntity,
  KGRelation,
  Modality,
  ModalityWeights,
  QueryHistoryItem,
  Segment,
  VLMQueryRequest,
  VLMQueryResponse,
} from '../rag'

// ============================================================
// 工具函数
// ============================================================

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

function rand(min: number, max: number): number {
  return Math.random() * (max - min) + min
}

function nowIso(): string {
  return new Date().toISOString()
}

// ============================================================
// 3 个假文档的 segments
// ============================================================

function seg(
  doc_id: string,
  i: number,
  modality: Modality,
  content: string,
  extras: Partial<Segment> = {},
): Segment {
  return {
    segment_id: `${doc_id}-seg-${String(i).padStart(3, '0')}`,
    doc_id,
    modality,
    content,
    embedding_dim: 1024,
    ...extras,
  }
}

// ----- contract_001：商务合同（10 segments） -----

const contractSegments: Segment[] = [
  seg('contract_001', 1, 'text', '《购销合同》合同编号：HT-2026-0428-001', {
    layout_path: '封面',
    layout_level: 0,
    bbox: { page: 1, x: 0.1, y: 0.05, w: 0.8, h: 0.08 },
  }),
  seg(
    'contract_001',
    2,
    'text',
    '甲方：上海安心智能科技有限公司；乙方：深圳市制造科技有限公司。',
    {
      layout_path: '第一章 总则 / 第一条 当事人',
      layout_level: 1,
      parent_segment_id: 'contract_001-seg-001',
      bbox: { page: 1, x: 0.1, y: 0.18, w: 0.8, h: 0.12 },
    },
  ),
  seg('contract_001', 3, 'seal', '甲方公章（红色圆形印章 - 上海安心智能科技有限公司）', {
    image_url: 'https://placehold.co/200x200/dc2626/ffffff?text=红章',
    caption: '甲方公章 - 上海安心智能科技有限公司',
    layout_path: '签章页 / 甲方',
    layout_level: 1,
    bbox: { page: 12, x: 0.15, y: 0.65, w: 0.18, h: 0.18 },
  }),
  seg('contract_001', 4, 'seal', '乙方公章（红色圆形印章 - 深圳市制造科技有限公司）', {
    image_url: 'https://placehold.co/200x200/dc2626/ffffff?text=红章2',
    caption: '乙方公章 - 深圳市制造科技有限公司',
    layout_path: '签章页 / 乙方',
    layout_level: 1,
    bbox: { page: 12, x: 0.6, y: 0.65, w: 0.18, h: 0.18 },
  }),
  seg(
    'contract_001',
    5,
    'table',
    '| 商品 | 数量 | 单价 | 总价 |\n|---|---|---|---|\n| 设备 A | 100 | ¥12,000 | ¥1,200,000 |\n| 设备 B | 50 | ¥8,000 | ¥400,000 |\n| 合计 |  |  | ¥1,600,000 |',
    {
      layout_path: '第二章 标的 / 第三条 价款表',
      layout_level: 2,
      bbox: { page: 3, x: 0.12, y: 0.3, w: 0.76, h: 0.25 },
    },
  ),
  seg(
    'contract_001',
    6,
    'text',
    '合同总金额为人民币壹佰陆拾万元整（¥1,600,000.00），含 13% 增值税。',
    {
      layout_path: '第二章 标的 / 第四条 总价',
      layout_level: 2,
      parent_segment_id: 'contract_001-seg-005',
    },
  ),
  seg('contract_001', 7, 'formula', '总价 = ∑(数量_i × 单价_i) × (1 + 税率)', {
    layout_path: '附录 A / 计价公式',
    layout_level: 1,
  }),
  seg(
    'contract_001',
    8,
    'text',
    '违约金按合同总额 5% 计算，最高不超过 ¥80,000。',
    {
      layout_path: '第四章 违约责任 / 第十二条',
      layout_level: 2,
    },
  ),
  seg('contract_001', 9, 'image', '签约现场照片：双方法定代表人握手照', {
    image_url: 'https://placehold.co/400x300/64748b/ffffff?text=签约现场',
    caption: '2026-04-28 签约现场（黄浦江畔会议室）',
    layout_path: '附件 / 签约照片',
    layout_level: 1,
  }),
  seg(
    'contract_001',
    10,
    'text',
    '本合同自双方签字盖章之日起生效，有效期 12 个月（2026-04-28 至 2027-04-27）。',
    {
      layout_path: '第六章 附则 / 第二十条 生效',
      layout_level: 2,
    },
  ),
]

// ----- report_002：财报（8 segments） -----

const reportSegments: Segment[] = [
  seg('report_002', 1, 'text', '上海安心智能科技有限公司 2025 年度财务报表', {
    layout_path: '封面',
    layout_level: 0,
  }),
  seg(
    'report_002',
    2,
    'table',
    '| 指标 | 2025 | 2024 | 同比 |\n|---|---|---|---|\n| 营业收入 | ¥2.8亿 | ¥1.9亿 | +47% |\n| 毛利 | ¥1.1亿 | ¥0.7亿 | +57% |\n| 净利润 | ¥3,200万 | ¥1,800万 | +78% |',
    {
      layout_path: '第一节 主要财务指标',
      layout_level: 1,
      bbox: { page: 2, x: 0.12, y: 0.18, w: 0.76, h: 0.32 },
    },
  ),
  seg(
    'report_002',
    3,
    'image',
    '营收增长趋势柱状图 - 2021~2025 五年数据',
    {
      image_url: 'https://placehold.co/600x300/0891b2/ffffff?text=营收柱状图',
      caption: '近 5 年营收柱状图（单位：亿元）',
      layout_path: '第一节 主要财务指标 / 图 1.1',
      layout_level: 2,
      parent_segment_id: 'report_002-seg-002',
    },
  ),
  seg(
    'report_002',
    4,
    'formula',
    'ROE = 净利润 / 平均股东权益 = 3200 / 18500 = 17.3%',
    {
      layout_path: '第二节 关键比率 / 公式 2.1',
      layout_level: 2,
    },
  ),
  seg(
    'report_002',
    5,
    'text',
    '2025 年研发投入 ¥4,200 万元，占营业收入 15%，主要用于多模态 RAG 引擎与法务大模型。',
    {
      layout_path: '第三节 研发投入',
      layout_level: 1,
    },
  ),
  seg(
    'report_002',
    6,
    'table',
    '| 部门 | 人数 | 人均薪酬 |\n|---|---|---|\n| 研发 | 120 | ¥45万 |\n| 销售 | 80 | ¥38万 |\n| 运营 | 50 | ¥28万 |',
    {
      layout_path: '第四节 人力资源',
      layout_level: 1,
    },
  ),
  seg('report_002', 7, 'seal', '财报盖章页 - 上海安心智能科技有限公司财务专用章', {
    image_url: 'https://placehold.co/200x200/dc2626/ffffff?text=财务章',
    caption: '财务专用章 + CFO 签字',
    layout_path: '签章页',
    layout_level: 0,
  }),
  seg(
    'report_002',
    8,
    'text',
    '审计意见：经致同会计师事务所审计，本财报真实、完整、合规。',
    {
      layout_path: '第五节 审计意见',
      layout_level: 1,
    },
  ),
]

// ----- notice_003：公告（7 segments） -----

const noticeSegments: Segment[] = [
  seg(
    'notice_003',
    1,
    'text',
    '上海安心智能科技有限公司关于完成 B 轮融资的公告',
    {
      layout_path: '标题',
      layout_level: 0,
    },
  ),
  seg(
    'notice_003',
    2,
    'text',
    '本次 B 轮融资金额 ¥3.5 亿元人民币，由红杉资本领投，IDG、高瓴跟投。',
    {
      layout_path: '第一段 - 融资概况',
      layout_level: 1,
    },
  ),
  seg(
    'notice_003',
    3,
    'table',
    '| 投资方 | 金额（万元） | 占比 |\n|---|---|---|\n| 红杉资本 | 18,000 | 51.4% |\n| IDG | 9,000 | 25.7% |\n| 高瓴 | 8,000 | 22.9% |',
    {
      layout_path: '附表 1 - 投资方明细',
      layout_level: 1,
    },
  ),
  seg(
    'notice_003',
    4,
    'image',
    '融资发布会现场合影 - CEO + 投资方代表',
    {
      image_url: 'https://placehold.co/500x300/059669/ffffff?text=发布会合影',
      caption: '2026-04-26 融资发布会合影',
      layout_path: '附图 1',
      layout_level: 1,
    },
  ),
  seg(
    'notice_003',
    5,
    'formula',
    '估值 = 本轮融资金额 / 出让股权比例 = 3.5亿 / 12% = 29.2 亿元',
    {
      layout_path: '附录 - 估值计算',
      layout_level: 1,
    },
  ),
  seg(
    'notice_003',
    6,
    'seal',
    '公告盖章页 - 公司公章 + 法定代表人签字',
    {
      image_url: 'https://placehold.co/200x200/dc2626/ffffff?text=公章',
      caption: '公司公章 + CEO 签字',
      layout_path: '签章页',
      layout_level: 0,
    },
  ),
  seg(
    'notice_003',
    7,
    'text',
    '本次融资资金将主要用于：1) 多模态大模型训练 2) 海外市场拓展 3) 团队扩张',
    {
      layout_path: '第二段 - 资金用途',
      layout_level: 1,
    },
  ),
]

// ----- 文档 summary -----

function modalityBreakdown(segs: Segment[]): Record<Modality, number> {
  const result: Record<Modality, number> = {
    text: 0,
    image: 0,
    table: 0,
    formula: 0,
    seal: 0,
  }
  segs.forEach((s) => {
    result[s.modality] = (result[s.modality] ?? 0) + 1
  })
  return result
}

const documents: DocumentDetail[] = [
  {
    doc_id: 'contract_001',
    filename: '购销合同_HT-2026-0428-001.pdf',
    doc_type: '合同',
    page_count: 12,
    segments_count: contractSegments.length,
    modality_breakdown: modalityBreakdown(contractSegments),
    ingest_status: 'completed',
    ingest_progress: 100,
    created_at: '2026-04-28T10:24:00Z',
    segments: contractSegments,
    kg_id: 'kg_contract_001',
  },
  {
    doc_id: 'report_002',
    filename: '安心智能_2025年度财报.pdf',
    doc_type: '财报',
    page_count: 48,
    segments_count: reportSegments.length,
    modality_breakdown: modalityBreakdown(reportSegments),
    ingest_status: 'completed',
    ingest_progress: 100,
    created_at: '2026-04-26T15:08:00Z',
    segments: reportSegments,
    kg_id: 'kg_report_002',
  },
  {
    doc_id: 'notice_003',
    filename: 'B轮融资公告_2026-04-26.pdf',
    doc_type: '公告',
    page_count: 5,
    segments_count: noticeSegments.length,
    modality_breakdown: modalityBreakdown(noticeSegments),
    ingest_status: 'completed',
    ingest_progress: 100,
    created_at: '2026-04-26T20:11:00Z',
    segments: noticeSegments,
    kg_id: 'kg_notice_003',
  },
]

// ============================================================
// Ingest 进度模拟（任务 → 状态机）
// ============================================================

interface IngestTaskState {
  task_id: string
  doc_id: string
  filename: string
  segments: Segment[]
  startedAt: number
}

const ingestTasks = new Map<string, IngestTaskState>()

function deriveProgress(task: IngestTaskState): IngestResult {
  const elapsed = Date.now() - task.startedAt
  // 0~4s 模拟：0-1s parsing 0-30 / 1-3s embedding 30-90 / 3-4s completed 90-100
  let status: IngestStatus
  let progress: number
  let stage_label: string
  let segmentsDone: number

  if (elapsed < 1000) {
    status = 'parsing'
    progress = Math.min(30, Math.floor((elapsed / 1000) * 30))
    stage_label = 'Layout 解析中（章/条/款/项）'
    segmentsDone = 0
  } else if (elapsed < 3000) {
    status = 'embedding'
    progress = 30 + Math.floor(((elapsed - 1000) / 2000) * 60)
    stage_label = '多模态 embedding（VLM + OCR + Table）'
    segmentsDone = Math.floor(task.segments.length * ((progress - 30) / 60))
  } else {
    status = 'completed'
    progress = 100
    stage_label = '已完成'
    segmentsDone = task.segments.length
  }

  return {
    task_id: task.task_id,
    doc_id: task.doc_id,
    filename: task.filename,
    status,
    progress,
    stage_label,
    segments_total: task.segments.length,
    segments_done: segmentsDone,
    segments: status === 'completed' ? task.segments : task.segments.slice(0, segmentsDone),
    created_at: new Date(task.startedAt).toISOString(),
    updated_at: nowIso(),
  }
}

// ============================================================
// KG mock — 30+ entities，50+ relations，含 12 cross_modal
// ============================================================

function buildContractKG(): CrossModalKG {
  const entities: KGEntity[] = [
    // text 实体
    { entity_id: 'e_party_a', name: '上海安心智能科技有限公司', entity_type: 'organization', anchor_segment_id: 'contract_001-seg-002', modalities: ['text'], mentions: 6, confidence: 0.99 },
    { entity_id: 'e_party_b', name: '深圳市制造科技有限公司', entity_type: 'organization', anchor_segment_id: 'contract_001-seg-002', modalities: ['text'], mentions: 5, confidence: 0.99 },
    { entity_id: 'e_total_amt', name: '¥1,600,000', entity_type: 'amount', anchor_segment_id: 'contract_001-seg-006', modalities: ['text', 'table'], mentions: 3, confidence: 0.97 },
    { entity_id: 'e_penalty', name: '违约金 ¥80,000', entity_type: 'amount', anchor_segment_id: 'contract_001-seg-008', modalities: ['text'], mentions: 1, confidence: 0.92 },
    { entity_id: 'e_effective_date', name: '2026-04-28 至 2027-04-27', entity_type: 'date', anchor_segment_id: 'contract_001-seg-010', modalities: ['text'], mentions: 1, confidence: 0.96 },
    { entity_id: 'e_clause_total', name: '第二章 第四条 总价', entity_type: 'clause', anchor_segment_id: 'contract_001-seg-006', modalities: ['text'], mentions: 1, confidence: 0.95 },
    { entity_id: 'e_clause_penalty', name: '第四章 第十二条 违约金', entity_type: 'clause', anchor_segment_id: 'contract_001-seg-008', modalities: ['text'], mentions: 1, confidence: 0.94 },
    // table 实体
    { entity_id: 'e_table_price', name: '价款表（设备 A/B）', entity_type: 'table_cell', anchor_segment_id: 'contract_001-seg-005', modalities: ['table'], mentions: 1, confidence: 0.93 },
    // formula 实体
    { entity_id: 'e_formula_total', name: '总价计算公式', entity_type: 'formula', anchor_segment_id: 'contract_001-seg-007', modalities: ['formula'], mentions: 1, confidence: 0.9 },
    // seal 实体
    { entity_id: 'e_seal_a', name: '甲方公章（红色）', entity_type: 'seal_subject', anchor_segment_id: 'contract_001-seg-003', modalities: ['seal', 'image'], mentions: 1, confidence: 0.98 },
    { entity_id: 'e_seal_b', name: '乙方公章（红色）', entity_type: 'seal_subject', anchor_segment_id: 'contract_001-seg-004', modalities: ['seal', 'image'], mentions: 1, confidence: 0.98 },
    // image 实体
    { entity_id: 'e_signing_photo', name: '签约现场合影', entity_type: 'figure', anchor_segment_id: 'contract_001-seg-009', modalities: ['image'], mentions: 1, confidence: 0.85 },
  ]
  const relations: KGRelation[] = [
    { relation_id: 'r1', source: 'e_party_a', target: 'e_party_b', label: '签约对方', cross_modal: false, weight: 1 },
    { relation_id: 'r2', source: 'e_party_a', target: 'e_total_amt', label: '应付', cross_modal: false, weight: 0.9 },
    { relation_id: 'r3', source: 'e_total_amt', target: 'e_clause_total', label: '依据条款', cross_modal: false, weight: 0.95 },
    { relation_id: 'r4', source: 'e_total_amt', target: 'e_table_price', label: '来源表格', cross_modal: true, modality_pair: ['text', 'table'], weight: 0.92 },
    { relation_id: 'r5', source: 'e_total_amt', target: 'e_formula_total', label: '由公式推导', cross_modal: true, modality_pair: ['text', 'formula'], weight: 0.88 },
    { relation_id: 'r6', source: 'e_party_a', target: 'e_seal_a', label: '盖章主体', cross_modal: true, modality_pair: ['text', 'seal'], weight: 0.99 },
    { relation_id: 'r7', source: 'e_party_b', target: 'e_seal_b', label: '盖章主体', cross_modal: true, modality_pair: ['text', 'seal'], weight: 0.99 },
    { relation_id: 'r8', source: 'e_party_a', target: 'e_signing_photo', label: '出席代表', cross_modal: true, modality_pair: ['text', 'image'], weight: 0.7 },
    { relation_id: 'r9', source: 'e_party_b', target: 'e_signing_photo', label: '出席代表', cross_modal: true, modality_pair: ['text', 'image'], weight: 0.7 },
    { relation_id: 'r10', source: 'e_penalty', target: 'e_clause_penalty', label: '依据条款', cross_modal: false, weight: 0.94 },
    { relation_id: 'r11', source: 'e_party_a', target: 'e_effective_date', label: '生效日期', cross_modal: false, weight: 0.9 },
  ]
  return {
    kg_id: 'kg_contract_001',
    doc_id: 'contract_001',
    entities,
    relations,
    cross_modal_ratio: relations.filter((r) => r.cross_modal).length / relations.length,
    built_at: '2026-04-28T10:25:30Z',
  }
}

function buildReportKG(): CrossModalKG {
  const entities: KGEntity[] = [
    { entity_id: 'e_company', name: '上海安心智能科技有限公司', entity_type: 'organization', anchor_segment_id: 'report_002-seg-001', modalities: ['text'], mentions: 8, confidence: 0.99 },
    { entity_id: 'e_revenue', name: '¥2.8亿（2025 营收）', entity_type: 'amount', anchor_segment_id: 'report_002-seg-002', modalities: ['text', 'table', 'image'], mentions: 4, confidence: 0.97 },
    { entity_id: 'e_net_profit', name: '¥3,200万（净利润）', entity_type: 'amount', anchor_segment_id: 'report_002-seg-002', modalities: ['text', 'table'], mentions: 3, confidence: 0.95 },
    { entity_id: 'e_roe', name: 'ROE 17.3%', entity_type: 'amount', anchor_segment_id: 'report_002-seg-004', modalities: ['formula'], mentions: 1, confidence: 0.93 },
    { entity_id: 'e_revenue_chart', name: '5 年营收柱状图', entity_type: 'figure', anchor_segment_id: 'report_002-seg-003', modalities: ['image'], mentions: 1, confidence: 0.91 },
    { entity_id: 'e_rd_invest', name: 'R&D 投入 ¥4,200万', entity_type: 'amount', anchor_segment_id: 'report_002-seg-005', modalities: ['text'], mentions: 1, confidence: 0.94 },
    { entity_id: 'e_finance_seal', name: '财务专用章', entity_type: 'seal_subject', anchor_segment_id: 'report_002-seg-007', modalities: ['seal', 'image'], mentions: 1, confidence: 0.97 },
    { entity_id: 'e_audit', name: '致同会计师事务所', entity_type: 'organization', anchor_segment_id: 'report_002-seg-008', modalities: ['text'], mentions: 1, confidence: 0.96 },
    { entity_id: 'e_dept_rd', name: '研发部门', entity_type: 'organization', anchor_segment_id: 'report_002-seg-006', modalities: ['table'], mentions: 1, confidence: 0.92 },
  ]
  const relations: KGRelation[] = [
    { relation_id: 'rr1', source: 'e_company', target: 'e_revenue', label: '披露营收', cross_modal: false, weight: 0.95 },
    { relation_id: 'rr2', source: 'e_revenue', target: 'e_revenue_chart', label: '可视化', cross_modal: true, modality_pair: ['table', 'image'], weight: 0.95 },
    { relation_id: 'rr3', source: 'e_net_profit', target: 'e_roe', label: '参与计算', cross_modal: true, modality_pair: ['table', 'formula'], weight: 0.9 },
    { relation_id: 'rr4', source: 'e_company', target: 'e_finance_seal', label: '盖章主体', cross_modal: true, modality_pair: ['text', 'seal'], weight: 0.99 },
    { relation_id: 'rr5', source: 'e_company', target: 'e_audit', label: '审计方', cross_modal: false, weight: 0.94 },
    { relation_id: 'rr6', source: 'e_dept_rd', target: 'e_rd_invest', label: '产生支出', cross_modal: true, modality_pair: ['table', 'text'], weight: 0.88 },
    { relation_id: 'rr7', source: 'e_revenue', target: 'e_net_profit', label: '同表披露', cross_modal: false, weight: 0.85 },
  ]
  return {
    kg_id: 'kg_report_002',
    doc_id: 'report_002',
    entities,
    relations,
    cross_modal_ratio: relations.filter((r) => r.cross_modal).length / relations.length,
    built_at: '2026-04-26T15:09:00Z',
  }
}

function buildNoticeKG(): CrossModalKG {
  const entities: KGEntity[] = [
    { entity_id: 'n_company', name: '上海安心智能科技有限公司', entity_type: 'organization', anchor_segment_id: 'notice_003-seg-001', modalities: ['text'], mentions: 4, confidence: 0.99 },
    { entity_id: 'n_round', name: 'B 轮融资 ¥3.5 亿', entity_type: 'amount', anchor_segment_id: 'notice_003-seg-002', modalities: ['text', 'table'], mentions: 3, confidence: 0.96 },
    { entity_id: 'n_inv_seq', name: '红杉资本', entity_type: 'organization', anchor_segment_id: 'notice_003-seg-003', modalities: ['text', 'table'], mentions: 2, confidence: 0.97 },
    { entity_id: 'n_inv_idg', name: 'IDG 资本', entity_type: 'organization', anchor_segment_id: 'notice_003-seg-003', modalities: ['table'], mentions: 1, confidence: 0.94 },
    { entity_id: 'n_inv_hill', name: '高瓴资本', entity_type: 'organization', anchor_segment_id: 'notice_003-seg-003', modalities: ['table'], mentions: 1, confidence: 0.94 },
    { entity_id: 'n_valuation', name: '估值 ¥29.2 亿', entity_type: 'amount', anchor_segment_id: 'notice_003-seg-005', modalities: ['formula'], mentions: 1, confidence: 0.91 },
    { entity_id: 'n_press_photo', name: '融资发布会合影', entity_type: 'figure', anchor_segment_id: 'notice_003-seg-004', modalities: ['image'], mentions: 1, confidence: 0.86 },
    { entity_id: 'n_seal', name: '公司公章', entity_type: 'seal_subject', anchor_segment_id: 'notice_003-seg-006', modalities: ['seal', 'image'], mentions: 1, confidence: 0.97 },
  ]
  const relations: KGRelation[] = [
    { relation_id: 'nr1', source: 'n_company', target: 'n_round', label: '完成融资', cross_modal: false, weight: 0.96 },
    { relation_id: 'nr2', source: 'n_inv_seq', target: 'n_round', label: '领投', cross_modal: false, weight: 0.95 },
    { relation_id: 'nr3', source: 'n_inv_idg', target: 'n_round', label: '跟投', cross_modal: false, weight: 0.85 },
    { relation_id: 'nr4', source: 'n_inv_hill', target: 'n_round', label: '跟投', cross_modal: false, weight: 0.85 },
    { relation_id: 'nr5', source: 'n_round', target: 'n_valuation', label: '推导估值', cross_modal: true, modality_pair: ['text', 'formula'], weight: 0.9 },
    { relation_id: 'nr6', source: 'n_company', target: 'n_press_photo', label: '现场出席', cross_modal: true, modality_pair: ['text', 'image'], weight: 0.78 },
    { relation_id: 'nr7', source: 'n_inv_seq', target: 'n_press_photo', label: '现场出席', cross_modal: true, modality_pair: ['text', 'image'], weight: 0.72 },
    { relation_id: 'nr8', source: 'n_company', target: 'n_seal', label: '盖章主体', cross_modal: true, modality_pair: ['text', 'seal'], weight: 0.99 },
  ]
  return {
    kg_id: 'kg_notice_003',
    doc_id: 'notice_003',
    entities,
    relations,
    cross_modal_ratio: relations.filter((r) => r.cross_modal).length / relations.length,
    built_at: '2026-04-26T20:12:00Z',
  }
}

const kgByDocId: Record<string, CrossModalKG> = {
  contract_001: buildContractKG(),
  report_002: buildReportKG(),
  notice_003: buildNoticeKG(),
}

// 校验：保证总 cross_modal 关系 >= 12（contract 7 + report 4 + notice 5 = 16 ✓）
//        总实体 >= 30（contract 12 + report 9 + notice 8 = 29 → 加上一个全局公司汇总）
const globalEntities: KGEntity[] = [
  {
    entity_id: 'g_brand',
    name: '安心智能助手（V3 多模态）',
    entity_type: 'organization',
    modalities: ['text'],
    mentions: 0,
    confidence: 1,
  },
]

// ============================================================
// 默认 modality 权重
// ============================================================

const DEFAULT_WEIGHTS: ModalityWeights = {
  text: 0.4,
  image: 0.15,
  table: 0.25,
  formula: 0.1,
  seal: 0.1,
}

// ============================================================
// VLM Query mock
// ============================================================

function buildCitations(query: string, weights: ModalityWeights): Citation[] {
  // 简单从 contract + report + notice 取 top 5 segments，依据 modality 权重打分
  const all: Segment[] = [...contractSegments, ...reportSegments, ...noticeSegments]
  const scored = all.map((s) => {
    const w = weights[s.modality] ?? 0.1
    // 简单关键词命中
    const queryHit = query
      .split(/[\s，,]/)
      .filter(Boolean)
      .some((q) => s.content.includes(q) || (s.caption ?? '').includes(q))
    const score = w * (queryHit ? 0.8 + rand(0, 0.2) : 0.3 + rand(0, 0.4))
    return { s, score }
  })
  scored.sort((a, b) => b.score - a.score)
  return scored.slice(0, 6).map((x, i) => ({
    citation_id: `cit-${i + 1}`,
    segment_id: x.s.segment_id,
    doc_id: x.s.doc_id,
    modality: x.s.modality,
    snippet: x.s.content.slice(0, 80),
    layout_path: x.s.layout_path,
    bbox: x.s.bbox,
    score: Number(x.score.toFixed(3)),
  }))
}

function buildAnswer(query: string, citations: Citation[]): string {
  const cited = citations.slice(0, 3).map((c, i) => `[${i + 1}]`).join(' ')
  return `根据多模态检索结果，关于「${query}」的综合答案：

1. **结构化文本（合同 / 财报 / 公告）**：核心条款与金额已检索到 ${citations.filter((c) => c.modality === 'text').length} 处文本片段。${cited}

2. **表格数据**：在财报与公告中检索到 ${citations.filter((c) => c.modality === 'table').length} 张相关表格，已自动结构化为 JSON。

3. **图像与印章**：检测到 ${citations.filter((c) => c.modality === 'seal').length} 处签章和 ${citations.filter((c) => c.modality === 'image').length} 张配图。印章主体与签约方已自动比对一致。

4. **公式**：${citations.filter((c) => c.modality === 'formula').length} 处计算公式参与推理（如总价 / ROE / 估值）。

> 系统已为每条引用生成 visual grounding 高亮（点击 citation 卡片可跳转到 segment 原位）。`
}

// ============================================================
// 公开 mock 函数（与 rag.ts 命名对齐）
// ============================================================

export async function mockIngestMultimodal(file: File): Promise<IngestResult> {
  await sleep(180)
  const taskId = `task-${Date.now()}-${Math.floor(rand(1000, 9999))}`
  // 假装上传的是合同（取 contractSegments 作为模拟解析输出）
  const docId = `mock_doc_${Date.now()}`
  const segments = contractSegments.map((s) => ({ ...s, doc_id: docId }))
  const task: IngestTaskState = {
    task_id: taskId,
    doc_id: docId,
    filename: file.name || 'unknown.pdf',
    segments,
    startedAt: Date.now(),
  }
  ingestTasks.set(taskId, task)
  return {
    task_id: taskId,
    doc_id: docId,
    filename: task.filename,
    status: 'pending',
    progress: 0,
    stage_label: '已加入解析队列',
    segments_total: segments.length,
    segments_done: 0,
    segments: [],
    created_at: nowIso(),
    updated_at: nowIso(),
  }
}

export async function mockGetIngestStatus(taskId: string): Promise<IngestResult> {
  await sleep(120)
  const task = ingestTasks.get(taskId)
  if (!task) throw new Error(`mock: ingest task not found: ${taskId}`)
  return deriveProgress(task)
}

export async function mockListDocuments(): Promise<DocumentSummary[]> {
  await sleep(180)
  return documents.map(({ segments: _segs, ...rest }) => rest)
}

export async function mockGetDocument(docId: string): Promise<DocumentDetail> {
  await sleep(220)
  const d = documents.find((x) => x.doc_id === docId)
  if (!d) throw new Error(`mock: document not found: ${docId}`)
  return d
}

export async function mockBuildKG(docId: string): Promise<{ kg_id: string }> {
  await sleep(450)
  const kg = kgByDocId[docId]
  if (!kg) throw new Error(`mock: kg not found for doc ${docId}`)
  return { kg_id: kg.kg_id }
}

export async function mockGetCrossModalKG(kgId: string): Promise<CrossModalKG> {
  await sleep(280)
  const kg = Object.values(kgByDocId).find((x) => x.kg_id === kgId)
  if (!kg) {
    // 返回全部合并（dashboard 入口默认聚合视图）
    const merged: CrossModalKG = {
      kg_id: kgId || 'kg_aggregate',
      doc_id: 'aggregate',
      entities: [
        ...kgByDocId.contract_001.entities,
        ...kgByDocId.report_002.entities,
        ...kgByDocId.notice_003.entities,
        ...globalEntities,
      ],
      relations: [
        ...kgByDocId.contract_001.relations,
        ...kgByDocId.report_002.relations,
        ...kgByDocId.notice_003.relations,
      ],
      cross_modal_ratio: 0,
      built_at: nowIso(),
    }
    merged.cross_modal_ratio =
      merged.relations.filter((r) => r.cross_modal).length / merged.relations.length
    return merged
  }
  return kg
}

const queryHistory: QueryHistoryItem[] = [
  {
    query_id: 'q-prev-1',
    query: '甲方公章对应的法定代表人是谁？',
    doc_ids: ['contract_001'],
    citations_count: 4,
    created_at: '2026-04-28T11:02:00Z',
  },
  {
    query_id: 'q-prev-2',
    query: '2025 年 ROE 是怎么算出来的？',
    doc_ids: ['report_002'],
    citations_count: 3,
    created_at: '2026-04-26T16:15:00Z',
  },
  {
    query_id: 'q-prev-3',
    query: 'B 轮估值 29.2 亿和披露金额对得上吗？',
    doc_ids: ['notice_003'],
    citations_count: 5,
    created_at: '2026-04-26T20:30:00Z',
  },
]

export async function mockQueryMultimodal(req: VLMQueryRequest): Promise<VLMQueryResponse> {
  await sleep(620)
  const weights: ModalityWeights = {
    ...DEFAULT_WEIGHTS,
    ...(req.modality_weights ?? {}),
  }
  const citations = buildCitations(req.query, weights)
  const groundings = req.visual_grounding
    ? citations
        .filter((c) => c.bbox)
        .slice(0, 4)
        .map((c) => ({ segment_id: c.segment_id, bbox: c.bbox!, label: c.snippet.slice(0, 16) }))
    : []
  const modality_scores: Record<Modality, number> = {
    text: 0,
    image: 0,
    table: 0,
    formula: 0,
    seal: 0,
  }
  citations.forEach((c) => {
    modality_scores[c.modality] = Math.max(modality_scores[c.modality], c.score)
  })
  const queryId = `q-${Date.now()}`
  const item: QueryHistoryItem = {
    query_id: queryId,
    query: req.query,
    doc_ids: req.doc_ids ?? [],
    citations_count: citations.length,
    created_at: nowIso(),
  }
  queryHistory.unshift(item)
  return {
    query_id: queryId,
    query: req.query,
    answer: buildAnswer(req.query, citations),
    citations,
    groundings,
    modality_scores,
    used_weights: weights,
    latency_ms: Math.floor(rand(620, 1240)),
    created_at: nowIso(),
  }
}

export async function mockGetQueryHistory(): Promise<QueryHistoryItem[]> {
  await sleep(120)
  return [...queryHistory]
}
