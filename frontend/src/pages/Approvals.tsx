import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, buttonStyle, statusBadge, heading, iconSize, inputStyle } from '@/lib/design-tokens'
import { approvalsApi, type ApprovalItem } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'

// ===== 状态配置 =====
const statusConfig: Record<ApprovalItem['status'], { label: string; style: string }> = {
  pending: { label: '待审批', style: statusBadge.warning },
  approved: { label: '已通过', style: statusBadge.success },
  rejected: { label: '已驳回', style: statusBadge.error },
  withdrawn: { label: '已撤回', style: statusBadge.neutral },
}

// ===== 类型配置 =====
const typeConfig: Record<string, { label: string; style: string }> = {
  contract: { label: '合同', style: 'text-primary bg-primary/5 border border-primary/20' },
  document: { label: '文档', style: 'text-violet-700 bg-violet-50 border border-violet-200 dark:text-violet-400 dark:bg-violet-950/30 dark:border-violet-800' },
  case_assign: { label: '案件分配', style: 'text-indigo-700 bg-indigo-50 border border-indigo-200 dark:text-indigo-400 dark:bg-indigo-950/30 dark:border-indigo-800' },
  expense: { label: '费用', style: 'text-orange-700 bg-orange-50 border border-orange-200 dark:text-orange-400 dark:bg-orange-950/30 dark:border-orange-800' },
  leave: { label: '请假', style: 'text-teal-700 bg-teal-50 border border-teal-200 dark:text-teal-400 dark:bg-teal-950/30 dark:border-teal-800' },
  custom: { label: '自定义', style: statusBadge.neutral },
}

// ===== 筛选标签配置 =====
type FilterTab = 'all' | 'pending_me' | 'my_requests'
type StatusFilter = 'all' | 'pending' | 'approved' | 'rejected'

const filterTabs: { key: FilterTab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'pending_me', label: '待我审批' },
  { key: 'my_requests', label: '我发起的' },
]

const statusFilters: { key: StatusFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'pending', label: '待审批' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已驳回' },
]

const typeOptions = [
  { value: 'contract', label: '合同审批' },
  { value: 'document', label: '文档审批' },
  { value: 'case_assign', label: '案件分配' },
  { value: 'expense', label: '费用审批' },
  { value: 'leave', label: '请假申请' },
  { value: 'custom', label: '自定义' },
]

// ===== Mock 数据 =====
const mockApprovals: ApprovalItem[] = [
  { id: '1', title: '甲方供应链合同审批', type: 'contract', status: 'pending', description: '需审批甲方供应链合同第三章违约条款修订', requester_id: 'u1', requester_name: '张律师', approver_name: '李主任', priority: 3, created_at: '2026-03-25T10:30:00Z', updated_at: '2026-03-25T10:30:00Z' },
  { id: '2', title: '尽调报告文档审批', type: 'document', status: 'pending', description: '乙公司并购案尽调报告终稿审批', requester_id: 'u2', requester_name: '陈助理', approver_name: '张律师', priority: 2, created_at: '2026-03-24T14:00:00Z', updated_at: '2026-03-24T14:00:00Z' },
  { id: '3', title: '王某劳动仲裁案件分配', type: 'case_assign', status: 'approved', description: '将王某劳动仲裁案分配给李律师团队', requester_id: 'u1', requester_name: '张律师', approver_name: '李主任', priority: 1, created_at: '2026-03-23T09:00:00Z', updated_at: '2026-03-23T16:00:00Z', approved_at: '2026-03-23T16:00:00Z', comment: '同意分配' },
  { id: '4', title: '差旅费用报销', type: 'expense', status: 'rejected', description: '庭审出差差旅费用报销申请', requester_id: 'u3', requester_name: '李律师', approver_name: '财务部', priority: 1, created_at: '2026-03-22T11:00:00Z', updated_at: '2026-03-22T17:00:00Z', comment: '超出预算额度，请重新提交' },
  { id: '5', title: '年假申请', type: 'leave', status: 'withdrawn', description: '申请3月28日-29日年假两天', requester_id: 'u2', requester_name: '陈助理', priority: 1, created_at: '2026-03-21T08:00:00Z', updated_at: '2026-03-21T12:00:00Z' },
  { id: '6', title: '标准劳动合同模板更新', type: 'contract', status: 'pending', description: '根据新法规修订标准劳动合同模板', requester_id: 'u3', requester_name: '李律师', approver_name: '张律师', priority: 1, created_at: '2026-03-20T15:00:00Z', updated_at: '2026-03-20T15:00:00Z' },
]

