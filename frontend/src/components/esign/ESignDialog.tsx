/**
 * ESignDialog - 电子签署对话框
 *
 * Demo 版：mock 签署状态流转（发起 → 等待 → 完成）
 * 真实版：接入 E签宝/法大大 SDK
 */

import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

type SignStatus = 'init' | 'creating' | 'waiting' | 'signing' | 'completed' | 'failed'

interface Signer {
  name: string
  phone: string
  role: '甲方' | '乙方' | '丙方'
}

interface ESignDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contract: {
    id: string
    title: string
    contractType?: string
  } | null
  onCompleted?: () => void
}

export function ESignDialog({ open, onOpenChange, contract, onCompleted }: ESignDialogProps) {
  const [status, setStatus] = useState<SignStatus>('init')
  const [signers, setSigners] = useState<Signer[]>([
    { name: '', phone: '', role: '甲方' },
    { name: '', phone: '', role: '乙方' },
  ])
  const [flowId, setFlowId] = useState<string>('')
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!open) {
      setStatus('init')
      setSigners([
        { name: '', phone: '', role: '甲方' },
        { name: '', phone: '', role: '乙方' },
      ])
      setFlowId('')
      setProgress(0)
    }
  }, [open])

  if (!contract) return null

  const handleAddSigner = () => {
    if (signers.length >= 3) {
      toast.error('最多支持 3 方签署')
      return
    }
    setSigners([...signers, { name: '', phone: '', role: '丙方' }])
  }

  const handleRemoveSigner = (idx: number) => {
    setSigners(signers.filter((_, i) => i !== idx))
  }

  const updateSigner = (idx: number, field: keyof Signer, value: string) => {
    const next = [...signers]
    next[idx] = { ...next[idx], [field]: value }
    setSigners(next)
  }

  const handleInitiate = async () => {
    // 验证
    for (const s of signers) {
      if (!s.name || !s.phone) {
        toast.error('请填写所有签署人信息')
        return
      }
      if (!/^1[3-9]\d{9}$/.test(s.phone)) {
        toast.error(`${s.name} 的手机号格式不正确`)
        return
      }
    }

    setStatus('creating')
    // Demo 版：mock 创建签署流程
    await new Promise(r => setTimeout(r, 1200))
    const mockFlowId = `FLOW-${Date.now()}`
    setFlowId(mockFlowId)
    setStatus('waiting')
    toast.success('签署流程已创建，签署人将收到短信通知')

    // 模拟签署进度
    let pct = 0
    const timer = setInterval(() => {
      pct += 25
      setProgress(pct)
      if (pct === 50) setStatus('signing')
      if (pct >= 100) {
        clearInterval(timer)
        setStatus('completed')
        setTimeout(() => {
          toast.success('所有签署方已完成签署！')
          onCompleted?.()
        }, 500)
      }
    }, 1500)
  }

  const statusInfo: Record<SignStatus, { label: string; color: string; icon: any }> = {
    init: { label: '填写签署人信息', color: 'text-muted-foreground', icon: icons.FileText },
    creating: { label: '正在创建签署流程...', color: 'text-blue-600', icon: icons.Clock },
    waiting: { label: '等待签署方签署', color: 'text-orange-600', icon: icons.Clock },
    signing: { label: '签署进行中', color: 'text-blue-600', icon: icons.Clock },
    completed: { label: '签署完成', color: 'text-green-600', icon: icons.CheckCircle },
    failed: { label: '签署失败', color: 'text-destructive', icon: icons.AlertTriangle },
  }

  const current = statusInfo[status]
  const StatusIcon = current.icon

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <icons.FileText className="h-5 w-5 text-primary" />
            电子签署：{contract.title}
          </DialogTitle>
          <DialogDescription>
            通过 E签宝 发起合同电子签署
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Demo 版标识 */}
          <Badge variant="outline" className="text-orange-600 border-orange-600">
            演示版 - Mock 签署流程
          </Badge>

          {/* 状态展示 */}
          <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg">
            <StatusIcon className={`h-5 w-5 ${current.color}`} />
            <span className={`text-sm font-medium ${current.color}`}>{current.label}</span>
            {flowId && (
              <span className="ml-auto text-xs font-mono text-muted-foreground">{flowId}</span>
            )}
          </div>

          {/* init: 签署人表单 */}
          {status === 'init' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium">签署方（{signers.length}）</Label>
                <Button size="sm" variant="outline" onClick={handleAddSigner} disabled={signers.length >= 3}>
                  <icons.Plus className="h-3.5 w-3.5 mr-1" />
                  添加签署方
                </Button>
              </div>

              {signers.map((s, i) => (
                <div key={i} className="p-3 border rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="secondary">{s.role}</Badge>
                    {i >= 2 && (
                      <Button size="sm" variant="ghost" onClick={() => handleRemoveSigner(i)}>
                        <icons.X className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">姓名</Label>
                      <Input
                        value={s.name}
                        onChange={e => updateSigner(i, 'name', e.target.value)}
                        placeholder="签署人姓名"
                        className="h-9"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">手机号</Label>
                      <Input
                        value={s.phone}
                        onChange={e => updateSigner(i, 'phone', e.target.value)}
                        placeholder="13800138000"
                        className="h-9"
                      />
                    </div>
                  </div>
                </div>
              ))}

              <Button onClick={handleInitiate} className="w-full">
                <icons.FileText className="h-4 w-4 mr-2" />
                发起签署
              </Button>
            </div>
          )}

          {/* waiting / signing: 进度条 */}
          {(status === 'waiting' || status === 'signing') && (
            <div className="space-y-3">
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">签署进度</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
              <div className="text-sm text-muted-foreground">
                签署方已通过短信收到签署链接，请等待对方完成签署。
              </div>
              <div className="space-y-1">
                {signers.map((s, i) => (
                  <div key={i} className="flex items-center justify-between text-xs p-2 border rounded">
                    <span>{s.role}：{s.name}（{s.phone}）</span>
                    {progress >= (i + 1) * (100 / signers.length) ? (
                      <icons.CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <icons.Clock className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* completed: 成功 */}
          {status === 'completed' && (
            <div className="flex flex-col items-center gap-3 py-4">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
                <icons.CheckCircle className="h-10 w-10 text-green-600" />
              </div>
              <p className="font-medium text-green-700">签署完成</p>
              <p className="text-sm text-muted-foreground text-center">
                所有签署方已完成签署，<br />合同已生效并存档
              </p>
              <Button onClick={() => onOpenChange(false)} className="w-full">
                关闭
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
