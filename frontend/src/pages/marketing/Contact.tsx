/**
 * 官网 · 联系我们 / 申请试用
 *
 * 表单仅本地校验 + 提示；真实表单后端待接（POST /api/v1/leads/public 等）
 */

import { useState } from 'react'
import { toast } from 'sonner'

import { icons } from '@/lib/icons'
import { iconSize, heading } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

type ContactForm = {
  name: string
  company: string
  role: string
  email: string
  phone: string
  scenario: string
  size: string
}

const SIZES = ['1-10 人', '11-50 人', '51-200 人', '201-1000 人', '1000+ 人']

export default function Contact() {
  const [form, setForm] = useState<ContactForm>({
    name: '',
    company: '',
    role: '',
    email: '',
    phone: '',
    scenario: '',
    size: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const onChange = (k: keyof ContactForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [k]: e.target.value }))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name || !form.email) {
      toast.error('请至少填写姓名与邮箱')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      toast.error('邮箱格式不正确')
      return
    }
    setSubmitting(true)
    try {
      // TODO: 接入真实 POST /api/v1/leads/public 端点
      await new Promise((r) => setTimeout(r, 600))
      toast.success('已提交，1 个工作日内联系您')
      setForm({
        name: '',
        company: '',
        role: '',
        email: '',
        phone: '',
        scenario: '',
        size: '',
      })
    } catch (err) {
      toast.error('提交失败，请稍后再试或直接邮件联系我们')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-16 grid grid-cols-1 lg:grid-cols-5 gap-8">
      {/* 左侧：联系方式 */}
      <aside className="lg:col-span-2 space-y-6">
        <div>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            联系我们
          </h1>
          <p className="mt-3 text-muted-foreground">
            填表后我们会在 1 个工作日内联系你，安排演示 / POC / 商务洽谈。
          </p>
        </div>

        <div className="space-y-3">
          <ContactItem
            icon="Mail"
            label="商务邮箱"
            value="hello@anxin.ai"
            href="mailto:hello@anxin.ai"
          />
          <ContactItem
            icon="ShieldCheck"
            label="安全 / DSAR"
            value="security@anxin.ai"
            href="mailto:security@anxin.ai"
          />
          <ContactItem
            icon="MessageSquare"
            label="技术社区"
            value="开发者社区（待开放）"
          />
          <ContactItem
            icon="Building2"
            label="北京 / 上海 / 深圳"
            value="支持上门拜访"
          />
        </div>

        <div className="rounded-2xl border border-border bg-card p-4 text-sm text-muted-foreground">
          <div className="font-medium text-foreground mb-1">数据使用承诺</div>
          表单信息仅用于本次商务联系；不进入营销库，不二次分享。
          根据 GB/T 35273，你随时可以邮件 security@anxin.ai 撤回或删除。
        </div>
      </aside>

      {/* 右侧：表单 */}
      <form
        onSubmit={onSubmit}
        className="lg:col-span-3 rounded-3xl border border-border bg-card p-6 sm:p-8 space-y-4"
      >
        <h2 className={heading.section}>申请演示 / 试用</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="姓名" required>
            <Input value={form.name} onChange={onChange('name')} placeholder="您的姓名" />
          </Field>
          <Field label="所在公司">
            <Input value={form.company} onChange={onChange('company')} placeholder="公司 / 律所" />
          </Field>
          <Field label="职位">
            <Input value={form.role} onChange={onChange('role')} placeholder="法务总监 / 合伙人 ..." />
          </Field>
          <Field label="公司规模">
            <select
              value={form.size}
              onChange={(e) => setForm((p) => ({ ...p, size: e.target.value }))}
              className="w-full h-9 px-3 rounded-2xl border border-border bg-background text-sm"
            >
              <option value="">请选择</option>
              {SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </Field>
          <Field label="邮箱" required>
            <Input
              type="email"
              value={form.email}
              onChange={onChange('email')}
              placeholder="you@example.com"
            />
          </Field>
          <Field label="手机">
            <Input value={form.phone} onChange={onChange('phone')} placeholder="便于联系" />
          </Field>
        </div>

        <Field label="您希望解决的场景">
          <Textarea
            value={form.scenario}
            onChange={onChange('scenario')}
            placeholder="例如：合同审查自动化、跨部门合规审批、跨境电商出口合规..."
            rows={4}
          />
        </Field>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            type="submit"
            size="lg"
            disabled={submitting}
            className="min-w-[140px]"
          >
            {submitting ? '提交中...' : '提交'}
            {!submitting && <icons.ArrowRight className={`${iconSize.sm} ml-2`} />}
          </Button>
        </div>
      </form>
    </div>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
    </div>
  )
}

function ContactItem({
  icon,
  label,
  value,
  href,
}: {
  icon: keyof typeof icons
  label: string
  value: string
  href?: string
}) {
  const Icon = icons[icon]
  const content = (
    <div className="flex items-start gap-3 rounded-2xl border border-border bg-card p-4 hover:shadow-card transition-shadow">
      <Icon className={`${iconSize.md} text-primary mt-0.5 shrink-0`} />
      <div>
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="font-medium">{value}</div>
      </div>
    </div>
  )
  return href ? <a href={href}>{content}</a> : content
}
