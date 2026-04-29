// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, TouchableOpacity, Switch } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import type {
  AppAuthorization,
  AppProvider,
} from '@/lib/api/__mocks__/capabilities.mock'

/**
 * AppAuthCard — 单个 OAuth 应用卡
 *
 * 移动端 vs Web:
 *   - Web 是 4 列网格;移动端单列 list,信息密度更高,有更多副文本
 *   - "已连接 / 未连接" 用 Switch 而不是按钮 → 单手快速断开/重连
 *   - 完整的 OAuth 流程通过外层调用 expo-web-browser
 */

interface Props {
  provider: AppProvider
  authorization: AppAuthorization | undefined
  onConnect: (provider: AppProvider) => void
  onDisconnect: (provider: AppProvider, auth: AppAuthorization) => void
}

const PROVIDER_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  feishu: 'chatbubbles',
  dingtalk: 'chatbubbles',
  wecom: 'chatbubbles',
  lark: 'chatbubbles',
  slack: 'chatbubble-ellipses',
  notion: 'book-outline',
  feishu_doc: 'document-text-outline',
  dingtalk_drive: 'cloud-outline',
  google_drive: 'cloud-outline',
  onedrive: 'cloud-outline',
  salesforce: 'business-outline',
  hubspot: 'magnet-outline',
  fxiaoke: 'business-outline',
  xiaoshouyi: 'business-outline',
  shopify: 'cart-outline',
  amazon_seller: 'cart-outline',
  taobao_open: 'cart-outline',
  jd_open: 'cart-outline',
  douyin_open: 'cart-outline',
  qichacha: 'search-outline',
  tianyancha: 'search-outline',
  wenshu: 'library-outline',
  beidafabao: 'library-outline',
  figma: 'color-palette-outline',
  jianying: 'film-outline',
  canva: 'image-outline',
  compliance_gov: 'shield-checkmark-outline',
  creditchina: 'shield-checkmark-outline',
  kingdee: 'cash-outline',
  yongyou: 'cash-outline',
}

export function AppAuthCard({ provider, authorization, onConnect, onDisconnect }: Props) {
  const connected = authorization?.status === 'connected'
  const expired = authorization?.status === 'expired'
  const icon = PROVIDER_ICON[provider.provider_id] ?? 'apps-outline'

  const handleToggle = (next: boolean) => {
    if (next) {
      onConnect(provider)
    } else if (authorization) {
      onDisconnect(provider, authorization)
    }
  }

  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.7}
      onPress={() => connected ? null : onConnect(provider)}
    >
      <View style={styles.iconWrap}>
        <Ionicons name={icon} size={22} color={Colors.primary} />
      </View>
      <View style={styles.body}>
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={1}>
            {provider.display_name}
          </Text>
          {connected && (
            <View style={[styles.pill, { backgroundColor: Colors.success + '20' }]}>
              <Text style={[styles.pillText, { color: Colors.success }]}>已连接</Text>
            </View>
          )}
          {expired && (
            <View style={[styles.pill, { backgroundColor: Colors.warning + '20' }]}>
              <Text style={[styles.pillText, { color: Colors.warning }]}>已过期</Text>
            </View>
          )}
        </View>
        <Text style={styles.desc} numberOfLines={1}>
          {authorization?.account_label ?? provider.description}
        </Text>
      </View>
      <Switch
        value={connected}
        onValueChange={handleToggle}
        trackColor={{ false: Colors.border, true: Colors.primary + '60' }}
        thumbColor={connected ? Colors.primary : Colors.surface}
      />
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.md,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    backgroundColor: Colors.primary + '15',
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  desc: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary, marginTop: 2 },
  pill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  pillText: { fontSize: 10, fontWeight: '600' },
})
