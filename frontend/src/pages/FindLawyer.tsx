/**
 * FindLawyer · 找律师（Editorial Luxury 改造 · Phase 1.12）
 *
 * 旧版用 PageContainer + 圆形步进器 + 圆角填充按钮 + bg-primary/5 提示框。
 * 新版：EditorialPageHeader + 衬线序号步进 + 1px hairline 选项卡 + 极简选择反馈（仅 1 个左侧色条）。
 *
 * 4 步向导：describe → matching → chatting → delegate
 * 功能保持完整：consultation API、anonymous chat room、delegation API。
 */
import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { toast } from 'sonner'
import {
  FileText, Users, ShieldCheck, Building, Scale, ClipboardCheck, ShieldAlert, HelpCircle,
  Loader2, Search, Check, User, Star, MessageSquare, CheckCircle, ArrowLeft,
} from 'lucide-react'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { lawyerMatchingApi, anonymousChatApi } from '@/lib/api'
import AnonymousChatRoom from '@/components/chat/AnonymousChatRoom'
import { cn } from '@/components/ui/utils'

type Step = 'describe' | 'matching' | 'chatting' | 'delegate'
const STEPS: Step[] = ['describe', 'matching', 'chatting', 'delegate']

const LEGAL_DOMAINS = [
  { value: 'contract',   label: '合同纠纷', icon: FileText },
  { value: 'labor',      label: '劳动争议', icon: Users },
  { value: 'ip',         label: '知识产权', icon: ShieldCheck },
  { value: 'corporate',  label: '公司治理', icon: Building },
  { value: 'litigation', label: '民事诉讼', icon: Scale },
  { value: 'compliance', label: '合规审查', icon: ClipboardCheck },
  { value: 'criminal',   label: '刑事案件', icon: ShieldAlert },
  { value: 'other',      label: '其他问题', icon: HelpCircle },
]

const URGENCY_OPTIONS = [
  { value: 'low',    label: '一般咨询',   desc: '不着急，想了解一下', tone: 'normal' as const },
  { value: 'medium', label: '需要尽快',   desc: '最近需要处理',       tone: 'warning' as const },
  { value: 'high',   label: '紧急',       desc: '尽快处理',           tone: 'warning' as const },
  { value: 'urgent', label: '非常紧急',   desc: '3 分钟内匹配律师',   tone: 'error' as const },
]

const STEP_META: Record<Step, { label: string; labelEn: string }> = {
  describe: { label: '描述问题', labelEn: 'Describe' },
  matching: { label: '匹配律师', labelEn: 'Match' },
  chatting: { label: '匿名咨询', labelEn: 'Consult' },
  delegate: { label: '一键委托', labelEn: 'Delegate' },
}

function StepIndicator({ current }: { current: Step }) {
  const currentIdx = STEPS.indexOf(current)
  return (
    <nav className="grid grid-cols-4 gap-px bg-border border-t border-l border-border mb-12" aria-label="步骤">
      {STEPS.map((s, i) => {
        const done = i < currentIdx
        const active = i === currentIdx
        return (
          <div
            key={s}
            className={cn(
              'bg-card border-r border-b border-border px-5 py-4 flex items-center gap-3',
              active && 'relative',
            )}
          >
            <span className={cn(
              'font-serif text-[28px] leading-none tabular-nums shrink-0',
              done   ? 'text-success' :
              active ? 'text-primary' :
                       'text-muted-foreground/40',
            )}>
              {done ? <Check className="w-5 h-5 stroke-[1.5] inline" /> : String(i + 1).padStart(2, '0')}
            </span>
            <div className="min-w-0">
              <div className={cn(
                'text-[11px] font-medium uppercase tracking-[0.16em]',
                active ? 'text-foreground' : 'text-muted-foreground',
              )}>
                {STEP_META[s].labelEn}
              </div>
              <div className={cn(
                'text-[13px] mt-0.5 truncate',
                active ? 'text-foreground' : 'text-muted-foreground/70',
              )}>
                {STEP_META[s].label}
              </div>
            </div>
            {active && <span aria-hidden className="absolute left-0 right-0 bottom-0 h-px bg-primary" />}
          </div>
        )
      })}
    </nav>
  )
}

