/**
 * 官网首页 —— 公开访问，无需登录
 *
 * 结构：Hero / 数字 / Persona 矩阵 / 三层架构 / CTA
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { useDocumentMeta } from '@/components/marketing/useDocumentMeta'

const PERSONAS: { name: string; tagline: string; icon: keyof typeof icons }[] = [
  { name: '安心助理', tagline: '总入口，分发到各专家', icon: 'Sparkles' },
  { name: '法律顾问', tagline: '法务咨询 / 合规检查', icon: 'ShieldCheck' },
  { name: '合同管家', tagline: '合同审查 / 条款风险', icon: 'FileCheck' },
  { name: '尽调专家', tagline: '尽职调查 / 风险报告', icon: 'FileSearch' },
  { name: '财税顾问', tagline: '税务咨询 / 财务测算', icon: 'Calculator' },
  { name: '内容总监', tagline: '内容创作 / 多模态', icon: 'Newspaper' },
  { name: '获客猎手', tagline: '线索挖掘 / 营销自动化', icon: 'Users' },
  { name: '市场研究员', tagline: '行业研究 / 竞品分析', icon: 'BarChart3' },
  { name: '跨境电商助手', tagline: '出海 / 多语言 / 跨境合规', icon: 'Globe' },
  { name: '流程管家', tagline: '工作流编排 / 审批', icon: 'Network' },
]

const STATS: { value: string; label: string }[] = [
  { value: '76+', label: 'Skills 能力原子' },
  { value: '10', label: '专业 Persona' },
  { value: '6 层', label: '权限校验闸门' },
  { value: '4 端', label: 'Web / 桌面 / 移动 / 小程序' },
]

export default function Home() {
  useDocumentMeta({
    title: '安心智能助手 · 把 AI 装进业务',
    description:
      '10 个专业 Persona + 76 个 Skill + 六层权限闸门 + 五分层沙箱，企业级可落地的 AI 助手平台。',
    ogUrl: 'https://anxin.ai/site',
  })

  return (
    <div className="space-y-24 pb-16">
      {/* Hero */}
      <section className="pt-16 pb-8">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-muted text-xs text-muted-foreground mb-6">
            <icons.Sparkles className="w-3 h-3" />
            企业级多 Persona AI 智能助手
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight">
            把 AI 装进
            <span className="text-primary"> 业务</span>，
            <br className="hidden sm:block" />
            而不是把员工装进 AI。
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-base sm:text-lg text-muted-foreground">
            安心智能助手覆盖法务、财税、合规、增长、出海全链路 ——
            10 个专业角色 + 76 个 Skill，按权限装配、按风险隔离、按场景落地。
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link to="/site/contact">
              <Button size="lg" className="px-6">
                申请试用
                <icons.ArrowRight className={`${iconSize.sm} ml-2`} />
              </Button>
            </Link>
            <Link to="/site/features">
              <Button size="lg" variant="outline" className="px-6">
                看产品功能
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* 数字 */}
      <section>
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="rounded-3xl border border-border bg-card p-6 text-center"
              >
                <div className="text-3xl sm:text-4xl font-semibold tracking-tight">
                  {s.value}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Persona 矩阵 */}
      <section>
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex items-end justify-between mb-6 flex-wrap gap-2">
            <div>
              <h2 className={heading.section}>10 个专业 Persona</h2>
              <p className="text-sm text-muted-foreground mt-1">
                每个 Persona 是一个真正"懂行"的智能体，按角色装配 Skill 与权限。
              </p>
            </div>
            <Link to="/site/personas" className="text-sm text-primary hover:underline">
              查看完整矩阵 →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {PERSONAS.map((p) => {
              const Icon = icons[p.icon]
              return (
                <div
                  key={p.name}
                  className="rounded-2xl border border-border bg-card p-4 hover:shadow-card transition-shadow"
                >
                  <Icon className={`${iconSize.md} mb-2 text-primary`} />
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">{p.tagline}</div>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* 三层架构 */}
      <section>
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className={heading.section}>为什么是"企业级"</h2>
          <p className="text-sm text-muted-foreground mt-1 mb-8">
            从权限、隔离、合规、可观测每一层都按企业标准设计。
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FeatureCard
              icon="ShieldCheck"
              title="六层权限闸门"
              desc="订阅 → 角色 → 权限 → 风险分级 → 隐私模式 → 设备信任。任一失败即拒绝，fail-closed。"
            />
            <FeatureCard
              icon="Lock"
              title="Skills 沙箱五分层"
              desc="T0 Prompt-only / T1 受信进程 / T2 子进程 / T3 容器 / T4 远程沙箱。"
            />
            <FeatureCard
              icon="Building2"
              title="飞书式组织目录"
              desc="部门树 + 一人多部门 + 角色绑定 + 跨部门用户组，权限自上而下继承。"
            />
            <FeatureCard
              icon="Database"
              title="GB/T 35273 数据分级"
              desc="公开 / 内部 / 受控 / 敏感 / 绝密 五级，按级隔离与访问审计。"
            />
            <FeatureCard
              icon="Network"
              title="本地 / 混合 / 云端"
              desc="同一份代码三种部署形态。私有化、断网部署也是一等公民。"
            />
            <FeatureCard
              icon="BarChart3"
              title="可观测三件套"
              desc="Prometheus + Grafana + 审计日志，开箱即用，支持 Thanos 多集群聚合。"
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <div className="rounded-3xl border border-border bg-card p-8 sm:p-12 text-center">
            <h2 className={heading.section}>把 AI 真正落到业务里</h2>
            <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
              来一次实地演示。我们会带着你的真实场景跑一遍，看 Skill / Persona / 权限 / 沙箱怎么落地。
            </p>
            <div className="mt-6 flex items-center justify-center gap-3">
              <Link to="/site/contact">
                <Button size="lg">预约演示</Button>
              </Link>
              <Link to="/site/pricing">
                <Button size="lg" variant="outline">查看价格</Button>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  desc,
}: {
  icon: keyof typeof icons
  title: string
  desc: string
}) {
  const Icon = icons[icon]
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <Icon className={`${iconSize.md} text-primary mb-3`} />
      <div className="font-medium mb-1">{title}</div>
      <div className="text-sm text-muted-foreground leading-relaxed">{desc}</div>
    </div>
  )
}
