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
import { McpSettingsPanel } from '@/pages/Settings'

export default function AdminIntegrations() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [oauth, setOauth] = useState({ wechat_app_id: '', wechat_app_secret: '', alipay_app_id: '', alipay_app_secret: '' })
  const [storage, setStorage] = useState({ minio_endpoint: 'localhost:9000', minio_bucket: 'ailegal', minio_access_key: '', minio_secret_key: '' })
  const [sms, setSms] = useState({ aliyun_access_key_id: '', aliyun_access_key_secret: '', aliyun_sms_sign_name: '', aliyun_sms_template_verify: '', aliyun_sms_template_login: '', aliyun_sms_template_reset: '' })
  const [email, setEmail] = useState({ aliyun_email_account: '', aliyun_email_alias: '安心智能助手' })
  // E签宝 配置
  const [esign, setEsign] = useState({
    app_id: '', app_secret: '', app_secret_masked: '', has_app_secret: false,
    api_url: 'https://smlopenapi.esign.cn',
    webhook_secret: '', webhook_secret_masked: '', has_webhook_secret: false,
    official_webhook_enabled: false,
  })
  // 法大大 配置
  const [fadada, setFadada] = useState({
    app_id: '', app_secret: '', app_secret_masked: '', has_app_secret: false,
    api_url: 'https://api.fadada.com/api/v5',
  })
  // 微信支付 配置
  const [wechatPay, setWechatPay] = useState({
    app_id: '', mch_id: '', api_base_url: 'https://api.mch.weixin.qq.com',
    merchant_private_key: '', has_private_key: false,
    api_v3_key: '', has_api_v3_key: false,
    webhook_secret: '',
    official_webhook_enabled: false,
  })
  // 支付宝 配置
  const [alipay, setAlipay] = useState({
    app_id: '', gateway_url: 'https://openapi.alipay.com/gateway.do',
    private_key: '', has_private_key: false,
    public_key: '', has_public_key: false,
    webhook_secret: '',
    official_webhook_enabled: false,
  })

  useEffect(() => {
    void (async () => {
      try {
        const config = await adminApi.getSystemConfig()
        if (config?.oauth) setOauth(prev => ({ ...prev, ...config.oauth }))
        if (config?.storage) setStorage(prev => ({ ...prev, ...config.storage }))
        if (config?.sms) setSms(prev => ({ ...prev, ...config.sms }))
        if (config?.email) setEmail(prev => ({ ...prev, ...config.email }))
        if (config?.esign) setEsign(prev => ({ ...prev, ...config.esign }))
        if (config?.fadada) setFadada(prev => ({ ...prev, ...config.fadada }))
        if (config?.wechat_pay) setWechatPay(prev => ({ ...prev, ...config.wechat_pay }))
        if (config?.alipay) setAlipay(prev => ({ ...prev, ...config.alipay }))
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

  // 电签/支付 专用保存（敏感字段空字符串 = 保留原值，由后端处理）
  const handleSaveSecure = async (section: string, data: any) => {
    setSaving(true)
    try {
      // 过滤掉 _masked / has_ 只读字段，只发送真正要更新的字段
      const payload: Record<string, any> = {}
      for (const [k, v] of Object.entries(data)) {
        if (k.endsWith('_masked') || k.startsWith('has_')) continue
        payload[k] = v
      }
      await adminApi.updateSystemConfig({ [section]: payload })
      toast.success('配置已保存，请重启后端使敏感字段生效')
      // 重新拉一次配置，更新脱敏显示
      const config = await adminApi.getSystemConfig()
      if (config?.esign) setEsign(prev => ({ ...prev, ...config.esign, app_secret: '', webhook_secret: '' }))
      if (config?.fadada) setFadada(prev => ({ ...prev, ...config.fadada, app_secret: '' }))
      if (config?.wechat_pay) setWechatPay(prev => ({ ...prev, ...config.wechat_pay, merchant_private_key: '', api_v3_key: '', webhook_secret: '' }))
      if (config?.alipay) setAlipay(prev => ({ ...prev, ...config.alipay, private_key: '', public_key: '', webhook_secret: '' }))
    } catch (e: any) { toast.error(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  if (loading) {
    return <PageContainer title="系统集成"><Skeleton className="h-96 rounded-xl" /></PageContainer>
  }

  return (
    <PageContainer title="系统集成" description="组织级 OAuth 登录、对象存储、短信、邮件和 MCP/工具服务治理">
      <Tabs defaultValue="oauth" className="space-y-4">
        <TabsList>
          <TabsTrigger value="oauth" className="gap-1.5"><icons.Globe className="w-3.5 h-3.5" />OAuth 登录</TabsTrigger>
          <TabsTrigger value="esign" className="gap-1.5"><icons.FileText className="w-3.5 h-3.5" />电签服务</TabsTrigger>
          <TabsTrigger value="payment" className="gap-1.5"><icons.CreditCard className="w-3.5 h-3.5" />支付渠道</TabsTrigger>
          <TabsTrigger value="storage" className="gap-1.5"><icons.Database className="w-3.5 h-3.5" />对象存储</TabsTrigger>
          <TabsTrigger value="sms" className="gap-1.5"><icons.Phone className="w-3.5 h-3.5" />短信服务</TabsTrigger>
          <TabsTrigger value="email" className="gap-1.5"><icons.Mail className="w-3.5 h-3.5" />邮件服务</TabsTrigger>
          <TabsTrigger value="mcp" className="gap-1.5"><icons.Server className="w-3.5 h-3.5" />MCP / 工具</TabsTrigger>
        </TabsList>

        <TabsContent value="oauth">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">OAuth 登录配置</CardTitle>
              <CardDescription>微信和支付宝第三方登录</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="text-sm font-medium mb-3">微信登录</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>App ID</Label><Input value={oauth.wechat_app_id} onChange={e => setOauth({ ...oauth, wechat_app_id: e.target.value })} placeholder="wx..." /></div>
                  <div className="space-y-2"><Label>App Secret</Label><Input type="password" value={oauth.wechat_app_secret} onChange={e => setOauth({ ...oauth, wechat_app_secret: e.target.value })} /></div>
                </div>
              </div>
              <Separator />
              <div>
                <h4 className="text-sm font-medium mb-3">支付宝登录</h4>
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

        <TabsContent value="esign">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">电签服务配置</CardTitle>
              <CardDescription>E签宝 / 法大大 电子签名集成（敏感字段留空=保留原值）</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
                  E签宝（推荐）
                </h4>
                <p className="text-xs text-muted-foreground mb-3">
                  申请地址：<a href="https://open.esign.cn/" target="_blank" rel="noopener" className="text-primary underline">https://open.esign.cn/</a>
                  {' · '}
                  文档：<a href="https://open.esign.cn/doc" target="_blank" rel="noopener" className="text-primary underline">OpenAPI 文档</a>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input value={esign.app_id} onChange={e => setEsign({ ...esign, app_id: e.target.value })} placeholder="e签宝应用 App ID" />
                  </div>
                  <div className="space-y-2">
                    <Label>App Secret{esign.has_app_secret && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <Input
                      type="password"
                      value={esign.app_secret}
                      onChange={e => setEsign({ ...esign, app_secret: e.target.value })}
                      placeholder={esign.has_app_secret ? esign.app_secret_masked + '（留空=保留原值）' : 'App Secret'}
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>API 网关</Label>
                    <Input value={esign.api_url} onChange={e => setEsign({ ...esign, api_url: e.target.value })} />
                    <p className="text-xs text-muted-foreground">生产：smlopenapi.esign.cn；沙箱：smlopenapi-sandbox.esign.cn</p>
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>Webhook 密钥{esign.has_webhook_secret && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <Input
                      type="password"
                      value={esign.webhook_secret}
                      onChange={e => setEsign({ ...esign, webhook_secret: e.target.value })}
                      placeholder={esign.has_webhook_secret ? esign.webhook_secret_masked + '（留空=保留原值）' : '用于签名校验的 Webhook 密钥'}
                    />
                    <p className="text-xs text-muted-foreground">
                      回调地址：https://www.anxinai.com/api/v1/esign/webhook
                    </p>
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    <input
                      type="checkbox"
                      id="esign-official"
                      checked={esign.official_webhook_enabled}
                      onChange={e => setEsign({ ...esign, official_webhook_enabled: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <Label htmlFor="esign-official" className="font-normal cursor-pointer">
                      启用官方 Webhook 签名验证（生产环境必须勾选）
                    </Label>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-orange-500" />
                  法大大（备选）
                </h4>
                <p className="text-xs text-muted-foreground mb-3">
                  申请地址：<a href="https://www.fadada.com/" target="_blank" rel="noopener" className="text-primary underline">https://www.fadada.com/</a>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input value={fadada.app_id} onChange={e => setFadada({ ...fadada, app_id: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>App Secret{fadada.has_app_secret && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <Input
                      type="password"
                      value={fadada.app_secret}
                      onChange={e => setFadada({ ...fadada, app_secret: e.target.value })}
                      placeholder={fadada.has_app_secret ? fadada.app_secret_masked + '（留空=保留原值）' : 'App Secret'}
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>API 网关</Label>
                    <Input value={fadada.api_url} onChange={e => setFadada({ ...fadada, api_url: e.target.value })} />
                  </div>
                </div>
              </div>

              <Separator />
              <div className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">提示：敏感字段（密钥、webhook 密钥）留空表示保留原值</p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => handleSaveSecure('fadada', fadada)} disabled={saving}>保存法大大</Button>
                  <Button onClick={() => handleSaveSecure('esign', esign)} disabled={saving}>{saving ? '保存中...' : '保存 E签宝'}</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="payment">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">支付渠道配置</CardTitle>
              <CardDescription>微信支付 / 支付宝 商户密钥（敏感字段留空=保留原值）</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                  微信支付 V3
                </h4>
                <p className="text-xs text-muted-foreground mb-3">
                  商户平台：<a href="https://pay.weixin.qq.com/" target="_blank" rel="noopener" className="text-primary underline">https://pay.weixin.qq.com/</a>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input value={wechatPay.app_id} onChange={e => setWechatPay({ ...wechatPay, app_id: e.target.value })} placeholder="wx..." />
                  </div>
                  <div className="space-y-2">
                    <Label>商户号 Mch ID</Label>
                    <Input value={wechatPay.mch_id} onChange={e => setWechatPay({ ...wechatPay, mch_id: e.target.value })} />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>商户私钥 PEM{wechatPay.has_private_key && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <textarea
                      className="w-full min-h-[100px] px-3 py-2 text-sm rounded-md border bg-background font-mono"
                      value={wechatPay.merchant_private_key}
                      onChange={e => setWechatPay({ ...wechatPay, merchant_private_key: e.target.value })}
                      placeholder={wechatPay.has_private_key ? '已配置（留空=保留原值）' : '-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>API V3 密钥{wechatPay.has_api_v3_key && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <Input
                      type="password"
                      value={wechatPay.api_v3_key}
                      onChange={e => setWechatPay({ ...wechatPay, api_v3_key: e.target.value })}
                      placeholder={wechatPay.has_api_v3_key ? '已配置（留空=保留原值）' : '32 位密钥'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Webhook 密钥</Label>
                    <Input
                      type="password"
                      value={wechatPay.webhook_secret}
                      onChange={e => setWechatPay({ ...wechatPay, webhook_secret: e.target.value })}
                      placeholder="（可选）"
                    />
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    <input
                      type="checkbox"
                      id="wechat-official"
                      checked={wechatPay.official_webhook_enabled}
                      onChange={e => setWechatPay({ ...wechatPay, official_webhook_enabled: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <Label htmlFor="wechat-official" className="font-normal cursor-pointer">
                      启用官方 Webhook 签名验证（生产必须勾选）
                    </Label>
                  </div>
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
                  支付宝
                </h4>
                <p className="text-xs text-muted-foreground mb-3">
                  开放平台：<a href="https://open.alipay.com/" target="_blank" rel="noopener" className="text-primary underline">https://open.alipay.com/</a>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input value={alipay.app_id} onChange={e => setAlipay({ ...alipay, app_id: e.target.value })} />
                  </div>
                  <div className="space-y-2">
                    <Label>网关 URL</Label>
                    <Input value={alipay.gateway_url} onChange={e => setAlipay({ ...alipay, gateway_url: e.target.value })} />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>应用私钥 PEM{alipay.has_private_key && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <textarea
                      className="w-full min-h-[100px] px-3 py-2 text-sm rounded-md border bg-background font-mono"
                      value={alipay.private_key}
                      onChange={e => setAlipay({ ...alipay, private_key: e.target.value })}
                      placeholder={alipay.has_private_key ? '已配置（留空=保留原值）' : '-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----'}
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label>支付宝公钥 PEM{alipay.has_public_key && <span className="ml-2 text-xs text-green-600">✓ 已配置</span>}</Label>
                    <textarea
                      className="w-full min-h-[100px] px-3 py-2 text-sm rounded-md border bg-background font-mono"
                      value={alipay.public_key}
                      onChange={e => setAlipay({ ...alipay, public_key: e.target.value })}
                      placeholder={alipay.has_public_key ? '已配置（留空=保留原值）' : '-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----'}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Webhook 密钥</Label>
                    <Input
                      type="password"
                      value={alipay.webhook_secret}
                      onChange={e => setAlipay({ ...alipay, webhook_secret: e.target.value })}
                      placeholder="（可选）"
                    />
                  </div>
                  <div className="flex items-center gap-2 col-span-2">
                    <input
                      type="checkbox"
                      id="alipay-official"
                      checked={alipay.official_webhook_enabled}
                      onChange={e => setAlipay({ ...alipay, official_webhook_enabled: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <Label htmlFor="alipay-official" className="font-normal cursor-pointer">
                      启用官方 Webhook 签名验证（生产必须勾选）
                    </Label>
                  </div>
                </div>
              </div>

              <Separator />
              <div className="flex justify-between items-center">
                <p className="text-xs text-muted-foreground">提示：敏感字段（私钥、API 密钥）留空表示保留原值</p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => handleSaveSecure('alipay', alipay)} disabled={saving}>保存支付宝</Button>
                  <Button onClick={() => handleSaveSecure('wechat_pay', wechatPay)} disabled={saving}>{saving ? '保存中...' : '保存微信支付'}</Button>
                </div>
              </div>
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
              <div className="space-y-2"><Label>短信签名</Label><Input value={sms.aliyun_sms_sign_name} onChange={e => setSms({ ...sms, aliyun_sms_sign_name: e.target.value })} placeholder="安心智能助手" /></div>
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
              <div className="space-y-2"><Label>发信地址</Label><Input value={email.aliyun_email_account} onChange={e => setEmail({ ...email, aliyun_email_account: e.target.value })} placeholder="noreply@mail.anxinai.com" /></div>
              <div className="space-y-2"><Label>发件人昵称</Label><Input value={email.aliyun_email_alias} onChange={e => setEmail({ ...email, aliyun_email_alias: e.target.value })} /></div>
              <div className="flex justify-end"><Button onClick={() => handleSave('email', email)} disabled={saving}>{saving ? '保存中...' : '保存'}</Button></div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="mcp">
          <McpSettingsPanel scope="governance" />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
