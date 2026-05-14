/**
 * 官网 · 10 Persona 矩阵
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'

const PERSONAS: {
  name: string
  tagline: string
  icon: keyof typeof icons
  best_for: string[]
  example_skill: string
}[] = [
  {
    name: '安心助理',
    tagline: '总入口，意图分发到各专家',
    icon: 'Sparkles',
    best_for: ['不知道找谁问', '跨域问题', '统一对话'],
    example_skill: 'intent_dispatch',
  },
  {
    name: '法律顾问',
    tagline: '法律咨询 / 法规检索 / 合规检查',
    icon: 'ShieldCheck',
    best_for: ['企业法务', '个人咨询', '日常合规'],
    example_skill: 'legal_research',
  },
  {
    name: '合同管家',
    tagline: '合同审查 / 条款风险 / 版本比对',
    icon: 'FileCheck',
    best_for: ['合同审查', '电子签', '模板复用'],
    example_skill: 'contract_review',
  },
  {
    name: '尽调专家',
    tagline: '尽职调查 / 多源数据融合 / 风险报告',
    icon: 'FileSearch',
    best_for: ['投融资', '供应商核查', '诉讼前调查'],
    example_skill: 'due_diligence',
  },
  {
    name: '财税顾问',
    tagline: '税务测算 / 财务诊断 / 政策匹配',
    icon: 'Calculator',
    best_for: ['财税合规', '税收筹划', '政策利好检索'],
    example_skill: 'tax_calculator',
  },
  {
    name: '内容总监',
    tagline: '多模态内容生成 / 选题 / 排期',
    icon: 'Newspaper',
    best_for: ['品牌内容', '运营创作', '社媒矩阵'],
    example_skill: 'content_pipeline',
  },
  {
    name: '获客猎手',
    tagline: '线索挖掘 / 营销自动化 / SDR',
    icon: 'Users',
    best_for: ['ToB 销售', '私域引流', 'SDR 团队'],
    example_skill: 'lead_hunter',
  },
  {
    name: '市场研究员',
    tagline: '行业研究 / 竞品分析 / 战略复盘',
    icon: 'BarChart3',
    best_for: ['BD / 战略', 'PM 立项', '商分专题'],
    example_skill: 'market_research',
  },
  {
    name: '跨境电商助手',
    tagline: '出海 / 多语言 / 跨境合规',
    icon: 'Globe',
    best_for: ['跨境电商', '海外法务', '多语言客服'],
    example_skill: 'ecommerce_ops',
  },
  {
    name: '流程管家',
    tagline: '工作流编排 / 审批链 / 任务',
    icon: 'Network',
    best_for: ['企业运营', '跨部门审批', '任务派发'],
    example_skill: 'workflow_run',
  },
]

export default function Personas() {
  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-16 space-y-12">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          10 个真正"懂行"的 Persona
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          每个 Persona 都是一个独立的智能体 ——
          有自己的提示词、Skill 装配、权限边界与风险阈值，按角色分发任务。
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {PERSONAS.map((p) => {
          const Icon = icons[p.icon]
          return (
            <div
              key={p.name}
              className="rounded-2xl border border-border bg-card p-5 flex flex-col"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Icon className={iconSize.md} />
                </div>
                <div className="font-medium">{p.name}</div>
              </div>
              <p className="text-sm text-muted-foreground mb-4">{p.tagline}</p>
              <div className="mt-auto space-y-2 text-xs">
                <div className="flex flex-wrap gap-1.5">
                  {p.best_for.map((b) => (
                    <span
                      key={b}
                      className="px-2 py-0.5 rounded bg-muted text-muted-foreground"
                    >
                      {b}
                    </span>
                  ))}
                </div>
                <div className="text-muted-foreground/70 font-mono">
                  e.g. {p.example_skill}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <section>
        <div className="rounded-3xl border border-border bg-card p-8 text-center">
          <h2 className={heading.section}>Persona 不够用？</h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
            企业可以基于 Skill 注册表 + 提示词模板自建专属 Persona ——
            财法税合规之外的任何垂直领域都可以快速派生。
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link to="/site/contact">
              <Button size="lg">咨询自建 Persona</Button>
            </Link>
            <Link to="/site/features">
              <Button size="lg" variant="outline">看 Skill 体系</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
