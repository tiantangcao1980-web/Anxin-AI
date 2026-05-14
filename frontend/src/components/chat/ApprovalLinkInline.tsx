/**
 * ApprovalLinkInline — I3 (2026-05-14)
 *
 * 用法: 在 chat AI message 中, 当 backend 因 REQUIRE_APPROVAL 拒绝工具调用并
 * 自动创建审批工单时, message.content 会含 "已自动创建工单 {id}" 文本.
 * 本组件检测该模式, 渲染成 inline link/chip, 用户可直接跳转 admin 审批面板.
 *
 * 后端注入位置: backend/src/agents/base.py:710 (A6)
 *   tool_output += f"\n\n该操作需要人工审批, 已自动创建工单 {_ap_id}, 审批通过后请重试。"
 *
 * 前端注入位置: components/chat/LongMessage.tsx 渲染 markdown body 前 preprocess.
 */
import { Link } from 'react-router-dom'
import { icons } from '@/lib/icons'

/**
 * 从一段文本里识别 "已自动创建工单 {id}" 模式, 返回工单 id 列表。
 * id 长度通常为 8-36 字符 (UUID 或短 hash), 容忍中英文标点。
 */
export function extractApprovalIds(content: string): string[] {
  if (!content) return []
  const ids: string[] = []
  // 匹配多种文案变体: "已自动创建工单 X" / "approval id: X" / "工单 X"
  const re = /(?:已自动创建工单|approval[\s_]*id[:\s]*|工单)\s+([A-Za-z0-9_-]{6,40})/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(content)) !== null) {
    if (m[1] && !ids.includes(m[1])) ids.push(m[1])
  }
  return ids
}

interface Props {
  approvalId: string
  /** 可选: 已知的当前状态 (待审批 / 已批准 / 已拒绝). 缺省 → 显示通用"待人工审批" */
  status?: 'pending' | 'approved' | 'rejected'
}

export function ApprovalLinkInline({ approvalId, status = 'pending' }: Props) {
  const statusMap = {
    pending: { label: '待人工审批', cls: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30' },
    approved: { label: '已批准', cls: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30' },
    rejected: { label: '已拒绝', cls: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/30' },
  } as const
  const s = statusMap[status]
  return (
    <Link
      to={`/agent-approvals?approval_id=${encodeURIComponent(approvalId)}`}
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-medium hover:underline ${s.cls}`}
      title={`审批工单 ${approvalId} · ${s.label} · 点击查看 / 处理`}
    >
      <icons.ShieldCheck className="w-3 h-3" />
      <span className="font-mono">工单 {approvalId.slice(0, 12)}</span>
      <span>· {s.label}</span>
    </Link>
  )
}

/**
 * 复合渲染: 给一段含 "已自动创建工单 {id}" 的文本, 返回拆分后的 React 节点数组,
 * 工单 id 处替换为 ApprovalLinkInline。
 *
 * 调用方 (LongMessage / MarkdownRenderer) 把字符串先过本函数, 再交给后续渲染。
 */
export function renderWithApprovalLinks(content: string): React.ReactNode[] {
  if (!content) return [content]
  const ids = extractApprovalIds(content)
  if (ids.length === 0) return [content]

  // 简单实现: 用第一个 id 的位置切分; 多个 id 重复处理
  // 为避免复杂的 React.Fragment 拼接, 我们用文本切片 + 注入组件
  const segments: React.ReactNode[] = []
  let cursor = 0
  const escapedIds = ids.map(id => id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')
  const re = new RegExp(`(${escapedIds})`, 'g')
  let m: RegExpExecArray | null
  while ((m = re.exec(content)) !== null) {
    const before = content.slice(cursor, m.index)
    if (before) segments.push(before)
    segments.push(<ApprovalLinkInline key={`ap-${m.index}-${m[1]}`} approvalId={m[1]} />)
    cursor = m.index + m[1].length
  }
  if (cursor < content.length) segments.push(content.slice(cursor))
  return segments
}