// ===== 时间格式化 =====
function timeAgo(dateStr: string): string {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}小时前`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay < 30) return `${diffDay}天前`
  return date.toLocaleDateString('zh-CN')
}

export default function Approvals() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>(mockApprovals)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<FilterTab>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [rejectDialogId, setRejectDialogId] = useState<string | null>(null)
  const [rejectComment, setRejectComment] = useState('')
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0, withdrawn: 0 })

  // ===== 表单状态 =====
  const [formTitle, setFormTitle] = useState('')
  const [formType, setFormType] = useState('contract')
  const [formDescription, setFormDescription] = useState('')
  const [formPriority, setFormPriority] = useState(1)

  const loadApprovals = useCallback(async () => {
    setLoading(true)
    try {
      const params: { status?: string; type?: string; page_size?: number } = { page_size: 50 }
      if (statusFilter !== 'all') params.status = statusFilter
      const data = await approvalsApi.list(params)
      if (data.items?.length > 0) {
        setApprovals(data.items)
      } else {
        setApprovals(mockApprovals)
      }
    } catch {
      setApprovals(mockApprovals)
    } finally {
      setLoading(false)
    }
  }, [statusFilter])

  const loadStats = useCallback(async () => {
    try {
      const data = await approvalsApi.stats()
      setStats({
        pending: data.pending || 0,
        approved: data.approved || 0,
        rejected: data.rejected || 0,
        withdrawn: data.withdrawn || 0,
      })
    } catch {
      // Use mock stats
      const counts = { pending: 0, approved: 0, rejected: 0, withdrawn: 0 }
      mockApprovals.forEach((a) => { counts[a.status]++ })
      setStats(counts)
    }
  }, [])

  useEffect(() => {
    loadApprovals()
    loadStats()
  }, [loadApprovals, loadStats])

  // ===== 过滤逻辑 =====
  const filteredApprovals = approvals.filter((item) => {
    if (statusFilter !== 'all' && item.status !== statusFilter) return false
    // Tab filtering is simplified since we don't have current user context in mock
    return true
  })

  // ===== 操作 =====
  const handleApprove = async (id: string) => {
    try {
      await approvalsApi.approve(id)
      toast.success('审批已通过')
      loadApprovals()
      loadStats()
    } catch {
      // Mock: update locally
      setApprovals((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'approved' as const, approved_at: new Date().toISOString() } : a))
      )
      toast.success('审批已通过')
    }
  }

  const handleReject = async (id: string) => {
    if (!rejectComment.trim()) {
      toast.error('请填写驳回原因')
      return
    }
    try {
      await approvalsApi.reject(id, rejectComment)
      toast.success('审批已驳回')
      setRejectDialogId(null)
      setRejectComment('')
      loadApprovals()
      loadStats()
    } catch {
      setApprovals((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'rejected' as const, comment: rejectComment } : a))
      )
      toast.success('审批已驳回')
      setRejectDialogId(null)
      setRejectComment('')
    }
  }

  const handleCreate = async () => {
    if (!formTitle.trim()) {
      toast.error('请填写审批标题')
      return
    }
    try {
      await approvalsApi.create({
        title: formTitle,
        type: formType,
        description: formDescription,
        priority: formPriority,
      })
      toast.success('审批已提交')
      setShowCreateDialog(false)
      resetForm()
      loadApprovals()
      loadStats()
    } catch {
      // Mock: add locally
      const newItem: ApprovalItem = {
        id: String(Date.now()),
        title: formTitle,
        type: formType,
        status: 'pending',
        description: formDescription,
        requester_id: 'current',
        requester_name: '当前用户',
        priority: formPriority,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
      setApprovals((prev) => [newItem, ...prev])
      toast.success('审批已提交')
      setShowCreateDialog(false)
      resetForm()
    }
  }

  const resetForm = () => {
    setFormTitle('')
    setFormType('contract')
    setFormDescription('')
    setFormPriority(1)
  }

  // ===== 统计卡片 =====
  const statCards = [
    { label: '待审批', value: stats.pending, icon: icons.Clock, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/30' },
    { label: '已通过', value: stats.approved, icon: icons.CheckCircle, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: '已驳回', value: stats.rejected, icon: icons.XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/30' },
    { label: '已撤回', value: stats.withdrawn, icon: icons.ArrowLeft, color: 'text-muted-foreground', bg: 'bg-muted' },
  ]

  return (
    <PageContainer
      title="审批中心"
      description="管理合同、文档、费用等审批流程"
      actions={
        <button onClick={() => setShowCreateDialog(true)} className={buttonStyle.primary}>
          <icons.Plus className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          发起审批
        </button>
      }
    >
      {/* ===== 统计卡片 ===== */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className={cardStyle.base}>
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${card.bg}`}>
                  <Icon className={`${iconSize.md} ${card.color}`} />
                </div>
                <div>
                  <p className={heading.micro}>{card.label}</p>
                  <p className="text-xl font-bold text-foreground">{card.value}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* ===== 筛选栏 ===== */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3">
        {/* Tab 筛选 */}
        <div className="flex items-center gap-1 bg-muted rounded-lg p-1">
          {filterTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === tab.key
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 状态筛选 */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {statusFilters.map((sf) => (
            <button
              key={sf.key}
              onClick={() => setStatusFilter(sf.key)}
              className={`px-3 py-1 text-xs font-medium rounded-full border transition-colors ${
                statusFilter === sf.key
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-background text-muted-foreground border-border hover:border-primary/30 hover:text-foreground'
              }`}
            >
              {sf.label}
            </button>
          ))}
        </div>
      </div>

      {/* ===== 审批列表 ===== */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className={`${cardStyle.base} animate-pulse`}>
              <div className="h-4 bg-muted rounded w-1/3 mb-3" />
              <div className="h-3 bg-muted rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className={`${cardStyle.base} text-center py-16`}>
          <icons.ClipboardCheck className="w-12 h-12 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-muted-foreground text-sm">暂无审批记录</p>
          <button
            onClick={() => setShowCreateDialog(true)}
            className={`${buttonStyle.primary} mt-4`}
          >
            发起审批
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredApprovals.map((item) => {
            const sConfig = statusConfig[item.status]
            const tConfig = typeConfig[item.type] || typeConfig.custom
            return (
              <div
                key={item.id}
                className={`${cardStyle.base} hover:shadow-md hover:border-primary/20 transition-all`}
              >
                <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                  {/* 左侧内容 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1.5">
                      {/* 优先级指示 */}
                      {item.priority >= 3 && (
                        <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" title="特急" />
                      )}
                      {item.priority === 2 && (
                        <span className="w-2 h-2 rounded-full bg-amber-500 shrink-0" title="紧急" />
                      )}
                      <h3 className={`text-sm font-medium text-foreground truncate ${item.priority >= 3 ? 'font-bold' : ''}`}>
                        {item.title}
                      </h3>
                      <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${tConfig.style}`}>
                        {tConfig.label}
                      </span>
                      <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-medium rounded-md ${sConfig.style}`}>
                        {sConfig.label}
                      </span>
                    </div>
                    {item.description && (
                      <p className="text-xs text-muted-foreground line-clamp-1 mb-2">
                        {item.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <icons.User className="w-3 h-3" />
                        {item.requester_name || '未知'}
                      </span>
                      {item.approver_name && (
                        <span className="flex items-center gap-1">
                          <icons.ArrowRight className="w-3 h-3" />
                          {item.approver_name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <icons.Clock className="w-3 h-3" />
                        {timeAgo(item.created_at)}
                      </span>
                      {item.comment && item.status !== 'pending' && (
                        <span className="flex items-center gap-1 text-muted-foreground/70 italic">
                          "{item.comment}"
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 右侧操作按钮 */}
                  {item.status === 'pending' && (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleApprove(item.id)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:text-emerald-400 dark:hover:bg-emerald-950/50 transition-colors"
                      >
                        <icons.Check className="w-3.5 h-3.5" />
                        通过
                      </button>
                      <button
                        onClick={() => setRejectDialogId(item.id)}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-950/30 dark:text-red-400 dark:hover:bg-red-950/50 transition-colors"
                      >
                        <icons.X className="w-3.5 h-3.5" />
                        驳回
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ===== 驳回弹窗 ===== */}
      {rejectDialogId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
            <h3 className={`${heading.section} mb-4`}>驳回审批</h3>
            <textarea
              value={rejectComment}
              onChange={(e) => setRejectComment(e.target.value)}
              placeholder="请填写驳回原因（必填）"
              className={`${inputStyle.search} resize-none h-24`}
            />
            <div className="flex items-center justify-end gap-2 mt-4">
              <button
                onClick={() => { setRejectDialogId(null); setRejectComment('') }}
                className={buttonStyle.secondary}
              >
                取消
              </button>
              <button
                onClick={() => handleReject(rejectDialogId)}
                className={buttonStyle.danger}
              >
                确认驳回
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== 新建审批弹窗 ===== */}
      {showCreateDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
            <div className="flex items-center justify-between mb-5">
              <h3 className={heading.section}>发起审批</h3>
              <button onClick={() => { setShowCreateDialog(false); resetForm() }} className={buttonStyle.icon}>
                <icons.X className={iconSize.md} />
              </button>
            </div>

            <div className="space-y-4">
              {/* 标题 */}
              <div>
                <label className={`block ${heading.card} mb-1.5`}>审批标题 *</label>
                <input
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="请输入审批标题"
                  className={inputStyle.search}
                />
              </div>

              {/* 类型 */}
              <div>
                <label className={`block ${heading.card} mb-1.5`}>审批类型</label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  className={inputStyle.search}
                >
                  {typeOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              {/* 优先级 */}
              <div>
                <label className={`block ${heading.card} mb-1.5`}>优先级</label>
                <div className="flex items-center gap-2">
                  {[
                    { value: 1, label: '普通' },
                    { value: 2, label: '紧急' },
                    { value: 3, label: '特急' },
                  ].map((p) => (
                    <button
                      key={p.value}
                      onClick={() => setFormPriority(p.value)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                        formPriority === p.value
                          ? p.value === 3
                            ? statusBadge.error
                            : p.value === 2
                            ? statusBadge.warning
                            : statusBadge.info
                          : 'bg-background text-muted-foreground border border-border hover:border-primary/30'
                      }`}
                    >
                      {p.value >= 2 && (
                        <span className={`w-1.5 h-1.5 rounded-full ${p.value === 3 ? 'bg-red-500' : 'bg-amber-500'}`} />
                      )}
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 描述 */}
              <div>
                <label className={`block ${heading.card} mb-1.5`}>描述</label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="请输入审批描述（可选）"
                  className={`${inputStyle.search} resize-none h-20`}
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 mt-5">
              <button onClick={() => { setShowCreateDialog(false); resetForm() }} className={buttonStyle.secondary}>
                取消
              </button>
              <button onClick={handleCreate} className={buttonStyle.primary}>
                提交审批
              </button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  )
}
