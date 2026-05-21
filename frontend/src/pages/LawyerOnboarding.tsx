/**
 * LawyerOnboarding · 律师入驻引导（Editorial Luxury 改造 · Phase 2.4）
 *
 * 旧版：PageContainer + cardStyle.base 圆角卡 + 药丸 Stepper + 多色 Badge + bg-primary 圆角填充按钮。
 * 新版：EditorialPageHeader + 4 步衬线序号步进器 + Section（hairline）+ tone-only chip + 1px 选择网格。
 *
 * 4 步流程：基本资料 → 执业证上传 → 接单设置 → 提交审核
 * 联调真实 API：getOnboardingStatus / createOrUpdateProfile / updateServiceConfig / submitCertification
 */
import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  User, FileCheck, Settings as SettingsIcon, CheckCircle, ChevronLeft, ChevronRight,
  Loader2, Clock, XCircle, Edit2, AlertTriangle,
} from 'lucide-react'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { ErrorState } from '@/components/common'
import { lawyerApi } from '@/lib/api'
import { cn } from '@/components/ui/utils'

interface LawyerProfile {
  name: string
  licenseNo: string
  lawFirm: string
  practiceYears: number | ''
  province: string
  city: string
  specialties: string[]
  bio: string
  hourlyRateMin: number | ''
  hourlyRateMax: number | ''
}

interface LicenseInfo {
  validFrom: string
  validTo: string
  barAssociation: string
  licenseImageUrl: string
  idCardImageUrl: string
}

interface OrderSettings {
  serviceTypes: string[]
  autoAccept: boolean
  maxConcurrent: number | ''
  responseTime: string
  minCaseAmount: number | ''
}

type ReviewStatus = 'pending' | 'approved' | 'rejected'

interface ReviewResult {
  status: ReviewStatus
  reason?: string
  reviewedAt?: string
}

interface OnboardingStatusResponse {
  current_step: number
  steps: Array<{
    name: string
    status: string
    detail?: Record<string, any> | null
  }>
}

const STEPS = [
  { key: 'basic',    label: '基本资料',   labelEn: 'Profile',  icon: User },
  { key: 'license',  label: '执业证上传', labelEn: 'License',  icon: FileCheck },
  { key: 'settings', label: '接单设置',   labelEn: 'Settings', icon: SettingsIcon },
  { key: 'submit',   label: '提交审核',   labelEn: 'Submit',   icon: CheckCircle },
] as const

const SPECIALTY_OPTIONS = [
  '合同纠纷', '劳动争议', '知识产权', '公司法务', '刑事辩护',
  '婚姻家庭', '房产纠纷', '债权债务', '交通事故', '行政诉讼',
  '税务法律', '环境法',   '国际贸易', '金融证券', '医疗纠纷',
]

const SERVICE_TYPE_OPTIONS = [
  { value: 'instant',       label: '即时咨询' },
  { value: 'appointment',   label: '预约咨询' },
  { value: 'case_delegate', label: '案件委托' },
]

const RESPONSE_TIME_OPTIONS = [
  { value: '1h',  label: '1 小时内' },
  { value: '2h',  label: '2 小时内' },
  { value: '4h',  label: '4 小时内' },
  { value: '12h', label: '12 小时内' },
  { value: '24h', label: '24 小时内' },
]

const PROVINCES = ['北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东', '福建', '重庆']

// =============== UI ===============
function Section({ tracker, title, description, children }: {
  tracker: string
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <section className="border border-border bg-card">
      <header className="px-6 py-4 border-b border-border">
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          {tracker}
        </div>
        <h3 className="font-serif text-[20px] text-foreground mt-1">{title}</h3>
        {description && <p className="text-[13px] text-muted-foreground mt-1">{description}</p>}
      </header>
      <div className="p-6">{children}</div>
    </section>
  )
}

function Field({ label, required, error, hint, children }: {
  label: string
  required?: boolean
  error?: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {children}
      {hint && !error && <p className="text-[11px] text-muted-foreground">{hint}</p>}
      {error && <p className="text-[11px] text-destructive">{error}</p>}
    </div>
  )
}

