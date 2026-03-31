import { useState, useEffect, useMemo } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, heading, iconSize, statusBadge } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { aiAssistantApi } from '@/lib/api'

interface AgentInfo {
  id: string
  name: string
  description: string
  icon: keyof typeof icons
  enabled: boolean
  capabilities: string[]
  status: 'active' | 'idle'
}

type PageState = 'loading' | 'error' | 'ready'

const statusConfig = {
  active: { label: '已启用', badge: statusBadge.success },
  idle: { label: '未启用', badge: statusBadge.neutral },
} as const

function normalizeIcon(icon?: string): keyof typeof icons {
  if (!icon) return 'Bot'
  const iconMap: Record<string, keyof typeof icons> = {
    scale: 'Scale',
    'file-text': 'FileText',
    'shield-alert': 'ShieldAlert',
    search: 'Search',
    'pen-tool': 'PenTool',
    'check-circle': 'ShieldCheck',
    lightbulb: 'Lightbulb',
    users: 'Users',
    calculator: 'Calculator',
    'clipboard-list': 'Tasks',
    bell: 'Bell',
    'book-open': 'BookOpen',
  }
  return iconMap[icon] || 'Bot'
}

function buildConfigPayload(config: any, enabledAgents: string[]) {
  return {
    name: config?.name || '安心法务助手',
    description: config?.description || '',
    avatar_url: config?.avatar_url || '',
    welcome_message: config?.welcome_message || '',
    system_prompt: config?.system_prompt || '',
    personality: config?.personality || {},
    enabled_agents: enabledAgents,
    knowledge_base_ids: config?.knowledge_base_ids || [],
    max_context_turns: config?.max_context_turns || 10,
    temperature: config?.temperature ?? 0.7,
    llm_config_id: config?.llm_config_id || null,
  }
}

