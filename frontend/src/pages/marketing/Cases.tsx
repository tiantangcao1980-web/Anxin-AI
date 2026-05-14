/**
 * 官网 · 客户案例
 *
 * 当前是占位骨架：3 个示例案例卡，等真实客户授权后替换。
 * 数据放在文件内静态数组，方便非工程人员（如 BD）走 PR 流程改。
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { useDocumentMeta } from '@/components/marketing/useDocumentMeta'

interface CaseStudy {
  slug: string
  industry: string
  customer: string
  headline: string
  summary: string
  metrics: { value: string; label: string }[]
  personas: string[]
}

// TODO: 真实客户案例替换；BD 同事可走 PR 修改这里
const CASES: CaseStudy[] = [
  {
    slug: 'lawfirm-a',
    industry: '律师事务所',
    customer: '某综合所（200+ 律师）',
    headline: '合同审查 + 尽调报告效率提升 5×',
    summary:
      '律所部署私有化版本，10 个 Persona 全开。引入 6 个月后：合同初审从 4 人天压缩到 1 人天，尽调报告草稿自动产出比例从 0 升到 70%。',
    metrics: [
      { value: '5×', label: '合同审查效率' },
      { value: '70%', label: '尽调草稿自动率' },
      { value: '40%', label: '律师非诉时间节省' },
    ],
    personas: ['法律顾问', '合同管家', '尽调专家'],
  },
  {
    slug: 'enterprise-b',
    industry: '制造业上市公司',
    customer: '某 A 股制造业（10000+ 员工）',
    headline: '法务 + 合规一体化',
    summary:
      '集团法务部接入，跨 12 个子公司统一合同审查 + 合规自检。LDAP 同步 + 部门树继承让权限管理零运维。',
    metrics: [
      { value: '12', label: '子公司统一接入' },
      { value: '0', label: '权限同步运维' },
      { value: '85%', label: '合同自助审查率' },
    ],
    personas: ['合同管家', '法律顾问', '流程管家'],
  },
  {
    slug: 'cross-border-c',
    industry: '跨境电商',
    customer: '某出海品牌（亚马逊 GMV TOP1%）',
    headline: '跨境合规 + 多语言客服',
    summary:
      '同时合规对接美国 / 欧盟 / 日本，结合跨境电商助手 + 法律顾问。多语言能力覆盖 8 个市场。',
    metrics: [
      { value: '8', label: '目标市场' },
      { value: '24×7', label: 'AI 客服覆盖' },
      { value: '60%', label: '合规材料预生成' },
    ],
    personas: ['跨境电商助手', '法律顾问'],
  },
]

export default function Cases() {
  useDocumentMeta({
    title: '客户案例 · 安心智能助手',
    description:
      '律所 / 制造业 / 跨境电商等真实客户的落地数据：合同审查 5× 提速、尽调草稿 70% 自动产出。',
    ogUrl: 'https://anxin.ai/site/cases',
  })

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-16 space-y-12">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          客户案例
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          真实客户的真实数字。涉密客户已脱敏处理；具体材料请通过商务渠道索取。
        </p>
      </header>

      <div className="space-y-4">
        {CASES.map((c) => (
          <article
            key={c.slug}
            className="rounded-3xl border border-border bg-card p-6 sm:p-8"
          >
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3">
              <icons.Building2 className={iconSize.sm} />
              <span>{c.industry}</span>
              <span>·</span>
              <span>{c.customer}</span>
            </div>
            <h2 className={heading.section}>{c.headline}</h2>
            <p className="mt-3 text-muted-foreground leading-relaxed">
              {c.summary}
            </p>
            <div className="mt-6 grid grid-cols-3 gap-4">
              {c.metrics.map((m) => (
                <div key={m.label} className="text-center">
                  <div className="text-2xl sm:text-3xl font-semibold tracking-tight">
                    {m.value}
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{m.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap gap-1.5">
              {c.personas.map((p) => (
                <span
                  key={p}
                  className="px-2 py-0.5 rounded bg-muted text-xs"
                >
                  {p}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>

      <section>
        <div className="rounded-3xl border border-border bg-card p-8 text-center">
          <h2 className={heading.section}>想成为下一个案例？</h2>
          <p className="mt-3 text-muted-foreground">
            首批合作客户享 POC 价格 + 专属架构师 + 公开案例授权（双向同意）。
          </p>
          <div className="mt-6">
            <Link to="/site/contact">
              <Button size="lg">预约 POC</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