function HairlineSelectGrid({ options, selected, onToggle, columns = 4 }: {
  options: { value: string; label: string }[]
  selected: string[]
  onToggle: (value: string) => void
  columns?: number
}) {
  return (
    <div
      className={cn('grid gap-px bg-border border-t border-l border-border')}
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    >
      {options.map((opt) => {
        const isSel = selected.includes(opt.value)
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onToggle(opt.value)}
            className={cn(
              'relative bg-card border-r border-b border-border px-3 py-2.5 text-[13px] transition-colors text-center',
              isSel ? 'bg-surface-2 text-foreground' : 'text-muted-foreground hover:bg-surface-2/60',
            )}
          >
            {opt.label}
            {isSel && <span aria-hidden className="absolute left-0 top-0 bottom-0 w-px bg-primary" />}
          </button>
        )
      })}
    </div>
  )
}

function StepIndicator({ current, steps, onJump }: {
  current: number
  steps: ReadonlyArray<{ key: string; label: string; labelEn: string }>
  onJump: (idx: number) => void
}) {
  return (
    <nav
      className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border border-t border-l border-border mb-10"
      aria-label="步骤"
    >
      {steps.map((s, i) => {
        const done = i < current
        const active = i === current
        const reachable = i <= current
        return (
          <button
            key={s.key}
            type="button"
            disabled={!reachable}
            onClick={() => reachable && onJump(i)}
            className={cn(
              'relative bg-card border-r border-b border-border px-5 py-4 text-left transition-colors',
              active && 'bg-surface-2/40',
              reachable ? 'cursor-pointer hover:bg-surface-2/60' : 'cursor-not-allowed opacity-60',
            )}
          >
            <div className="flex items-center gap-3">
              <span className={cn(
                'font-serif text-[26px] leading-none tabular-nums shrink-0',
                done   ? 'text-success' :
                active ? 'text-primary' :
                         'text-muted-foreground/40',
              )}>
                {done ? <CheckCircle className="w-5 h-5 stroke-[1.5] inline" /> : String(i + 1).padStart(2, '0')}
              </span>
              <div className="min-w-0">
                <div className={cn(
                  'text-[11px] font-medium uppercase tracking-[0.16em]',
                  active ? 'text-foreground' : 'text-muted-foreground',
                )}>
                  {s.labelEn}
                </div>
                <div className={cn(
                  'text-[13px] mt-0.5 truncate',
                  active ? 'text-foreground' : 'text-muted-foreground/70',
                )}>
                  {s.label}
                </div>
              </div>
            </div>
            {active && <span aria-hidden className="absolute left-0 right-0 bottom-0 h-px bg-primary" />}
          </button>
        )
      })}
    </nav>
  )
}

