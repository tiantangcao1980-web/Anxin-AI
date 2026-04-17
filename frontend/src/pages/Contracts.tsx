import { useState, useEffect } from'react'
import { useNavigate } from'react-router-dom'
import { icons } from'@/lib/icons'
import { EmptyState, LoadingState } from'@/components/common'
import { toast } from'sonner'
import { contractsApi, Contract, ContractCreate } from'@/lib/api'
import { PageContainer } from'@/components/ui/PageContainer'
import { cardStyle, heading, buttonStyle, iconSize, statusBadge, radius, inputStyle } from'@/lib/design-tokens'

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
 const navigate = useNavigate()
 const [contracts, setContracts] = useState<Contract[]>([])
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 const [total, setTotal] = useState(0)
 const [page, setPage] = useState(1)
 const [showReviewModal, setShowReviewModal] = useState(false)
 const [selectedContract, setSelectedContract] = useState<Contract | null>(null)
 const [showCreateModal, setShowCreateModal] = useState(false)

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

 const handleReview = (contract: Contract) => {
 setSelectedContract(contract)
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
 onClick={() => navigate('/contract-review')}
 className={`${buttonStyle.primary} flex items-center gap-2 whitespace-nowrap`}
 >
 <icons.Upload className={iconSize.sm} />
 完整审查
 </button>
 </div>
 }
 >
 {/* 统计卡片 */}
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 <div data-ui="surface-card" className={cardStyle.compact}>
 <div className="flex items-center justify-between">
 <p className={heading.muted}>待审核</p>
 <icons.Clock className={`${iconSize.md} text-warning`} />
 </div>
 <p className="text-2xl font-bold mt-2">
 {contracts.filter(c => c.status ==='pending_review').length}
 </p>
 </div>
 <div data-ui="surface-card" className={cardStyle.compact}>
 <div className="flex items-center justify-between">
 <p className={heading.muted}>审核中</p>
 <icons.Loader2 className={`${iconSize.md} text-primary`} />
 </div>
 <p className="text-2xl font-bold mt-2">
 {contracts.filter(c => c.status ==='under_review').length}
 </p>
 </div>
 <div data-ui="surface-card" className={cardStyle.compact}>
 <div className="flex items-center justify-between">
 <p className={heading.muted}>高风险</p>
 <icons.AlertTriangle className={`${iconSize.md} text-destructive`} />
 </div>
 <p className="text-2xl font-bold mt-2">
 {contracts.filter(c => c.risk_level ==='high' || c.risk_level ==='critical').length}
 </p>
 </div>
 <div data-ui="surface-card" className={cardStyle.compact}>
 <div className="flex items-center justify-between">
 <p className={heading.muted}>已完成</p>
 <icons.CheckCircle className={`${iconSize.md} text-success`} />
 </div>
 <p className="text-2xl font-bold mt-2">
 {contracts.filter(c => c.status ==='approved' || c.status ==='signed').length}
 </p>
 </div>
 </div>

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
 onClick={() => handleReview(contract)}
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

 <button
 onClick={(e) => { e.stopPropagation(); handleReview(contract); }}
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
 contract={selectedContract}
 onClose={() => {
 setShowReviewModal(false)
 setSelectedContract(null)
 }}
 onComplete={loadContracts}
 />
 )}

 {/* 创建合同模态框 */}
 {showCreateModal && (
 <CreateContractModal
 onClose={() => setShowCreateModal(false)}
 onComplete={loadContracts}
 />
 )}
 </PageContainer>
 )
}

