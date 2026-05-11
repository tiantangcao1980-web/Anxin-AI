/**
 * PersonaAppsBadges — supported_apps 徽章
 *
 * 含一个简易的 "name → emoji 图标" 映射。未匹配的 app 用 🔌 兜底。
 * 超过 max 时折叠 "+N"。
 */

import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

const APP_ICON: Record<string, string> = {
  feishu: '🪶',
  feishu_doc: '📄',
  dingtalk: '🛎',
  wecom: '🐧',
  notion: '📓',
  outlook: '📧',
  google_calendar: '📅',
  linkedin: '💼',
  reddit: '👽',
  x: '🐦',
  youtube: '📺',
  tiktok: '🎵',
  tiktok_shop: '🛒',
  tiktok_ads: '📢',
  shopify: '🛍',
  shopee: '🛒',
  amazon_sp_api: '📦',
  '1688': '🏭',
  stripe: '💳',
  paypal: '💵',
  meta_ads: '📣',
  google_ads: '📣',
  '巨量引擎': '📣',
  '腾讯广告': '📣',
  salesforce: '☁️',
  hubspot: '🟠',
  zoho: '🟢',
  pipedrive: '🚀',
  '法大大': '✍️',
  e签宝: '✍️',
  '北大法宝': '⚖️',
  '威科先行': '⚖️',
  '国务院政策库': '🏛',
  '中国裁判文书网': '📜',
  '信用中国': '🏷',
  '企查查': '🔍',
  '天眼查': '👁',
  '启信宝': '🛡',
  '金蝶': '📊',
  '用友': '📊',
  xero: '🟦',
  quickbooks: '🟩',
  '国家税务总局': '🏛',
  '微信公众号': '📰',
  '抖音': '📱',
  '视频号': '📺',
  figma: '🎨',
  canva: '🖌',
  higgsfield: '✨',
  remotion: '🎬',
  'canvas-design': '🖼',
  'web-artifacts-builder': '🌐',
  headlessx: '🕵️',
  '桌面通知中心': '🖥',
  '移动推送': '📲',
}

interface Props {
  apps: string[]
  max?: number
  className?: string
}

export function PersonaAppsBadges({ apps, max = 8, className }: Props) {
  if (apps.length === 0) {
    return null
  }
  const visible = apps.slice(0, max)
  const overflow = apps.length - visible.length

  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      {visible.map((a) => (
        <Badge
          key={a}
          variant="outline"
          className="gap-1 px-1.5 py-0.5 text-[10px] text-foreground/80"
          title={a}
        >
          <span aria-hidden>{APP_ICON[a] ?? '🔌'}</span>
          <span className="truncate max-w-[120px]">{a}</span>
        </Badge>
      ))}
      {overflow > 0 && (
        <Badge
          variant="outline"
          className="px-1.5 py-0.5 text-[10px] text-muted-foreground"
          title={apps.slice(max).join(', ')}
        >
          +{overflow}
        </Badge>
      )}
    </div>
  )
}
