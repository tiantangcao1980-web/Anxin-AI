/**
 * LawyerOnboarding - 律师入驻引导页
 *
 * 4 步 Stepper 流程：基本资料 → 执业证上传 → 接单设置 → 提交审核
 * 使用 design-tokens 统一样式，联调真实 API
 */

import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, statusBadge, iconSize, inputStyle } from '@/lib/design-tokens'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { lawyerApi } from '@/lib/api'

// ============ 类型定义 ============

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

// ============ 常量 ============

const STEPS = [
  { key: 'basic', label: '基本资料', icon: icons.User },
  { key: 'license', label: '执业证上传', icon: icons.FileCheck },
  { key: 'settings', label: '接单设置', icon: icons.Settings },
  { key: 'submit', label: '提交审核', icon: icons.CheckCircle },
] as const

const SPECIALTY_OPTIONS = [
  '合同纠纷', '劳动争议', '知识产权', '公司法务', '刑事辩护',
  '婚姻家庭', '房产纠纷', '债权债务', '交通事故', '行政诉讼',
  '税务法律', '环境法', '国际贸易', '金融证券', '医疗纠纷',
]

const SERVICE_TYPE_OPTIONS = [
  { value: 'instant', label: '即时咨询' },
  { value: 'appointment', label: '预约咨询' },
  { value: 'case_delegate', label: '案件委托' },
]

const RESPONSE_TIME_OPTIONS = [
  { value: '1h', label: '1 小时内' },
  { value: '2h', label: '2 小时内' },
  { value: '4h', label: '4 小时内' },
  { value: '12h', label: '12 小时内' },
  { value: '24h', label: '24 小时内' },
]

const PROVINCES = [
  '北京', '上海', '广东', '浙江', '江苏', '四川', '湖北', '山东', '福建', '重庆',
]

// ============ 主组件 ============

