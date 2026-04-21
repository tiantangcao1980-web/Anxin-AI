import { useState } from 'react'
import { View, Text, TouchableOpacity, Switch, ScrollView, Alert, StyleSheet } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { router, Stack } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useStackHeaderOptions, useTheme } from '@/lib/theme'

type IoniconsName = React.ComponentProps<typeof Ionicons>['name']

interface SettingItem {
  key: string
  icon: IoniconsName
  label: string
  type: 'navigate' | 'switch' | 'value'
  value?: string
}

interface SettingSection {
  title: string
  items: SettingItem[]
}

// @mock-data FALLBACK
const SETTING_SECTIONS: SettingSection[] = [
  {
    title: '账户设置',
    items: [
      { key: 'profile', icon: 'person-outline', label: '个人信息', type: 'navigate' },
      { key: 'password', icon: 'lock-closed-outline', label: '修改密码', type: 'navigate' },
    ],
  },
  {
    title: '通知设置',
    items: [
      { key: 'push', icon: 'notifications-outline', label: '推送通知', type: 'switch' },
      { key: 'message', icon: 'chatbubble-outline', label: '消息提醒', type: 'switch' },
      { key: 'email', icon: 'mail-outline', label: '邮件通知', type: 'switch' },
    ],
  },
  {
    title: '通用设置',
    items: [
      { key: 'language', icon: 'language-outline', label: '语言', type: 'value', value: '中文' },
      { key: 'cache', icon: 'trash-outline', label: '清理缓存', type: 'navigate' },
      {
        key: 'about',
        icon: 'information-circle-outline',
        label: '关于我们',
        type: 'navigate',
      },
    ],
  },
]

export default function SettingsScreen() {
  const [switches, setSwitches] = useState<Record<string, boolean>>({
    push: true,
    message: true,
    email: false,
  })

  const toggleSwitch = (key: string) => {
    setSwitches((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const headerOptions = useStackHeaderOptions({ title: '设置' })
  const theme = useTheme()

  const handlePress = (key: string) => {
    switch (key) {
      case 'cache':
        Alert.alert('清理缓存', '确定要清理所有缓存数据吗？', [
          { text: '取消', style: 'cancel' },
          { text: '确定', onPress: () => Alert.alert('提示', '缓存已清理') },
        ])
        break
      case 'about':
        Alert.alert('关于安心法务', '安心智慧法务平台\n版本 v1.0.0\n\n让法律服务更简单')
        break
      default:
        break
    }
  }

  const renderItem = (item: SettingItem, isLast: boolean) => {
    return (
      <TouchableOpacity
        key={item.key}
        style={[styles.settingItem, !isLast && styles.settingItemBorder]}
        activeOpacity={item.type === 'switch' ? 1 : 0.6}
        onPress={() => item.type !== 'switch' && handlePress(item.key)}
      >
        <View style={styles.settingItemLeft}>
          <Ionicons name={item.icon} size={20} color="#D4A574" />
          <Text style={styles.settingItemLabel}>{item.label}</Text>
        </View>
        <View style={styles.settingItemRight}>
          {item.type === 'switch' && (
            <Switch
              value={switches[item.key] ?? false}
              onValueChange={() => toggleSwitch(item.key)}
              trackColor={{ false: '#E0E0E0', true: '#D4A57480' }}
              thumbColor={switches[item.key] ? '#D4A574' : '#FFF'}
            />
          )}
          {item.type === 'value' && (
            <>
              <Text style={styles.settingValueText}>{item.value}</Text>
              <Ionicons name="chevron-forward" size={18} color="#CCC" />
            </>
          )}
          {item.type === 'navigate' && (
            <Ionicons name="chevron-forward" size={18} color="#CCC" />
          )}
        </View>
      </TouchableOpacity>
    )
  }

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: theme.surface }]}
      edges={['bottom']}
    >
      <Stack.Screen options={headerOptions} />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {SETTING_SECTIONS.map((section) => (
          <View key={section.title} style={styles.section}>
            <Text style={styles.sectionTitle}>{section.title}</Text>
            <View style={styles.sectionCard}>
              {section.items.map((item, index) =>
                renderItem(item, index === section.items.length - 1)
              )}
            </View>
          </View>
        ))}

        {/* 底部版本号 */}
        <Text style={styles.versionText}>v1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 40,
  },
  section: {
    marginTop: 16,
  },
  sectionTitle: {
    fontSize: 13,
    color: '#999',
    fontWeight: '500',
    marginLeft: 28,
    marginBottom: 6,
  },
  sectionCard: {
    backgroundColor: '#FFF',
    marginHorizontal: 16,
    borderRadius: 12,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    height: 52,
  },
  settingItemBorder: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#F0F0F0',
  },
  settingItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingItemLabel: {
    fontSize: 15,
    color: '#333',
    marginLeft: 12,
  },
  settingItemRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingValueText: {
    fontSize: 14,
    color: '#999',
    marginRight: 4,
  },
  versionText: {
    textAlign: 'center',
    color: '#CCC',
    fontSize: 13,
    marginTop: 32,
  },
})
