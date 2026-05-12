import { useState, useEffect } from'react'
import { icons } from'@/lib/icons'
import { EmptyState, LoadingState } from'@/components/common'
import { StatCard, StatGrid } from'@/components/ui-unified'
import { toast } from'sonner'
import { contractsApi, Contract, ContractCreate } from'@/lib/api'
import { PageContainer } from'@/components/ui/PageContainer'
import { cardStyle, heading, buttonStyle, iconSize, statusBadge, radius, inputStyle } from'@/lib/design-tokens'
import { ESignDialog } from'@/components/esign/ESignDialog'
import ContractReview from'./ContractReview'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
 draft: { label:'草稿', color: statusBadge.neutral },
 pending_review: { label:'待审核', color: statusBadge.warning },
 under_review: { label:'审核中', color: statusBadge.info },
 approved: { label:'已批准', color: statusBadge.success },
 signed: { label:'已签署', color: statusBadge.info },
 active: { label:'生效中', color: statusBadge.success },
 expired: { label:'已过期', color: statusBadge.error },
}

const RISK_LEVEL_MAP: Record<string, { label: string; color: string; icon: any }> = {
 low: { label:'低风险', color:'text-success', icon: icons.CheckCircle },
 medium: { label:'中风险', color:'text-warning', icon: icons.Clock },
 high: { label:'高风险', color:'text-orange-600', icon: icons.AlertTriangle },
 critical: { label:'极高风险', color:'text-destructive', icon: icons.AlertTriangle },
}

const CONTRACT_TYPES = [
 { value:'purchase', label:'采购合同' },
 { value:'sales', label:'销售合同' },
 { value:'service', label:'服务协议' },
 { value:'labor', label:'劳动合同' },
 { value:'lease', label:'租赁合同' },
 { value:'nda', label:'保密协议' },
 { value:'cooperation', label:'合作协议' },
 { value:'other', label:'其他' },
]

