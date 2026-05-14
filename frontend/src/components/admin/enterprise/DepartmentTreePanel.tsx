/**
 * 部门树面板 —— 后台 → 企业 → 组织目录
 *
 * - 左侧：递归树（折叠展开 / 选中节点）
 * - 右侧：选中节点详情 + 子部门列表 + 操作
 * - 顶部：新建根部门、刷新、LDAP 同步触发
 *
 * 失败时显示具体后端报错（含 401 / 403 / 503），便于运维定位。
 */

import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { icons } from '@/lib/icons'
import { heading, iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  enterpriseApi,
  type DepartmentNode,
} from '@/lib/api/enterprise-directory'

interface Props {
  /** 当前用户所属组织 id —— 顶层管理后台传入 */
  orgId: string | null | undefined
}

export function DepartmentTreePanel({ orgId }: Props) {
  const [tree, setTree] = useState<DepartmentNode[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCode, setNewCode] = useState('')
  const [creatingUnder, setCreatingUnder] = useState<string | null>(null)

  const refresh = async () => {
    if (!orgId) return
    setLoading(true)
    setError(null)
    try {
      const data = await enterpriseApi.getTree(orgId)
      setTree(data)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId])

  const flatById = useMemo(() => {
    const map = new Map<string, DepartmentNode>()
    const walk = (nodes: DepartmentNode[]) => {
      for (const n of nodes) {
        map.set(n.id, n)
        walk(n.children || [])
      }
    }
    walk(tree)
    return map
  }, [tree])

  const selected = selectedId ? flatById.get(selectedId) : null

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const onCreate = async () => {
    if (!newName.trim()) {
      toast.error('部门名不能为空')
      return
    }
    try {
      await enterpriseApi.createDepartment({
        name: newName.trim(),
        code: newCode.trim() || null,
        parent_id: creatingUnder || null,
      })
      toast.success(creatingUnder ? '子部门已创建' : '根部门已创建')
      setCreateOpen(false)
      setNewName('')
      setNewCode('')
      setCreatingUnder(null)
      void refresh()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const onDelete = async (id: string) => {
    if (!confirm('确认软删除此部门？子部门 / 成员关系不会级联删除。')) return
    try {
      await enterpriseApi.deleteDepartment(id)
      toast.success('已软删除')
      void refresh()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  const onLdapSync = async () => {
    try {
      const report = await enterpriseApi.triggerLdapSync(true)
      toast.success(`LDAP dry-run 完成：${JSON.stringify(report)}`)
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  if (!orgId) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
        当前账号未关联组织，无法管理部门树。
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 工具条 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className={heading.section}>组织目录</h3>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => void refresh()}>
            <icons.RefreshCw className={`${iconSize.sm} mr-1`} />
            刷新
          </Button>
          <Button size="sm" variant="outline" onClick={() => void onLdapSync()}>
            <icons.Cloud className={`${iconSize.sm} mr-1`} />
            LDAP 同步（dry-run）
          </Button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button
                size="sm"
                onClick={() => {
                  setCreatingUnder(null)
                  setNewName('')
                  setNewCode('')
                }}
              >
                <icons.Plus className={`${iconSize.sm} mr-1`} />
                新建根部门
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  {creatingUnder ? '新建子部门' : '新建根部门'}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-3 py-2">
                <div className="space-y-1.5">
                  <Label>名称</Label>
                  <Input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="例如：技术中心"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>编码（可选）</Label>
                  <Input
                    value={newCode}
                    onChange={(e) => setNewCode(e.target.value)}
                    placeholder="对接 HR / LDAP 时使用"
                  />
                </div>
                {creatingUnder && (
                  <div className="text-xs text-muted-foreground">
                    父部门：{flatById.get(creatingUnder)?.name}
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateOpen(false)}>
                  取消
                </Button>
                <Button onClick={() => void onCreate()}>创建</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* 树 */}
        <div className="lg:col-span-2 rounded-2xl border border-border bg-card p-2 min-h-[320px]">
          {loading && (
            <div className="p-4 text-sm text-muted-foreground">加载中…</div>
          )}
          {!loading && tree.length === 0 && !error && (
            <div className="p-6 text-center text-sm text-muted-foreground">
              暂无部门 —— 点击右上角"新建根部门"开始构建组织架构。
            </div>
          )}
          <ul className="space-y-0.5">
            {tree.map((node) => (
              <TreeRow
                key={node.id}
                node={node}
                depth={0}
                selectedId={selectedId}
                expandedIds={expandedIds}
                onSelect={setSelectedId}
                onToggle={toggle}
              />
            ))}
          </ul>
        </div>

        {/* 详情 */}
        <div className="lg:col-span-3 rounded-2xl border border-border bg-card p-5">
          {!selected ? (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground">
              在左侧选择一个部门查看详情
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs text-muted-foreground">部门</div>
                  <div className="text-lg font-medium">{selected.name}</div>
                  {selected.code && (
                    <div className="text-xs text-muted-foreground mt-1 font-mono">
                      code: {selected.code}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setCreatingUnder(selected.id)
                      setNewName('')
                      setNewCode('')
                      setCreateOpen(true)
                    }}
                  >
                    <icons.Plus className={`${iconSize.sm} mr-1`} />
                    新建子部门
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive"
                    onClick={() => void onDelete(selected.id)}
                  >
                    <icons.Trash2 className={`${iconSize.sm} mr-1`} />
                    软删
                  </Button>
                </div>
              </div>

              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted-foreground">id</dt>
                <dd className="font-mono text-xs truncate">{selected.id}</dd>
                <dt className="text-muted-foreground">path</dt>
                <dd className="font-mono text-xs truncate">{selected.path || '—'}</dd>
                <dt className="text-muted-foreground">parent_id</dt>
                <dd className="font-mono text-xs truncate">
                  {selected.parent_id || '（根部门）'}
                </dd>
                <dt className="text-muted-foreground">激活</dt>
                <dd>{selected.is_active ? '是' : '否'}</dd>
              </dl>

              {selected.children.length > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground mb-2">
                    子部门（{selected.children.length}）
                  </div>
                  <ul className="space-y-1">
                    {selected.children.map((c) => (
                      <li
                        key={c.id}
                        className="text-sm flex items-center justify-between px-3 py-1.5 rounded hover:bg-muted cursor-pointer"
                        onClick={() => setSelectedId(c.id)}
                      >
                        <span>{c.name}</span>
                        <icons.ChevronRight className={iconSize.sm} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// 树节点（递归）
// ---------------------------------------------------------------------------

function TreeRow({
  node,
  depth,
  selectedId,
  expandedIds,
  onSelect,
  onToggle,
}: {
  node: DepartmentNode
  depth: number
  selectedId: string | null
  expandedIds: Set<string>
  onSelect: (id: string) => void
  onToggle: (id: string) => void
}) {
  const hasChildren = (node.children || []).length > 0
  const expanded = expandedIds.has(node.id) || depth === 0
  const selected = selectedId === node.id

  return (
    <li>
      <div
        className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm ${
          selected ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
        }`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => onSelect(node.id)}
      >
        {hasChildren ? (
          <button
            type="button"
            className="p-0.5 hover:bg-muted-foreground/10 rounded"
            onClick={(e) => {
              e.stopPropagation()
              onToggle(node.id)
            }}
            aria-label={expanded ? '折叠' : '展开'}
          >
            {expanded ? (
              <icons.ChevronDown className={iconSize.sm} />
            ) : (
              <icons.ChevronRight className={iconSize.sm} />
            )}
          </button>
        ) : (
          <span style={{ width: 22 }} />
        )}
        <icons.Folder className={`${iconSize.sm} text-muted-foreground`} />
        <span className={node.is_active ? '' : 'line-through text-muted-foreground'}>
          {node.name}
        </span>
      </div>
      {hasChildren && expanded && (
        <ul className="space-y-0.5">
          {node.children.map((c) => (
            <TreeRow
              key={c.id}
              node={c}
              depth={depth + 1}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggle={onToggle}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

export default DepartmentTreePanel
