import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { API_BASE_URL, buildApiHeaders } from '@/lib/api'
import { PageContainer } from '@/components/ui/PageContainer'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

interface SnapshotMeta {
  snapshot_id: string
  loaded_at: string
  files: string[]
}

const POLICY_FILES = [
  'access-matrix.yaml',
  'trust-levels.yaml',
  'data-classification.yaml',
  'jurisdiction-rules.yaml',
  'tool-allowlist.yaml',
  'pii-redaction.yaml',
  'skill-lifecycle.yaml',
]

export default function AdminGovernancePolicy() {
  const [snapshots, setSnapshots] = useState<SnapshotMeta[]>([])
  const [currentSnapshot, setCurrentSnapshot] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<string>(POLICY_FILES[0])
  const [fileContent, setFileContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [loadingFile, setLoadingFile] = useState(false)

  const loadHistory = useCallback(async () => {
    setLoading(true)
    try {
      const headers = await buildApiHeaders()
      const [snapsR, curR] = await Promise.all([
        fetch(`${API_BASE_URL}/governance/policy/snapshots?limit=100`, { headers }),
        fetch(`${API_BASE_URL}/governance/policy/current`, { headers }),
      ])
      if (snapsR.ok) setSnapshots(await snapsR.json())
      if (curR.ok) {
        const j = await curR.json()
        setCurrentSnapshot(j.snapshot_id)
      }
    } catch (e) {
      toast.error('加载 policy 快照失败')
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFile = useCallback(async (filename: string) => {
    setLoadingFile(true)
    setSelectedFile(filename)
    try {
      const headers = await buildApiHeaders()
      const r = await fetch(`${API_BASE_URL}/governance/policy/files/${filename}`, { headers })
      if (!r.ok) {
        toast.error(`读取 ${filename} 失败`)
        return
      }
      const j = await r.json()
      setFileContent(j.content)
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingFile(false)
    }
  }, [])

  useEffect(() => {
    void loadHistory()
    void loadFile(POLICY_FILES[0])
  }, [loadHistory, loadFile])

  return (
    <PageContainer title="Policy 快照与原文" description="历史 policy snapshot + 7 份 yaml 在线浏览（只读）">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Snapshot history */}
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">快照历史</h2>
              <Badge variant="secondary" className="text-xs">{snapshots.length}</Badge>
            </div>
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
              </div>
            ) : snapshots.length === 0 ? (
              <p className="text-sm text-muted-foreground">尚无快照（修改 policy 后会自动写入 .claude/policy-snapshots/）</p>
            ) : (
              <div className="space-y-2 max-h-[600px] overflow-auto">
                {snapshots.map(s => (
                  <div
                    key={s.snapshot_id}
                    className={`p-2 rounded border text-sm ${
                      s.snapshot_id === currentSnapshot ? 'border-primary bg-primary-50' : 'border-border'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs truncate" title={s.snapshot_id}>{s.snapshot_id}</span>
                      {s.snapshot_id === currentSnapshot && (
                        <Badge variant="default" className="text-xs">当前</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(s.loaded_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* File viewer */}
        <Card className="lg:col-span-2">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">Policy 原文（只读）</h2>
              <Button
                size="sm"
                variant="outline"
                onClick={() => loadFile(selectedFile)}
              >
                刷新
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              {POLICY_FILES.map(f => (
                <Button
                  key={f}
                  size="sm"
                  variant={f === selectedFile ? 'default' : 'outline'}
                  onClick={() => loadFile(f)}
                >
                  {f}
                </Button>
              ))}
            </div>
            {loadingFile ? (
              <Skeleton className="h-[500px]" />
            ) : (
              <pre className="bg-surface-2 rounded p-4 text-xs overflow-auto max-h-[600px] font-mono whitespace-pre-wrap">
                {fileContent || '— 空 —'}
              </pre>
            )}
            <p className="text-xs text-muted-foreground mt-3">
              编辑 policy 需要走 PR + 双签；改完后调 <code className="text-xs">POST /governance/policy/reload</code> 或 <code>SIGHUP</code> 重载。
            </p>
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  )
}
