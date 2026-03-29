// -*- coding: utf-8 -*-
import { useState, useEffect } from 'react'
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  SafeAreaView,
} from 'react-native'
import { router } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { api } from '@/services/api'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'

// 快捷功能入口
const quickActions = [
  { id: 'chat', icon: 'chatbubbles', label: 'AI 法律咨询', route: '/(tabs)/chat', color: Colors.primary },
  { id: 'contract', icon: 'document-text', label: '合同审查', route: '/contracts', color: '#3B82F6' },
  { id: 'lawyer', icon: 'people', label: '找律师', route: '/find-lawyer', color: '#8B5CF6' },
  { id: 'compliance', icon: 'shield-checkmark', label: '合规自检', route: '/contracts', color: '#22C55E' },
] as const

interface NewsItem {
  id: string
  title: string
  date: string
  category: string
}

// @mock-data FALLBACK
const mockNews: NewsItem[] = [
  { id: '1', title: '最高法发布民法典婚姻家庭编解释(二)', date: '2026-03-28', category: '法规解读' },
  { id: '2', title: '新《公司法》实施要点解析', date: '2026-03-27', category: '政策解读' },
  { id: '3', title: '企业数据合规：个人信息保护法实务指南', date: '2026-03-26', category: '合规指引' },
  { id: '4', title: '劳动争议案件裁判规则梳理', date: '2026-03-25', category: '案例分析' },
]

export default function HomeScreen() {
  const [searchText, setSearchText] = useState('')
  const [news, setNews] = useState<NewsItem[]>(mockNews)
  const [refreshing, setRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadNews()
  }, [])

  const loadNews = async () => {
    try {
      const data = await api.get<NewsItem[]>('/news/latest?limit=10')
      if (Array.isArray(data) && data.length > 0) {
        setNews(data)
      }
    } catch {
      // fallback to mock
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = () => {
    setRefreshing(true)
    loadNews()
  }

  const handleSearch = () => {
    if (searchText.trim()) {
      router.push('/(tabs)/chat')
    }
  }

  const renderQuickActions = () => (
    <>
      <Text style={styles.sectionTitle}>快捷服务</Text>
      <View style={styles.quickGrid}>
        {quickActions.map((action) => (
          <TouchableOpacity
            key={action.id}
            style={styles.quickItem}
            onPress={() => router.push(action.route as any)}
            activeOpacity={0.7}
          >
            <View style={[styles.quickIcon, { backgroundColor: action.color + '15' }]}>
              <Ionicons name={action.icon as any} size={28} color={action.color} />
            </View>
            <Text style={styles.quickLabel}>{action.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <Text style={styles.sectionTitle}>法律资讯</Text>
    </>
  )

  const renderNewsItem = ({ item }: { item: NewsItem }) => (
    <TouchableOpacity
      style={styles.newsCard}
      onPress={() => router.push('/(tabs)/chat')}
      activeOpacity={0.7}
    >
      <View style={styles.newsCategory}>
        <Text style={styles.newsCategoryText}>{item.category}</Text>
      </View>
      <Text style={styles.newsTitle} numberOfLines={2}>
        {item.title}
      </Text>
      <Text style={styles.newsDate}>{item.date}</Text>
    </TouchableOpacity>
  )

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* 搜索栏 */}
        <View style={styles.searchBar}>
          <Ionicons name="search" size={20} color={Colors.textSecondary} />
          <TextInput
            style={styles.searchInput}
            placeholder="搜索法律问题、法规、案例..."
            placeholderTextColor={Colors.textMuted}
            value={searchText}
            onChangeText={setSearchText}
            onSubmitEditing={handleSearch}
            returnKeyType="search"
          />
          {searchText.length > 0 && (
            <TouchableOpacity onPress={() => setSearchText('')}>
              <Ionicons name="close-circle" size={18} color={Colors.textMuted} />
            </TouchableOpacity>
          )}
        </View>

        <FlatList
          data={news}
          keyExtractor={(item) => item.id}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={Colors.primary}
            />
          }
          ListHeaderComponent={renderQuickActions}
          renderItem={renderNewsItem}
          ListEmptyComponent={
            loading ? (
              <ActivityIndicator color={Colors.primary} style={{ marginTop: 20 }} />
            ) : null
          }
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />
      </View>
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
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    marginHorizontal: Layout.spacing.md,
    marginVertical: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: 10,
    borderRadius: Layout.borderRadius.md,
    gap: Layout.spacing.sm,
  },
  searchInput: {
    flex: 1,
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    paddingVertical: 0,
  },
  listContent: {
    paddingHorizontal: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
  },
  sectionTitle: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.lg,
    marginBottom: Layout.spacing.md,
  },
  quickGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  quickItem: {
    width: '23%',
    alignItems: 'center',
    paddingVertical: Layout.spacing.sm,
  },
  quickIcon: {
    width: 56,
    height: 56,
    borderRadius: Layout.borderRadius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickLabel: {
    fontSize: Layout.fontSize.xs,
    color: Colors.text,
    textAlign: 'center',
    marginTop: Layout.spacing.sm,
  },
  newsCard: {
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    padding: Layout.spacing.md,
    marginBottom: Layout.spacing.sm,
  },
  newsCategory: {
    backgroundColor: Colors.primary + '15',
    alignSelf: 'flex-start',
    paddingHorizontal: Layout.spacing.sm,
    paddingVertical: 2,
    borderRadius: Layout.borderRadius.sm,
    marginBottom: Layout.spacing.sm,
  },
  newsCategoryText: {
    fontSize: Layout.fontSize.xs,
    color: Colors.primary,
    fontWeight: '500',
  },
  newsTitle: {
    fontSize: Layout.fontSize.md,
    fontWeight: '600',
    color: Colors.text,
    lineHeight: 22,
    marginBottom: Layout.spacing.xs,
  },
  newsDate: {
    fontSize: Layout.fontSize.xs,
    color: Colors.textMuted,
  },
})