export default function Contracts() {
 const [contracts, setContracts] = useState<Contract[]>([])
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [total, setTotal] = useState(0)
 const [page, setPage] = useState(1)
 const [showReviewModal, setShowReviewModal] = useState(false)
 const [showCreateModal, setShowCreateModal] = useState(false)
 // 电签对话框
 const [esignDialog, setEsignDialog] = useState<{ open: boolean; contract: Contract | null }>({ open: false, contract: null })

 useEffect(() => {
 loadContracts()
 }, [page])

 const loadContracts = async () => {
 setLoading(true)
 setError(null)
 try {
 const response = await contractsApi.list({ page, page_size: 20 })
 setContracts(response.items)
 setTotal(response.total)
 setError(null)
 } catch (err: any) {
 setContracts([])
 setTotal(0)
 setError(err.message ||'合同数据加载失败')
 toast.error(err.message ||'合同数据加载失败')
 } finally {
 setLoading(false)
 }
 }

 const handleReview = () => {
 setShowReviewModal(true)
 }

 return (
 <PageContainer
 title="合同管理"
 description="AI智能审查合同，识别风险条款"
 embedded
 actions={
 <div className="flex gap-2 flex-wrap">
 <button
 onClick={() => setShowCreateModal(true)}
 className={`${buttonStyle.secondary} flex items-center gap-2 whitespace-nowrap`}
 >
 <icons.Plus className={iconSize.sm} />
 新建合同
 </button>
 <button
 onClick={() => setShowReviewModal(true)}
 className={`${buttonStyle.secondary} flex items-center gap-2 whitespace-nowrap`}
 >
 <icons.Search className={iconSize.sm} />
 快捷审查
 </button>
 <button
 onClick={() => setShowReviewModal(true)}
 className={`${buttonStyle.primary} flex items-center gap-2 whitespace-nowrap`}
 >
 <icons.Upload className={iconSize.sm} />
 完整审查
 </button>
 </div>
 }
 >
 {/* 统计卡片 — StatGrid 统一接入，自动获得错峰入场、趋势徽章、悬浮抬升、骨架加载 */}
 <StatGrid cols={4}>
 <StatCard
 index={0}
 icon={icons.Clock}
 tone="warning"
 label="待审核"
 value={contracts.filter(c => c.status ==='pending_review').length}
 hint="需人工介入"
 loading={loading}
 />
 <StatCard
 index={1}
 icon={icons.Loader2}
 tone="primary"
 label="审核中"
 value={contracts.filter(c => c.status ==='under_review').length}
 hint="AI 审查进行中"
 loading={loading}
 />
 <StatCard
 index={2}
 icon={icons.AlertTriangle}
 tone="destructive"
 label="高风险"
 value={contracts.filter(c => c.risk_level ==='high' || c.risk_level ==='critical').length}
 hint="建议立即处理"
 loading={loading}
 />
 <StatCard
 index={3}
 icon={icons.CheckCircle}
 tone="success"
 label="已完成"
 value={contracts.filter(c => c.status ==='approved' || c.status ==='signed').length}
 hint="已批准/签署"
 loading={loading}
 />
 </StatGrid>

 {/* 合同列表 */}
 <div data-ui="surface-card" className={cardStyle.base}>
 {loading ? (
 <LoadingState />
 ) : error ? (
 <div className="flex flex-col items-center justify-center py-12">
 <icons.AlertTriangle className={`${iconSize['2xl']} mx-auto text-muted-foreground mb-4`} />
 <p className={heading.muted}>{error}</p>
 <button onClick={loadContracts} className={`mt-4 ${buttonStyle.primary} flex items-center gap-1`}>
 <icons.Refresh className={iconSize.sm} />
 重试
 </button>
 </div>
 ) : contracts.length === 0 ? (
 <EmptyState
 icon="FileText"
 title="暂无合同"
 action={{ label: '上传第一份合同进行审查', onClick: () => setShowReviewModal(true) }}
 />
 ) : (
 <div className="divide-y">
 {contracts.map((contract) => {
 const status = STATUS_MAP[contract.status] || STATUS_MAP.draft
 const riskLevel = contract.risk_level 
 ? RISK_LEVEL_MAP[contract.risk_level] 
 : null
 const RiskIcon = riskLevel?.icon
 
 return (
 <div
 key={contract.id}
 onClick={() => handleReview()}
 className="p-4 hover:bg-muted/30 transition-colors cursor-pointer"
 >
 <div className="flex items-start justify-between gap-2">
 <div className="flex items-start gap-3 min-w-0 flex-1">
 <div className={`p-2 ${radius.button} bg-muted shrink-0`}>
 <icons.FileText className={`${iconSize.md} text-muted-foreground`} />
 </div>
 <div className="min-w-0">
 <h3 className={`${heading.card} truncate`}>{contract.title}</h3>
 <div className={`flex items-center gap-2 mt-1 ${heading.micro} flex-wrap`}>
 <span className="truncate">{contract.contract_number ||'-'}</span>
 <span>·</span>
 <span className="whitespace-nowrap">{CONTRACT_TYPES.find(t => t.value === contract.contract_type)?.label || contract.contract_type}</span>
 {contract.amount && (
 <>
 <span>·</span>
 <span className="whitespace-nowrap">¥{contract.amount.toLocaleString()}</span>
 </>
 )}
 </div>
 </div>
 </div>

 <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
 {riskLevel && (
 <div className={`flex items-center gap-1 ${riskLevel.color}`}>
 {RiskIcon && <RiskIcon className={iconSize.sm} />}
 <span className="text-sm whitespace-nowrap">{riskLevel.label}</span>
 </div>
 )}

 <span className={`px-2 py-1 ${radius.badge} text-xs whitespace-nowrap ${status.color}`}>
 {status.label}
 </span>

 {/* 已批准合同显示"发起签署"按钮 */}
 {(contract.status === 'approved' || contract.status === 'active') && (
 <button
 onClick={(e) => { e.stopPropagation(); setEsignDialog({ open: true, contract }); }}
 className={`${buttonStyle.secondary} flex items-center gap-1 text-xs whitespace-nowrap`}
 title="发起电子签署"
 >
 <icons.FileText className={iconSize.sm} />
 发起签署
 </button>
 )}

 <button
 onClick={(e) => { e.stopPropagation(); handleReview(); }}
 className={buttonStyle.icon}
 >
 <icons.Eye className={iconSize.sm} />
 </button>
 </div>
 </div>
 
 {contract.risk_score !== null && contract.risk_score !== undefined && (
 <div className="mt-3 flex items-center gap-2">
 <span className={`${heading.micro} whitespace-nowrap`}>风险评分:</span>
 <div className="flex-1 h-2 bg-muted border border-border/50 rounded-full overflow-hidden max-w-xs">
 <div
 className={`h-full rounded-full transition-[width] duration-300 ${
 contract.risk_score >= 0.7 ?'bg-destructive' :
 contract.risk_score >= 0.5 ?'bg-warning' :
 contract.risk_score >= 0.3 ?'bg-warning' :
'bg-success'
 }`}
 style={{
 width: `${Math.max(contract.risk_score * 100, contract.risk_score > 0 ? 2 : 0)}%`,
 }}
 />
 </div>
 <span className={`text-xs font-medium tabular-nums whitespace-nowrap ${
 contract.risk_score >= 0.7 ?'text-destructive' :
 contract.risk_score >= 0.5 ?'text-warning' :
 contract.risk_score >= 0.3 ?'text-warning' :
'text-success'
 }`}>
 {(contract.risk_score * 100).toFixed(0)}%
 </span>
 </div>
 )}
 </div>
 )
 })}
 </div>
 )}
 </div>

 {/* 审查模态框 */}
 {showReviewModal && (
 <ReviewModal
 onClose={() => {
 setShowReviewModal(false)
 }}
 />
 )}

 {/* 创建合同模态框 */}
 {showCreateModal && (
 <CreateContractModal
 onClose={() => setShowCreateModal(false)}
 onComplete={loadContracts}
 />
 )}

 {/* 电子签署对话框 */}
 <ESignDialog
 open={esignDialog.open}
 onOpenChange={(open) => setEsignDialog({ ...esignDialog, open })}
 contract={esignDialog.contract ? {
 id: esignDialog.contract.id,
 title: esignDialog.contract.title,
 contractType: esignDialog.contract.contract_type,
 } : null}
 onCompleted={loadContracts}
 />
 </PageContainer>
 )
}

