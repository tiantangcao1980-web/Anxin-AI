/**
 * ChannelCard — 单个 IM 渠道卡片
 *
 * 布局参考 Accio Work "消息渠道"页：
 *   - 顶部：图标 + 名称 + 子名 + 状态徽章
 *   - 中部：3 列统计
 *   - "请配置智能体" 区域（虚线边框，未配置时显示提示，已配置时显示下拉）
 *   - 底部：设置按钮（"绑定微信账号" / "设置机器人"）
 */

import { icons } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/components/ui/utils'

import type { IMChannel, IMChannelType } from '@/lib/api/imChannels'

import { AgentBinder } from './AgentBinder'
import { ChannelStatsRow } from './ChannelStatsRow'
import { ChannelStatusBadge } from './ChannelStatusBadge'

interface ChannelMeta {
  emoji: string
  brand: string
  subTitle: string
  bg: string
  primaryAction: string
  secondaryAction?: string
  helpUrl?: string
}

const CHANNEL_META: Record<IMChannelType, ChannelMeta> = {
  dingtalk: {
    emoji: '🟦',
    brand: '钉钉',
    subTitle: 'ClawBot — 钉钉机器人',
    bg: 'bg-blue-100 dark:bg-blue-500/15',
    primaryAction: '设置机器人',
    helpUrl: 'https://open.dingtalk.com/document/robots',
  },
  wechat: {
    emoji: '🟢',
    brand: '微信',
    subTitle: 'ClawBot — 微信ClawBot',
    bg: 'bg-emerald-100 dark:bg-emerald-500/15',
    primaryAction: '绑定微信账号',
  },
  feishu: {
    emoji: '🟣',
    brand: '飞书',
    subTitle: 'ClawBot — 飞书机器人',
    bg: 'bg-purple-100 dark:bg-purple-500/15',
    primaryAction: '设置机器人',
    helpUrl: 'https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM',
  },
  telegram: {
    emoji: '🔵',
    brand: 'Telegram',
    subTitle: 'Bot — Telegram Bot',
    bg: 'bg-sky-100 dark:bg-sky-500/15',
    primaryAction: '设置机器人',
    helpUrl: 'https://core.telegram.org/bots',
  },
  discord: {
    emoji: '🟪',
    brand: 'Discord',
    subTitle: 'Bot — Discord Bot',
    bg: 'bg-indigo-100 dark:bg-indigo-500/15',
    primaryAction: '设置机器人',
    helpUrl: 'https://discord.com/developers/docs/intro',
  },
  slack: {
    emoji: '🟧',
    brand: 'Slack',
    subTitle: 'Bot — Slack Bot',
    bg: 'bg-orange-100 dark:bg-orange-500/15',
    primaryAction: '设置机器人',
    helpUrl: 'https://api.slack.com/start',
  },
}

interface ChannelCardProps {
  channel: IMChannel
  onSetup: (channel: IMChannel) => void
  onBindAgent: (channel: IMChannel, persona: string) => Promise<void>
}

export function ChannelCard({ channel, onSetup, onBindAgent }: ChannelCardProps) {
  const meta = CHANNEL_META[channel.channel_type]
  const isConfigured = channel.status === 'connected'

  return (
    <Card className="flex flex-col gap-4 p-5 transition-all hover:border-primary/40 hover:shadow-sm">
      {/* 顶部：图标 + 名称 + 状态 */}
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'flex size-12 shrink-0 items-center justify-center rounded-2xl text-2xl',
            meta.bg,
          )}
          aria-label={meta.brand}
        >
          <span>{meta.emoji}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-base font-semibold text-foreground">{meta.brand}</h3>
            <ChannelStatusBadge status={channel.status} className="shrink-0" />
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="truncate">{meta.subTitle}</span>
            {meta.helpUrl && (
              <a
                href={meta.helpUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-0.5 text-primary hover:underline"
              >
                (如何接入?)
                <icons.ExternalLink className="size-3" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* 中部：统计三列 */}
      <ChannelStatsRow stats={channel.stats} />

      {/* 智能体配置区 */}
      <div
        className={cn(
          'rounded-xl border-2 border-dashed p-3',
          isConfigured
            ? 'border-border/60 bg-muted/20'
            : 'border-border/40 bg-muted/10',
        )}
      >
        {isConfigured ? (
          <AgentBinder
            value={channel.bound_agent_persona}
            onChange={(persona) => onBindAgent(channel, persona)}
          />
        ) : (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <icons.Wand2 className="size-3.5 shrink-0" />
            <span>请配置智能体 — 选择一个智能体来处理此渠道的消息</span>
          </div>
        )}
      </div>

      {/* 底部：操作按钮 */}
      <div className="flex justify-end">
        <Button
          variant={isConfigured ? 'outline' : 'default'}
          size="sm"
          onClick={() => onSetup(channel)}
        >
          <icons.Settings2 />
          {isConfigured ? '修改配置' : meta.primaryAction}
        </Button>
      </div>
    </Card>
  )
}
