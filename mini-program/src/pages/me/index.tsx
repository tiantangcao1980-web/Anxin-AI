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
import {
  getStoredPrivacyMode,
  setStoredPrivacyMode,
  type MiniProgramPrivacyMode,
} from '../../utils/privacy'
import './index.scss'

interface MenuItem {
  key: string
  emoji: string
  title: string
  description?: string
  rightText?: string
  action: () => void | Promise<void>
}

const PRIVACY_OPTIONS: { mode: MiniProgramPrivacyMode; label: string; desc: string }[] = [
  { mode: 'standard', label: '标准模式', desc: '联网使用全部功能' },
  { mode: 'local', label: '本地模式', desc: '禁用数据网络，仅本地缓存' },
  { mode: 'top-secret', label: '机密模式', desc: '禁用数据网络 + 不留痕' },
]

function privacyLabel(mode: MiniProgramPrivacyMode): string {
  return PRIVACY_OPTIONS.find((o) => o.mode === mode)?.label || '标准模式'
}

export default function MePage() {
  const [user, setUser] = useState<StoredUser | null>(null)
  const [vipLevel] = useState<'free' | 'pro' | 'enterprise'>('free')
  const [privacyMode, setPrivacyMode] = useState<MiniProgramPrivacyMode>('standard')

  useEffect(() => {
    setUser(tokenStorage.getUser())
    setPrivacyMode(getStoredPrivacyMode())
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

  const handlePrivacyMode = async () => {
    const res = await Taro.showActionSheet({
      itemList: PRIVACY_OPTIONS.map((o) => `${o.label} · ${o.desc}`),
    }).catch(() => null)
    if (!res || res.tapIndex === undefined) return
    const next = PRIVACY_OPTIONS[res.tapIndex]?.mode
    if (!next || next === privacyMode) return

    // 切到敏感模式前先告知后果
    if (next !== 'standard') {
      const confirm = await Taro.showModal({
        title: `切换到「${PRIVACY_OPTIONS[res.tapIndex]?.label}」`,
        content: '该模式下所有数据网络请求将被拒绝（包括 token 刷新、登录续期）。\n仅本地缓存功能可用。',
        confirmText: '确认切换',
        confirmColor: '#B45309',
      })
      if (!confirm.confirm) return
    }
    setStoredPrivacyMode(next)
    setPrivacyMode(next)
    Taro.showToast({ title: `已切换：${privacyLabel(next)}`, icon: 'none' })
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
    {
      key: 'privacy-mode',
      emoji: '🛡️',
      title: '隐私模式',
      rightText: privacyLabel(privacyMode),
      action: handlePrivacyMode,
    },
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

      {/* 隐私模式横幅（仅敏感模式显示） */}
      {privacyMode !== 'standard' ? (
        <View className='me-privacy-banner'>
          <Text className='me-privacy-banner__emoji'>🛡️</Text>
          <Text className='me-privacy-banner__text'>
            当前为「{privacyLabel(privacyMode)}」— 数据网络已禁用
          </Text>
        </View>
      ) : null}

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
            {item.rightText ? (
              <Text
                className={`me-menu__right ${
                  item.key === 'privacy-mode' && privacyMode !== 'standard'
                    ? 'me-menu__right--alert'
                    : ''
                }`}
              >
                {item.rightText}
              </Text>
            ) : null}
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
