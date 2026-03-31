import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, iconSize, inputStyle } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { aiAssistantApi } from '@/lib/api'

// ====================================================================
// 类型定义
// ====================================================================

interface AgentConfig {
  id: string
  name: string
  description: string
  icon: keyof typeof icons
  enabled: boolean
}

interface PersonalityPreset {
  id: string
  name: string
  description: string
  icon: keyof typeof icons
  systemPrompt: string
}

interface AssistantConfig {
  name: string
  avatarUrl: string
  welcomeMessage: string
  description: string
  personalityPresetId: string
  customSystemPrompt: string
  agents: AgentConfig[]
  temperature: number
  contextRounds: string
  llmConfigId: string
}

// 前端配置常量 - 性格预设和 Agent 组合方案
const personalityPresets: PersonalityPreset[] = [
  {
    id: 'professional',
    name: '专业严谨',
    description: '适合正式法律咨询',
    icon: 'Scale',
    systemPrompt: '你是一位专业严谨的法律顾问，回答务求准确、引用法条，语气正式。',
  },
  {
    id: 'friendly',
    name: '温和友好',
    description: '适合一般客户沟通',
    icon: 'Heart',
    systemPrompt: '你是一位温和友好的法律助手，用通俗易懂的语言解答法律问题。',
  },
  {
    id: 'efficient',
    name: '简洁高效',
    description: '适合快速问答场景',
    icon: 'Zap',
    systemPrompt: '你是一位高效的法律助手，回答简洁直接，重点突出。',
  },
]

const agentCombos: { label: string; ids: string[] | 'all' }[] = [
  { label: '全选', ids: 'all' },
  { label: '法律咨询', ids: ['legal_advisor', 'legal_researcher', 'risk_assessor', 'litigation_strategist'] },
  { label: '合同管理', ids: ['contract_reviewer', 'document_drafter', 'compliance_officer'] },
  { label: '尽职调查', ids: ['due_diligence', 'evidence_analyst', 'regulatory_monitor'] },
]

const defaultConfig: AssistantConfig = {
  name: '安心法务 AI 助手',
  avatarUrl: '',
  welcomeMessage: '您好！我是安心法务 AI 助手，可以为您提供专业的法律咨询服务。请问有什么可以帮助您的？',
  description: '企业专属 AI 法律顾问，提供合同审查、法律咨询、风险评估等智能服务。',
  personalityPresetId: 'professional',
  customSystemPrompt: '',
  agents: [],
  temperature: 0.7,
  contextRounds: '10',
  llmConfigId: 'default',
}

// ====================================================================

type PageState = 'loading' | 'error' | 'ready'