export default function AgentWorkflow() {
  const [state, setState] = useState<PageState>('loading')
  const [error, setError] = useState('')
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [config, setConfig] = useState<any>(null)
  const [filterCapability, setFilterCapability] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [updatingAgentId, setUpdatingAgentId] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setState('loading')
    setError('')
    try {
      const [agentList, assistantConfig] = await Promise.all([
        aiAssistantApi.listAgents(),
        aiAssistantApi.getConfig(),
      ])

      const enabledSet = new Set<string>(assistantConfig?.enabled_agents || [])
      const mappedAgents: AgentInfo[] = (agentList || []).map((agent: any) => {
        const enabled = enabledSet.has(agent.key)
        return {
          id: agent.key,
          name: agent.name,
          description: agent.description,
          icon: normalizeIcon(agent.icon),
          enabled,
          capabilities: agent.capabilities || [],
          status: enabled ? 'active' : 'idle',
        }
      })

      setConfig(assistantConfig)
      setAgents(mappedAgents)
      setState('ready')
    } catch (e: any) {
      setAgents([])
      setConfig(null)
      setError(e.message || '无法加载 Agent 配置')
      setState('error')
    }
  }

  const allCapabilities = useMemo(() => {
    const caps = new Set<string>()
    agents.forEach(agent => agent.capabilities.forEach(cap => caps.add(cap)))
    return Array.from(caps)
  }, [agents])

  const filteredAgents = useMemo(() => {
    return agents.filter(agent => {
      if (filterCapability !== 'all' && !agent.capabilities.includes(filterCapability)) return false
      if (filterStatus === 'enabled' && !agent.enabled) return false
      if (filterStatus === 'disabled' && agent.enabled) return false
      return true
    })
  }, [agents, filterCapability, filterStatus])

  const enabledAgentCount = useMemo(
    () => agents.filter(agent => agent.enabled).length,
    [agents]
  )

  const toggleAgent = async (id: string) => {
    if (!config) return
    const nextAgents: AgentInfo[] = agents.map(agent =>
      agent.id === id
        ? { ...agent, enabled: !agent.enabled, status: !agent.enabled ? 'active' : 'idle' }
        : agent
    )

    setUpdatingAgentId(id)
    setAgents(nextAgents)
    try {
      const enabledAgents = nextAgents.filter(agent => agent.enabled).map(agent => agent.id)
      const updatedConfig = await aiAssistantApi.updateConfig(buildConfigPayload(config, enabledAgents))
      setConfig(updatedConfig)
      toast.success('Agent 配置已更新')
    } catch (e: any) {
      setAgents(agents)
      toast.error(e.message || '更新 Agent 失败')
    } finally {
      setUpdatingAgentId(null)
    }
  }

  if (state === 'loading') {
    return (
      <PageContainer title="Agent 工作流" description="管理 AI Agent 能力与执行流程">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Skeleton key={i} className="h-40 rounded-xl" />
          ))}
        </div>
      </PageContainer>
    )
  }

  if (state === 'error') {
    return (
      <PageContainer title="Agent 工作流" description="管理 AI Agent 能力与执行流程">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>加载失败</p>
          <p className={`${heading.muted} mt-1`}>{error}</p>
          <Button className="mt-4" onClick={loadData}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="Agent 工作流" description="管理 AI Agent 能力与执行流程">
      <PageSection
        title="Agent 能力面板"
        actions={
          <div className="flex items-center gap-2">
            <Select value={filterCapability} onValueChange={setFilterCapability}>
              <SelectTrigger className="w-[140px] h-8 text-xs">
                <SelectValue placeholder="按能力筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部能力</SelectItem>
                {allCapabilities.map(cap => (
                  <SelectItem key={cap} value={cap}>{cap}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[120px] h-8 text-xs">
                <SelectValue placeholder="按状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="enabled">已启用</SelectItem>
                <SelectItem value="disabled">未启用</SelectItem>
              </SelectContent>
            </Select>
          </div>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAgents.map(agent => {
            const Icon = icons[agent.icon] || icons.Bot
            const stCfg = statusConfig[agent.status]
            return (
              <div key={agent.id} className={`${cardStyle.base} flex flex-col`}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-primary/5">
                      <Icon className={`${iconSize.md} text-primary`} />
                    </div>
                    <div>
                      <p className={heading.card}>{agent.name}</p>
                      <p className={heading.micro}>{agent.description}</p>
                    </div>
                  </div>
                  <Switch
                    checked={agent.enabled}
                    onCheckedChange={() => toggleAgent(agent.id)}
                    disabled={updatingAgentId === agent.id}
                  />
                </div>
                <div className="flex flex-wrap gap-1 mb-3">
                  {agent.capabilities.map(cap => (
                    <Badge key={cap} variant="outline" className="text-xs">{cap}</Badge>
                  ))}
                </div>
                <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
                  <span>{agent.enabled ? '已加入当前助手编排' : '当前未启用'}</span>
                  <Badge className={stCfg.badge + ' text-xs'}>{stCfg.label}</Badge>
                </div>
              </div>
            )
          })}
        </div>

        {filteredAgents.length === 0 && (
          <div className={`${cardStyle.base} text-center py-12 mt-4`}>
            <icons.Bot className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
            <p className={heading.muted}>暂无符合条件的 Agent</p>
          </div>
        )}
      </PageSection>

      <PageSection title="当前配置概览">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className={cardStyle.base}>
            <p className={heading.micro}>已启用 Agent</p>
            <p className="text-3xl font-bold text-foreground mt-1">{enabledAgentCount}</p>
          </div>
          <div className={cardStyle.base}>
            <p className={heading.micro}>上下文轮数</p>
            <p className="text-3xl font-bold text-foreground mt-1">{config?.max_context_turns || 0}</p>
          </div>
          <div className={cardStyle.base}>
            <p className={heading.micro}>温度</p>
            <p className="text-3xl font-bold text-foreground mt-1">{config?.temperature ?? 0}</p>
          </div>
        </div>
      </PageSection>

      <PageSection title="运行统计与流程编排">
        <div className={`${cardStyle.base} text-center py-16`}>
          <icons.GitBranch className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className={heading.section}>运行统计暂未开放</p>
          <p className={`${heading.muted} mt-1`}>
            当前页面已接入真实 Agent 清单与启用状态，调用次数、成功率和流程拓扑待后端开放统计接口后再展示。
          </p>
        </div>
      </PageSection>
    </PageContainer>
  )
}
