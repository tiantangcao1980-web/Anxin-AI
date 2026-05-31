/**
 * OnboardingWizard — 桌面端首次启动引导
 *
 * 4 步：
 *  1. 欢迎 + 产品介绍
 *  2. 选择隐私模式（local / hybrid / cloud）
 *  3. 配置 LLM（跳到 /private-llm 页面，或快速选 Ollama 本地）
 *  4. 完成 + 推荐入口
 *
 * 触发：App.tsx Layout mount 后，未完成（localStorage anxin.onboarding.completed.v1 !== 'true'）
 * 持久：localStorage + Tauri store（如可用）
 *
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §5
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { useAppModeStore } from '@/lib/store'
import { checkLlmStatus, type LlmStatus } from '@/lib/llm-status'

export const ONBOARDING_KEY = 'anxin.onboarding.completed.v1'

type Step = 1 | 2 | 3 | 4

interface PrivacyMode {
  id: 'local' | 'hybrid' | 'cloud'
  icon: keyof typeof icons
  title: string
  subtitle: string
  recommended?: boolean
}

const PRIVACY_MODES: PrivacyMode[] = [
  {
    id: 'local',
    icon: 'Lock',
    title: '完全本地',
    subtitle: '数据不出设备，AI 也在本机运行（需要本地 LLM）',
  },
  {
    id: 'hybrid',
    icon: 'RefreshCw',
    title: '智能混合',
    subtitle: '敏感数据本地，其它通过云端协作',
    recommended: true,
  },
  {
    id: 'cloud',
    icon: 'Cloud',
    title: '全云端',
    subtitle: '最佳体验，全云端协作，跨设备无缝',
  },
]

const PERSONAS_PREVIEW = [
  { emoji: '🎯', name: '安心助理', desc: '综合协调' },
  { emoji: '⚖️', name: '法律顾问', desc: '合规经营' },
  { emoji: '📄', name: '合同管家', desc: '审查 / 起草' },
  { emoji: '💰', name: '财税顾问', desc: '财税合规' },
  { emoji: '📋', name: '流程管家', desc: 'OKR / 周报' },
  { emoji: '📊', name: '市场研究员', desc: 'DeepResearch' },
  { emoji: '🎯', name: '获客猎手', desc: 'Lead / 邮件' },
  { emoji: '✍️', name: '内容总监', desc: '公众号 / 海报' },
  { emoji: '🌍', name: '跨境电商助手', desc: '选品 / VAT' },
  { emoji: '🔍', name: '尽调专家', desc: '企业尽调' },
]

const FINAL_ENTRIES = [
  {
    icon: 'MessageSquare' as const,
    title: '消息',
    desc: '人 / agent / 群聊',
    href: '/chat',
  },
  {
    icon: 'ClipboardCheck' as const,
    title: '任务',
    desc: 'Agent 任务中心',
    href: '/v3/tasks',
  },
  {
    icon: 'LayoutGrid' as const,
    title: '工作台',
    desc: '10 personas',
    href: '/agents',
  },
  {
    icon: 'BookOpen' as const,
    title: '知识',
    desc: '文档 / 智库 / 图谱',
    href: '/knowledge-base',
  },
]

interface OnboardingWizardProps {
  /** 强制显示（用于"重新查看引导"入口）。默认按 localStorage 自动判断 */
  forceOpen?: boolean
  /** 关闭时回调（通常 forceOpen 模式下用） */
  onClose?: () => void
}

function hasCompletedOnboarding(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_KEY) === 'true'
  } catch {
    return false
  }
}

function markCompleted(): void {
  try {
    localStorage.setItem(ONBOARDING_KEY, 'true')
    localStorage.setItem('anxin.onboarding.completedAt', new Date().toISOString())
  } catch {
    // ignore
  }
}