// 审查模态框
function ReviewModal({ onClose }: { onClose: () => void }) {
 return (
 <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
 <div className={`bg-background ${radius.dialog} shadow-lg w-full max-w-6xl mx-4 h-[90vh] overflow-hidden flex flex-col`}>
 <div className="px-5 py-4 border-b flex items-center justify-between">
 <h2 className={heading.section}>合同智能审查</h2>
 <button onClick={onClose} className={buttonStyle.icon} title="关闭">
 <icons.X className={iconSize.md} />
 </button>
 </div>
 <div className="flex-1 min-h-0">
 <ContractReview embedded />
 </div>
 </div>
 </div>
 )
}

// 创建合同模态框
function CreateContractModal({ onClose, onComplete }: { onClose: () => void; onComplete: () => void }) {
 const [formData, setFormData] = useState<ContractCreate>({
 title:'',
 contract_type:'other',
 })
 const [submitting, setSubmitting] = useState(false)

 const handleSubmit = async (e: React.FormEvent) => {
 e.preventDefault()
 if (!formData.title.trim()) {
 toast.error('请输入合同标题')
 return
 }

 setSubmitting(true)
 try {
 await contractsApi.create(formData)
 toast.success('合同创建成功')
 onComplete()
 onClose()
 } catch (error: any) {
 toast.error(error.message ||'创建失败')
 } finally {
 setSubmitting(false)
 }
 }

 return (
 <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
 <div className={`bg-background ${radius.dialog} shadow-lg w-full max-w-lg mx-4`}>
 <div className="p-6 border-b">
 <h2 className={heading.section}>新建合同</h2>
 </div>

 <form onSubmit={handleSubmit} className="p-6 space-y-4">
 <div>
 <label className={`${heading.card} block mb-1`}>合同标题 *</label>
 <input
 type="text"
 value={formData.title}
 onChange={(e) => setFormData({ ...formData, title: e.target.value })}
 className={inputStyle.search}
 placeholder="请输入合同标题"
 />
 </div>

 <div>
 <label className={`${heading.card} block mb-1`}>合同类型</label>
 <select
 value={formData.contract_type}
 onChange={(e) => setFormData({ ...formData, contract_type: e.target.value })}
 className={inputStyle.search}
 >
 {CONTRACT_TYPES.map((type) => (
 <option key={type.value} value={type.value}>{type.label}</option>
 ))}
 </select>
 </div>

 <div>
 <label className={`${heading.card} block mb-1`}>合同金额</label>
 <input
 type="number"
 value={formData.amount ||''}
 onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || undefined })}
 className={inputStyle.search}
 placeholder="请输入合同金额"
 />
 </div>

 <div className="flex justify-end gap-3 pt-4">
 <button
 type="button"
 onClick={onClose}
 className={buttonStyle.secondary}
 >
 取消
 </button>
 <button
 type="submit"
 disabled={submitting}
 className={`${buttonStyle.primary} disabled:opacity-50`}
 >
 {submitting ? <icons.Loader2 className={`${iconSize.sm} animate-spin`} /> :'创建'}
 </button>
 </div>
 </form>
 </div>
 </div>
 )
}
