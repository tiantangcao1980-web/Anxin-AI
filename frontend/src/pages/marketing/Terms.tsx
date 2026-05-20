/**
 * 官网 · 服务条款（公开页骨架）
 */

import { heading } from '@/lib/design-tokens'

export default function Terms() {
  return (
    <article className="mx-auto max-w-3xl px-4 sm:px-6 py-16 space-y-8">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">服务条款</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          最后更新：2026-05-14（草案）
        </p>
      </header>

      <Section title="1. 接受条款">
        <p>
          注册或使用安心智能助手即表示你同意本条款。如果你代表组织接受，
          你声明已获得该组织授权。
        </p>
      </Section>

      <Section title="2. 服务范围">
        <p>
          安心智能助手提供 AI 智能助手、智能协作、智能调查、法律智库四个业务域的能力。
          AI 输出**不构成法律意见 / 财税建议**，重要决策请由有资质的专业人士复核。
        </p>
      </Section>

      <Section title="3. 用户义务">
        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
          <li>不上传违法、侵权或恶意内容</li>
          <li>不尝试绕过安全沙箱或权限校验</li>
          <li>不利用本服务从事自动化爬取以外用途的反向工程</li>
          <li>保管账号凭证；账号下行为视为本人行为</li>
        </ul>
      </Section>

      <Section title="4. 计费与退款">
        <p>
          按选定套餐预付。除非另有约定，已用周期不退款，未用整月可按比例退。
          私有化合同另签。
        </p>
      </Section>

      <Section title="5. 知识产权">
        <p>
          客户上传的内容归客户所有；AI 生成结果在客户合理使用范围内归客户使用。
          安心智能助手保留底层模型、Skill 框架、平台软件的著作权。
        </p>
      </Section>

      <Section title="6. 责任限制">
        <p>
          在法律允许的最大范围内，因服务原因造成的间接 / 衍生损失我们不承担责任。
          直接责任上限为最近 12 个月你支付的服务费总额。
        </p>
      </Section>

      <Section title="7. 终止">
        <p>
          任一方可提前 30 天书面通知终止。严重违约方可立即终止。
          终止后 90 天内可申请导出数据，之后数据将按安全策略销毁。
        </p>
      </Section>

      <Section title="8. 适用法律">
        <p>
          本条款适用中华人民共和国法律。争议优先协商，协商不成提交服务提供方所在地有管辖权法院。
        </p>
      </Section>
    </article>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className={heading.section}>{title}</h2>
      <div className="text-sm leading-relaxed space-y-2">{children}</div>
    </section>
  )
}
