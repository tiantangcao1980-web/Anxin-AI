/**
 * 官网 · 安全与合规
 *
 * 把后端真实的安全模型公开化：六层闸门 / 五分层沙箱 / GB/T 35273 / 审计。
 */

import { Link } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'

const GATES: { name: string; desc: string }[] = [
  { name: '1. 订阅开关', desc: '租户是否解锁该能力 / Skill 信任分级' },
  { name: '2. 角色检查', desc: '调用者是否属于 9 大角色之一' },
  { name: '3. 权限映射', desc: '角色到 Permission 枚举（read:cases / write:contracts 等）' },
  { name: '4. 风险分级', desc: 'L0-L5 风险标签，触发即审批 / 双人复核' },
  { name: '5. 隐私模式', desc: '本地 / 混合 / 云端三档，按敏感度路由' },
  { name: '6. 设备信任', desc: '指纹 + 行为基线，可疑设备触发挑战' },
]

const TIERS: { tier: string; name: string; desc: string }[] = [
  { tier: 'T0', name: 'Prompt-only', desc: 'LLM 直接消费 SKILL.md，无代码执行' },
  { tier: 'T1', name: 'In-process（受信）', desc: '签名后的官方 Skill 进程内运行' },
  { tier: 'T2', name: 'Subprocess 沙箱', desc: '子进程 + setrlimit + 受限 PATH' },
  { tier: 'T3', name: 'Container 沙箱', desc: 'Docker：only-read fs + cap-drop ALL + no-new-privileges + network=none' },
  { tier: 'T4', name: 'Remote 沙箱', desc: 'E2B / CodexCloud 等远端隔离' },
]

const COMPLIANCE: { id: string; desc: string }[] = [
  { id: 'GB/T 35273-2020', desc: '个人信息安全规范：数据五级分类 + 收集最小化 + 主体权利' },
  { id: '等保 2.0', desc: '三级等保对照清单（私有化部署）' },
  { id: 'GDPR / CCPA', desc: '跨境业务支持 DSAR、被遗忘权、数据可携带' },
  { id: 'ISO 27001 (规划)', desc: '信息安全管理体系认证（2026 Q4）' },
]

export default function Security() {
  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-16 space-y-16">
      <header className="text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-muted text-xs text-muted-foreground mb-4">
          <icons.ShieldCheck className="w-3 h-3" />
          安全与合规
        </div>
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
          AI 不能成为新的攻击面
        </h1>
        <p className="mt-4 max-w-2xl mx-auto text-muted-foreground">
          安心智能助手把"安全"刻进每一层：从权限闸门到沙箱隔离，
          从数据分级到审计留痕，按企业级标准设计。
        </p>
      </header>

      <section>
        <h2 className={heading.section}>六层权限闸门</h2>
        <p className="text-sm text-muted-foreground mt-1 mb-6">
          每次能力调用都串行经过六层校验，任一失败即拒绝（fail-closed），全程留痕。
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {GATES.map((g) => (
            <div key={g.name} className="rounded-2xl border border-border bg-card p-5">
              <div className="font-medium">{g.name}</div>
              <p className="mt-1 text-sm text-muted-foreground">{g.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className={heading.section}>Skill 沙箱五分层</h2>
        <p className="text-sm text-muted-foreground mt-1 mb-6">
          不同信任级别的代码跑在不同的隔离层；未声明 tier 的 Skill 默认 T3（最严）。
        </p>
        <div className="rounded-3xl border border-border bg-card overflow-hidden">
          {TIERS.map((t, i) => (
            <div
              key={t.tier}
              className={`flex items-start gap-4 p-5 ${
                i !== TIERS.length - 1 ? 'border-b border-border' : ''
              }`}
            >
              <div className="font-mono text-sm w-12 shrink-0 text-primary font-semibold">
                {t.tier}
              </div>
              <div>
                <div className="font-medium">{t.name}</div>
                <p className="text-sm text-muted-foreground mt-1">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className={heading.section}>合规对照</h2>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3">
          {COMPLIANCE.map((c) => (
            <div key={c.id} className="rounded-2xl border border-border bg-card p-5">
              <div className="flex items-center gap-2 font-medium">
                <icons.ShieldCheck className={`${iconSize.sm} text-primary`} />
                {c.id}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className={heading.section}>审计与可观测</h2>
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="rounded-2xl border border-border bg-card p-5">
            <icons.FileText className={`${iconSize.md} text-primary mb-2`} />
            <div className="font-medium">不可篡改审计日志</div>
            <p className="text-sm text-muted-foreground mt-1">
              所有能力调用、Skill 执行、权限决策落 audit_log，WAL 归档冷存
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-5">
            <icons.BarChart3 className={`${iconSize.md} text-primary mb-2`} />
            <div className="font-medium">Prometheus 指标</div>
            <p className="text-sm text-muted-foreground mt-1">
              Skill 执行 / 沙箱拒绝 / OOM / 超时四套指标 + Grafana 看板
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card p-5">
            <icons.Bell className={`${iconSize.md} text-primary mb-2`} />
            <div className="font-medium">实时告警</div>
            <p className="text-sm text-muted-foreground mt-1">
              异常审批激增 / 越权尝试 / 签名假伪即时告警，可对接客户 SOC
            </p>
          </div>
        </div>
      </section>

      <section>
        <div className="rounded-3xl border border-border bg-card p-8 text-center">
          <h2 className={heading.section}>需要安全评估材料？</h2>
          <p className="mt-3 text-muted-foreground max-w-xl mx-auto">
            我们可以提供完整的等保合规对照清单、渗透测试报告（脱敏）与架构白皮书。
          </p>
          <div className="mt-6">
            <Link to="/site/contact">
              <Button size="lg">索取安全白皮书</Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
