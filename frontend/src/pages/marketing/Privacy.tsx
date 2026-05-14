/**
 * 官网 · 隐私政策（公开页）
 *
 * 内容是占位骨架，需要法务最终确认；先把页面挂上去保证合规链接不死。
 */

import { heading } from '@/lib/design-tokens'

export default function Privacy() {
  return (
    <article className="mx-auto max-w-3xl px-4 sm:px-6 py-16 space-y-8">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">隐私政策</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          最后更新：2026-05-14（草案）· 适用对象：安心智能助手
        </p>
      </header>

      <Section title="1. 我们收集什么">
        <p>
          安心智能助手按"最小必要原则"收集信息：
        </p>
        <ul className="list-disc list-inside space-y-1 mt-2 text-muted-foreground">
          <li>账户信息：邮箱、姓名、所在组织</li>
          <li>设备信息：浏览器 / 客户端版本、操作系统、IP 区段</li>
          <li>使用信息：会话日志、Skill 调用记录（不含完整内容）</li>
          <li>上传内容：仅在你主动上传文件 / 输入对话时存储</li>
        </ul>
      </Section>

      <Section title="2. 我们怎么使用">
        <p>
          仅用于提供和改进服务：身份验证、能力调度、计费、可观测、合规审计。
        </p>
        <p>
          私有化部署下，所有数据**完全留在客户内网**，我们不主动外发任何数据。
        </p>
      </Section>

      <Section title="3. 数据分级">
        <p>
          我们按 GB/T 35273-2020 把数据分为五级：公开、内部、受控、敏感、绝密。
          每一级对应不同的访问、加密、留痕、销毁策略。详见{' '}
          <a href="/site/security" className="text-primary hover:underline">
            安全与合规
          </a>
          。
        </p>
      </Section>

      <Section title="4. 你的权利（DSAR）">
        <p>根据 GB/T 35273 / GDPR / CCPA，你可以：</p>
        <ul className="list-disc list-inside space-y-1 mt-2 text-muted-foreground">
          <li>查询你的全部数据副本</li>
          <li>请求更正或删除</li>
          <li>撤回同意</li>
          <li>数据可携带（结构化导出）</li>
        </ul>
        <p className="mt-2">
          提交 DSAR：邮件 <a className="text-primary hover:underline" href="mailto:security@anxin.ai">security@anxin.ai</a>。
        </p>
      </Section>

      <Section title="5. Cookie 与跟踪">
        <p>
          官网仅使用功能性 Cookie（保持登录、主题偏好）。
          我们不投放第三方广告 SDK，不向第三方共享行为数据。
        </p>
      </Section>

      <Section title="6. 数据出境">
        <p>
          私有化客户的数据不出境。SaaS 客户的数据存储在中国境内服务器；
          跨境电商类工作负载在用户明确授权后，按目标市场合规要求处理。
        </p>
      </Section>

      <Section title="7. 政策更新">
        <p>
          重大变更前 30 天会通过站内信和邮件告知。继续使用即视为接受新版本。
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
