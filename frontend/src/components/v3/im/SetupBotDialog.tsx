/**
 * SetupBotDialog — 设置机器人弹窗
 *
 * 根据 channel_type 渲染不同表单字段：
 *   - 飞书: app_id / app_secret / encrypt_key / verify_token
 *   - 微信: corp_id / secret
 *   - 钉钉: robot_token
 *   - Telegram: bot_token
 *   - Discord: token / server_id
 *   - Slack: bot_token / signing_secret（兜底，便于后端接入）
 */

import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

import { useIMChannelsStore } from '@/lib/store/imChannelsStore'
import type { IMChannelType } from '@/lib/api/imChannels'

interface FieldDef {
  key: string
  label: string
  placeholder?: string
  type?: 'text' | 'password'
  required?: boolean
  hint?: string
}

const FORM_SCHEMA: Record<IMChannelType, { title: string; fields: FieldDef[] }> = {
  feishu: {
    title: '飞书机器人 · 设置',
    fields: [
      { key: 'app_id', label: 'App ID', placeholder: 'cli_xxxxxxxx', required: true },
      { key: 'app_secret', label: 'App Secret', type: 'password', required: true },
      { key: 'encrypt_key', label: 'Encrypt Key', type: 'password' },
      { key: 'verify_token', label: 'Verification Token', type: 'password' },
    ],
  },
  wechat: {
    title: '微信ClawBot · 绑定企微账号',
    fields: [
      { key: 'corp_id', label: '企业 CorpID', placeholder: 'wwxxxxxxxx', required: true },
      { key: 'secret', label: '应用 Secret', type: 'password', required: true },
    ],
  },
  dingtalk: {
    title: '钉钉机器人 · 设置',
    fields: [
      {
        key: 'robot_token',
        label: '机器人 Token',
        type: 'password',
        required: true,
        hint: '钉钉群机器人 webhook 中的 access_token',
      },
    ],
  },
  telegram: {
    title: 'Telegram Bot · 设置',
    fields: [
      {
        key: 'bot_token',
        label: 'Bot Token',
        type: 'password',
        required: true,
        hint: '从 @BotFather 获取',
      },
    ],
  },
  discord: {
    title: 'Discord Bot · 设置',
    fields: [
      { key: 'token', label: 'Bot Token', type: 'password', required: true },
      { key: 'server_id', label: '服务器 ID', placeholder: 'guild id', required: true },
    ],
  },
  slack: {
    title: 'Slack Bot · 设置',
    fields: [
      { key: 'bot_token', label: 'Bot User OAuth Token', type: 'password', required: true },
      { key: 'signing_secret', label: 'Signing Secret', type: 'password', required: true },
    ],
  },
}

interface SetupBotDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  channelType: IMChannelType | null
  /** 已有 config（编辑场景） */
  initialConfig?: Record<string, any>
}

export function SetupBotDialog({
  open,
  onOpenChange,
  channelType,
  initialConfig,
}: SetupBotDialogProps) {
  const setupChannel = useIMChannelsStore((s) => s.setupChannel)

  const schema = channelType ? FORM_SCHEMA[channelType] : null

  const [values, setValues] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  const initialValues = useMemo(() => {
    if (!schema) return {}
    const v: Record<string, string> = {}
    for (const f of schema.fields) {
      v[f.key] = (initialConfig?.[f.key] as string | undefined) ?? ''
    }
    return v
  }, [schema, initialConfig])

  useEffect(() => {
    if (open) setValues(initialValues)
  }, [open, initialValues])

  if (!channelType || !schema) return null

  const handleSubmit = async () => {
    const missing = schema.fields.find((f) => f.required && !values[f.key]?.trim())
    if (missing) {
      toast.error(`请填写「${missing.label}」`)
      return
    }
    setSubmitting(true)
    try {
      const config: Record<string, string> = {}
      for (const f of schema.fields) {
        const v = values[f.key]?.trim()
        if (v) config[f.key] = v
      }
      await setupChannel(channelType, { config })
      toast.success('已保存配置')
      onOpenChange(false)
    } catch (e) {
      toast.error(`保存失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{schema.title}</DialogTitle>
          <DialogDescription>
            填写机器人凭据，所有数据存储在服务端，不会上传至第三方。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          {schema.fields.map((f) => (
            <div key={f.key} className="space-y-1.5">
              <label className="text-xs font-medium text-foreground">
                {f.label}
                {f.required && <span className="ml-0.5 text-red-500">*</span>}
              </label>
              <Input
                type={f.type ?? 'text'}
                placeholder={f.placeholder}
                value={values[f.key] ?? ''}
                onChange={(e) =>
                  setValues((prev) => ({ ...prev, [f.key]: e.target.value }))
                }
                autoComplete="off"
              />
              {f.hint && <p className="text-[10px] text-muted-foreground">{f.hint}</p>}
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? '保存中...' : '保存并连接'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
