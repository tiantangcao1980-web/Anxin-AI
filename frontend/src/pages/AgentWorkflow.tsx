import { useState, useEffect, useMemo } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, iconSize, statusBadge, chartColors } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  BarChart, Bar,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from 'recharts'

// ====================================================================
// @mock-data FALLBACK: 后端就绪后从 API 获取
// ====================================================================

interface AgentInfo {
  id: string
  name: string
  description: string
  icon: keyof typeof icons
  enabled: boolean
  capabilities: string[]
  callCount: number
  successRate: number
  avgLatency: number
  status: 'active' | 'idle' | 'error'
}

interface WorkflowNode {
  id: string
  label: string
  agentId?: string
  type: 'start' | 'agent' | 'parallel_start' | 'parallel_end' | 'end'
  status: 'success' | 'active' | 'pending'
}

interface WorkflowDefinition {
  id: string
  name: string
  description: string
  nodes: WorkflowNode[][]
}

const mockAgents: AgentInfo[] = [
  { id: 'legal_advisor', name: '法律顾问', description: '综合法律咨询与建议', icon: 'Scale', enabled: true, capabilities: ['法律咨询', '法条引用', '案例分析'], callCount: 1280, successRate: 96.5, avgLatency: 820, status: 'active' },
  { id: 'contract_reviewer', name: '合同审查', description: '合同条款分析与风险识别', icon: 'FileCheck', enabled: true, capabilities: ['条款审查', '风险标注', '修改建议'], callCount: 956, successRate: 98.2, avgLatency: 1200, status: 'active' },
  { id: 'risk_assessor', name: '风险评估', description: '法律风险量化评估', icon: 'ShieldAlert', enabled: true, capabilities: ['风险评分', '风险矩阵', '预警建议'], callCount: 743, successRate: 95.8, avgLatency: 680, status: 'active' },
  { id: 'legal_researcher', name: '法律研究', description: '法律法规检索与分析', icon: 'Search', enabled: true, capabilities: ['法规检索', '判例分析', '学术研究'], callCount: 621, successRate: 94.3, avgLatency: 1500, status: 'active' },
  { id: 'document_drafter', name: '文书起草', description: '法律文书智能生成', icon: 'FileText', enabled: true, capabilities: ['合同生成', '文书模板', '条款组装'], callCount: 534, successRate: 97.1, avgLatency: 2100, status: 'active' },
  { id: 'compliance_officer', name: '合规审查', description: '企业合规性检查', icon: 'ShieldCheck', enabled: true, capabilities: ['合规检查', '政策对照', '整改建议'], callCount: 412, successRate: 93.7, avgLatency: 950, status: 'idle' },
  { id: 'litigation_strategist', name: '诉讼策略', description: '诉讼方案规划', icon: 'Briefcase', enabled: false, capabilities: ['策略规划', '证据分析', '庭审准备'], callCount: 198, successRate: 91.2, avgLatency: 1800, status: 'idle' },
  { id: 'ip_specialist', name: '知识产权', description: '商标/专利/版权保护', icon: 'Lock', enabled: false, capabilities: ['商标检索', '专利分析', '侵权评估'], callCount: 167, successRate: 95.0, avgLatency: 1100, status: 'idle' },
  { id: 'due_diligence', name: '尽职调查', description: '企业背景深度调查', icon: 'FileSearch', enabled: true, capabilities: ['背景调查', '财务审查', '关联分析'], callCount: 389, successRate: 94.8, avgLatency: 3200, status: 'active' },
  { id: 'tax_compliance', name: '税务合规', description: '税务法规咨询', icon: 'Calculator', enabled: false, capabilities: ['税务咨询', '纳税筹划', '税务合规'], callCount: 145, successRate: 92.3, avgLatency: 780, status: 'idle' },
  { id: 'labor_compliance', name: '劳动法', description: '劳动法律咨询', icon: 'Users', enabled: false, capabilities: ['劳动合同', '工伤认定', '仲裁指导'], callCount: 223, successRate: 96.1, avgLatency: 650, status: 'idle' },
  { id: 'evidence_analyst', name: '证据分析', description: '证据链条梳理与评估', icon: 'Eye', enabled: false, capabilities: ['证据梳理', '证明力评估', '举证指引'], callCount: 89, successRate: 90.5, avgLatency: 1400, status: 'idle' },
  { id: 'regulatory_monitor', name: '监管动态', description: '法规变更监测预警', icon: 'Activity', enabled: false, capabilities: ['法规监测', '变更预警', '影响评估'], callCount: 312, successRate: 97.8, avgLatency: 450, status: 'active' },
]