export default function AIAssistantSettings() {
  const [state, setState] = useState<PageState>('loading')
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [config, setConfig] = useState<AssistantConfig>(defaultConfig)
  const [showCustomPrompt, setShowCustomPrompt] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function fetchData() {
      setState('loading')
      try {
        const [configData, agentsData] = await Promise.all([
          aiAssistantApi.getConfig(),
          aiAssistantApi.listAgents(),
        ])
        if (cancelled) return

        // 合并配置
        const agents: AgentConfig[] = Array.isArray(agentsData)
          ? agentsData.map((a: any) => ({
              id: a.id || '',
              name: a.name || '',
              description: a.description || '',
              icon: a.icon || 'Bot',
              enabled: a.enabled ?? true,
            }))
          : (agentsData?.agents || []).map((a: any) => ({
              id: a.id || '',
              name: a.name || '',
              description: a.description || '',
              icon: a.icon || 'Bot',
              enabled: a.enabled ?? true,
            }))

        if (configData) {
          setConfig({
            name: configData.name || defaultConfig.name,
            avatarUrl: configData.avatar_url || configData.avatarUrl || defaultConfig.avatarUrl,
            welcomeMessage: configData.welcome_message || configData.welcomeMessage || defaultConfig.welcomeMessage,
            description: configData.description || defaultConfig.description,
            personalityPresetId: configData.personality_preset_id || configData.personalityPresetId || defaultConfig.personalityPresetId,
            customSystemPrompt: configData.custom_system_prompt || configData.customSystemPrompt || '',
            agents: agents.length > 0 ? agents : defaultConfig.agents,
            temperature: configData.temperature ?? defaultConfig.temperature,
            contextRounds: String(configData.context_rounds ?? configData.contextRounds ?? defaultConfig.contextRounds),
            llmConfigId: configData.llm_config_id || configData.llmConfigId || defaultConfig.llmConfigId,
          })
        } else {
          setConfig(prev => ({ ...prev, agents: agents.length > 0 ? agents : prev.agents }))
        }

        setState('ready')
      } catch (err: any) {
        if (!cancelled) {
          console.error('AI 助手配置加载失败:', err)
          setErrorMsg(err?.message || '数据加载失败，请稍后重试')
          setState('error')
        }
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])

  const updateField = <K extends keyof AssistantConfig>(key: K, value: AssistantConfig[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const toggleAgent = (agentId: string) => {
    setConfig(prev => ({
      ...prev,
      agents: prev.agents.map(a => (a.id === agentId ? { ...a, enabled: !a.enabled } : a)),
    }))
  }

  const applyCombo = (combo: typeof agentCombos[number]) => {
    setConfig(prev => ({
      ...prev,
      agents: prev.agents.map(a => ({
        ...a,
        enabled: combo.ids === 'all' ? true : (combo.ids as string[]).includes(a.id),
      })),
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await aiAssistantApi.updateConfig({
        name: config.name,
        avatar_url: config.avatarUrl,
        welcome_message: config.welcomeMessage,
        description: config.description,
        personality_preset_id: config.personalityPresetId,
        custom_system_prompt: config.customSystemPrompt,
        agents: config.agents.map(a => ({ id: a.id, enabled: a.enabled })),
        temperature: config.temperature,
        context_rounds: Number(config.contextRounds),
        llm_config_id: config.llmConfigId,
      })
      toast.success('配置已保存')
    } catch (err: any) {
      toast.error(err?.message || '保存失败，请稍后重试')
    } finally {
      setSaving(false)
    }
  }

  if (state === 'loading') {
    return (
      <PageContainer title="AI 助手配置" description="配置企业专属 AI 法律助手">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {[1, 2, 3, 4].map(i => (
              <Skeleton key={i} className="h-48 w-full rounded-xl" />
            ))}
          </div>
          <div>
            <Skeleton className="h-96 w-full rounded-xl" />
          </div>
        </div>
      </PageContainer>
    )
  }

  if (state === 'error') {
    return (
      <PageContainer title="AI 助手配置" description="配置企业专属 AI 法律助手">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>加载失败</p>
          <p className={heading.muted}>{errorMsg || '请检查网络后重试'}</p>
          <Button className="mt-4" onClick={() => setState('loading')}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
      </PageContainer>
    )
  }

  const currentPreset = personalityPresets.find(p => p.id === config.personalityPresetId)

  return (
    <PageContainer title="AI 助手配置" description="配置企业专属 AI 法律助手">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ===== 左侧配置区 ===== */}
        <div className="lg:col-span-2 space-y-6">
          {/* Section 1: 基本信息 */}
          <div className={cardStyle.base}>
            <PageSection title="基本信息">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className={heading.card}>助手名称</Label>
                  <Input
                    className={inputStyle.search}
                    placeholder="输入助手名称"
                    maxLength={100}
                    value={config.name}
                    onChange={e => updateField('name', e.target.value)}
                  />
                  <p className={heading.micro}>{config.name.length}/100</p>
                </div>

                <div className="space-y-2">
                  <Label className={heading.card}>头像 URL</Label>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-full bg-muted border border-border flex items-center justify-center overflow-hidden shrink-0">
                      {config.avatarUrl ? (
                        <img src={config.avatarUrl} alt="avatar" className="w-full h-full object-cover" />
                      ) : (
                        <icons.Bot className={`${iconSize.lg} text-muted-foreground`} />
                      )}
                    </div>
                    <Input
                      className={`${inputStyle.search} flex-1`}
                      placeholder="https://example.com/avatar.png"
                      value={config.avatarUrl}
                      onChange={e => updateField('avatarUrl', e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className={heading.card}>欢迎语</Label>
                  <Textarea
                    placeholder="输入欢迎语..."
                    maxLength={2000}
                    rows={3}
                    value={config.welcomeMessage}
                    onChange={e => updateField('welcomeMessage', e.target.value)}
                    className="resize-none"
                  />
                  <p className={heading.micro}>{config.welcomeMessage.length}/2000</p>
                </div>

                <div className="space-y-2">
                  <Label className={heading.card}>助手描述</Label>
                  <Textarea
                    placeholder="输入描述..."
                    maxLength={1000}
                    rows={2}
                    value={config.description}
                    onChange={e => updateField('description', e.target.value)}
                    className="resize-none"
                  />
                  <p className={heading.micro}>{config.description.length}/1000</p>
                </div>
              </div>
            </PageSection>
          </div>

          {/* Section 2: 性格设定 */}
          <div className={cardStyle.base}>
            <PageSection title="性格设定">
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {personalityPresets.map(preset => {
                    const Icon = icons[preset.icon]
                    const isActive = config.personalityPresetId === preset.id
                    return (
                      <button
                        key={preset.id}
                        onClick={() => updateField('personalityPresetId', preset.id)}
                        className={`p-4 rounded-xl border text-left transition-all ${
                          isActive
                            ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                            : 'border-border hover:border-primary/30 hover:bg-muted/50'
                        }`}
                      >
                        <Icon className={`${iconSize.md} ${isActive ? 'text-primary' : 'text-muted-foreground'} mb-2`} />
                        <p className={heading.card}>{preset.name}</p>
                        <p className={heading.micro}>{preset.description}</p>
                      </button>
                    )
                  })}
                </div>

                <div>
                  <button
                    onClick={() => setShowCustomPrompt(!showCustomPrompt)}
                    className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showCustomPrompt ? (
                      <icons.ChevronUp className={iconSize.sm} />
                    ) : (
                      <icons.ChevronDown className={iconSize.sm} />
                    )}
                    自定义 System Prompt
                  </button>
                  {showCustomPrompt && (
                    <div className="mt-3 space-y-2">
                      <Textarea
                        placeholder="输入自定义 System Prompt，留空则使用预设..."
                        rows={5}
                        value={config.customSystemPrompt}
                        onChange={e => updateField('customSystemPrompt', e.target.value)}
                        className="resize-none font-mono text-sm"
                      />
                      {currentPreset && !config.customSystemPrompt && (
                        <p className={heading.micro}>
                          当前使用预设: {currentPreset.systemPrompt}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </PageSection>
          </div>

          {/* Section 3: Agent 能力配置 */}
          <div className={cardStyle.base}>
            <PageSection title="Agent 能力配置">
              <div className="space-y-4">
                {/* 快捷按钮 */}
                <div className="flex flex-wrap gap-2">
                  {agentCombos.map(combo => (
                    <Button
                      key={combo.label}
                      variant="outline"
                      size="sm"
                      onClick={() => applyCombo(combo)}
                    >
                      {combo.label}
                    </Button>
                  ))}
                </div>

                {/* Agent 列表 */}
                {config.agents.length > 0 ? (
                  <div className="space-y-1">
                    {config.agents.map(agent => {
                      const Icon = icons[agent.icon] || icons.Bot
                      return (
                        <div
                          key={agent.id}
                          className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-muted/50 transition-colors"
                        >
                          <Icon className={`${iconSize.md} text-muted-foreground shrink-0`} />
                          <div className="flex-1 min-w-0">
                            <p className={heading.card}>{agent.name}</p>
                            <p className={heading.micro}>{agent.description}</p>
                          </div>
                          <Switch
                            checked={agent.enabled}
                            onCheckedChange={() => toggleAgent(agent.id)}
                          />
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="py-8 text-center text-sm text-muted-foreground">暂无可配置的 Agent</div>
                )}
              </div>
            </PageSection>
          </div>

          {/* Section 4: 参数调优 */}
          <div className={cardStyle.base}>
            <PageSection title="参数调优">
              <div className="space-y-5">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className={heading.card}>Temperature</Label>
                    <span className="text-sm font-mono text-muted-foreground">{config.temperature.toFixed(1)}</span>
                  </div>
                  <Slider
                    min={0}
                    max={2}
                    step={0.1}
                    value={[config.temperature]}
                    onValueChange={([v]) => updateField('temperature', v)}
                  />
                  <p className={heading.micro}>较低值输出更确定，较高值输出更多样</p>
                </div>

                <div className="space-y-2">
                  <Label className={heading.card}>上下文轮数</Label>
                  <Select
                    value={config.contextRounds}
                    onValueChange={v => updateField('contextRounds', v)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {['5', '10', '20', '30', '50'].map(n => (
                        <SelectItem key={n} value={n}>{n} 轮</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className={heading.card}>LLM 配置</Label>
                  <Select
                    value={config.llmConfigId}
                    onValueChange={v => updateField('llmConfigId', v)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">默认配置</SelectItem>
                      <SelectItem value="custom">自定义配置</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </PageSection>
          </div>
        </div>

        {/* ===== 右侧预览区 ===== */}
        <div className="lg:col-span-1">
          <div className="sticky top-6 space-y-4">
            <div className={cardStyle.base}>
              <PageSection title="对话预览">
                <div className="space-y-3">
                  {/* 助手信息 */}
                  <div className="flex items-center gap-2 pb-3 border-b border-border">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center overflow-hidden">
                      {config.avatarUrl ? (
                        <img src={config.avatarUrl} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <icons.Bot className={`${iconSize.sm} text-primary`} />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{config.name || '未命名助手'}</p>
                      <p className="text-xs text-muted-foreground">在线</p>
                    </div>
                  </div>

                  {/* 欢迎语 */}
                  <div className="flex gap-2">
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                      <icons.Bot className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div className="bg-muted/60 border border-border rounded-2xl rounded-bl-md px-3 py-2 text-sm text-foreground max-w-[85%]">
                      {config.welcomeMessage || '请设置欢迎语...'}
                    </div>
                  </div>

                  {/* 模拟用户消息 */}
                  <div className="flex justify-end">
                    <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-3 py-2 text-sm max-w-[85%]">
                      我想咨询一下劳动合同相关问题
                    </div>
                  </div>

                  {/* 模拟 AI 回复 */}
                  <div className="flex gap-2">
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                      <icons.Bot className="w-3.5 h-3.5 text-primary" />
                    </div>
                    <div className="bg-muted/60 border border-border rounded-2xl rounded-bl-md px-3 py-2 text-sm text-foreground max-w-[85%]">
                      好的，关于劳动合同问题，我可以帮您分析。请您具体描述一下遇到的情况...
                    </div>
                  </div>

                  {/* 已启用 Agent 标签 */}
                  <div className="pt-2 border-t border-border">
                    <p className={heading.micro + ' mb-2'}>已启用 Agent ({config.agents.filter(a => a.enabled).length})</p>
                    <div className="flex flex-wrap gap-1">
                      {config.agents
                        .filter(a => a.enabled)
                        .slice(0, 6)
                        .map(a => (
                          <Badge key={a.id} variant="secondary" className="text-xs">
                            {a.name.replace(' Agent', '')}
                          </Badge>
                        ))}
                      {config.agents.filter(a => a.enabled).length > 6 && (
                        <Badge variant="secondary" className="text-xs">
                          +{config.agents.filter(a => a.enabled).length - 6}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </PageSection>
            </div>

            {/* 保存按钮 */}
            <Button
              className={`${buttonStyle.primary} w-full`}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? (
                <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
              ) : (
                <icons.Check className={iconSize.sm} />
              )}
              {saving ? '保存中...' : '保存配置'}
            </Button>
          </div>
        </div>
      </div>
    </PageContainer>
  )
}
