import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { pluginsApi, Plugin } from '../_mock'
import './index.scss'

const STATUS_LABEL: Record<Plugin['status'], { text: string; cls: string; cta: string }> = {
  enabled: { text: '已激活', cls: 'pl-status--ok', cta: '已激活' },
  disabled: { text: '未激活', cls: 'pl-status--off', cta: '激活' },
  pending_review: { text: '审核中', cls: 'pl-status--warn', cta: '审核中' },
}

export default function PluginsPage() {
  const [list, setList] = useState<Plugin[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await pluginsApi.list()
      setList(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onToggle = async (p: Plugin) => {
    if (p.status === 'pending_review') {
      Taro.showToast({ title: '审核中，请稍候', icon: 'none' })
      return
    }
    try {
      const updated = await pluginsApi.toggle(p.id, p.status !== 'enabled')
      setList((arr) => arr.map((x) => (x.id === p.id ? updated : x)))
      Taro.showToast({
        title: updated.status === 'enabled' ? '已激活' : '已停用',
        icon: 'none',
      })
    } catch {
      Taro.showToast({ title: '操作失败', icon: 'none' })
    }
  }

  const onDetail = (p: Plugin) => {
    Taro.showModal({
      title: p.display_name,
      content: `${p.description}\n包含 ${p.skill_count} 个技能\n发布方：${p.publisher}`,
      showCancel: false,
    })
  }

  return (
    <ScrollView scrollY className='pl-page'>
      {loading ? (
        <View className='pl-empty'><Text>加载中…</Text></View>
      ) : (
        list.map((p) => {
          const s = STATUS_LABEL[p.status]
          return (
            <View key={p.id} className='pl-card' onClick={() => onDetail(p)}>
              <View className='pl-card-icon'>{p.icon}</View>
              <View className='pl-card-body'>
                <View className='pl-card-titlerow'>
                  <Text className='pl-card-title'>{p.display_name}</Text>
                  <View className={`pl-status ${s.cls}`}>
                    <Text className='pl-status-text'>{s.text}</Text>
                  </View>
                </View>
                <Text className='pl-card-desc'>{p.description}</Text>
                <View className='pl-card-meta'>
                  <Text className='pl-meta'>📦 {p.skill_count} 个技能</Text>
                  <Text className='pl-meta'>🏷 {p.publisher}</Text>
                </View>
              </View>
              <View
                className={`pl-cta ${p.status === 'enabled' ? 'pl-cta--off' : 'pl-cta--on'}`}
                onClick={(e) => { e.stopPropagation(); onToggle(p) }}
              >
                <Text className='pl-cta-text'>
                  {p.status === 'enabled' ? '停用' : s.cta}
                </Text>
              </View>
            </View>
          )
        })
      )}
    </ScrollView>
  )
}