const mockWorkflows: WorkflowDefinition[] = [
  {
    id: 'contract_review_flow',
    name: '合同审查流程',
    description: '从需求分析到审查报告的完整合同审查链路',
    nodes: [
      [{ id: 'n1', label: '需求分析', agentId: 'requirement_analyst', type: 'start', status: 'success' }],
      [
        { id: 'n2', label: '合同审查', agentId: 'contract_reviewer', type: 'agent', status: 'success' },
        { id: 'n3', label: '风险评估', agentId: 'risk_assessor', type: 'agent', status: 'success' },
      ],
      [{ id: 'n4', label: '共识决策', agentId: 'consensus_agent', type: 'agent', status: 'active' }],
      [{ id: 'n5', label: '审查报告', type: 'end', status: 'pending' }],
    ],
  },
  {
    id: 'legal_consult_flow',
    name: '法律咨询流程',
    description: '从意图识别到咨询答复的智能咨询链路',
    nodes: [
      [{ id: 'n1', label: '意图识别', type: 'start', status: 'success' }],
      [{ id: 'n2', label: '法律顾问', agentId: 'legal_advisor', type: 'agent', status: 'success' }],
      [{ id: 'n3', label: '引用检索', agentId: 'legal_researcher', type: 'agent', status: 'active' }],
      [{ id: 'n4', label: '咨询答复', type: 'end', status: 'pending' }],
    ],
  },
]

const mockCallData = mockAgents
  .filter(a => a.callCount > 0)
  .sort((a, b) => b.callCount - a.callCount)
  .map(a => ({ name: a.name, 调用次数: a.callCount }))

// ====================================================================

type PageState = 'loading' | 'error' | 'ready'

const statusConfig = {
  active: { label: '运行中', badge: statusBadge.success },
  idle: { label: '空闲', badge: statusBadge.neutral },
  error: { label: '异常', badge: statusBadge.error },
} as const

const nodeStatusColor = {
  success: 'border-emerald-400 bg-emerald-50 text-emerald-700 dark:border-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400',
  active: 'border-primary bg-primary/10 text-primary animate-pulse',
  pending: 'border-border bg-muted text-muted-foreground',
} as const

