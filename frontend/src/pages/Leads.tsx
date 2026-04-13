import { useState, useEffect, useCallback } from'react'
import { icons } from'@/lib/icons'
import { EmptyState, LoadingState } from'@/components/common'
import { cardStyle, buttonStyle, heading, statusColor } from'@/lib/design-tokens'
import { leadsApi, type LeadItem } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'

type LeadStage ='new' |'contacted' |'qualified' |'proposal' |'won' |'lost'

interface FollowUp {
 id: string
 date: string
 content: string
 type:'电话' |'面谈' |'邮件' |'微信'
}

interface Lead {
 id: string
 clientName: string
 contactInfo: string
 source: string
 caseType: string
 estimatedAmount: number
 stage: LeadStage
 assignee: string
 followUps: FollowUp[]
 createdAt: string
}

const stageConfig: Record<LeadStage, { label: string; color: string }> = {
 new: { label:'新线索', color: statusColor.info },
 contacted: { label:'已联系', color:'text-cyan-600 bg-cyan-50' },
 qualified: { label:'需求确认', color: statusColor.warning },
 proposal: { label:'报价中', color:'text-primary bg-primary/5' },
 won: { label:'已签约', color: statusColor.success },
 lost: { label:'已流失', color: statusColor.error },
}

const stages: LeadStage[] = ['new','contacted','qualified','proposal','won']

function apiToLead(item: LeadItem): Lead {
 return {
 id: item.id,
 clientName: item.clientName,
 contactInfo: item.contactInfo ||'',
 source: item.source ||'',
 caseType: item.caseType ||'',
 estimatedAmount: item.estimatedAmount,
 stage: (item.stage as LeadStage) ||'new',
 assignee: item.assignee ||'',
 followUps: (item.followUps || []) as FollowUp[],
 createdAt: item.createdAt?.split('T')[0] ||'',
 }
}