// =============== 主组件 ===============
export default function LawyerOnboarding() {
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [profile, setProfile] = useState<LawyerProfile>({
    name: '', licenseNo: '', lawFirm: '', practiceYears: '',
    province: '', city: '', specialties: [], bio: '',
    hourlyRateMin: '', hourlyRateMax: '',
  })

  const [license, setLicense] = useState<LicenseInfo>({
    validFrom: '', validTo: '', barAssociation: '',
    licenseImageUrl: '', idCardImageUrl: '',
  })

  const [orderSettings, setOrderSettings] = useState<OrderSettings>({
    serviceTypes: [], autoAccept: false, maxConcurrent: 5, responseTime: '4h', minCaseAmount: '',
  })

  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const loadStatus = useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const status: OnboardingStatusResponse = await lawyerApi.getOnboardingStatus()
      applyStatus(status)
    } catch (e: any) {
      setLoadError(e?.message || '无法加载入驻进度')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadStatus() }, [loadStatus])

  function applyStatus(status: OnboardingStatusResponse) {
    const certification = status.steps.find((item) => item.name === 'certification')
    const certificationStatus = certification?.status

    if (certificationStatus === 'pending') {
      setReviewResult({ status: 'pending' })
      setStep(3)
      return
    }
    if (certificationStatus === 'approved') {
      setReviewResult({
        status: 'approved',
        reviewedAt: certification?.detail?.verified_at as string | undefined,
      })
      setStep(3)
      return
    }
    if (certificationStatus === 'rejected') {
      setReviewResult({
        status: 'rejected',
        reason: certification?.detail?.rejection_reason as string | undefined,
        reviewedAt: certification?.detail?.verified_at as string | undefined,
      })
      setStep(3)
      return
    }

    setReviewResult(null)
    setStep(Math.max(0, Math.min((status.current_step || 1) - 1, STEPS.length - 1)))
  }

  function validateStep1(): boolean {
    const newErrors: Record<string, string> = {}
    if (!profile.name || profile.name.length < 2) newErrors.name = '姓名至少 2 个字'
    if (!profile.licenseNo || profile.licenseNo.length < 5) newErrors.licenseNo = '执业证号至少 5 位'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function validateStep2(): boolean {
    const newErrors: Record<string, string> = {}
    if (!license.licenseImageUrl.trim()) newErrors.licenseImageUrl = '请填写执业证图片 URL'
    if (!license.validFrom) newErrors.validFrom = '请选择执业证签发日期'
    if (!license.validTo)   newErrors.validTo = '请选择执业证到期日期'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function validateStep3(): boolean {
    const newErrors: Record<string, string> = {}
    if (orderSettings.serviceTypes.length === 0) newErrors.serviceTypes = '请至少选择一种服务类型'
    if (!orderSettings.maxConcurrent || orderSettings.maxConcurrent < 1) newErrors.maxConcurrent = '最大并发案件数至少为 1'
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleNext() {
    if (step === 0) {
      if (!validateStep1()) { toast.error('请完善必填信息'); return }
      setSubmitting(true)
      try {
        await lawyerApi.createOrUpdateProfile({
          real_name: profile.name.trim(),
          license_number: profile.licenseNo.trim(),
          law_firm: profile.lawFirm.trim() || undefined,
          years_of_practice: Number(profile.practiceYears || 0),
          province: profile.province || undefined,
          city: profile.city.trim() || undefined,
          specializations: profile.specialties,
          bio: profile.bio.trim() || undefined,
          hourly_rate_min: profile.hourlyRateMin === '' ? undefined : Number(profile.hourlyRateMin),
          hourly_rate_max: profile.hourlyRateMax === '' ? undefined : Number(profile.hourlyRateMax),
        })
        toast.success('基本资料已保存')
      } catch (e: any) {
        toast.error(e?.message || '保存基本资料失败')
        setSubmitting(false)
        return
      } finally {
        setSubmitting(false)
      }
    }

    if (step === 1) {
      if (!validateStep2()) { toast.error('请完善执业证信息'); return }
    }

    if (step === 2) {
      if (!validateStep3()) { toast.error('请完善接单设置'); return }
      setSubmitting(true)
      try {
        await lawyerApi.updateServiceConfig({
          service_types: orderSettings.serviceTypes,
          auto_accept: orderSettings.autoAccept,
          max_concurrent_cases: Number(orderSettings.maxConcurrent || 1),
          response_time_hours: Number(orderSettings.responseTime.replace('h', '')),
          min_case_amount: orderSettings.minCaseAmount === '' ? undefined : Number(orderSettings.minCaseAmount),
        })
        toast.success('接单设置已保存')
      } catch (e: any) {
        toast.error(e?.message || '保存接单设置失败')
        setSubmitting(false)
        return
      } finally {
        setSubmitting(false)
      }
    }

    if (step < STEPS.length - 1) {
      setStep(step + 1)
      setErrors({})
    }
  }

  function handlePrev() {
    if (step > 0) {
      setStep(step - 1)
      setErrors({})
    }
  }

  async function handleSubmit() {
    if (!validateStep2()) {
      setStep(1)
      toast.error('请先完善执业证信息')
      return
    }
    setSubmitting(true)
    try {
      await lawyerApi.submitCertification({
        license_image_url: license.licenseImageUrl.trim(),
        id_card_image_url: license.idCardImageUrl.trim() || undefined,
        license_issue_date: license.validFrom,
        license_expiry_date: license.validTo,
        bar_association: license.barAssociation || undefined,
      })
      toast.success('入驻申请已提交，请耐心等待审核')
      await loadStatus()
    } catch (e: any) {
      toast.error(e?.message || '提交审核失败')
    } finally {
      setSubmitting(false)
    }
  }

  function toggleSpecialty(s: string) {
    setProfile((prev) => ({
      ...prev,
      specialties: prev.specialties.includes(s)
        ? prev.specialties.filter((x) => x !== s)
        : [...prev.specialties, s],
    }))
  }

  function toggleServiceType(val: string) {
    setOrderSettings((prev) => ({
      ...prev,
      serviceTypes: prev.serviceTypes.includes(val)
        ? prev.serviceTypes.filter((x) => x !== val)
        : [...prev.serviceTypes, val],
    }))
  }

  // ====== 渲染 ======
  if (loading) {
    return (
      <Shell>
        <Skeleton className="h-24 w-full mb-6" />
        <Skeleton className="h-64 w-full" />
      </Shell>
    )
  }

  if (loadError) {
    return (
      <Shell>
        <ErrorState
          title="入驻进度加载失败"
          message={loadError}
          onRetry={() => void loadStatus()}
        />
      </Shell>
    )
  }

  return (
    <Shell>
      <StepIndicator current={step} steps={STEPS} onJump={(i) => setStep(i)} />

      {step === 0 && (
        <Step1Basic
          profile={profile}
          setProfile={setProfile}
          errors={errors}
          toggleSpecialty={toggleSpecialty}
        />
      )}
      {step === 1 && (
        <Step2License license={license} setLicense={setLicense} errors={errors} />
      )}
      {step === 2 && (
        <Step3Settings
          settings={orderSettings}
          setSettings={setOrderSettings}
          toggleServiceType={toggleServiceType}
          errors={errors}
        />
      )}
      {step === 3 && (
        <Step4Submit
          profile={profile}
          license={license}
          settings={orderSettings}
          reviewResult={reviewResult}
        />
      )}

      {!reviewResult && (
        <div className="flex justify-between mt-8 pt-6 border-t border-border">
          <button
            type="button"
            onClick={handlePrev}
            disabled={step === 0 || submitting}
            className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed px-5 py-2 text-[13px] text-foreground transition-colors"
          >
            <ChevronLeft className="w-4 h-4 stroke-[1.5]" />
            <span>上一步</span>
          </button>
          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => void handleNext()}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              <span>{submitting ? '保存中…' : '下一步'}</span>
              {!submitting && <ChevronRight className="w-4 h-4 stroke-[1.5]" />}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={submitting}
              className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
            >
              {submitting
                ? <Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" />
                : <CheckCircle className="w-4 h-4 stroke-[1.5]" />}
              <span>{submitting ? '提交中…' : '提交审核'}</span>
            </button>
          )}
        </div>
      )}
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <div className="max-w-5xl mx-auto px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-10">
        <EditorialPageHeader
          tracker={['Network', '律师入驻']}
          title="律师入驻"
          description="完善资料 · 上传执业证 · 配置接单 · 提交审核 — 4 步开启接案。"
        />
        {children}
      </div>
    </div>
  )
}

