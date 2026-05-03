import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView, Picker } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { imChannelsApi, IMChannel } from '../_mock'
import './index.scss'

const STATUS: Record<IMChannel['status'], { text: string; cls: string }> = {
  unconfigured: { text: '未配置', cls: 'mc-status--off' },
  connecting: { text: '连接中', cls: 'mc-status--warn' },
  connected: { text: '已连接', cls: 'mc-status--ok' },
  error: { text: '异常', cls: 'mc-status--err' },
}

const PERSONA_OPTIONS = [
  { value: 'legal', label: '法律顾问' },
  { value: 'tax_finance', label: '财税顾问' },
  { value: 'office', label: '办公助手' },
  { value: 'intelligence', label: '情报分析师' },
  { value: 'sales', label: '销售助理' },
]
const PERSONA_LABEL = (v: string | null) =>
  PERSONA_OPTIONS.find((o) => o.value === v)?.label ?? '未指定'

export default function MessageChannelsPage() {
  const [channels, setChannels] = useState<IMChannel[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await imChannelsApi.list()
      setChannels(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onSetupBot = (c: IMChannel) => {
    Taro.showModal({
      title: `设置 ${c.name} 机器人`,
      content: `小程序无法直接打开 OAuth 链接，请前往 Web 后台完成${c.name}机器人绑定。`,
      showCancel: false,
    })
  }

  const onPickPersona = (c: IMChannel, idx: number) => {
    const persona = PERSONA_OPTIONS[idx].value
    setChannels((arr) =>
      arr.map((x) => (x.id === c.id ? { ...x, bound_agent_persona: persona } : x))
    )
    Taro.showToast({ title: `已绑定 ${PERSONA_OPTIONS[idx].label}`, icon: 'none' })
  }

  return (
    <ScrollView scrollY className='mc-page'>
      <View className='mc-intro'>
        <Text className='mc-intro-title'>IM 渠道接入</Text>
        <Text className='mc-intro-sub'>
          为每个 IM 渠道选择一个智能体角色，处理来自该渠道的所有消息。
        </Text>
      </View>

      {loading ? (
        <View className='mc-empty'><Text>加载中…</Text></View>
      ) : (
        channels.map((c) => {
          const s = STATUS[c.status]
          return (
            <View key={c.id} className='mc-card'>
              <View className='mc-card-header'>
                <Text className='mc-card-icon'>{imChannelsApi.iconOf(c.channel_type)}</Text>
                <View className='mc-card-titlebox'>
                  <Text className='mc-card-name'>{c.name}</Text>
                  <View className={`mc-status ${s.cls}`}>
                    <Text className='mc-status-text'>{s.text}</Text>
                  </View>
                </View>
              </View>

              <View className='mc-stats'>
                <View className='mc-stat'>
                  <Text className='mc-stat-num'>{c.stats.bound_users}</Text>
                  <Text className='mc-stat-label'>已配对用户</Text>
                </View>
                <View className='mc-stat'>
                  <Text className='mc-stat-num'>{c.stats.bound_groups}</Text>
                  <Text className='mc-stat-label'>已配对群聊</Text>
                </View>
                <View className='mc-stat mc-stat--warn'>
                  <Text className='mc-stat-num'>{c.stats.pending_pairings}</Text>
                  <Text className='mc-stat-label'>待审核</Text>
                </View>
              </View>

              <View className='mc-config'>
                <View className='mc-config-row'>
                  <Text className='mc-config-label'>处理智能体</Text>
                  <Picker
                    mode='selector'
                    range={PERSONA_OPTIONS}
                    rangeKey='label'
                    onChange={(e) => onPickPersona(c, Number(e.detail.value))}
                  >
                    <View className='mc-picker'>
                      <Text className='mc-picker-text'>{PERSONA_LABEL(c.bound_agent_persona)}</Text>
                      <Text className='mc-picker-arrow'>▾</Text>
                    </View>
                  </Picker>
                </View>
                <View className='mc-bot-btn' onClick={() => onSetupBot(c)}>
                  <Text className='mc-bot-btn-text'>
                    {c.status === 'connected' ? '管理机器人' : '设置机器人'}
                  </Text>
                </View>
              </View>
            </View>
          )
        })
      )}
    </ScrollView>
  )
}
