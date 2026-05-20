/**
 * 官网 · 关于我们
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'

const VALUES: { icon: keyof typeof icons; title: string; desc: string }[] = [
  {
    icon: 'ShieldCheck',
    title: '安全优先',
    desc: '宁可慢一点上线，也不让 AI 成为新的攻击面。fail-closed 是默认值。',
  },
  {
    icon: 'Users',
    title: '业务为重',
    desc: '不做"通用 AI"。每个 Persona 都按真实场景打磨，按真实角色装配。',
  },
  {
    icon: 'Lock',
    title: '客户数据归客户',
    desc: '本地 / 混合 / 云端三态共存。数据所有权永远属于使用者。',
  },
  {
    icon: 'Sparkles',
    title: '工程师友好',
    desc: 'SKILL.md / 沙箱清单 / 权限矩阵全部可读，可改，可签名分发。',
  },
]

const MILESTONES: { year: string; title: string; desc: string }[] = [
  { year: '2024', title: '法务垂直起步', desc: '从合同审查 / 法律 RAG 切入，验证 PMF' },
  { year: '2025 H1', title: '升级为安心智能助手', desc: '从单产品 → 10 Persona + Skill 注册表 + 沙箱' },
  { year: '2025 H2', title: '企业级底座完成', desc: '六层权限 / Skill 五分层 / 飞书式组织 / LDAP 同步' },
  { year: '2026', title: '私有化 + 出海', desc: 'AirGap 部署 + 跨境电商 / 多语言 / 多合规' },
]

export default function About() {
  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-16 space-y-16">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          关于安心智能助手
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          我们相信 AI 应该装进业务里，而不是把员工装进 AI 里。
          一套底座，10 个 Persona，76 个 Skill，覆盖法务 / 财税 / 合规 / 增长 / 出海全链路。
        </p>
      </header>

      <section>
        <h2 className={heading.section}>我们坚信的事</h2>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
          {VALUES.map((v) => {
            const Icon = icons[v.icon]
            return (
              <div key={v.title} className="rounded-2xl border border-border bg-card p-5">
                <Icon className={`${iconSize.md} text-primary mb-2`} />
                <div className="font-medium">{v.title}</div>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">
                  {v.desc}
                </p>
              </div>
            )
          })}
        </div>
      </section>

      <section>
        <h2 className={heading.section}>我们的里程碑</h2>
        <div className="mt-6 space-y-3">
          {MILESTONES.map((m) => (
            <div key={m.year} className="flex gap-4 sm:gap-6 items-start">
              <div className="font-mono text-sm text-muted-foreground w-20 sm:w-24 shrink-0 pt-1">
                {m.year}
              </div>
              <div className="rounded-2xl border border-border bg-card p-4 flex-1">
                <div className="font-medium">{m.title}</div>
                <p className="text-sm text-muted-foreground mt-1">{m.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="rounded-3xl border border-border bg-card p-8 text-center">
          <h2 className={heading.section}>想加入或合作？</h2>
          <p className="mt-3 text-muted-foreground">
            我们在招人，也在找渠道伙伴。
          </p>
          <div className="mt-6">
            <Link to="/site/contact">
              <Button size="lg">联系我们</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
