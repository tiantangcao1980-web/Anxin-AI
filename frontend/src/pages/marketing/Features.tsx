/**
 * 官网 · 产品功能
 *
 * 4 个业务域 + 每域 3-4 个能力卡，标注落地状态。
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'

type Status = 'ready' | 'beta' | 'planned'

const DOMAINS: {
  title: string
  desc: string
  icon: keyof typeof icons
  items: { name: string; desc: string; status: Status }[]
}[] = [
  {
    title: 'AI 智能助手',
    icon: 'Sparkles',
    desc: '基于 10 个 Persona 的多智能体协作框架',
    items: [
      { name: '统一对话入口', desc: 'V3 安心助理统一分发到法务 / 财税 / 合规等专业 Agent', status: 'ready' },
      { name: 'Skill 注册表 + 热加载', desc: 'SKILL.md 文件式 skill 体系，watchdog 热更', status: 'ready' },
      { name: 'Skills 沙箱五分层', desc: 'T0-T4 信任分级，资源 / 网络 / 文件系统三重隔离', status: 'ready' },
      { name: 'Skill Marketplace', desc: '第三方 skill 安装 + ed25519 签名校验', status: 'beta' },
    ],
  },
  {
    title: '智能协作',
    icon: 'Users',
    desc: '面向企业 / 律所 / 团队的协作中枢',
    items: [
      { name: '文档协同（CRDT）', desc: 'tiptap + yjs，多人实时编辑 + 注释 + 历史快照', status: 'ready' },
      { name: '审批 + IM 网关', desc: '内置审批流；支持飞书 / 钉钉 / 企业微信适配', status: 'ready' },
      { name: '组织目录 / 部门 / 角色绑定', desc: '飞书式部门树 + 一人多部门 + 跨部门用户组', status: 'ready' },
      { name: 'LDAP / AD 同步', desc: '内网部署下与企业目录服务双向同步', status: 'beta' },
    ],
  },
  {
    title: '智能调查',
    icon: 'FileSearch',
    desc: '面向律师 / 风控 / 尽调的核查能力',
    items: [
      { name: '4 层 Fetch 栈', desc: 'L1 HTTP / L2 Headless / L3 反爬 / L4 官方 API', status: 'ready' },
      { name: '多源情报融合', desc: '企业信息 / 司法 / 舆情 / 跨境数据源横向打通', status: 'ready' },
      { name: '尽调报告自动生成', desc: '调用 12+ 数据源，按律所模板出具尽调报告', status: 'ready' },
      { name: '知识图谱（K-G）', desc: '关系网穿透 + 同人 / 同 IP / 关联交易识别', status: 'beta' },
    ],
  },
  {
    title: '法律智库',
    icon: 'BookOpen',
    desc: '基于 RAG + 司法语料的法律知识检索',
    items: [
      { name: '法规 RAG', desc: '全量法律法规 + 司法解释 + 部委文件检索', status: 'ready' },
      { name: '司法案例 RAG', desc: '裁判文书 + 类案推送 + 判决倾向分析', status: 'ready' },
      { name: 'VLM 增强 Query', desc: '多模态查询：图片 / 表格 / 公式直接做 RAG', status: 'beta' },
      { name: '司法学院', desc: '案例库 + 课程 + 律师入驻认证', status: 'planned' },
    ],
  },
]

const STATUS_STYLE: Record<Status, { label: string; cls: string }> = {
  ready: { label: '已上线', cls: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' },
  beta: { label: 'Beta', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' },
  planned: { label: '规划中', cls: 'bg-muted text-muted-foreground border-border' },
}

export default function Features() {
  return (
    <div className="mx-auto max-w-6xl px-4 sm:px-6 py-16 space-y-16">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          四大业务域 · 一套底座
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          AI 智能助手、智能协作、智能调查、法律智库 ——
          全部跑在同一个 Skill / Persona / 权限 / 沙箱底座之上。
        </p>
      </header>

      {DOMAINS.map((d) => {
        const Icon = icons[d.icon]
        return (
          <section key={d.title}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                <Icon className={iconSize.md} />
              </div>
              <div>
                <h2 className={heading.section}>{d.title}</h2>
                <p className="text-sm text-muted-foreground">{d.desc}</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {d.items.map((it) => (
                <div
                  key={it.name}
                  className="rounded-2xl border border-border bg-card p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-medium">{it.name}</div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded border ${STATUS_STYLE[it.status].cls}`}
                    >
                      {STATUS_STYLE[it.status].label}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    {it.desc}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )
      })}

      <section>
        <div className="rounded-3xl border border-border bg-card p-8 text-center">
          <h2 className={heading.section}>想看真实演示？</h2>
          <p className="mt-3 text-muted-foreground">
            把你的场景告诉我们，我们用真实数据走一遍流程。
          </p>
          <div className="mt-6">
            <Link to="/site/contact">
              <Button size="lg">预约演示</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