// 审查模态框
function ReviewModal({ 
 contract, 
 onClose, 
 onComplete 
}: { 
 contract: Contract | null
 onClose: () => void
 onComplete: () => void 
}) {
 const [contractText, setContractText] = useState('')
 const [reviewing, setReviewing] = useState(false)
 const [result, setResult] = useState<any>(null)

 const handleReview = async () => {
 if (!contractText.trim()) {
 toast.error('请输入合同文本')
 return
 }

 setReviewing(true)
 try {
 // 如果没有选中的合同，先创建一个
 let contractId = contract?.id
 if (!contractId) {
 const newContract = await contractsApi.create({
 title:'待审查合同',
 contract_type:'other',
 })
 contractId = newContract.id
 }

 const reviewResult = await contractsApi.review(contractId, contractText)
 setResult(reviewResult)
 toast.success('审查完成')
 onComplete()
 } catch (error: any) {
 toast.error(error.message ||'审查失败')
 } finally {
 setReviewing(false)
 }
 }

 return (
 <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
 <div className={`bg-background ${radius.dialog} shadow-lg w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col`}>
 <div className="p-6 border-b">
 <h2 className={heading.section}>合同智能审查</h2>
 </div>
 
 <div className="flex-1 overflow-auto p-6">
 {result ? (
 <div className="space-y-6">
 {/* 审查结果概览 */}
 <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
 <div className={cardStyle.compact}>
 <p className={heading.muted}>风险等级</p>
 <p className={`text-lg font-bold ${
 result.risk_level ==='critical' || result.risk_level ==='high' ?'text-destructive' :
 result.risk_level ==='medium' ?'text-warning' :'text-success'
 }`}>
 {RISK_LEVEL_MAP[result.risk_level]?.label || result.risk_level}
 </p>
 </div>
 <div className={cardStyle.compact}>
 <p className={heading.muted}>风险评分</p>
 <p className="text-lg font-bold">{((result.risk_score || 0) * 100).toFixed(0)}%</p>
 </div>
 <div className={cardStyle.compact}>
 <p className={heading.muted}>风险点数量</p>
 <p className="text-lg font-bold">{result.risks?.length || 0}</p>
 </div>
 </div>

 {/* 审查摘要 */}
 <div className={cardStyle.compact}>
 <h3 className={`${heading.card} mb-2`}>审查摘要</h3>
 <p className={`${heading.muted} whitespace-pre-wrap`}>
 {result.summary ||'暂无摘要'}
 </p>
 </div>

 {/* 风险点列表 */}
 {result.risks && result.risks.length > 0 && (
 <div className="space-y-3">
 <h3 className={heading.card}>风险点 ({result.risks.length})</h3>
 {result.risks.map((risk: any, index: number) => (
 <div key={index} className={cardStyle.compact}>
 <div className="flex items-center gap-2">
 <icons.AlertTriangle className={`${iconSize.sm} ${
 risk.level ==='critical' || risk.level ==='high' ?'text-destructive' :
 risk.level ==='medium' ?'text-warning' :'text-success'
 }`} />
 <span className={heading.card}>{risk.title}</span>
 </div>
 <p className={`${heading.muted} mt-2`}>{risk.description}</p>
 {risk.suggestion && (
 <p className="text-sm mt-2 text-primary">建议: {risk.suggestion}</p>
 )}
 </div>
 ))}
 </div>
 )}
 </div>
 ) : (
 <div className="space-y-4">
 <p className={heading.muted}>
 请粘贴合同文本，AI将自动识别风险条款并提供修改建议
 </p>
 <textarea
 value={contractText}
 onChange={(e) => setContractText(e.target.value)}
 placeholder="请在此粘贴合同文本..."
 className={`${inputStyle.search} h-96 px-4 py-3 resize-none`}
 />
 </div>
 )}
 </div>
 
 <div className="p-6 border-t flex justify-end gap-3">
 <button
 onClick={onClose}
 className={buttonStyle.secondary}
 >
 关闭
 </button>
 {!result && (
 <button
 onClick={handleReview}
 disabled={reviewing || !contractText.trim()}
 className={`${buttonStyle.primary} flex items-center gap-2 disabled:opacity-50`}
 >
 {reviewing ? (
 <>
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 审查中...
 </>
 ) : (
 <>
 <icons.Search className={iconSize.sm} />
 开始审查
 </>
 )}
 </button>
 )}
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