export default function AgentWorkflow() {
  const [state, setState] = useState<PageState>('loading')
  const [agents, setAgents] = useState<AgentInfo[]>(mockAgents)
  const [filterCapability, setFilterCapability] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  useEffect(() => {
    const timer = setTimeout(() => setState('ready'), 600)
    return () => clearTimeout(timer)
  }, [])

  const allCapabilities = useMemo(() => {
    const caps = new Set<string>()
    agents.forEach(a => a.capabilities.forEach(c => caps.add(c)))
    return Array.from(caps)
  }, [agents])

  const filteredAgents = useMemo(() => {
    return agents.filter(a => {
      if (filterCapability !== 'all' && !a.capabilities.includes(filterCapability)) return false
      if (filterStatus === 'enabled' && !a.enabled) return false
      if (filterStatus === 'disabled' && a.enabled) return false
      return true
    })
  }, [agents, filterCapability, filterStatus])

  const toggleAgent = (id: string) => {
    setAgents(prev => prev.map(a => (a.id === id ? { ...a, enabled: !a.enabled } : a)))
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
          <Button className="mt-4" onClick={() => setState('loading')}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="Agent 工作流" description="管理 AI Agent 能力与执行流程">
      {/* ===== Agent 网格 ===== */}
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
            const Icon = icons[agent.icon]
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
                  <Switch checked={agent.enabled} onCheckedChange={() => toggleAgent(agent.id)} />
                </div>
                <div className="flex flex-wrap gap-1 mb-3">
                  {agent.capabilities.map(cap => (
                    <Badge key={cap} variant="outline" className="text-xs">{cap}</Badge>
                  ))}
                </div>
                <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
                  <span>调用 {agent.callCount} 次</span>
                  <Badge className={stCfg.badge + ' text-xs'}>{stCfg.label}</Badge>
                </div>
              </div>
            )
          })}
        </div>
      </PageSection>

      {/* ===== 执行统计 ===== */}
      <PageSection title="执行统计（近30天）">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 柱状图 */}
          <div className={cardStyle.base}>
            <p className={heading.card + ' mb-4'}>Agent 调用次数</p>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={mockCallData} layout="vertical" margin={{ left: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={56} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="调用次数" fill={chartColors[0]} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 表格 */}
          <div className={cardStyle.base}>
            <p className={heading.card + ' mb-4'}>详细数据</p>
            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Agent</TableHead>
                    <TableHead className="text-right">调用</TableHead>
                    <TableHead className="text-right">成功率</TableHead>
                    <TableHead className="text-right">延迟</TableHead>
                    <TableHead>状态</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockAgents
                    .sort((a, b) => b.callCount - a.callCount)
                    .map(agent => {
                      const stCfg = statusConfig[agent.status]
                      return (
                        <TableRow key={agent.id}>
                          <TableCell className="text-sm font-medium">{agent.name}</TableCell>
                          <TableCell className="text-sm text-right">{agent.callCount}</TableCell>
                          <TableCell className="text-sm text-right">{agent.successRate}%</TableCell>
                          <TableCell className="text-sm text-right font-mono">{agent.avgLatency}ms</TableCell>
                          <TableCell>
                            <Badge className={stCfg.badge + ' text-xs'}>{stCfg.label}</Badge>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </PageSection>

      {/* ===== 工作流可视化 ===== */}
      <PageSection title="典型工作流">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {mockWorkflows.map(wf => (
            <div key={wf.id} className={cardStyle.base}>
              <div className="mb-4">
                <p className={heading.card}>{wf.name}</p>
                <p className={heading.micro}>{wf.description}</p>
              </div>

              {/* DAG 可视化 */}
              <div className="flex items-center gap-2 overflow-x-auto py-2">
                {wf.nodes.map((column, colIdx) => (
                  <div key={colIdx} className="flex flex-col items-center gap-2 shrink-0">
                    {/* 连接线 (非首列) */}
                    {colIdx > 0 && (
                      <div className="absolute" style={{ display: 'none' }} />
                    )}

                    {column.length > 1 && (
                      <div className="text-xs text-muted-foreground mb-1">并行</div>
                    )}

                    {column.map(node => (
                      <div
                        key={node.id}
                        className={`px-3 py-2 rounded-lg border-2 text-center min-w-[80px] text-xs font-medium ${nodeStatusColor[node.status]}`}
                      >
                        {node.label}
                      </div>
                    ))}

                    {/* 箭头 */}
                    {colIdx < wf.nodes.length - 1 && (
                      <div className="hidden" />
                    )}
                  </div>
                ))}

                {/* 箭头连接 - 使用 flexbox 水平布局 */}
              </div>

              {/* 使用水平流式布局重绘 */}
              <div className="flex items-stretch gap-0 overflow-x-auto py-4">
                {wf.nodes.map((column, colIdx) => (
                  <div key={colIdx} className="flex items-center">
                    {/* 列内节点 */}
                    <div className={`flex ${column.length > 1 ? 'flex-col gap-2' : ''} items-center`}>
                      {column.length > 1 && (
                        <p className="text-[10px] text-muted-foreground mb-1 whitespace-nowrap">并行执行</p>
                      )}
                      {column.map(node => (
                        <div
                          key={node.id}
                          className={`px-3 py-2 rounded-lg border-2 text-center whitespace-nowrap text-xs font-medium ${nodeStatusColor[node.status]}`}
                        >
                          {node.label}
                        </div>
                      ))}
                    </div>

                    {/* 箭头 */}
                    {colIdx < wf.nodes.length - 1 && (
                      <div className="flex items-center px-2 text-muted-foreground">
                        <div className="w-6 h-px bg-border" />
                        <icons.ChevronRight className="w-3.5 h-3.5 -ml-1" />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* 状态图例 */}
              <div className="flex items-center gap-4 mt-2 pt-2 border-t border-border">
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="w-2 h-2 rounded-full bg-emerald-500" /> 已完成
                </span>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" /> 执行中
                </span>
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="w-2 h-2 rounded-full bg-muted-foreground/30" /> 待执行
                </span>
              </div>
            </div>
          ))}
        </div>
      </PageSection>
    </PageContainer>
  )
}