export default function FindLawyer() {
  const [step, setStep] = useState<Step>('describe')
  const [description, setDescription] = useState('')
  const [selectedDomain, setSelectedDomain] = useState('')
  const [urgency, setUrgency] = useState('medium')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [consultationId, setConsultationId] = useState<string | null>(null)
  const [anonymousSummary, setAnonymousSummary] = useState('')
  const [chatRoomId, setChatRoomId] = useState<string | null>(null)
  const [chatToken, setChatToken] = useState<string | null>(null)
  const [isCreatingRoom, setIsCreatingRoom] = useState(false)
  const [selectedLawyer, setSelectedLawyer] = useState<any>(null)
  const [isDelegating, setIsDelegating] = useState(false)
  const [lawyers, setLawyers] = useState<any[]>([])
  const [loadingLawyers, setLoadingLawyers] = useState(false)
  const [lawyerLoadError, setLawyerLoadError] = useState('')

  const loadLawyers = useCallback(async () => {
    if (step !== 'matching' || !consultationId) return
    setLoadingLawyers(true)
    setLawyerLoadError('')
    try {
      const result = await lawyerMatchingApi.listLawyers({
        domain: selectedDomain || undefined,
        page: 1,
        page_size: 20,
      })
      setLawyers(result.items || [])
    } catch (e: any) {
      setLawyers([])
      setLawyerLoadError(e?.message || '律师列表加载失败')
    } finally {
      setLoadingLawyers(false)
    }
  }, [consultationId, selectedDomain, step])

  useEffect(() => { void loadLawyers() }, [loadLawyers])

  const handleSubmit = useCallback(async () => {
    if (!description.trim() || description.length < 10) {
      toast.error('请详细描述您的法律问题（至少 10 个字）')
      return
    }
    setIsSubmitting(true)
    try {
      const result = await lawyerMatchingApi.createConsultation({
        description, legal_domain: selectedDomain || undefined, urgency,
      })
      setConsultationId(result.consultation_id)
      setAnonymousSummary(result.anonymous_summary)
      setStep('matching')
      toast.success('已提交，正在为您匹配律师…')
    } catch (e: any) {
      toast.error(e?.message || '提交失败，请重试')
    } finally {
      setIsSubmitting(false)
    }
  }, [description, selectedDomain, urgency])

  const handleEnterChat = useCallback(async () => {
    setIsCreatingRoom(true)
    try {
      const result = await anonymousChatApi.createRoom({
        consultation_id: consultationId || undefined,
        lawyer_name: selectedLawyer?.real_name,
      })
      setChatRoomId(result.room_id)
      setChatToken(result.user_token)
      setStep('chatting')
    } catch (e: any) {
      toast.error(e?.message || '创建聊天室失败')
    } finally {
      setIsCreatingRoom(false)
    }
  }, [consultationId, selectedLawyer])

  const handleLeaveChat = useCallback(() => {
    setChatRoomId(null)
    setChatToken(null)
    setStep('matching')
  }, [])

  const handleDelegate = useCallback(async () => {
    if (!selectedLawyer) { toast.error('请先选择一位律师'); return }
    setIsDelegating(true)
    try {
      if (!consultationId) throw new Error('咨询记录不存在，请重新发起咨询')
      await lawyerMatchingApi.createDelegation(consultationId, {
        title: `${selectedLawyer.real_name} 委托申请`,
        description: anonymousSummary || description,
        service_type: 'instant',
      })
      toast.success('委托请求已提交，律师将尽快与您联系')
      setStep('describe')
      setDescription('')
      setSelectedDomain('')
      setSelectedLawyer(null)
      setConsultationId(null)
      setAnonymousSummary('')
      setLawyers([])
    } catch (e: any) {
      toast.error(e?.message || '委托提交失败，当前需要律师先完成接单')
    } finally {
      setIsDelegating(false)
    }
  }, [anonymousSummary, consultationId, description, selectedDomain, selectedLawyer])

  /* ------------ Chat 模式 ------------ */
  if (step === 'chatting' && chatRoomId && chatToken) {
    return (
      <div className="min-h-screen flex flex-col">
        <EditorialPageHeader
          tracker={['Network', '找律师', '匿名咨询']}
          title="匿名咨询"
          description="与律师匿名沟通 — AI 隐私脱敏。"
        />
        <main className="flex-1 max-w-3xl w-full mx-auto px-8 py-8 h-[calc(100vh-200px)] min-h-[500px]">
          <AnonymousChatRoom
            roomId={chatRoomId}
            token={chatToken}
            role="user"
            onClose={handleLeaveChat}
          />
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <EditorialPageHeader
        tracker={['Network', '找律师']}
        title="找律师"
        description="AI 智能匹配 · 匿名咨询 · 隐私保护。"
      />

      <main className="flex-1 max-w-3xl w-full mx-auto px-8 py-10">
        <StepIndicator current={step} />

        <AnimatePresence mode="wait">
          {/* Step 1 · 描述 */}
          {step === 'describe' && (
            <motion.div
              key="describe"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-10"
            >
              {/* 隐私提示（hairline） */}
              <aside className="border-l-2 border-primary/40 pl-4 py-1">
                <div className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-primary mb-1">
                  <ShieldCheck className="w-3 h-3 stroke-[1.5]" />
                  <span>Privacy</span>
                </div>
                <p className="text-[13px] leading-relaxed text-foreground/80">
                  AI 自动脱敏您的描述，律师仅看到匿名案情摘要。在您主动选择委托前，律师不会知道您的任何个人信息。
                </p>
              </aside>

              {/* 法律领域 */}
              <section>
                <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
                  Domain · 选择法律领域（可选）
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border-t border-l border-border">
                  {LEGAL_DOMAINS.map((d) => {
                    const Icon = d.icon
                    const selected = selectedDomain === d.value
                    return (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => setSelectedDomain(selected ? '' : d.value)}
                        className={cn(
                          'relative bg-card border-r border-b border-border px-4 py-5 flex flex-col items-center gap-2 transition-colors',
                          selected ? 'bg-surface-2' : 'hover:bg-surface-2/60',
                        )}
                      >
                        <Icon className={cn('w-4 h-4 stroke-[1.5]', selected ? 'text-primary' : 'text-muted-foreground')} />
                        <span className={cn('text-[12px]', selected ? 'text-foreground' : 'text-muted-foreground')}>
                          {d.label}
                        </span>
                        {selected && <span aria-hidden className="absolute left-0 top-0 bottom-0 w-px bg-primary" />}
                      </button>
                    )
                  })}
                </div>
              </section>

              {/* 问题描述 */}
              <section>
                <label htmlFor="desc" className="block text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-2">
                  Description · 详细描述您的法律问题
                </label>
                <textarea
                  id="desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="请尽可能详细地描述您遇到的法律问题，AI 会自动分析并生成匿名摘要发送给律师…"
                  className="w-full h-40 p-4 bg-card border border-border text-[14px] text-foreground placeholder:text-muted-foreground/70 resize-none transition-colors focus:outline-none focus:border-primary"
                />
                <div className="mt-1 text-[11px] text-muted-foreground tabular-nums text-right">
                  {description.length} / 5000
                </div>
              </section>

              {/* 紧急程度 */}
              <section>
                <h2 className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
                  Urgency · 紧急程度
                </h2>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border-t border-l border-border">
                  {URGENCY_OPTIONS.map((u) => {
                    const selected = urgency === u.value
                    const toneClass = {
                      normal:  'text-muted-foreground',
                      warning: 'text-warning',
                      error:   'text-destructive',
                    }[u.tone]
                    return (
                      <button
                        key={u.value}
                        type="button"
                        onClick={() => setUrgency(u.value)}
                        className={cn(
                          'relative text-left bg-card border-r border-b border-border px-4 py-4 transition-colors',
                          selected ? 'bg-surface-2' : 'hover:bg-surface-2/60',
                        )}
                      >
                        <div className={cn('text-[13px] font-medium', selected ? 'text-foreground' : toneClass)}>
                          {u.label}
                        </div>
                        <div className="text-[12px] text-muted-foreground mt-0.5">{u.desc}</div>
                        {selected && <span aria-hidden className="absolute left-0 top-0 bottom-0 w-px bg-primary" />}
                      </button>
                    )
                  })}
                </div>
              </section>

              {/* 提交 */}
              <button
                type="button"
                onClick={() => void handleSubmit()}
                disabled={isSubmitting || description.length < 10}
                className="w-full py-3 bg-primary hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground text-[14px] font-medium transition-colors flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <><Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" /> AI 分析中…</>
                ) : (
                  <><Search className="w-4 h-4 stroke-[1.5]" /> 开始匹配律师</>
                )}
              </button>
            </motion.div>
          )}

          {/* Step 2 · 匹配 */}
          {step === 'matching' && (
            <motion.div
              key="matching"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-8"
            >
              {anonymousSummary && (
                <aside className="border-l-2 border-primary/40 pl-4 py-1">
                  <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-1">
                    AI Summary · 律师将看到
                  </div>
                  <p className="text-[14px] leading-relaxed text-foreground/90">{anonymousSummary}</p>
                </aside>
              )}

              <p className="text-[12px] text-muted-foreground text-center">
                匹配过程中您的个人信息完全隐藏，律师仅能看到 AI 生成的匿名摘要。
              </p>

              <section>
                <h3 className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
                  Recommended · 为您推荐
                </h3>
                {loadingLawyers ? (
                  <div className="border border-border bg-card p-8 flex items-center justify-center gap-2 text-[13px] text-muted-foreground">
                    <Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" />
                    <span>正在加载律师列表…</span>
                  </div>
                ) : lawyerLoadError ? (
                  <div className="border-l-2 border-destructive/60 pl-4 py-2">
                    <p className="text-[13px] text-destructive">{lawyerLoadError}</p>
                    <button
                      type="button"
                      onClick={() => void loadLawyers()}
                      className="mt-2 text-[12px] uppercase tracking-[0.12em] text-primary hover:text-primary-700"
                    >
                      重新加载 →
                    </button>
                  </div>
                ) : lawyers.length === 0 ? (
                  <div className="border border-border bg-card p-8 text-center text-[13px] text-muted-foreground">
                    暂无符合条件的律师，您可以返回修改领域后重试。
                  </div>
                ) : (
                  <ol className="space-y-px">
                    {lawyers.map((lawyer, i) => {
                      const badge = lawyer.is_online ? '在线' : lawyer.is_verified ? '已认证' : '待确认'
                      const badgeTone = lawyer.is_online ? 'success' : 'normal'
                      const speciality = lawyer.specializations?.[0] || selectedDomain || '综合法务'
                      const selected = selectedLawyer?.id === lawyer.id
                      return (
                        <li key={lawyer.id}>
                          <button
                            type="button"
                            onClick={() => setSelectedLawyer(lawyer)}
                            className={cn(
                              'group relative w-full text-left flex items-start gap-4 py-5 px-4 border-b border-border/60 transition-colors',
                              selected ? 'bg-surface-2' : 'hover:bg-surface-2/40',
                            )}
                          >
                            {selected && <span aria-hidden className="absolute left-0 top-0 bottom-0 w-px bg-primary" />}
                            <span className="font-serif text-[13px] text-muted-foreground w-8 shrink-0 pt-1 tabular-nums">
                              {String(i + 1).padStart(2, '0')}
                            </span>
                            <div className="w-10 h-10 border border-border flex items-center justify-center bg-card shrink-0">
                              <User className="w-5 h-5 stroke-[1.5] text-muted-foreground" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-3 flex-wrap">
                                <span className="font-serif text-[16px] text-foreground">{lawyer.real_name}</span>
                                <span className={cn(
                                  'inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-[0.16em]',
                                  badgeTone === 'success' ? 'text-success' : 'text-muted-foreground',
                                )}>
                                  <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
                                  <span>{badge}</span>
                                </span>
                              </div>
                              <p className="text-[12px] text-muted-foreground mt-1">
                                {speciality} · {lawyer.years_of_practice || 0} 年执业 · {lawyer.total_cases || 0}+ 案件
                              </p>
                              {lawyer.law_firm && (
                                <p className="text-[12px] text-muted-foreground/80 mt-0.5">{lawyer.law_firm}</p>
                              )}
                            </div>
                            <div className="text-right shrink-0">
                              <div className="inline-flex items-center gap-1 text-warning">
                                <Star className="w-3.5 h-3.5 stroke-[1.5] fill-current" />
                                <span className="text-[13px] font-medium tabular-nums">{(lawyer.rating || 0).toFixed(1)}</span>
                              </div>
                            </div>
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                )}
              </section>

              <div className="flex items-center justify-between gap-4 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={() => setStep('describe')}
                  className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="w-4 h-4 stroke-[1.5]" />
                  <span>返回修改</span>
                </button>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => void handleEnterChat()}
                    disabled={isCreatingRoom || !selectedLawyer}
                    className="inline-flex items-center gap-1.5 border border-border bg-card hover:bg-surface-2 disabled:opacity-50 disabled:cursor-not-allowed px-5 py-2 text-[13px] text-foreground transition-colors"
                  >
                    {isCreatingRoom ? (
                      <><Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" /> 创建聊天室…</>
                    ) : (
                      <><MessageSquare className="w-4 h-4 stroke-[1.5]" /> 匿名咨询</>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setStep('delegate')}
                    disabled={!selectedLawyer}
                    className="inline-flex items-center gap-1.5 bg-primary hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground px-5 py-2 text-[13px] font-medium transition-colors"
                  >
                    <Check className="w-4 h-4 stroke-[1.5]" /> 一键委托
                  </button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Step 4 · 委托 */}
          {step === 'delegate' && (
            <motion.div
              key="delegate"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="space-y-8 max-w-md mx-auto"
            >
              <header className="text-center">
                <CheckCircle className="w-12 h-12 stroke-[1.5] text-success mx-auto mb-3" />
                <h3 className="font-serif text-[24px] text-foreground">确认委托</h3>
                <p className="text-[13px] text-muted-foreground mt-2">确认后将向律师发送委托请求。</p>
              </header>

              {selectedLawyer && (
                <div className="border border-border bg-card p-5 flex items-center gap-4">
                  <div className="w-10 h-10 border border-border flex items-center justify-center">
                    <User className="w-5 h-5 stroke-[1.5] text-primary" />
                  </div>
                  <div className="min-w-0">
                    <div className="font-serif text-[16px] text-foreground">{selectedLawyer.real_name}</div>
                    <div className="text-[12px] text-muted-foreground mt-0.5">
                      {selectedLawyer.specializations?.[0] || '综合法务'} · {selectedLawyer.years_of_practice || 0} 年执业
                    </div>
                  </div>
                </div>
              )}

              <aside className="border-l-2 border-warning/60 pl-4 py-1">
                <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-warning mb-1">
                  Notice · 提示
                </div>
                <p className="text-[13px] text-foreground/80 leading-relaxed">
                  委托后，您的联系方式将对律师可见。律师将在 24 小时内与您取得联系。如有问题请联系客服。
                </p>
              </aside>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setStep('matching')}
                  className="flex-1 border border-border bg-card hover:bg-surface-2 py-2.5 text-[13px] text-foreground transition-colors"
                >
                  返回选择
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelegate()}
                  disabled={isDelegating}
                  className="flex-1 bg-primary hover:bg-primary-700 disabled:opacity-50 text-primary-foreground py-2.5 text-[13px] font-medium transition-colors flex items-center justify-center gap-2"
                >
                  {isDelegating ? (
                    <><Loader2 className="w-4 h-4 stroke-[1.5] animate-spin" /> 提交中…</>
                  ) : (
                    '确认委托'
                  )}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
