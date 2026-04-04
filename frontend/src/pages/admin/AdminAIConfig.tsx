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

export default function AdminAIConfig() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [llm, setLlm] = useState({
    provider: 'openai',
    api_key: '',
    models: 'gpt-4,gpt-3.5-turbo',
  })

  useEffect(() => {
    ;(async () => {
      try {
        const config = await adminApi.getSystemConfig()
        if (config?.llm) setLlm(prev => ({ ...prev, ...config.llm }))
      } catch { /* use defaults */ }
      setLoading(false)
    })()
  }, [])

  const maskValue = (val: string) => {
    if (!val || val.length < 8) return val
    return val.slice(0, 4) + '****' + val.slice(-4)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await adminApi.updateSystemConfig({ llm })
      toast.success('模型配置已保存')
    } catch (e: any) {
      toast.error(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <PageContainer title="模型配置"><Skeleton className="h-80 rounded-xl" /></PageContainer>
  }

  return (
    <PageContainer title="模型配置" subtitle="大语言模型提供商和 API 密钥">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">LLM 模型配置</CardTitle>
              <CardDescription>配置系统默认的大语言模型。用户可在个人设置中覆盖。</CardDescription>
            </div>
            <Badge variant="outline" className="text-xs">系统级 · 全局默认</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>模型提供商</Label>
            <Select value={llm.provider} onValueChange={v => setLlm({ ...llm, provider: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="azure">Azure OpenAI</SelectItem>
                <SelectItem value="anthropic">Anthropic</SelectItem>
                <SelectItem value="qwen">通义千问</SelectItem>
                <SelectItem value="deepseek">DeepSeek</SelectItem>
                <SelectItem value="glm">智谱 GLM</SelectItem>
                <SelectItem value="ollama">Ollama（本地）</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>API Key</Label>
            <Input
              type="password"
              value={llm.api_key}
              onChange={e => setLlm({ ...llm, api_key: e.target.value })}
              placeholder="sk-..."
            />
            {llm.api_key && (
              <p className="text-xs text-muted-foreground">当前值：{maskValue(llm.api_key)}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label>可用模型（逗号分隔）</Label>
            <Input
              value={llm.models}
              onChange={e => setLlm({ ...llm, models: e.target.value })}
              placeholder="gpt-4,gpt-3.5-turbo"
            />
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">修改后立即生效，服务重启后将重置</p>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? '保存中...' : '保存配置'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </PageContainer>
  )
}
