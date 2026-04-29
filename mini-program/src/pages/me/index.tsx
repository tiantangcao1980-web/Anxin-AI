// -*- coding: utf-8 -*-
/**
 * Me tabBar —— 个人中心
 *
 * 区块：
 *   1. 用户卡：头像 + 昵称 + 等级
 *   2. 设置入口列表：清缓存 / 关于 / 用户协议 / 隐私 / 反馈
 *   3. 退出登录
 */

import { useEffect, useState } from 'react'
import { View, Text, Image } from '@tarojs/components'
import Taro from '@tarojs/taro'

import { Screen } from '../../components/Layout'
import { tokenStorage, type StoredUser } from '../../utils/auth/token'
import { logout } from '../../utils/api/auth'
import './index.scss'

interface MenuItem {
  key: string
  emoji: string
  title: string
  description?: string
  action: () => void | Promise<void>
}

export default function MePage() {
  const [user, setUser] = useState<StoredUser | null>(null)
  const [vipLevel] = useState<'free' | 'pro' | 'enterprise'>('free')

  useEffect(() => {
    setUser(tokenStorage.getUser())
  }, [])

  const handleClearCache = async () => {
    const ok = await Taro.showModal({
      title: '清除缓存',
      content: '会清除本地非登录数据，确定继续？',
    })
    if (ok.confirm) {
      const access = tokenStorage.getAccessToken()
      const refresh = tokenStorage.getRefreshToken()
      const u = tokenStorage.getUser()
      Taro.clearStorageSync()
      // 保留登录态
      if (access) tokenStorage.setAccessToken(access)
      if (refresh) tokenStorage.setRefreshToken(refresh)
      if (u) tokenStorage.setUser(u)
      Taro.showToast({ title: '已清除', icon: 'success' })
    }
  }

  const handleAbout = () => {
    Taro.showModal({
      title: '关于安心智能助手',
      content: 'V3 · 制造业全链路智能助理\n法/税/财/管理 + 调研 + 获客 + 内容 + 跨境出海',
      showCancel: false,
    })
  }

  const handleAgreement = (kind: 'tos' | 'privacy') => {
    const url =
      kind === 'tos'
        ? 'https://www.anxinagent.com/legal/terms'
        : 'https://www.anxinagent.com/legal/privacy'
    Taro.navigateTo({
      url: `/pages/webview/index?url=${encodeURIComponent(url)}&title=${encodeURIComponent(
        kind === 'tos' ? '用户协议' : '隐私政策',
      )}`,
    })
  }

  const handleFeedback = () => {
    Taro.showModal({
      title: '反馈渠道',
      content: '请发邮件至 hi@anxinagent.com，或在公众号留言',
      showCancel: false,
    })
  }

  const handleLogout = async () => {
    const ok = await Taro.showModal({
      title: '确认退出登录',
      content: '退出后需要重新授权微信',
    })
    if (!ok.confirm) return
    await logout()
    Taro.reLaunch({ url: '/pages/login/index' })
  }

  const menu: MenuItem[] = [
    { key: 'clear', emoji: '🧹', title: '清除缓存', action: handleClearCache },
    { key: 'about', emoji: 'ℹ️', title: '关于安心', action: handleAbout },
    {
      key: 'tos',
      emoji: '📄',
      title: '用户协议',
      action: () => handleAgreement('tos'),
    },
    {
      key: 'privacy',
      emoji: '🔒',
      title: '隐私政策',
      action: () => handleAgreement('privacy'),
    },
    { key: 'feedback', emoji: '💬', title: '问题反馈', action: handleFeedback },
  ]

  const vipLabel = {
    free: '免费版',
    pro: 'PRO 会员',
    enterprise: '企业版',
  }[vipLevel]

  return (
    <Screen padded={false}>
      {/* 用户卡 */}
      <View className='me-card'>
        <View className='me-card__head'>
          {user?.avatar_url ? (
            <Image src={user.avatar_url} className='me-card__avatar' mode='aspectFill' />
          ) : (
            <View className='me-card__avatar me-card__avatar--placeholder'>
              <Text className='me-card__avatar-emoji'>👤</Text>
            </View>
          )}
          <View className='me-card__info'>
            <Text className='me-card__name'>{user?.name || '未登录'}</Text>
            <View className='me-card__vip'>
              <Text className='me-card__vip-text'>{vipLabel}</Text>
            </View>
          </View>
        </View>
        {user ? (
          <Text className='me-card__email'>{user.email}</Text>
        ) : (
          <View
            className='me-card__login-btn'
            onClick={() => Taro.reLaunch({ url: '/pages/login/index' })}
          >
            <Text className='me-card__login-text'>立即登录</Text>
          </View>
        )}
      </View>

      {/* 菜单 */}
      <View className='me-menu'>
        {menu.map((item, idx) => (
          <View
            key={item.key}
            className={`me-menu__item ${idx === menu.length - 1 ? 'me-menu__item--last' : ''}`}
            onClick={() => void item.action()}
          >
            <Text className='me-menu__emoji'>{item.emoji}</Text>
            <Text className='me-menu__title'>{item.title}</Text>
            <Text className='me-menu__chevron'>›</Text>
          </View>
        ))}
      </View>

      {/* 退出 */}
      {user ? (
        <View className='me-logout' onClick={handleLogout}>
          <Text className='me-logout__text'>退出登录</Text>
        </View>
      ) : null}

      <View className='me-footer'>
        <Text className='me-footer__text'>安心智能助手 V3</Text>
        <Text className='me-footer__build'>build {process.env.NODE_ENV || 'dev'}</Text>
      </View>
    </Screen>
  )
}
