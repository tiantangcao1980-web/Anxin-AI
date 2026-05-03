import { useEffect, useState, useCallback } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  appAuthApi, AppProvider, AppAuthorization,
  APP_CATEGORY_LABELS, APP_CATEGORY_ORDER, AppCategory,
} from '../_mock'
import './index.scss'

const PROVIDER_EMOJI: Record<string, string> = {
  feishu: '🪶', dingtalk: '🟦', wecom: '💼', lark: '🌱', slack: '💬',
  notion: '📒', feishu_doc: '📄', dingtalk_drive: '💾', google_drive: '🟨', onedrive: '🟦',
  salesforce: '☁️', hubspot: '🟧', fxiaoke: '📈', xiaoshouyi: '📊',
  shopify: '🛒', amazon_seller: '📦', taobao_open: '🅿️', jd_open: '🅹', douyin_open: '🅓',
  qichacha: '🔍', tianyancha: '👁️', wenshu: '⚖️', beidafabao: '📚',
  figma: '🎨', jianying: '🎬', canva: '🖼️',
  compliance_gov: '🏛️', creditchina: '✅',
  kingdee: '💰', yongyou: '💳',
}

function statusBadge(status: AppAuthorization['status']): { text: string; cls: string } {
  switch (status) {
    case 'connected': return { text: '已连接', cls: 'aa-badge--ok' }
    case 'expired': return { text: '已过期', cls: 'aa-badge--warn' }
    case 'revoked': return { text: '已撤销', cls: 'aa-badge--err' }
    case 'error': return { text: '异常', cls: 'aa-badge--err' }
  }
}

export default function AppAuthorizationsPage() {
  const [providers, setProviders] = useState<AppProvider[]>([])
  const [auths, setAuths] = useState<AppAuthorization[]>([])
  const [activeCategory, setActiveCategory] = useState<AppCategory | 'all'>('all')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [p, a] = await Promise.all([
        appAuthApi.listProviders(),
        appAuthApi.listAuthorizations(),
      ])
      setProviders(p)
      setAuths(a)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleConnect = async (p: AppProvider) => {
    try {
      const { authorize_url } = await appAuthApi.startConnect(p.provider_id)
      // 小程序无法直接打开外部 URL，跳 webview 中转页（如未实现，提示用户）
      Taro.showModal({
        title: `连接 ${p.display_name}`,
        content: `将通过 OAuth 打开：${authorize_url}\n请在 Web 端完成授权后回到小程序。`,
        showCancel: true,
      })
    } catch {
      Taro.showToast({ title: '获取授权链接失败', icon: 'none' })
    }
  }

  const handleManage = (auth: AppAuthorization) => {
    Taro.showActionSheet({
      itemList: ['查看权限范围', '断开连接'],
      success: async (res) => {
        if (res.tapIndex === 0) {
          Taro.showModal({
            title: '权限范围',
            content: auth.scopes.length > 0 ? auth.scopes.join('\n') : '（无显式 scope）',
            showCancel: false,
          })
        } else if (res.tapIndex === 1) {
          try {
            await appAuthApi.disconnect(auth.id)
            setAuths((arr) => arr.filter((a) => a.id !== auth.id))
            Taro.showToast({ title: '已断开', icon: 'none' })
          } catch {
            Taro.showToast({ title: '断开失败', icon: 'none' })
          }
        }
      },
    })
  }

  const authMap = new Map(auths.map((a) => [a.provider_id, a]))

  let list = providers
  if (activeCategory !== 'all') list = list.filter((p) => p.category === activeCategory)

  // 已连接置顶
  list = [...list].sort((a, b) => {
    const aOk = authMap.has(a.provider_id) ? 0 : 1
    const bOk = authMap.has(b.provider_id) ? 0 : 1
    return aOk - bOk
  })

  return (
    <View className='aa-page'>
      <ScrollView scrollX className='aa-tabs' enhanced showScrollbar={false}>
        <View
          className={`aa-tab ${activeCategory === 'all' ? 'aa-tab--active' : ''}`}
          onClick={() => setActiveCategory('all')}
        >
          <Text>全部</Text>
        </View>
        {APP_CATEGORY_ORDER.map((c) => (
          <View
            key={c}
            className={`aa-tab ${activeCategory === c ? 'aa-tab--active' : ''}`}
            onClick={() => setActiveCategory(c)}
          >
            <Text>{APP_CATEGORY_LABELS[c]}</Text>
          </View>
        ))}
      </ScrollView>

      <ScrollView scrollY className='aa-scroll'>
        {loading ? (
          <View className='aa-empty'><Text>加载中…</Text></View>
        ) : list.length === 0 ? (
          <View className='aa-empty'><Text>该分类暂无应用</Text></View>
        ) : (
          list.map((p) => {
            const auth = authMap.get(p.provider_id)
            const badge = auth ? statusBadge(auth.status) : null
            return (
              <View
                key={p.provider_id}
                className='aa-card'
                onLongPress={auth ? () => handleManage(auth) : undefined}
              >
                <View className='aa-card-emoji'>{PROVIDER_EMOJI[p.provider_id] || '🔌'}</View>
                <View className='aa-card-body'>
                  <View className='aa-card-titlerow'>
                    <Text className='aa-card-title'>{p.display_name}</Text>
                    {badge && (
                      <View className={`aa-badge ${badge.cls}`}>
                        <Text className='aa-badge-text'>{badge.text}</Text>
                      </View>
                    )}
                  </View>
                  <Text className='aa-card-desc'>{p.description}</Text>
                  {auth?.account_label && (
                    <Text className='aa-card-account'>{auth.account_label}</Text>
                  )}
                </View>
                {auth ? (
                  <View className='aa-action aa-action--manage' onClick={() => handleManage(auth)}>
                    <Text className='aa-action-text'>管理</Text>
                  </View>
                ) : (
                  <View className='aa-action aa-action--connect' onClick={() => handleConnect(p)}>
                    <Text className='aa-action-text'>+ 连接</Text>
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