// =============== Step 1 ===============
function Step1Basic({
  profile, setProfile, errors, toggleSpecialty,
}: {
  profile: LawyerProfile
  setProfile: React.Dispatch<React.SetStateAction<LawyerProfile>>
  errors: Record<string, string>
  toggleSpecialty: (s: string) => void
}) {
  return (
    <Section tracker="Step 01 · Profile" title="基本资料" description="填写您的执业信息与专业领域。">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
        <Field label="真实姓名" required error={errors.name}>
          <Input
            placeholder="请输入真实姓名"
            value={profile.name}
            onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
            className={cn(errors.name && 'border-destructive')}
          />
        </Field>
        <Field label="执业证号" required error={errors.licenseNo}>
          <Input
            placeholder="请输入执业证号"
            value={profile.licenseNo}
            onChange={(e) => setProfile((p) => ({ ...p, licenseNo: e.target.value }))}
            className={cn(errors.licenseNo && 'border-destructive')}
          />
        </Field>
        <Field label="所在律所">
          <Input
            placeholder="请输入律所名称"
            value={profile.lawFirm}
            onChange={(e) => setProfile((p) => ({ ...p, lawFirm: e.target.value }))}
          />
        </Field>
        <Field label="执业年限">
          <Input
            type="number"
            min={0}
            placeholder="例如: 5"
            value={profile.practiceYears}
            onChange={(e) => setProfile((p) => ({ ...p, practiceYears: e.target.value ? Number(e.target.value) : '' }))}
          />
        </Field>
        <Field label="省份">
          <Select value={profile.province} onValueChange={(v) => setProfile((p) => ({ ...p, province: v }))}>
            <SelectTrigger><SelectValue placeholder="选择省份" /></SelectTrigger>
            <SelectContent>
              {PROVINCES.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
        </Field>
        <Field label="城市">
          <Input
            placeholder="请输入城市"
            value={profile.city}
            onChange={(e) => setProfile((p) => ({ ...p, city: e.target.value }))}
          />
        </Field>
        <Field label="时费区间（¥/小时）">
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={0}
              placeholder="最低"
              value={profile.hourlyRateMin}
              onChange={(e) => setProfile((p) => ({ ...p, hourlyRateMin: e.target.value ? Number(e.target.value) : '' }))}
            />
            <span className="text-muted-foreground">—</span>
            <Input
              type="number"
              min={0}
              placeholder="最高"
              value={profile.hourlyRateMax}
              onChange={(e) => setProfile((p) => ({ ...p, hourlyRateMax: e.target.value ? Number(e.target.value) : '' }))}
            />
          </div>
        </Field>
      </div>

      <Field label="Specialties · 专业领域（多选）">
        <HairlineSelectGrid
          columns={5}
          options={SPECIALTY_OPTIONS.map((s) => ({ value: s, label: s }))}
          selected={profile.specialties}
          onToggle={toggleSpecialty}
        />
      </Field>

      <div className="mt-6">
        <Field label="个人简介">
          <textarea
            className="w-full min-h-[120px] bg-background border border-border px-3 py-2 text-[14px] text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:border-primary transition-colors resize-y"
            placeholder="简要介绍您的执业经验和专长…"
            value={profile.bio}
            onChange={(e) => setProfile((p) => ({ ...p, bio: e.target.value }))}
          />
        </Field>
      </div>
    </Section>
  )
}

// =============== Step 2 ===============
function Step2License({
  license, setLicense, errors,
}: {
  license: LicenseInfo
  setLicense: React.Dispatch<React.SetStateAction<LicenseInfo>>
  errors: Record<string, string>
}) {
  return (
    <Section tracker="Step 02 · License" title="执业证上传" description="上传执业证与有效期信息。">
      <div className="space-y-5">
        <Field
          label="执业证照片 URL"
          required
          error={errors.licenseImageUrl}
          hint="当前版本支持填写可访问的图片 URL 提交认证资料。后续会补齐平台内文件上传能力。"
        >
          <Input
            placeholder="https://example.com/license.jpg"
            value={license.licenseImageUrl}
            onChange={(e) => setLicense((p) => ({ ...p, licenseImageUrl: e.target.value }))}
            className={cn(errors.licenseImageUrl && 'border-destructive')}
          />
        </Field>

        <Field label="身份证照片 URL（可选）">
          <Input
            placeholder="https://example.com/id-card.jpg"
            value={license.idCardImageUrl}
            onChange={(e) => setLicense((p) => ({ ...p, idCardImageUrl: e.target.value }))}
          />
        </Field>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Field label="有效期起始日" error={errors.validFrom}>
            <Input
              type="date"
              value={license.validFrom}
              onChange={(e) => setLicense((p) => ({ ...p, validFrom: e.target.value }))}
              className={cn(errors.validFrom && 'border-destructive')}
            />
          </Field>
          <Field label="有效期截止日" error={errors.validTo}>
            <Input
              type="date"
              value={license.validTo}
              onChange={(e) => setLicense((p) => ({ ...p, validTo: e.target.value }))}
              className={cn(errors.validTo && 'border-destructive')}
            />
          </Field>
        </div>

        <Field label="所属律师协会（可选）">
          <Input
            placeholder="例如：北京市律师协会"
            value={license.barAssociation}
            onChange={(e) => setLicense((p) => ({ ...p, barAssociation: e.target.value }))}
          />
        </Field>
      </div>
    </Section>
  )
}

// =============== Step 3 ===============
function Step3Settings({
  settings, setSettings, toggleServiceType, errors,
}: {
  settings: OrderSettings
  setSettings: React.Dispatch<React.SetStateAction<OrderSettings>>
  toggleServiceType: (val: string) => void
  errors: Record<string, string>
}) {
  return (
    <Section tracker="Step 03 · Settings" title="接单设置" description="选择服务类型、自动接单和响应时间。">
      <div className="space-y-6">
        <Field label="Service Types · 服务类型（多选）" error={errors.serviceTypes}>
          <HairlineSelectGrid
            columns={3}
            options={SERVICE_TYPE_OPTIONS}
            selected={settings.serviceTypes}
            onToggle={toggleServiceType}
          />
        </Field>

        <div className="flex items-center justify-between py-3 border-t border-b border-border/60">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Auto Accept · 自动接单
            </div>
            <p className="text-[12px] text-muted-foreground mt-1">开启后系统将自动接受符合条件的咨询。</p>
          </div>
          <Switch
            checked={settings.autoAccept}
            onCheckedChange={(v) => setSettings((p) => ({ ...p, autoAccept: v }))}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Field label="最大并发案件数" error={errors.maxConcurrent}>
            <Input
              type="number"
              min={1}
              max={50}
              value={settings.maxConcurrent}
              onChange={(e) => setSettings((p) => ({ ...p, maxConcurrent: e.target.value ? Number(e.target.value) : '' }))}
              className={cn(errors.maxConcurrent && 'border-destructive')}
            />
          </Field>
          <Field label="承诺响应时间">
            <Select value={settings.responseTime} onValueChange={(v) => setSettings((p) => ({ ...p, responseTime: v }))}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {RESPONSE_TIME_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </Field>
          <Field label="最低接案金额（可选）">
            <Input
              type="number"
              min={0}
              placeholder="¥ 不设限则留空"
              value={settings.minCaseAmount}
              onChange={(e) => setSettings((p) => ({ ...p, minCaseAmount: e.target.value ? Number(e.target.value) : '' }))}
            />
          </Field>
        </div>
      </div>
    </Section>
  )
}

// =============== Step 4 ===============
function Step4Submit({
  profile, license, settings, reviewResult,
}: {
  profile: LawyerProfile
  license: LicenseInfo
  settings: OrderSettings
  reviewResult: ReviewResult | null
}) {
  if (reviewResult) {
    const meta = (
      reviewResult.status === 'approved'
        ? { tone: 'success' as const, icon: CheckCircle, labelEn: 'Approved', label: '审核通过', message: '恭喜！您已成功入驻安心智能助手平台。' }
        : reviewResult.status === 'rejected'
          ? { tone: 'error' as const, icon: XCircle, labelEn: 'Rejected', label: '审核驳回', message: reviewResult.reason || '材料不符合要求' }
          : { tone: 'warning' as const, icon: Clock, labelEn: 'Pending', label: '等待审核', message: '您的入驻申请已提交，预计 1-3 个工作日内完成审核。' }
    )
    const Icon = meta.icon
    const toneClass = {
      success: 'text-success',
      warning: 'text-warning',
      error:   'text-destructive',
    }[meta.tone]

    return (
      <Section tracker="Step 04 · Review" title="审核状态">
        <div className="text-center py-10">
          <Icon className={cn('w-12 h-12 stroke-[1] mx-auto mb-5', toneClass)} />
          <div className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] mb-3', toneClass)}>
            <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
            <span>{meta.labelEn}</span>
            <span className="text-foreground/30" aria-hidden>·</span>
            <span className="normal-case tracking-normal text-foreground/80">{meta.label}</span>
          </div>
          <p className="font-serif text-[20px] text-foreground mb-2">{meta.label}</p>
          <p className="text-[13px] text-muted-foreground max-w-md mx-auto">{meta.message}</p>
          {reviewResult.status === 'rejected' && (
            <Button
              variant="outline"
              className="mt-6 gap-2"
              onClick={() => window.location.reload()}
            >
              <Edit2 className="w-4 h-4 stroke-[1.5]" />
              修改后重新提交
            </Button>
          )}
        </div>
      </Section>
    )
  }

  return (
    <Section tracker="Step 04 · Submit" title="信息确认" description="请确认以下信息无误后提交审核。">
      <div className="space-y-8">
        <SummaryBlock icon={User} title="基本资料" labelEn="Profile">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <SummaryItem label="姓名"      value={profile.name || '—'} />
            <SummaryItem label="执业证号"  value={profile.licenseNo || '—'} />
            <SummaryItem label="律所"      value={profile.lawFirm || '—'} />
            <SummaryItem label="执业年限"  value={profile.practiceYears ? `${profile.practiceYears} 年` : '—'} />
            <SummaryItem label="地区"      value={[profile.province, profile.city].filter(Boolean).join(' ') || '—'} />
            <SummaryItem
              label="时费"
              value={
                profile.hourlyRateMin || profile.hourlyRateMax
                  ? `¥${profile.hourlyRateMin || '?'} - ¥${profile.hourlyRateMax || '?'}/h`
                  : '—'
              }
            />
          </div>
          {profile.specialties.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border/60">
              <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                Specialties · 专业领域
              </div>
              <div className="flex flex-wrap gap-2">
                {profile.specialties.map((s) => (
                  <span key={s} className="text-[12px] text-foreground/80 border border-border px-2.5 py-0.5">{s}</span>
                ))}
              </div>
            </div>
          )}
        </SummaryBlock>

        <SummaryBlock icon={FileCheck} title="执业证信息" labelEn="License">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <SummaryItem label="执业证" value={license.licenseImageUrl ? '已填写链接' : '未填写'} />
            <SummaryItem
              label="有效期"
              value={license.validFrom && license.validTo ? `${license.validFrom} ~ ${license.validTo}` : '—'}
            />
            <SummaryItem label="律师协会" value={license.barAssociation || '—'} />
          </div>
        </SummaryBlock>

        <SummaryBlock icon={SettingsIcon} title="接单设置" labelEn="Settings">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <SummaryItem
              label="服务类型"
              value={
                settings.serviceTypes
                  .map((v) => SERVICE_TYPE_OPTIONS.find((o) => o.value === v)?.label)
                  .filter(Boolean)
                  .join('、') || '—'
              }
            />
            <SummaryItem label="自动接单" value={settings.autoAccept ? '是' : '否'} />
            <SummaryItem label="最大并发" value={settings.maxConcurrent ? `${settings.maxConcurrent} 件` : '—'} />
            <SummaryItem
              label="响应时间"
              value={RESPONSE_TIME_OPTIONS.find((o) => o.value === settings.responseTime)?.label || '—'}
            />
            <SummaryItem
              label="最低金额"
              value={settings.minCaseAmount ? `¥${settings.minCaseAmount}` : '不限'}
            />
          </div>
        </SummaryBlock>

        {(!license.licenseImageUrl || !license.validFrom || !license.validTo) && (
          <aside className="border-l-2 border-warning/60 pl-4 py-1">
            <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-warning mb-1">
              <AlertTriangle className="w-3 h-3 stroke-[1.5]" />
              <span>Notice</span>
            </div>
            <p className="text-[13px] text-foreground/80">执业证信息不完整，提交时会自动跳回 Step 02 补全。</p>
          </aside>
        )}
      </div>
    </Section>
  )
}

function SummaryBlock({
  icon: Icon, title, labelEn, children,
}: {
  icon: typeof User
  title: string
  labelEn: string
  children: React.ReactNode
}) {
  return (
    <section className="border-l-2 border-border pl-4">
      <header className="flex items-center gap-2 mb-3">
        <Icon className="w-3.5 h-3.5 stroke-[1.5] text-muted-foreground" />
        <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          {labelEn}
          <span className="text-foreground/30 mx-1.5" aria-hidden>·</span>
          <span className="text-foreground/70 normal-case tracking-normal">{title}</span>
        </div>
      </header>
      {children}
    </section>
  )
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="text-[14px] text-foreground mt-1">{value}</p>
    </div>
  )
}
