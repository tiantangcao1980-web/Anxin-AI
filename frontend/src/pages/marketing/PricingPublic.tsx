/**
 * 官网 · 公开价格页
 *
 * 与登录后的 Pricing.tsx 不同 —— 这里**不**调用计费 API，
 * 是给匿名访客看的静态版本。月付价格为参考价，真实结算走登录后流程。
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'

const PLANS: {
  name: string
  tagline: string
  monthly: number
  yearly: number
  cta: string
  highlight?: boolean
  features: string[]
}[] = [
  {
    name: '个人版',
    tagline: '律师 / 法务 / 个人使用',
    monthly: 99,
    yearly: 990,
    cta: '免费试用',
    features: [
      '10 个 Persona 全开',
      '基础法律 RAG + 法规检索',
      '合同审查（每月 100 份）',
      '邮件支持',
    ],
  },
  {
    name: '企业版',
    tagline: '团队协作 / 部门管理',
    monthly: 999,
    yearly: 9990,
    cta: '联系销售',
    highlight: true,
    features: [
      '个人版全部能力',
      '飞书式组织目录 + 部门 / 角色绑定',
      '协作文档 + 审批流 + IM 网关',
      'Skill 沙箱 T0-T3 全开',
      'Prometheus / Grafana 可观测',
      '7×24 工单支持',
    ],
  },
  {
    name: '私有化',
    tagline: '政企 / 律所 / 内网部署',
    monthly: -1,
    yearly: -1,
    cta: '商务咨询',
    features: [
      '企业版全部能力',
      '完全内网部署，支持 AirGap',
      'LDAP / AD / SAML SSO 接入',
      'Skill T4 远程沙箱 + 签名校验',
      '专属 SLA + 现场实施',
      '源码托管选项',
    ],
  },
]

function formatPrice(plan: (typeof PLANS)[number], yearly: boolean): string {
  if (plan.monthly < 0) return '咨询'
  const price = yearly ? plan.yearly : plan.monthly
  return `¥${price.toLocaleString()}`
}

export default function PricingPublic() {
  const [yearly, setYearly] = useState(true)

  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-16 space-y-12">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          价格
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          按规模和部署形态分层。所有套餐都包含 10 个 Persona 与 76 个 Skill。
        </p>
        <div className="mt-6 inline-flex items-center gap-3 px-4 py-2 rounded-full bg-muted">
          <span className={`text-sm ${yearly ? 'text-muted-foreground' : 'text-foreground'}`}>
            月付
          </span>
          <Switch checked={yearly} onCheckedChange={setYearly} />
          <span className={`text-sm ${yearly ? 'text-foreground' : 'text-muted-foreground'}`}>
            年付
          </span>
          <span className="text-xs text-emerald-600 dark:text-emerald-400">
            年付优惠约 2 个月
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANS.map((plan) => (
          <div
            key={plan.name}
            className={`rounded-3xl border bg-card p-6 flex flex-col ${
              plan.highlight ? 'border-primary shadow-card' : 'border-border'
            }`}
          >
            {plan.highlight && (
              <div className="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground inline-block self-start mb-3">
                推荐
              </div>
            )}
            <div className="font-medium text-lg">{plan.name}</div>
            <p className="text-sm text-muted-foreground mt-1">{plan.tagline}</p>
            <div className="mt-4">
              <div className="text-3xl sm:text-4xl font-semibold tracking-tight">
                {formatPrice(plan, yearly)}
              </div>
              {plan.monthly > 0 && (
                <div className="text-sm text-muted-foreground mt-1">
                  {yearly ? '/ 年' : '/ 月 · 每人'}
                </div>
              )}
            </div>
            <ul className="mt-6 space-y-2 text-sm">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2">
                  <icons.Check className={`${iconSize.sm} text-primary mt-0.5 shrink-0`} />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6">
              <Link to="/site/contact">
                <Button
                  className="w-full"
                  variant={plan.highlight ? 'default' : 'outline'}
                >
                  {plan.cta}
                </Button>
              </Link>
            </div>
          </div>
        ))}
      </div>

      <section>
        <div className="rounded-3xl border border-border bg-card p-8">
          <h2 className={heading.section}>常见问题</h2>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6 text-sm">
            <Faq
              q="试用期多久？"
              a="个人版默认 14 天免费试用；企业版可申请 30 天 POC，含数据接入与培训。"
            />
            <Faq
              q="可以混合部署吗？"
              a="可以。同一份代码支持本地 / 混合 / 云端三种模式，按租户开关。"
            />
            <Faq
              q="数据归属是谁？"
              a="所有数据归你所有。私有化部署下数据完全在客户内网；SaaS 模式按 GB/T 35273 分级隔离。"
            />
            <Faq
              q="是否支持自带模型？"
              a="支持。私有化部署可以接入任何 OpenAI 兼容的本地 / 自建推理 endpoint。"
            />
          </div>
        </div>
      </section>
    </div>
  )
}

function Faq({ q, a }: { q: string; a: string }) {
  return (
    <div>
      <div className="font-medium">{q}</div>
      <p className="mt-1 text-muted-foreground leading-relaxed">{a}</p>
    </div>
  )
}
