/**
 * MessageChannelsPage — V3 消息渠道（P3-C 真业务化）
 *
 * 参考 Accio Work "消息渠道" 布局：
 *   - 顶部标题 + 副标题
 *   - "5 个渠道" 计数
 *   - 5 张 ChannelCard 网格（响应式：1 列 / 2 列）
 *   - mount 时 loadChannels；点 "设置机器人" 打开 SetupBotDialog
 *   - 已配置后显示 AgentBinder 下拉
 */

import { useEffect, useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'

import { ChannelCard } from '@/components/v3/im/ChannelCard'
import { SetupBotDialog } from '@/components/v3/im/SetupBotDialog'

import type { IMChannel, IMChannelType } from '@/lib/api/imChannels'
import { useIMChannelsStore } from '@/lib/store/imChannelsStore'

export default function MessageChannelsPage() {
  const channels = useIMChannelsStore((s) => s.channels)
  const loading = useIMChannelsStore((s) => s.loading)
  const loadError = useIMChannelsStore((s) => s.loadError)
  const loadChannels = useIMChannelsStore((s) => s.loadChannels)
  const bindAgent = useIMChannelsStore((s) => s.bindAgent)

  const [setupOpen, setSetupOpen] = useState(false)
  const [setupTarget, setSetupTarget] = useState<{
    channelType: IMChannelType
    initialConfig: Record<string, any>
  } | null>(null)

  useEffect(() => {
    loadChannels()
  }, [loadChannels])

  const handleSetup = (channel: IMChannel) => {
    setSetupTarget({
      channelType: channel.channel_type,
      initialConfig: channel.config ?? {},
    })
    setSetupOpen(true)
  }

  const handleBindAgent = async (channel: IMChannel, persona: string) => {
    try {
      await bindAgent(channel.id, persona)
    } catch (e) {
      toast.error(`绑定失败: ${e instanceof Error ? e.message : '未知错误'}`)
      throw e
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col gap-5 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <icons.MessageCircle className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              消息渠道
            </h1>
            <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
              配置 AI 智能体与用户交互的消息平台。所有连接数据存储在本地——无需云端。
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadChannels()}
          disabled={loading}
        >
          <icons.RefreshCcw className={loading ? 'animate-spin' : ''} />
          刷新
        </Button>
      </header>

      {/* 计数 */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium text-foreground">
          {channels.length} 个渠道
        </span>
        <span>· 当前已接入 {channels.filter((c) => c.status === 'connected').length} 个</span>
      </div>

      {/* 错误提示 */}
      {loadError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败: {loadError}
        </div>
      )}

      {/* 卡片网格 */}
      {loading && channels.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
          正在加载渠道...
        </div>
      ) : channels.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
          暂无渠道
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {channels.map((c) => (
            <ChannelCard
              key={c.id}
              channel={c}
              onSetup={handleSetup}
              onBindAgent={handleBindAgent}
            />
          ))}
        </div>
      )}

      {/* 设置机器人弹窗 */}
      <SetupBotDialog
        open={setupOpen}
        onOpenChange={(open) => {
          setSetupOpen(open)
          if (!open) setSetupTarget(null)
        }}
        channelType={setupTarget?.channelType ?? null}
        initialConfig={setupTarget?.initialConfig}
      />
    </div>
  )
}
