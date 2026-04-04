import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { adminApi } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'

export default function AdminIntegrations() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [oauth, setOauth] = useState({ wechat_app_id: '', wechat_app_secret: '', alipay_app_id: '', alipay_app_secret: '' })
  const [storage, setStorage] = useState({ minio_endpoint: 'localhost:9000', minio_bucket: 'ailegal', minio_access_key: '', minio_secret_key: '' })
  const [sms, setSms] = useState({ aliyun_access_key_id: '', aliyun_access_key_secret: '', aliyun_sms_sign_name: '', aliyun_sms_template_verify: '', aliyun_sms_template_login: '', aliyun_sms_template_reset: '' })
  const [email, setEmail] = useState({ aliyun_email_account: '', aliyun_email_alias: '安心法务' })

  useEffect(() => {
    void (async () => {
      try {
        const config = await adminApi.getSystemConfig()
        if (config?.oauth) setOauth(prev => ({ ...prev, ...config.oauth }))
        if (config?.storage) setStorage(prev => ({ ...prev, ...config.storage }))
        if (config?.sms) setSms(prev => ({ ...prev, ...config.sms }))
        if (config?.email) setEmail(prev => ({ ...prev, ...config.email }))
      } catch { /* defaults */ }
      setLoading(false)
    })()
  }, [])

  const handleSave = async (section: string, data: any) => {
    setSaving(true)
    try {
      await adminApi.updateSystemConfig({ [section]: data })
      toast.success('配置已保存')
    } catch (e: any) { toast.error(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  if (loading) {
    return <PageContainer title="服务集成"><Skeleton className="h-96 rounded-xl" /></PageContainer>
  }

  return (
    <PageContainer title="服务集成" subtitle="OAuth 登录、对象存储、短信和邮件服务">
      <Tabs defaultValue="oauth" className="space-y-4">
        <TabsList>
          <TabsTrigger value="oauth" className="gap-1.5"><icons.Globe className="w-3.5 h-3.5" />OAuth 登录</TabsTrigger>
          <TabsTrigger value="storage" className="gap-1.5"><icons.Database className="w-3.5 h-3.5" />对象存储</TabsTrigger>
          <TabsTrigger value="sms" className="gap-1.5"><icons.Phone className="w-3.5 h-3.5" />短信服务</TabsTrigger>
          <TabsTrigger value="email" className="gap-1.5"><icons.Mail className="w-3.5 h-3.5" />邮件服务</TabsTrigger>
        </TabsList>

        <TabsContent value="oauth">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">OAuth 登录配置</CardTitle>
              <CardDescription>微信和支付宝第三方登录</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold mb-3">微信登录</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>App ID</Label><Input value={oauth.wechat_app_id} onChange={e => setOauth({ ...oauth, wechat_app_id: e.target.value })} placeholder="wx..." /></div>
                  <div className="space-y-2"><Label>App Secret</Label><Input type="password" value={oauth.wechat_app_secret} onChange={e => setOauth({ ...oauth, wechat_app_secret: e.target.value })} /></div>
                </div>
              </div>
              <Separator />
              <div>
                <h4 className="text-sm font-semibold mb-3">支付宝登录</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>App ID</Label><Input value={oauth.alipay_app_id} onChange={e => setOauth({ ...oauth, alipay_app_id: e.target.value })} /></div>
                  <div className="space-y-2"><Label>App Secret</Label><Input type="password" value={oauth.alipay_app_secret} onChange={e => setOauth({ ...oauth, alipay_app_secret: e.target.value })} /></div>
                </div>
              </div>
              <Separator />
              <div className="flex justify-end"><Button onClick={() => handleSave('oauth', oauth)} disabled={saving}>{saving ? '保存中...' : '保存'}</Button></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="storage">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">MinIO 对象存储</CardTitle>
              <CardDescription>文档和附件的存储服务</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Endpoint</Label><Input value={storage.minio_endpoint} onChange={e => setStorage({ ...storage, minio_endpoint: e.target.value })} /></div>
                <div className="space-y-2"><Label>Bucket</Label><Input value={storage.minio_bucket} onChange={e => setStorage({ ...storage, minio_bucket: e.target.value })} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Access Key</Label><Input type="password" value={storage.minio_access_key} onChange={e => setStorage({ ...storage, minio_access_key: e.target.value })} /></div>
                <div className="space-y-2"><Label>Secret Key</Label><Input type="password" value={storage.minio_secret_key} onChange={e => setStorage({ ...storage, minio_secret_key: e.target.value })} /></div>
              </div>
              <Separator />
              <div className="flex justify-end"><Button onClick={() => handleSave('storage', storage)} disabled={saving}>{saving ? '保存中...' : '保存'}</Button></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sms">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">阿里云短信服务</CardTitle>
              <CardDescription>短信验证码发送</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>AccessKey ID</Label><Input value={sms.aliyun_access_key_id} onChange={e => setSms({ ...sms, aliyun_access_key_id: e.target.value })} /></div>
                <div className="space-y-2"><Label>AccessKey Secret</Label><Input type="password" value={sms.aliyun_access_key_secret} onChange={e => setSms({ ...sms, aliyun_access_key_secret: e.target.value })} /></div>
              </div>
              <div className="space-y-2"><Label>短信签名</Label><Input value={sms.aliyun_sms_sign_name} onChange={e => setSms({ ...sms, aliyun_sms_sign_name: e.target.value })} placeholder="安心法务" /></div>
              <Separator />
              <p className="text-sm font-medium">模板 Code</p>
              <div className="space-y-3">
                <div className="space-y-2"><Label>注册验证码</Label><Input value={sms.aliyun_sms_template_verify} onChange={e => setSms({ ...sms, aliyun_sms_template_verify: e.target.value })} placeholder="SMS_xxxxxx" /></div>
                <div className="space-y-2"><Label>登录验证码</Label><Input value={sms.aliyun_sms_template_login} onChange={e => setSms({ ...sms, aliyun_sms_template_login: e.target.value })} placeholder="SMS_xxxxxx" /></div>
                <div className="space-y-2"><Label>密码重置</Label><Input value={sms.aliyun_sms_template_reset} onChange={e => setSms({ ...sms, aliyun_sms_template_reset: e.target.value })} placeholder="SMS_xxxxxx" /></div>
              </div>
              <div className="flex justify-end"><Button onClick={() => handleSave('sms', sms)} disabled={saving}>{saving ? '保存中...' : '保存'}</Button></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">阿里云邮件推送</CardTitle>
              <CardDescription>邮箱验证码和通知邮件</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2"><Label>发信地址</Label><Input value={email.aliyun_email_account} onChange={e => setEmail({ ...email, aliyun_email_account: e.target.value })} placeholder="noreply@mail.anxinfawu.com" /></div>
              <div className="space-y-2"><Label>发件人昵称</Label><Input value={email.aliyun_email_alias} onChange={e => setEmail({ ...email, aliyun_email_alias: e.target.value })} /></div>
              <div className="flex justify-end"><Button onClick={() => handleSave('email', email)} disabled={saving}>{saving ? '保存中...' : '保存'}</Button></div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
