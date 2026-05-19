// -*- coding: utf-8 -*-
/**
 * 「我」tab — V3 P17-A 简单实装版。
 *
 * 当前包含：
 *   - 头像 / 昵称 / 邮箱
 *   - 设置入口（占位）
 *   - 登出按钮
 *
 * 后续 P17-B/C/D / P18 会扩展：订阅、运行模式、推送配置、设备管理、隐私 等。
 */

import React from 'react'
import {
  Alert,
  Image,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { router } from 'expo-router'
import {
  ChevronRight,
  CreditCard,
  LogOut,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react-native'
import { Screen } from '@/components/Layout'
import { useV3Theme } from '@/theme'
import { useAuthStore } from '@/lib/store'
import { logout as v3Logout } from '@/lib/api/auth'
import { domainMeta, type DomainId } from '@/theme/colors'

// 2026-05 Reset: 8 域名录改为 Editorial 编号列表（不用 DomainBadge 网格）
const DOMAIN_IDS: DomainId[] = [
  'legal',
  'finance',
  'tax',
  'compliance',
  'operations',
  'growth',
  'content',
  'global',
]

interface MenuRow {
  key: string
  label: string
  icon: LucideIcon
  onPress: () => void
  hint?: string
}

export default function MeTabScreen() {
  const t = useV3Theme()
  const { user, logout: storeLogout } = useAuthStore()

  const handleLogout = () => {
    Alert.alert('确认登出', '登出后需要重新登录才能使用智能体能力', [
      { text: '取消', style: 'cancel' },
      {
        text: '登出',
        style: 'destructive',
        onPress: async () => {
          try {
            await v3Logout()
          } catch {
            // 即使后端登出失败，本地也清掉
          }
          await storeLogout()
          router.replace('/(auth)/login')
        },
      },
    ])
  }

  const menus: MenuRow[] = [
    {
      key: 'subscription',
      label: '订阅与计费',
      icon: CreditCard,
      hint: '免费版',
      onPress: () => Alert.alert('提示', '订阅中心待 P18 接入'),
    },
    {
      key: 'privacy',
      label: '隐私与安全',
      icon: ShieldCheck,
      onPress: () => Alert.alert('提示', '隐私设置待接入'),
    },
    {
      key: 'settings',
      label: '设置',
      icon: Settings,
      onPress: () => router.push('/settings'),
    },
  ]

  const displayName = user?.name?.trim() || '未登录'
  const displayEmail = user?.email || '请登录账号'
  const avatarUrl = user?.avatar_url

  return (
    <Screen scrollable padded>
      {/* 用户卡片 */}
      <View
        style={[
          styles.userCard,
          {
            backgroundColor: t.colors.surface,
            borderColor: t.colors.divider,
          },
        ]}
      >
        <View style={styles.userInfo}>
          {avatarUrl ? (
            <Image source={{ uri: avatarUrl }} style={styles.avatar} />
          ) : (
            <View
              style={[
                styles.avatar,
                {
                  backgroundColor: t.colors.primary100,
                  alignItems: 'center',
                  justifyContent: 'center',
                },
              ]}
            >
              <Text style={[styles.avatarText, { color: t.colors.primary700 }]}>
                {(displayName[0] || 'A').toUpperCase()}
              </Text>
            </View>
          )}
          <View style={styles.userMeta}>
            <Text style={[styles.userName, { color: t.colors.text }]}>
              {displayName}
            </Text>
            <Text
              style={[styles.userEmail, { color: t.colors.textSecondary }]}
              numberOfLines={1}
            >
              {displayEmail}
            </Text>
          </View>
        </View>
      </View>

      {/* V3 8 大业务域 — Editorial 编号目录（Reset 后单色版） */}
      <View style={styles.domainSection}>
        <Text style={[styles.domainTrackerLabel, { color: t.colors.textSecondary }]}>
          INDEX · 八大业务
        </Text>
        <View style={styles.domainList}>
          {DOMAIN_IDS.map((id, i) => (
            <View key={id} style={[styles.domainRow, { borderBottomColor: t.colors.divider }]}>
              <Text style={[styles.domainNum, { color: t.colors.textSecondary }]}>
                {String(i + 1).padStart(2, '0')}
              </Text>
              <Text style={[styles.domainLabel, { color: t.colors.text }]}>
                {domainMeta[id].labelZh}
              </Text>
              <Text style={[styles.domainLabelEn, { color: t.colors.textMuted }]}>
                {domainMeta[id].labelEn}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* 菜单 */}
      <View
        style={[
          styles.menuGroup,
          { backgroundColor: t.colors.surface, borderColor: t.colors.divider },
        ]}
      >
        {menus.map((m, idx) => {
          const Icon = m.icon
          return (
            <React.Fragment key={m.key}>
              <TouchableOpacity
                style={styles.menuRow}
                onPress={m.onPress}
                activeOpacity={0.7}
              >
                <Icon size={20} color={t.colors.textSecondary} />
                <Text style={[styles.menuLabel, { color: t.colors.text }]}>
                  {m.label}
                </Text>
                <View style={styles.menuRight}>
                  {m.hint ? (
                    <Text
                      style={[styles.menuHint, { color: t.colors.textMuted }]}
                    >
                      {m.hint}
                    </Text>
                  ) : null}
                  <ChevronRight size={18} color={t.colors.textMuted} />
                </View>
              </TouchableOpacity>
              {idx < menus.length - 1 ? (
                <View
                  style={[
                    styles.divider,
                    { backgroundColor: t.colors.divider },
                  ]}
                />
              ) : null}
            </React.Fragment>
          )
        })}
      </View>

      {/* 登出 */}
      <TouchableOpacity
        style={[
          styles.logoutBtn,
          {
            backgroundColor: t.colors.surface,
            borderColor: t.colors.divider,
          },
        ]}
        onPress={handleLogout}
        activeOpacity={0.7}
      >
        <LogOut size={18} color={t.colors.error} />
        <Text style={[styles.logoutLabel, { color: t.colors.error }]}>
          登出
        </Text>
      </TouchableOpacity>

      {/* footer 占位 */}
      <View style={{ height: 24 }} />
    </Screen>
  )
}

const styles = StyleSheet.create({
  userCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 16,
    marginBottom: 16,
  },
  userInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  avatarText: {
    fontSize: 22,
    fontWeight: '600',
  },
  userMeta: {
    flex: 1,
    minWidth: 0,
  },
  userName: {
    fontSize: 17,
    fontWeight: '600',
    marginBottom: 4,
  },
  userEmail: {
    fontSize: 13,
  },
  domainSection: {
    marginBottom: 24,
  },
  domainTrackerLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginBottom: 12,
    letterSpacing: 1.8, // ~0.16em on 11px
    textTransform: 'uppercase',
  },
  domainList: {
    // 8 行编辑级目录
  },
  domainRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  domainNum: {
    fontSize: 13,
    fontWeight: '500',
    width: 28,
    fontVariant: ['tabular-nums'],
  },
  domainLabel: {
    fontSize: 15,
    flex: 1,
  },
  domainLabelEn: {
    fontSize: 11,
    fontWeight: '500',
    letterSpacing: 1.6,
    textTransform: 'uppercase',
  },
  menuGroup: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
    marginBottom: 16,
  },
  menuRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 12,
  },
  menuLabel: {
    flex: 1,
    fontSize: 15,
  },
  menuRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  menuHint: {
    fontSize: 13,
  },
  divider: {
    height: 0.5,
    marginLeft: 48,
  },
  logoutBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 16,
    borderWidth: 1,
  },
  logoutLabel: {
    fontSize: 15,
    fontWeight: '500',
  },
})
