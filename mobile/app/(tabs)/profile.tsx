// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView, Alert } from 'react-native'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { getAuthStorage } from '@/lib/auth-storage'
import { useAuthStore } from '@/lib/store'

interface MenuItem {
  icon: keyof typeof Ionicons.glyphMap
  label: string
  route: string
}

const menuItems: MenuItem[] = [
  { icon: 'chatbubbles-outline', label: '我的咨询', route: '/contracts' },
  { icon: 'document-text-outline', label: '我的合同', route: '/contracts' },
  { icon: 'briefcase-outline', label: '我的案件', route: '/cases' },
  { icon: 'people-outline', label: '找律师', route: '/find-lawyer' },
  { icon: 'settings-outline', label: '设置', route: '/settings' },
]

export default function ProfileScreen() {
  const { user, isAuthenticated, logout } = useAuthStore()

  const handleAvatarPress = () => {
    if (!isAuthenticated) {
      router.push('/(auth)/login')
    }
  }

  const handleMenuPress = (route: string) => {
    if (!isAuthenticated) {
      router.push('/(auth)/login')
      return
    }
    router.push(route as any)
  }

  const handleLogout = () => {
    Alert.alert('退出登录', '确定要退出当前账号吗？', [
      { text: '取消', style: 'cancel' },
      {
        text: '退出',
        style: 'destructive',
        onPress: async () => {
          await getAuthStorage().clearAuth()
          logout()
          router.replace('/')
        },
      },
    ])
  }

  const getRoleLabel = (role?: string): string => {
    const roleMap: Record<string, string> = {
      admin: '管理员',
      lawyer: '律师',
      client: '普通用户',
      enterprise: '企业用户',
    }
    return roleMap[role ?? ''] ?? '普通用户'
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* 顶部用户区域 */}
        <TouchableOpacity
          style={styles.header}
          onPress={handleAvatarPress}
          activeOpacity={isAuthenticated ? 1 : 0.7}
        >
          <View style={styles.avatar}>
            {user?.avatar_url ? (
              <Text style={styles.avatarText}>{user.name?.charAt(0) ?? '?'}</Text>
            ) : (
              <Ionicons name="person" size={44} color={Colors.white} />
            )}
          </View>
          {isAuthenticated && user ? (
            <View style={styles.userInfo}>
              <Text style={styles.userName}>{user.name}</Text>
              <View style={styles.roleTag}>
                <Text style={styles.roleTagText}>{getRoleLabel(user.role)}</Text>
              </View>
            </View>
          ) : (
            <View style={styles.userInfo}>
              <Text style={styles.loginHint}>点击登录</Text>
              <Text style={styles.loginSubHint}>登录后享受完整法律服务</Text>
            </View>
          )}
          <Ionicons name="chevron-forward" size={20} color={Colors.textMuted} />
        </TouchableOpacity>

        {/* 功能菜单 */}
        <View style={styles.menuSection}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.menuItem,
                index === menuItems.length - 1 && styles.menuItemLast,
              ]}
              onPress={() => handleMenuPress(item.route)}
              activeOpacity={0.6}
            >
              <View style={styles.menuItemLeft}>
                <Ionicons name={item.icon} size={22} color={Colors.text} />
                <Text style={styles.menuLabel}>{item.label}</Text>
              </View>
              <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
            </TouchableOpacity>
          ))}
        </View>

        {/* 退出登录 */}
        {isAuthenticated && (
          <TouchableOpacity
            style={styles.logoutButton}
            onPress={handleLogout}
            activeOpacity={0.7}
          >
            <Text style={styles.logoutText}>退出登录</Text>
          </TouchableOpacity>
        )}

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Layout.spacing.lg,
    paddingVertical: Layout.spacing.xl,
    paddingTop: Layout.spacing.xl + Layout.spacing.md,
    backgroundColor: Colors.background,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 28,
    fontWeight: '700',
    color: Colors.white,
  },
  userInfo: {
    flex: 1,
    marginLeft: Layout.spacing.md,
  },
  userName: {
    fontSize: Layout.fontSize.xl,
    fontWeight: '600',
    color: Colors.text,
  },
  roleTag: {
    backgroundColor: Colors.primary + '15',
    alignSelf: 'flex-start',
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.sm,
    marginTop: Layout.spacing.xs,
  },
  roleTagText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.primary,
    fontWeight: '500',
  },
  loginHint: {
    fontSize: Layout.fontSize.xl,
    fontWeight: '600',
    color: Colors.text,
  },
  loginSubHint: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    marginTop: Layout.spacing.xs,
  },
  menuSection: {
    marginTop: Layout.spacing.sm,
    marginHorizontal: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    overflow: 'hidden',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md + 2,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  menuItemLast: {
    borderBottomWidth: 0,
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
  },
  menuLabel: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
  },
  logoutButton: {
    marginTop: Layout.spacing.xl,
    marginHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    alignItems: 'center',
  },
  logoutText: {
    fontSize: Layout.fontSize.md,
    color: Colors.error,
    fontWeight: '500',
  },
  bottomSpacer: {
    height: Layout.spacing.xl,
  },
})
