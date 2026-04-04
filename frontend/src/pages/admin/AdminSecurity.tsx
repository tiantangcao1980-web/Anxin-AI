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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function AdminSecurity() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [security, setSecurity] = useState({
    email_verify_enabled: 'false',
    sms_enabled: 'false',
    oauth_wechat_enabled: 'false',
    oauth_alipay_enabled: 'false',
    jwt_expiry_hours: '24',
    rate_limit_per_minute: '60',
    password_min_length: '8',
    require_special_char: 'true',
  })

  useEffect(() => {
    ;(async () => {
      try {
        const config = await adminApi.getSystemConfig()
        if (config?.security) setSecurity(prev => ({ ...prev, ...config.security }))
      } catch { /* defaults */ }
      setLoading(false)
    })()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.updateSystemConfig({ security })
      toast.success('安全策略已保存')
    } catch (e: any) { toast.error(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  if (loading) {
    return <PageContainer title="安全策略"><Skeleton className="h-96 rounded-xl" /></PageContainer>
  }

  const toggleItems = [
    { key: 'email_verify_enabled', label: '邮箱验证', desc: '注册后需验证邮箱才能登录' },
    { key: 'sms_enabled', label: '短信服务', desc: '短信验证码（需配置阿里云）' },
    { key: 'oauth_wechat_enabled', label: '微信登录', desc: '需配置微信开放平台凭证' },
    { key: 'oauth_alipay_enabled', label: '支付宝登录', desc: '需配置支付宝开放平台凭证' },
  ]

  return (
    <PageContainer title="安全策略" subtitle="认证开关、JWT、速率限制和密码策略">
      {/* 功能开关 */}
      <Card className="mb-6">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">认证功能开关</CardTitle>
              <CardDescription>控制各认证方式的启用/关闭</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">系统级</Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {toggleItems.map(item => (
              <div key={item.key} className="flex items-center justify-between p-3 rounded-lg border">
                <div>
                  <div className="text-sm font-medium">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.desc}</div>
                </div>
                <Select
                  value={(security as any)[item.key] || 'false'}
                  onValueChange={v => setSecurity({ ...security, [item.key]: v })}
                >
                  <SelectTrigger className="w-20"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">开启</SelectItem>
                    <SelectItem value="false">关闭</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 安全策略 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">安全策略</CardTitle>
          <CardDescription>JWT 有效期、速率限制和密码强度要求</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>JWT 有效期（小时）</Label>
              <Input type="number" value={security.jwt_expiry_hours} onChange={e => setSecurity({ ...security, jwt_expiry_hours: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>每分钟速率限制</Label>
              <Input type="number" value={security.rate_limit_per_minute} onChange={e => setSecurity({ ...security, rate_limit_per_minute: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>密码最小长度</Label>
              <Input type="number" value={security.password_min_length} onChange={e => setSecurity({ ...security, password_min_length: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label>要求特殊字符</Label>
              <Select value={security.require_special_char} onValueChange={v => setSecurity({ ...security, require_special_char: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">是</SelectItem>
                  <SelectItem value="false">否</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">修改后立即生效，服务重启后将重置</p>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? '保存中...' : '保存安全策略'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