export default function LawyerOnboarding() {
  const [loading, setLoading] = useState(true)
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  // Step 1: 基本资料
  const [profile, setProfile] = useState<LawyerProfile>({
    name: '',
    licenseNo: '',
    lawFirm: '',
    practiceYears: '',
    province: '',
    city: '',
    specialties: [],
    bio: '',
    hourlyRateMin: '',
    hourlyRateMax: '',
  })

  // Step 2: 执业证
  const [license, setLicense] = useState<LicenseInfo>({
    validFrom: '',
    validTo: '',
    barAssociation: '',
    licenseImageUrl: '',
    idCardImageUrl: '',
  })

  // Step 3: 接单设置
  const [orderSettings, setOrderSettings] = useState<OrderSettings>({
    serviceTypes: [],
    autoAccept: false,
    maxConcurrent: 5,
    responseTime: '4h',
    minCaseAmount: '',
  })

  // Step 4: 审核结果
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null)

  // 验证错误
  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    loadStatus()
  }, [])

  async function loadStatus() {
    setLoading(true)
    setLoadError(null)
    try {
      const status: OnboardingStatusResponse = await lawyerApi.getOnboardingStatus()
      applyStatus(status)
    } catch (e: any) {
      setLoadError(e.message || '无法加载入驻进度')
    } finally {
      setLoading(false)
    }
  }

  function applyStatus(status: OnboardingStatusResponse) {
    const certification = status.steps.find(item => item.name === 'certification')
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

  // ===== 验证 =====

  function validateStep1(): boolean {
    const newErrors: Record<string, string> = {}
    if (!profile.name || profile.name.length < 2) {
      newErrors.name = '姓名至少 2 个字'
    }
    if (!profile.licenseNo || profile.licenseNo.length < 5) {
      newErrors.licenseNo = '执业证号至少 5 位'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function validateStep2(): boolean {
    const newErrors: Record<string, string> = {}
    if (!license.licenseImageUrl.trim()) {
      newErrors.licenseImageUrl = '请填写执业证图片 URL'
    }
    if (!license.validFrom) {
      newErrors.validFrom = '请选择执业证签发日期'
    }
    if (!license.validTo) {
      newErrors.validTo = '请选择执业证到期日期'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function validateStep3(): boolean {
    const newErrors: Record<string, string> = {}
    if (orderSettings.serviceTypes.length === 0) {
      newErrors.serviceTypes = '请至少选择一种服务类型'
    }
    if (!orderSettings.maxConcurrent || orderSettings.maxConcurrent < 1) {
      newErrors.maxConcurrent = '最大并发案件数至少为 1'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleNext() {
    if (step === 0) {
      if (!validateStep1()) {
        toast.error('请完善必填信息')
        return
      }
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
        toast.error(e.message || '保存基本资料失败')
        setSubmitting(false)
        return
      } finally {
        setSubmitting(false)
      }
    }

    if (step === 1) {
      if (!validateStep2()) {
        toast.error('请完善执业证信息')
        return
      }
    }

    if (step === 2) {
      if (!validateStep3()) {
        toast.error('请完善接单设置')
        return
      }
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
        toast.error(e.message || '保存接单设置失败')
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
      toast.error(e.message || '提交审核失败')
    } finally {
      setSubmitting(false)
    }
  }

  function toggleSpecialty(s: string) {
    setProfile(prev => ({
      ...prev,
      specialties: prev.specialties.includes(s)
        ? prev.specialties.filter(x => x !== s)
        : [...prev.specialties, s],
    }))
  }

  function toggleServiceType(val: string) {
    setOrderSettings(prev => ({
      ...prev,
      serviceTypes: prev.serviceTypes.includes(val)
        ? prev.serviceTypes.filter(x => x !== val)
        : [...prev.serviceTypes, val],
    }))
  }

  // ===== 渲染 =====

  if (loading) {
    return (
      <PageContainer title="律师入驻" description="完善资料，开始接案">
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </PageContainer>
    )
  }

  if (loadError) {
    return (
      <PageContainer title="律师入驻" description="完善资料，开始接案">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-12 text-center`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>入驻进度加载失败</p>
          <p className={`${heading.muted} mt-1`}>{loadError}</p>
          <Button className="mt-4 gap-2" onClick={loadStatus}>
            <icons.RefreshCw className={iconSize.sm} />
            重新加载
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="律师入驻" description="完善资料，开始接案">
      {/* Stepper 导航 */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {STEPS.map((s, i) => {
          const Icon = s.icon
          const isActive = i === step
          const isDone = i < step
          return (
            <button
              key={s.key}
              onClick={() => { if (i <= step) setStep(i) }}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : isDone
                  ? 'bg-primary/10 text-primary'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              <Icon className={iconSize.sm} />
              <span className="hidden sm:inline">{s.label}</span>
              <span className="sm:hidden">{i + 1}</span>
            </button>
          )
        })}
      </div>

      {/* 步骤进度条 */}
      <div className="w-full bg-muted rounded-full h-1.5">
        <div
          className="bg-primary h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
        />
      </div>

      {/* 步骤内容 */}
      <div className={cardStyle.base}>
        {step === 0 && <Step1Basic profile={profile} setProfile={setProfile} errors={errors} toggleSpecialty={toggleSpecialty} />}
        {step === 1 && <Step2License license={license} setLicense={setLicense} errors={errors} />}
        {step === 2 && <Step3Settings settings={orderSettings} setSettings={setOrderSettings} toggleServiceType={toggleServiceType} errors={errors} />}
        {step === 3 && (
          <Step4Submit
            profile={profile}
            license={license}
            settings={orderSettings}
            reviewResult={reviewResult}
            onSubmit={handleSubmit}
          />
        )}
      </div>

      {/* 底部导航按钮 */}
      {!reviewResult && (
        <div className="flex justify-between">
          <Button
            variant="outline"
            onClick={handlePrev}
            disabled={step === 0 || submitting}
            className="gap-2"
          >
            <icons.ChevronLeft className={iconSize.sm} />
            上一步
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={handleNext} className="gap-2" disabled={submitting}>
              {submitting ? '保存中...' : '下一步'}
              {!submitting && <icons.ChevronRight className={iconSize.sm} />}
            </Button>
          ) : (
            <Button onClick={handleSubmit} className="gap-2" disabled={submitting}>
              {submitting ? <icons.Loader2 className={`${iconSize.sm} animate-spin`} /> : <icons.CheckCircle className={iconSize.sm} />}
              {submitting ? '提交中...' : '提交审核'}
            </Button>
          )}
        </div>
      )}
    </PageContainer>
  )
}

// ============ Step 1: 基本资料 ============

function Step1Basic({
  profile,
  setProfile,
  errors,
  toggleSpecialty,
}: {
  profile: LawyerProfile
  setProfile: React.Dispatch<React.SetStateAction<LawyerProfile>>
  errors: Record<string, string>
  toggleSpecialty: (s: string) => void
}) {
  return (
    <div className="space-y-5">
      <h3 className={heading.section}>基本资料</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 真实姓名 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">
            真实姓名 <span className="text-destructive">*</span>
          </Label>
          <Input
            placeholder="请输入真实姓名"
            value={profile.name}
            onChange={e => setProfile(p => ({ ...p, name: e.target.value }))}
            className={errors.name ? 'border-destructive' : ''}
          />
          {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
        </div>

        {/* 执业证号 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">
            执业证号 <span className="text-destructive">*</span>
          </Label>
          <Input
            placeholder="请输入执业证号"
            value={profile.licenseNo}
            onChange={e => setProfile(p => ({ ...p, licenseNo: e.target.value }))}
            className={errors.licenseNo ? 'border-destructive' : ''}
          />
          {errors.licenseNo && <p className="text-xs text-destructive">{errors.licenseNo}</p>}
        </div>

        {/* 所在律所 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">所在律所</Label>
          <Input
            placeholder="请输入律所名称"
            value={profile.lawFirm}
            onChange={e => setProfile(p => ({ ...p, lawFirm: e.target.value }))}
          />
        </div>

        {/* 执业年限 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">执业年限</Label>
          <Input
            type="number"
            min={0}
            placeholder="例如: 5"
            value={profile.practiceYears}
            onChange={e => setProfile(p => ({ ...p, practiceYears: e.target.value ? Number(e.target.value) : '' }))}
          />
        </div>

        {/* 省份 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">省/市</Label>
          <Select value={profile.province} onValueChange={v => setProfile(p => ({ ...p, province: v }))}>
            <SelectTrigger>
              <SelectValue placeholder="选择省份" />
            </SelectTrigger>
            <SelectContent>
              {PROVINCES.map(p => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 城市 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">城市</Label>
          <Input
            placeholder="请输入城市"
            value={profile.city}
            onChange={e => setProfile(p => ({ ...p, city: e.target.value }))}
          />
        </div>

        {/* 时费区间 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">时费区间 (¥/小时)</Label>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={0}
              placeholder="最低"
              value={profile.hourlyRateMin}
              onChange={e => setProfile(p => ({ ...p, hourlyRateMin: e.target.value ? Number(e.target.value) : '' }))}
            />
            <span className="text-muted-foreground">—</span>
            <Input
              type="number"
              min={0}
              placeholder="最高"
              value={profile.hourlyRateMax}
              onChange={e => setProfile(p => ({ ...p, hourlyRateMax: e.target.value ? Number(e.target.value) : '' }))}
            />
          </div>
        </div>
      </div>

      {/* 专业领域 */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">专业领域（多选）</Label>
        <div className="flex flex-wrap gap-2">
          {SPECIALTY_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => toggleSpecialty(s)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                profile.specialties.includes(s)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* 个人简介 */}
      <div className="space-y-1.5">
        <Label className="text-sm font-medium">个人简介</Label>
        <textarea
          className="w-full min-h-[100px] bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all resize-y"
          placeholder="简要介绍您的执业经验和专长..."
          value={profile.bio}
          onChange={e => setProfile(p => ({ ...p, bio: e.target.value }))}
        />
      </div>
    </div>
  )
}

// ============ Step 2: 执业证上传 ============

function Step2License({
  license,
  setLicense,
  errors,
}: {
  license: LicenseInfo
  setLicense: React.Dispatch<React.SetStateAction<LicenseInfo>>
  errors: Record<string, string>
}) {
  return (
    <div className="space-y-5">
      <h3 className={heading.section}>执业证上传</h3>

      <div className="space-y-2">
        <Label className="text-sm font-medium">
          执业证照片 URL <span className="text-destructive">*</span>
        </Label>
        <Input
          placeholder="https://example.com/license.jpg"
          value={license.licenseImageUrl}
          onChange={e => setLicense(p => ({ ...p, licenseImageUrl: e.target.value }))}
          className={errors.licenseImageUrl ? 'border-destructive' : ''}
        />
        <p className="text-xs text-muted-foreground">
          当前版本支持填写可访问的图片 URL 提交认证资料。后续会补齐平台内文件上传能力。
        </p>
        {errors.licenseImageUrl && <p className="text-xs text-destructive">{errors.licenseImageUrl}</p>}
      </div>

      <div className="space-y-2">
        <Label className="text-sm font-medium">身份证照片 URL（可选）</Label>
        <Input
          placeholder="https://example.com/id-card.jpg"
          value={license.idCardImageUrl}
          onChange={e => setLicense(p => ({ ...p, idCardImageUrl: e.target.value }))}
        />
      </div>

      {/* 有效期 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">有效期起始日</Label>
          <Input
            type="date"
            value={license.validFrom}
            onChange={e => setLicense(p => ({ ...p, validFrom: e.target.value }))}
            className={errors.validFrom ? 'border-destructive' : ''}
          />
          {errors.validFrom && <p className="text-xs text-destructive">{errors.validFrom}</p>}
        </div>
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">有效期截止日</Label>
          <Input
            type="date"
            value={license.validTo}
            onChange={e => setLicense(p => ({ ...p, validTo: e.target.value }))}
            className={errors.validTo ? 'border-destructive' : ''}
          />
          {errors.validTo && <p className="text-xs text-destructive">{errors.validTo}</p>}
        </div>
      </div>

      {/* 律师协会 */}
      <div className="space-y-1.5">
        <Label className="text-sm font-medium">所属律师协会（可选）</Label>
        <Input
          placeholder="例如：北京市律师协会"
          value={license.barAssociation}
          onChange={e => setLicense(p => ({ ...p, barAssociation: e.target.value }))}
        />
      </div>
    </div>
  )
}

// ============ Step 3: 接单设置 ============

function Step3Settings({
  settings,
  setSettings,
  toggleServiceType,
  errors,
}: {
  settings: OrderSettings
  setSettings: React.Dispatch<React.SetStateAction<OrderSettings>>
  toggleServiceType: (val: string) => void
  errors: Record<string, string>
}) {
  return (
    <div className="space-y-5">
      <h3 className={heading.section}>接单设置</h3>

      {/* 服务类型 */}
      <div className="space-y-2">
        <Label className="text-sm font-medium">服务类型（多选）</Label>
        <div className="flex flex-wrap gap-2">
          {SERVICE_TYPE_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => toggleServiceType(opt.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                settings.serviceTypes.includes(opt.value)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {errors.serviceTypes && <p className="text-xs text-destructive">{errors.serviceTypes}</p>}
      </div>

      {/* 自动接单 */}
      <div className="flex items-center justify-between py-3">
        <div>
          <Label className="text-sm font-medium">自动接单</Label>
          <p className="text-xs text-muted-foreground mt-0.5">开启后系统将自动接受符合条件的咨询</p>
        </div>
        <Switch
          checked={settings.autoAccept}
          onCheckedChange={v => setSettings(p => ({ ...p, autoAccept: v }))}
        />
      </div>

      <Separator />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 最大并发案件数 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">最大并发案件数</Label>
          <Input
            type="number"
            min={1}
            max={50}
            value={settings.maxConcurrent}
            onChange={e => setSettings(p => ({ ...p, maxConcurrent: e.target.value ? Number(e.target.value) : '' }))}
            className={errors.maxConcurrent ? 'border-destructive' : ''}
          />
          {errors.maxConcurrent && <p className="text-xs text-destructive">{errors.maxConcurrent}</p>}
        </div>

        {/* 承诺响应时间 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">承诺响应时间</Label>
          <Select value={settings.responseTime} onValueChange={v => setSettings(p => ({ ...p, responseTime: v }))}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RESPONSE_TIME_OPTIONS.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 最低接案金额 */}
        <div className="space-y-1.5">
          <Label className="text-sm font-medium">最低接案金额（可选）</Label>
          <Input
            type="number"
            min={0}
            placeholder="¥ 不设限则留空"
            value={settings.minCaseAmount}
            onChange={e => setSettings(p => ({ ...p, minCaseAmount: e.target.value ? Number(e.target.value) : '' }))}
          />
        </div>
      </div>
    </div>
  )
}

// ============ Step 4: 提交审核 ============

function Step4Submit({
  profile,
  license,
  settings,
  reviewResult,
  onSubmit,
}: {
  profile: LawyerProfile
  license: LicenseInfo
  settings: OrderSettings
  reviewResult: ReviewResult | null
  onSubmit: () => void
}) {
  // 审核状态展示
  if (reviewResult) {
    return (
      <div className="space-y-5">
        <h3 className={heading.section}>审核状态</h3>
        <div className="flex flex-col items-center gap-4 py-8">
          {reviewResult.status === 'pending' && (
            <>
              <icons.Clock className={`${iconSize['2xl']} text-amber-500`} />
              <Badge className={statusBadge.warning}>等待审核</Badge>
              <p className={heading.muted}>您的入驻申请已提交，预计 1-3 个工作日内完成审核</p>
            </>
          )}
          {reviewResult.status === 'approved' && (
            <>
              <icons.CheckCircle className={`${iconSize['2xl']} text-emerald-500`} />
              <Badge className={statusBadge.success}>审核通过</Badge>
              <p className={heading.muted}>恭喜！您已成功入驻安心法务平台</p>
            </>
          )}
          {reviewResult.status === 'rejected' && (
            <>
              <icons.XCircle className={`${iconSize['2xl']} text-red-500`} />
              <Badge className={statusBadge.error}>审核驳回</Badge>
              {reviewResult.reason && (
                <p className="text-sm text-destructive text-center max-w-md">
                  驳回原因：{reviewResult.reason}
                </p>
              )}
              <Button onClick={() => window.location.reload()} variant="outline" className="mt-2 gap-2">
                <icons.Edit className={iconSize.sm} />
                修改后重新提交
              </Button>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <h3 className={heading.section}>信息确认</h3>
      <p className={heading.muted}>请确认以下信息无误后提交审核</p>

      {/* 基本资料汇总 */}
      <div className={cardStyle.flat}>
        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <icons.User className={iconSize.sm} />
          基本资料
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <SummaryItem label="姓名" value={profile.name || '—'} />
          <SummaryItem label="执业证号" value={profile.licenseNo || '—'} />
          <SummaryItem label="律所" value={profile.lawFirm || '—'} />
          <SummaryItem label="执业年限" value={profile.practiceYears ? `${profile.practiceYears} 年` : '—'} />
          <SummaryItem label="地区" value={[profile.province, profile.city].filter(Boolean).join(' ') || '—'} />
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
          <div className="mt-3">
            <span className="text-xs text-muted-foreground">专业领域：</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {profile.specialties.map(s => (
                <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 执业证汇总 */}
      <div className={cardStyle.flat}>
        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <icons.FileCheck className={iconSize.sm} />
          执业证信息
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <SummaryItem label="执业证" value={license.licenseImageUrl ? '已填写链接' : '未填写'} />
          <SummaryItem label="有效期" value={license.validFrom && license.validTo ? `${license.validFrom} ~ ${license.validTo}` : '—'} />
          <SummaryItem label="律师协会" value={license.barAssociation || '—'} />
        </div>
      </div>

      {/* 接单设置汇总 */}
      <div className={cardStyle.flat}>
        <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <icons.Settings className={iconSize.sm} />
          接单设置
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <SummaryItem
            label="服务类型"
            value={
              settings.serviceTypes
                .map(v => SERVICE_TYPE_OPTIONS.find(o => o.value === v)?.label)
                .filter(Boolean)
                .join('、') || '—'
            }
          />
          <SummaryItem label="自动接单" value={settings.autoAccept ? '是' : '否'} />
          <SummaryItem label="最大并发" value={settings.maxConcurrent ? `${settings.maxConcurrent} 件` : '—'} />
          <SummaryItem
            label="响应时间"
            value={RESPONSE_TIME_OPTIONS.find(o => o.value === settings.responseTime)?.label || '—'}
          />
          <SummaryItem
            label="最低金额"
            value={settings.minCaseAmount ? `¥${settings.minCaseAmount}` : '不限'}
          />
        </div>
      </div>
    </div>
  )
}

// ============ 辅助组件 ============

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground font-medium mt-0.5">{value}</p>
    </div>
  )
}