export default function Leads() {
 const [leads, setLeads] = useState<Lead[]>([])
 const [selectedLead, setSelectedLead] = useState<Lead | null>(null)
 const [viewMode, setViewMode] = useState<'pipeline' |'list'>('pipeline')
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)

 const loadLeads = useCallback(async () => {
 setLoading(true)
 setError(null)
 try {
 const data = await leadsApi.list({ page_size: 100 })
 setLeads((data.items || []).map(apiToLead))
 } catch (err) {
 setLeads([])
 setError(err instanceof Error ? err.message :'加载线索失败')
 } finally {
 setLoading(false)
 }
 }, [])

 useEffect(() => { loadLeads() }, [loadLeads])

 const moveStage = async (leadId: string, newStage: LeadStage) => {
 setLeads(prev => prev.map(l => l.id === leadId ? { ...l, stage: newStage } : l))
 if (selectedLead?.id === leadId) setSelectedLead({ ...selectedLead, stage: newStage })
 toast.success('线索状态已更新')
 try {
 await leadsApi.updateStage(leadId, newStage)
 } catch {
 // 静默失败
 }
 }

 const totalAmount = leads.filter(l => l.stage !=='lost').reduce((sum, l) => sum + l.estimatedAmount, 0)

 if (selectedLead) {
 const stageIndex = stages.indexOf(selectedLead.stage)
 return (
 <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
 <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-4 flex items-center gap-3">
 <button onClick={() => setSelectedLead(null)} className="p-1 rounded hover:bg-muted">
 <icons.ArrowLeft className="w-5 h-5" />
 </button>
 <div className="flex-1">
 <h1 className={heading.page}>{selectedLead.clientName}</h1>
 <p className="text-xs text-muted-foreground">{selectedLead.caseType} · {selectedLead.contactInfo}</p>
 </div>
 <span className={`text-xs px-2 py-0.5 rounded-full ${stageConfig[selectedLead.stage].color}`}>
 {stageConfig[selectedLead.stage].label}
 </span>
 </div>

 <div className="flex-1 overflow-y-auto px-4 sm:px-5 lg:px-6 py-4">
 <div className="flex items-center gap-1 mb-6">
 {stages.map((s, i) => (
 <div key={s} className="flex items-center flex-1">
 <div className={`flex-1 h-2 rounded-full ${i <= stageIndex ?'bg-primary' :'bg-muted'}`} />
 {i < stages.length - 1 && <div className="w-1" />}
 </div>
 ))}
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
 <div className={cardStyle.base}>
 <p className="text-xs text-muted-foreground mb-1">预估金额</p>
 <p className="text-lg font-bold text-foreground">{selectedLead.estimatedAmount.toLocaleString()} 元</p>
 </div>
 <div className={cardStyle.base}>
 <p className="text-xs text-muted-foreground mb-1">来源渠道</p>
 <p className="text-sm font-medium text-foreground">{selectedLead.source}</p>
 </div>
 </div>

 {selectedLead.stage !=='won' && selectedLead.stage !=='lost' && (
 <div className="flex gap-2 mb-6">
 {stageIndex < stages.length - 1 && (
 <button onClick={() => moveStage(selectedLead.id, stages[stageIndex + 1])} className={buttonStyle.primary}>
 推进至 {stageConfig[stages[stageIndex + 1]].label}
 </button>
 )}
 <button onClick={() => moveStage(selectedLead.id,'lost')} className={buttonStyle.ghost +' text-destructive'}>
 标记流失
 </button>
 </div>
 )}

 <h3 className={heading.section +' mb-3'}>跟进记录</h3>
 {selectedLead.followUps.length === 0 ? (
 <p className="text-xs text-muted-foreground py-4">暂无跟进记录</p>
 ) : (
 <div className="space-y-3">
 {selectedLead.followUps.map(fu => (
 <div key={fu.id} className="flex gap-3">
 <div className="flex flex-col items-center">
 <div className="w-2 h-2 rounded-full bg-primary mt-1.5" />
 <div className="w-px flex-1 bg-border" />
 </div>
 <div className="flex-1 pb-4">
 <div className="flex items-center gap-2 mb-1">
 <span className="text-xs font-medium text-foreground">{fu.date}</span>
 <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{fu.type}</span>
 </div>
 <p className="text-xs text-muted-foreground">{fu.content}</p>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 </PageContainer>
 )
 }

 return (
 <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
 <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-3 flex items-center justify-between">
 <p className="text-sm text-muted-foreground">
 {leads.filter(l => l.stage !=='lost').length} 条活跃线索 · 预估总额 {totalAmount.toLocaleString()} 元
 </p>
 <div className="flex rounded-lg border border-border overflow-hidden">
 <button onClick={() => setViewMode('pipeline')}
 className={`px-3 py-1.5 text-xs ${viewMode ==='pipeline' ?'bg-primary text-white' :'bg-background text-muted-foreground hover:bg-muted'}`}>
 管道
 </button>
 <button onClick={() => setViewMode('list')}
 className={`px-3 py-1.5 text-xs ${viewMode ==='list' ?'bg-primary text-white' :'bg-background text-muted-foreground hover:bg-muted'}`}>
 列表
 </button>
 </div>
 </div>

 <div className="flex-1 overflow-auto px-4 sm:px-5 lg:px-6 py-4">
 {loading ? (
 <LoadingState text="加载线索..." />
 ) : error ? (
 <div className="flex flex-col items-center justify-center py-20">
 <icons.AlertTriangle className="w-10 h-10 text-destructive/60 mb-3" />
 <p className="text-sm text-foreground mb-1">线索数据加载失败</p>
 <p className="text-xs text-muted-foreground mb-4">{error}</p>
 <button onClick={() => void loadLeads()} className={buttonStyle.primary}>
 重新加载
 </button>
 </div>
 ) : leads.length === 0 ? (
 <EmptyState icon="Leads" title="暂无线索数据" description="运行种子数据后即可验证真实案源流程。" />
 ) : viewMode ==='pipeline' ? (
 <div className="flex gap-4 h-full overflow-x-auto pb-2 min-w-0 md:min-w-[960px]">
 {stages.map(stage => {
 const stageLeads = leads.filter(l => l.stage === stage)
 const stageAmount = stageLeads.reduce((s, l) => s + l.estimatedAmount, 0)
 return (
 <div key={stage} className="flex-1 flex flex-col min-w-[180px]">
 <div className="flex items-center justify-between mb-3">
 <span className={`text-xs px-2 py-0.5 rounded-full ${stageConfig[stage].color}`}>
 {stageConfig[stage].label}
 </span>
 <span className="text-xs text-muted-foreground">{stageAmount.toLocaleString()}元</span>
 </div>
 <div className="flex-1 overflow-y-auto space-y-2">
 {stageLeads.map(lead => (
 <div key={lead.id} onClick={() => setSelectedLead(lead)} className={cardStyle.interactive}>
 <h4 className={heading.card +' mb-1'}>{lead.clientName}</h4>
 <p className="text-xs text-muted-foreground mb-2">{lead.caseType}</p>
 <div className="flex items-center justify-between text-xs text-muted-foreground">
 <span>{lead.estimatedAmount.toLocaleString()}元</span>
 <span>{lead.assignee}</span>
 </div>
 </div>
 ))}
 </div>
 </div>
 )
 })}
 </div>
 ) : (
 <div className="space-y-2">
 {leads.map(lead => (
 <div key={lead.id} onClick={() => setSelectedLead(lead)} className={cardStyle.interactive +' flex items-center gap-3 sm:gap-4'}>
 <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${stageConfig[lead.stage].color}`}>
 {stageConfig[lead.stage].label}
 </span>
 <div className="flex-1 min-w-0">
 <p className={heading.card +' truncate'}>{lead.clientName}</p>
 <p className="text-xs text-muted-foreground">{lead.caseType}</p>
 </div>
 <span className="text-xs text-muted-foreground flex-shrink-0 hidden sm:inline">{lead.source}</span>
 <span className="text-xs font-medium text-foreground flex-shrink-0">{lead.estimatedAmount.toLocaleString()}元</span>
 <span className="text-xs text-muted-foreground flex-shrink-0 hidden sm:inline">{lead.assignee}</span>
 </div>
 ))}
 </div>
 )}
 </div>
 </PageContainer>
 )
}
