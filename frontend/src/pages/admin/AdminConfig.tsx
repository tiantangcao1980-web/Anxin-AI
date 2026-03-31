import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface ConfigSection {
  [key: string]: any
}

export default function AdminConfig() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Config state per tab
  const [basic, setBasic] = useState<ConfigSection>({
    site_name: 'AI法务智能平台',
    site_description: '企业级AI法律服务平台',
  })
  const [llm, setLlm] = useState<ConfigSection>({
    provider: 'openai',
    api_key: '',
    models: 'gpt-4,gpt-3.5-turbo',
  })
  const [oauth, setOauth] = useState<ConfigSection>({
    wechat_app_id: '',
    wechat_app_secret: '',
    alipay_app_id: '',
    alipay_app_secret: '',
  })
  const [storage, setStorage] = useState<ConfigSection>({
    minio_endpoint: 'localhost:9000',
    minio_bucket: 'ailegal',
    minio_access_key: '',
    minio_secret_key: '',
  })
  const [security, setSecurity] = useState<ConfigSection>({
    jwt_expiry_hours: '24',
    rate_limit_per_minute: '60',
    password_min_length: '8',
    require_special_char: 'true',
  })
  const [sms, setSms] = useState<ConfigSection>({
    aliyun_access_key_id: '',
    aliyun_access_key_secret: '',
    aliyun_sms_sign_name: '',
    aliyun_sms_template_verify: '',
    aliyun_sms_template_login: '',
    aliyun_sms_template_reset: '',
  })
  const [email, setEmailConfig] = useState<ConfigSection>({
    aliyun_email_account: '',
    aliyun_email_alias: '安心法务',
  })

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const config = await adminApi.getSystemConfig()
      if (config) {
        if (config.basic) setBasic({ ...basic, ...config.basic })
        if (config.llm) setLlm({ ...llm, ...config.llm })
        if (config.oauth) setOauth({ ...oauth, ...config.oauth })
        if (config.storage) setStorage({ ...storage, ...config.storage })
        if (config.security) setSecurity({ ...security, ...config.security })
        if (config.sms) setSms({ ...sms, ...config.sms })
        if (config.email) setEmailConfig({ ...email, ...config.email })
      }
    } catch {
      // Use defaults
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (section: string, data: ConfigSection) => {
    setSaving(true)
    try {
      await adminApi.updateSystemConfig({ [section]: data })
      toast.success('配置已保存')
    } catch (e: any) {
      toast.error(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const maskValue = (val: string) => {
    if (!val || val.length < 8) return val
    return val.slice(0, 4) + '****' + val.slice(-4)
  }

  if (loading) {
    return (
      <PageContainer showHeader={false}>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[500px] rounded-xl" />
      </PageContainer>
    )
  }

  return (
    <PageContainer
      title="系统配置"
      description="管理平台基础设置、LLM模型、OAuth认证和安全策略"
    >
      <Tabs defaultValue="basic" className="space-y-4">
        <TabsList>
          <TabsTrigger value="basic" className="gap-2">
            <icons.Settings className="w-4 h-4" />
            基础配置
          </TabsTrigger>
          <TabsTrigger value="llm" className="gap-2">
            <icons.Cpu className="w-4 h-4" />
            LLM 配置
          </TabsTrigger>
          <TabsTrigger value="oauth" className="gap-2">
            <icons.Globe className="w-4 h-4" />
            OAuth 配置
          </TabsTrigger>
          <TabsTrigger value="storage" className="gap-2">
            <icons.Database className="w-4 h-4" />
            存储配置
          </TabsTrigger>
          <TabsTrigger value="sms" className="gap-2">
            <icons.Smartphone className="w-4 h-4" />
            短信服务
          </TabsTrigger>
          <TabsTrigger value="email" className="gap-2">
            <icons.Mail className="w-4 h-4" />
            邮件服务
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-2">
            <icons.Lock className="w-4 h-4" />
            安全配置
          </TabsTrigger>
        </TabsList>

        {/* 基础配置 */}
        <TabsContent value="basic">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">基础配置</CardTitle>
              <CardDescription>设置平台名称和基本信息</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>平台名称</Label>
                <Input
                  value={basic.site_name}
                  onChange={(e) => setBasic({ ...basic, site_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>平台描述</Label>
                <Input
                  value={basic.site_description}
                  onChange={(e) =>
                    setBasic({ ...basic, site_description: e.target.value })
                  }
                />
              </div>
              <Separator />
              <div className="flex justify-end">
                <Button onClick={() => handleSave('basic', basic)} disabled={saving}>
                  {saving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* LLM 配置 */}
        <TabsContent value="llm">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">LLM 模型配置</CardTitle>
              <CardDescription>配置大语言模型的提供商和 API 密钥</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>模型提供商</Label>
                <Select
                  value={llm.provider}
                  onValueChange={(v) => setLlm({ ...llm, provider: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI</SelectItem>
                    <SelectItem value="azure">Azure OpenAI</SelectItem>
                    <SelectItem value="anthropic">Anthropic</SelectItem>
                    <SelectItem value="qwen">通义千问</SelectItem>
                    <SelectItem value="deepseek">DeepSeek</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>API Key</Label>
                <Input
                  type="password"
                  value={llm.api_key}
                  onChange={(e) => setLlm({ ...llm, api_key: e.target.value })}
                  placeholder="sk-..."
                />
                {llm.api_key && (
                  <p className="text-xs text-muted-foreground">
                    当前值：{maskValue(llm.api_key)}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label>可用模型（逗号分隔）</Label>
                <Input
                  value={llm.models}
                  onChange={(e) => setLlm({ ...llm, models: e.target.value })}
                  placeholder="gpt-4,gpt-3.5-turbo"
                />
              </div>
              <Separator />
              <div className="flex justify-end">
                <Button onClick={() => handleSave('llm', llm)} disabled={saving}>
                  {saving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* OAuth 配置 */}
        <TabsContent value="oauth">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">OAuth 登录配置</CardTitle>
              <CardDescription>
                配置微信和支付宝第三方登录。填入 AppID 和密钥后自动启用。
                <a href="https://open.weixin.qq.com" target="_blank" rel="noopener" className="text-primary ml-1">微信开放平台</a>
                {' | '}
                <a href="https://open.alipay.com" target="_blank" rel="noopener" className="text-primary">支付宝开放平台</a>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <icons.Globe className="w-4 h-4" />
                  微信登录
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input
                      value={oauth.wechat_app_id}
                      onChange={(e) =>
                        setOauth({ ...oauth, wechat_app_id: e.target.value })
                      }
                      placeholder="wx..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>App Secret</Label>
                    <Input
                      type="password"
                      value={oauth.wechat_app_secret}
                      onChange={(e) =>
                        setOauth({ ...oauth, wechat_app_secret: e.target.value })
                      }
                    />
                  </div>
                </div>
              </div>
              <Separator />
              <div>
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <icons.Globe className="w-4 h-4" />
                  支付宝登录
                </h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>App ID</Label>
                    <Input
                      value={oauth.alipay_app_id}
                      onChange={(e) =>
                        setOauth({ ...oauth, alipay_app_id: e.target.value })
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>App Secret</Label>
                    <Input
                      type="password"
                      value={oauth.alipay_app_secret}
                      onChange={(e) =>
                        setOauth({ ...oauth, alipay_app_secret: e.target.value })
                      }
                    />
                  </div>
                </div>
              </div>
              <Separator />
              <div className="flex justify-end">
                <Button onClick={() => handleSave('oauth', oauth)} disabled={saving}>
                  {saving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 短信服务配置 */}
        <TabsContent value="sms">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">阿里云短信服务 (Dysmsapi)</CardTitle>
              <CardDescription>
                配置短信验证码发送服务。
                <a href="https://dysms.console.aliyun.com" target="_blank" rel="noopener" className="text-primary ml-1">控制台</a>
                {' | '}
                <a href="https://help.aliyun.com/document_detail/419273.html" target="_blank" rel="noopener" className="text-primary">文档</a>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Separator />
              <p className="text-xs text-muted-foreground">AccessKey 与邮件服务共用，在基础配置中统一设置。</p>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>AccessKey ID</Label>
                  <Input value={sms.aliyun_access_key_id} onChange={(e) => setSms({ ...sms, aliyun_access_key_id: e.target.value })} placeholder="LTAI5t..." />
                </div>
                <div className="space-y-2">
                  <Label>AccessKey Secret</Label>
                  <Input type="password" value={sms.aliyun_access_key_secret} onChange={(e) => setSms({ ...sms, aliyun_access_key_secret: e.target.value })} placeholder="******" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>短信签名</Label>
                <Input value={sms.aliyun_sms_sign_name} onChange={(e) => setSms({ ...sms, aliyun_sms_sign_name: e.target.value })} placeholder="安心法务" />
                <p className="text-xs text-muted-foreground">需在阿里云控制台申请并审核通过</p>
              </div>
              <Separator />
              <p className="text-sm font-medium">模板 Code（在阿里云控制台创建模板后获取）</p>
              <div className="grid grid-cols-1 gap-3">
                <div className="space-y-2">
                  <Label>注册验证码模板</Label>
                  <Input value={sms.aliyun_sms_template_verify} onChange={(e) => setSms({ ...sms, aliyun_sms_template_verify: e.target.value })} placeholder="SMS_xxxxxx" />
                </div>
                <div className="space-y-2">
                  <Label>登录验证码模板</Label>
                  <Input value={sms.aliyun_sms_template_login} onChange={(e) => setSms({ ...sms, aliyun_sms_template_login: e.target.value })} placeholder="SMS_xxxxxx" />
                </div>
                <div className="space-y-2">
                  <Label>密码重置模板</Label>
                  <Input value={sms.aliyun_sms_template_reset} onChange={(e) => setSms({ ...sms, aliyun_sms_template_reset: e.target.value })} placeholder="SMS_xxxxxx" />
                </div>
              </div>
              <div className="pt-2">
                <Button onClick={() => handleSave('sms', sms)} disabled={saving}>
                  {saving ? '保存中...' : '保存短信配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 邮件服务配置 */}
        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">阿里云邮件推送 (DirectMail)</CardTitle>
              <CardDescription>
                配置邮箱验证码和通知邮件发送服务。
                <a href="https://dm.console.aliyun.com" target="_blank" rel="noopener" className="text-primary ml-1">控制台</a>
                {' | '}
                <a href="https://help.aliyun.com/document_detail/29444.html" target="_blank" rel="noopener" className="text-primary">文档</a>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-muted-foreground">AccessKey 与短信服务共用。</p>
              <div className="space-y-2">
                <Label>发信地址 (AccountName)</Label>
                <Input value={email.aliyun_email_account} onChange={(e) => setEmailConfig({ ...email, aliyun_email_account: e.target.value })} placeholder="noreply@mail.anxinfawu.com" />
                <p className="text-xs text-muted-foreground">需在阿里云 DirectMail 控制台创建并验证域名</p>
              </div>
              <div className="space-y-2">
                <Label>发件人昵称</Label>
                <Input value={email.aliyun_email_alias} onChange={(e) => setEmailConfig({ ...email, aliyun_email_alias: e.target.value })} placeholder="安心法务" />
              </div>
              <div className="pt-2">
                <Button onClick={() => handleSave('email', email)} disabled={saving}>
                  {saving ? '保存中...' : '保存邮件配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 存储配置 */}
        <TabsContent value="storage">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">存储配置</CardTitle>
              <CardDescription>配置 MinIO 对象存储连接参数</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>MinIO Endpoint</Label>
                  <Input
                    value={storage.minio_endpoint}
                    onChange={(e) =>
                      setStorage({ ...storage, minio_endpoint: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Bucket</Label>
                  <Input
                    value={storage.minio_bucket}
                    onChange={(e) =>
                      setStorage({ ...storage, minio_bucket: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Access Key</Label>
                  <Input
                    type="password"
                    value={storage.minio_access_key}
                    onChange={(e) =>
                      setStorage({ ...storage, minio_access_key: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Secret Key</Label>
                  <Input
                    type="password"
                    value={storage.minio_secret_key}
                    onChange={(e) =>
                      setStorage({ ...storage, minio_secret_key: e.target.value })
                    }
                  />
                </div>
              </div>
              <Separator />
              <div className="flex justify-end">
                <Button
                  onClick={() => handleSave('storage', storage)}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 安全配置 */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">安全配置</CardTitle>
              <CardDescription>JWT、速率限制和密码策略</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>JWT 有效期（小时）</Label>
                  <Input
                    type="number"
                    value={security.jwt_expiry_hours}
                    onChange={(e) =>
                      setSecurity({ ...security, jwt_expiry_hours: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>每分钟速率限制</Label>
                  <Input
                    type="number"
                    value={security.rate_limit_per_minute}
                    onChange={(e) =>
                      setSecurity({
                        ...security,
                        rate_limit_per_minute: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>密码最小长度</Label>
                  <Input
                    type="number"
                    value={security.password_min_length}
                    onChange={(e) =>
                      setSecurity({
                        ...security,
                        password_min_length: e.target.value,
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>要求特殊字符</Label>
                  <Select
                    value={security.require_special_char}
                    onValueChange={(v) =>
                      setSecurity({ ...security, require_special_char: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">是</SelectItem>
                      <SelectItem value="false">否</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Separator />
              <div className="flex justify-end">
                <Button
                  onClick={() => handleSave('security', security)}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存配置'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
