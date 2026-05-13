import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'

export default function AdminBasic() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [basic, setBasic] = useState({
    site_name: 'AI 智能助手智能平台',
    site_description: '企业级AI法律服务平台',
  })

  useEffect(() => {
    void (async () => {
      try {
        const config = await adminApi.getSystemConfig()
        if (config?.basic) setBasic(prev => ({ ...prev, ...config.basic }))
      } catch { /* use defaults */ }
      setLoading(false)
    })()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.updateSystemConfig({ basic })
      toast.success('基础配置已保存')
    } catch (e: any) {
      toast.error(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <PageContainer title="平台基础"><Skeleton className="h-64 rounded-xl" /></PageContainer>
  }

  return (
    <PageContainer title="平台基础" description="组织与平台展示信息">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">平台信息</CardTitle>
              <CardDescription>设置对外展示的平台名称和描述</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">系统级 · 影响所有用户</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>平台名称</Label>
            <Input value={basic.site_name} onChange={e => setBasic({ ...basic, site_name: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label>平台描述</Label>
            <Input value={basic.site_description} onChange={e => setBasic({ ...basic, site_description: e.target.value })} />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">修改后立即生效，服务重启后将重置为默认值</p>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? '保存中...' : '保存配置'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
