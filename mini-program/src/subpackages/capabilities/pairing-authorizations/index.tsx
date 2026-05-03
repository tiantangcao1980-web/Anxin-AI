import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { pairingApi, PairingRequest, imChannelsApi } from '../_mock'
import './index.scss'

type Tab = 'pending' | 'approved'

function fmtDateTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${m}-${day} ${hh}:${mm}`
}

function countdown(iso: string): { text: string; warn: boolean } {
  const ms = new Date(iso).getTime() - Date.now()
  if (ms <= 0) return { text: '已过期', warn: true }
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  return { text: h > 0 ? `${h}h${m}m 后到期` : `${m}m 后到期`, warn: h < 4 }
}

export default function PairingAuthorizationsPage() {
  const [tab, setTab] = useState<Tab>('pending')
  const [pending, setPending] = useState<PairingRequest[]>([])
  const [approved, setApproved] = useState<PairingRequest[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [p, a] = await Promise.all([
        pairingApi.listPending(),
        pairingApi.listApproved(),
      ])
      setPending(p)
      setApproved(a)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onApprove = async (r: PairingRequest) => {
    try {
      const updated = await pairingApi.approve(r.id)
      setPending((arr) => arr.filter((x) => x.id !== r.id))
      setApproved((arr) => [updated, ...arr])
      Taro.showToast({ title: '已批准', icon: 'success' })
    } catch {
      Taro.showToast({ title: '操作失败', icon: 'none' })
    }
  }

  const onReject = async (r: PairingRequest) => {
    Taro.showModal({
      title: '拒绝配对',
      content: `确定拒绝来自 ${r.external_user_name} 的配对请求？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await pairingApi.reject(r.id)
          setPending((arr) => arr.filter((x) => x.id !== r.id))
          Taro.showToast({ title: '已拒绝', icon: 'none' })
        } catch {
          Taro.showToast({ title: '操作失败', icon: 'none' })
        }
      },
    })
  }

  const onRevoke = async (r: PairingRequest) => {
    Taro.showActionSheet({
      itemList: ['撤销授权'],
      success: async (res) => {
        if (res.tapIndex !== 0) return
        try {
          await pairingApi.revoke(r.id)
          setApproved((arr) => arr.filter((x) => x.id !== r.id))
          Taro.showToast({ title: '已撤销', icon: 'none' })
        } catch {
          Taro.showToast({ title: '操作失败', icon: 'none' })
        }
      },
    })
  }

  const list = tab === 'pending' ? pending : approved

  return (
    <View className='pa-page'>
      <View className='pa-seg'>
        <View
          className={`pa-seg-item ${tab === 'pending' ? 'pa-seg-item--active' : ''}`}
          onClick={() => setTab('pending')}
        >
          <Text>待审核 ({pending.length})</Text>
        </View>
        <View
          className={`pa-seg-item ${tab === 'approved' ? 'pa-seg-item--active' : ''}`}
          onClick={() => setTab('approved')}
        >
          <Text>已授权 ({approved.length})</Text>
        </View>
      </View>

      <ScrollView scrollY className='pa-scroll'>
        {loading ? (
          <View className='pa-empty'><Text>加载中…</Text></View>
        ) : list.length === 0 ? (
          <View className='pa-empty'>
            <Text className='pa-empty-icon'>{tab === 'pending' ? '🎉' : '📭'}</Text>
            <Text className='pa-empty-text'>
              {tab === 'pending' ? '没有待审核的配对' : '暂无已授权的配对'}
            </Text>
          </View>
        ) : (
          list.map((r) => {
            const cd = tab === 'pending' ? countdown(r.expires_at) : null
            return (
              <View key={r.id} className='pa-card'>
                <View className='pa-card-icon'>
                  {imChannelsApi.iconOf(r.channel_type)}
                </View>
                <View className='pa-card-body'>
                  <View className='pa-card-titlerow'>
                    <Text className='pa-card-name'>{r.external_user_name}</Text>
                    <Text className='pa-card-channel'>· {r.channel_name}</Text>
                  </View>
                  {r.external_group_name && (
                    <Text className='pa-card-group'>群聊：{r.external_group_name}</Text>
                  )}
                  <Text className='pa-card-time'>
                    {tab === 'pending'
                      ? `请求于 ${fmtDateTime(r.created_at)}`
                      : `授权于 ${fmtDateTime(r.approved_at || '')}`}
                  </Text>
                  {cd && (
                    <Text className={`pa-card-cd ${cd.warn ? 'pa-card-cd--warn' : ''}`}>
                      ⏳ {cd.text}
                    </Text>
                  )}
                </View>
                {tab === 'pending' ? (
                  <View className='pa-actions'>
                    <View className='pa-btn pa-btn--ok' onClick={() => onApprove(r)}>
                      <Text className='pa-btn-text'>批准</Text>
                    </View>
                    <View className='pa-btn pa-btn--no' onClick={() => onReject(r)}>
                      <Text className='pa-btn-text'>拒绝</Text>
                    </View>
                  </View>
                ) : (
                  <View
                    className='pa-btn pa-btn--more'
                    onClick={() => onRevoke(r)}
                  >
                    <Text className='pa-btn-text'>···</Text>
                  </View>
                )}
              </View>
            )
          })
        )}
      </ScrollView>
    </View>
  )
}