export function OnboardingWizard({ forceOpen = false, onClose }: OnboardingWizardProps = {}) {
  const navigate = useNavigate()
  const { setMode } = useAppModeStore()
  const [open, setOpen] = useState<boolean>(() => forceOpen || !hasCompletedOnboarding())
  const [step, setStep] = useState<Step>(1)
  const [selectedMode, setSelectedMode] = useState<PrivacyMode['id']>('hybrid')
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null)
  const [checkingLlm, setCheckingLlm] = useState(false)

  // 进入 step 3 时检测当前 LLM 配置
  useEffect(() => {
    if (step !== 3) return
    let active = true
    setCheckingLlm(true)
    checkLlmStatus()
      .then((s) => {
        if (active) setLlmStatus(s)
      })
      .finally(() => {
        if (active) setCheckingLlm(false)
      })
    return () => {
      active = false
    }
  }, [step])

  if (!open) return null

  const close = (completed: boolean) => {
    if (completed) markCompleted()
    setOpen(false)
    onClose?.()
  }

  const next = () => setStep((prev) => (prev < 4 ? ((prev + 1) as Step) : prev))
  const back = () => setStep((prev) => (prev > 1 ? ((prev - 1) as Step) : prev))

  const handleSelectMode = (modeId: PrivacyMode['id']) => {
    setSelectedMode(modeId)
    // 同步到全局 store；桌面端 ModeGate / Tauri runtime_config 会在用户进入相应路由时
    // 通过 set_app_mode IPC 命令持久化到本地 runtime-config.json。
    // PrivacyMode.id 的 'local' 对应 AppMode 的 'top-secret'（本地/涉密模式）。
    setMode(modeId === 'local' ? 'top-secret' : modeId)
  }

  const handleFinish = (href?: string) => {
    close(true)
    if (href) navigate(href)
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div className="bg-surface-1 rounded-xl border border-border shadow-float w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* 进度条 */}
        <div className="h-1 bg-surface-2">
          <div
            className="h-full bg-primary transition-all duration-300"
            style={{ width: `${(step / 4) * 100}%` }}
          />
        </div>

        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>第 {step} 步 / 共 4 步</span>
          </div>
          {forceOpen && (
            <button
              type="button"
              onClick={() => close(false)}
              className="p-1.5 rounded-md hover:bg-surface-2 transition-colors"
              aria-label="关闭"
            >
              <icons.X className="w-4 h-4 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {step === 1 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-primary flex items-center justify-center shadow-sm">
                  <icons.Sparkles className="w-6 h-6 text-primary-foreground" />
                </div>
                <div>
                  <h2 id="onboarding-title" className="text-xl font-medium text-foreground">
                    欢迎使用安心智能助手
                  </h2>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    一个 App 搞定法务 / 财务 / 税务 / 合规 / 经营管理 / 内容 / 出海
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-6">
                {PERSONAS_PREVIEW.map((p) => (
                  <div
                    key={p.name}
                    className="flex flex-col items-center text-center gap-1 p-3 rounded-md bg-surface-2 border border-border/60"
                  >
                    <span className="text-2xl leading-none">{p.emoji}</span>
                    <span className="text-xs font-medium text-foreground mt-1">{p.name}</span>
                    <span className="text-[10px] text-muted-foreground">{p.desc}</span>
                  </div>
                ))}
              </div>

              <p className="text-xs text-muted-foreground mt-6">
                接下来 3 步：选择隐私模式 → 配置 AI 模型 → 完成。整个过程约 1 分钟。
              </p>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 id="onboarding-title" className="text-xl font-medium text-foreground">
                选择隐私模式
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                可随时在「设置 → 隐私模式」更改。
              </p>
              <div className="space-y-2 mt-5">
                {PRIVACY_MODES.map((mode) => {
                  const Icon = icons[mode.icon] as React.ComponentType<{ className?: string }>
                  const isSelected = selectedMode === mode.id
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => handleSelectMode(mode.id)}
                      className={`w-full flex items-start gap-3 p-4 rounded-lg border text-left transition-colors ${
                        isSelected
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-border-strong hover:bg-surface-2'
                      }`}
                    >
                      <Icon
                        className={`w-5 h-5 mt-0.5 shrink-0 ${
                          isSelected ? 'text-primary' : 'text-muted-foreground'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-foreground">{mode.title}</span>
                          {mode.recommended && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                              推荐
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{mode.subtitle}</p>
                      </div>
                      {isSelected && <icons.Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 id="onboarding-title" className="text-xl font-medium text-foreground">
                配置 AI 模型
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                安心智能助手不绑定特定模型，你可以使用任意 LLM 提供商或本地模型。
              </p>

              {checkingLlm && (
                <div className="mt-5 p-4 rounded-lg border border-border bg-surface-2">
                  <p className="text-sm text-muted-foreground">检测现有配置中...</p>
                </div>
              )}

              {!checkingLlm && llmStatus?.configured && (
                <div className="mt-5 p-4 rounded-lg border border-success/40 bg-success/5">
                  <div className="flex items-center gap-2">
                    <icons.CheckCircle className="w-5 h-5 text-success" />
                    <p className="font-medium text-sm text-foreground">已检测到可用模型</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    默认 provider：
                    <span className="font-mono ml-1">{llmStatus.defaultProvider ?? '未知'}</span>
                    {llmStatus.defaultModel && (
                      <>
                        ，模型：<span className="font-mono ml-1">{llmStatus.defaultModel}</span>
                      </>
                    )}
                    。可继续下一步，或前往"设置 → AI 模型"调整。
                  </p>
                </div>
              )}

              {!checkingLlm && llmStatus && !llmStatus.configured && (
                <div className="mt-5 p-4 rounded-lg border border-warning/40 bg-warning/5">
                  <div className="flex items-center gap-2">
                    <icons.AlertTriangle className="w-5 h-5 text-warning" />
                    <p className="font-medium text-sm text-foreground">尚未配置 AI 模型</p>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    {selectedMode === 'local'
                      ? '本地模式需要先在本机安装 Ollama 或 LMStudio。'
                      : '可使用 OpenAI / Anthropic / 通义 / DeepSeek / 混元 等远程模型，或本地 Ollama / LMStudio。'}
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      // 跳到 LLM 配置页，但保持 wizard 打开状态
                      // 用户配置完返回后会重检测
                      navigate('/private-llm')
                    }}
                    className="mt-3 px-4 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-600 transition-colors flex items-center gap-1.5"
                  >
                    去配置模型
                    <icons.ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}

              <div className="mt-4 p-4 rounded-lg bg-surface-2 border border-border-subtle">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  <span className="font-medium text-foreground">支持的 provider：</span>
                  <br />
                  OpenAI · Anthropic · 通义千问 · DeepSeek · 混元 · Ollama（本地）· LMStudio（本地）·
                  企业自建（自定义 endpoint）
                </p>
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-success/10 flex items-center justify-center">
                  <icons.CheckCircle2 className="w-7 h-7 text-success" />
                </div>
                <div>
                  <h2 id="onboarding-title" className="text-xl font-medium text-foreground">
                    一切就绪
                  </h2>
                  <p className="text-sm text-muted-foreground mt-0.5">从下面任一入口开始使用</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-5">
                {FINAL_ENTRIES.map((entry) => {
                  const Icon = icons[entry.icon] as React.ComponentType<{ className?: string }>
                  return (
                    <button
                      key={entry.href}
                      type="button"
                      onClick={() => handleFinish(entry.href)}
                      className="flex items-start gap-3 p-4 rounded-lg border border-border hover:border-primary hover:bg-primary/5 transition-colors text-left"
                    >
                      <Icon className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-foreground">{entry.title}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{entry.desc}</div>
                      </div>
                    </button>
                  )
                })}
              </div>

              <p className="text-xs text-muted-foreground mt-5">
                后续可在「设置 → 关于 → 重新查看引导」重弹本页。
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-6 py-4 flex items-center justify-between">
          <button
            type="button"
            onClick={back}
            disabled={step === 1}
            className="px-3 h-9 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            上一步
          </button>
          <div className="flex items-center gap-2">
            {step === 3 && (
              <button
                type="button"
                onClick={next}
                className="px-3 h-9 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-surface-2 transition-colors"
              >
                跳过
              </button>
            )}
            {step < 4 && (
              <button
                type="button"
                onClick={next}
                className="px-4 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-600 transition-colors flex items-center gap-1.5"
              >
                {step === 1 ? '开始配置' : '下一步'}
                <icons.ArrowRight className="w-4 h-4" />
              </button>
            )}
            {step === 4 && (
              <button
                type="button"
                onClick={() => handleFinish('/chat')}
                className="px-4 h-9 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-600 transition-colors flex items-center gap-1.5"
              >
                开始使用
                <icons.ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingWizard
