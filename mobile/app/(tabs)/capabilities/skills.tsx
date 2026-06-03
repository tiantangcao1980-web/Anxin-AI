// -*- coding: utf-8 -*-
import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  View,
  Text,
  StyleSheet,
  SectionList,
  RefreshControl,
  ActivityIndicator,
  TouchableOpacity,
  TextInput,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import { SkillToggleRow } from '@/components/v3/capabilities-mobile/SkillToggleRow'
import {
  skillsApi,
  type Skill,
  type SkillCategory,
} from '@/lib/api/skills'

/**
 * 技能列表页 — 按域分组的开关列表 (P17-D)
 *
 * 移动端关键差异:
 *   - Web 用 sidebar+grid;移动端用 SectionList,域名作 sticky header
 *   - 搜索框始终可见,顶部固定
 *   - Switch 即时生效 + Optimistic UI
 */

const CATEGORY_LABEL: Record<SkillCategory, string> = {
  legal: '法律',
  tax_finance: '财税',
  operations: '运营',
  research: '调研',
  marketing: '营销',
  content: '内容',
  design: '设计',
  office: '办公',
  ecommerce: '跨境电商',
  sales: '销售',
  intelligence: '情报',
  decision: '决策',
  system: '系统',
}

export default function SkillsScreen() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await skillsApi.list()
      setSkills(data)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const onRefresh = () => {
    setRefreshing(true)
    load()
  }

  const handleToggle = async (skill: Skill, next: boolean) => {
    // Optimistic
    setSkills((prev) =>
      prev.map((s) => (s.name === skill.name ? { ...s, enabled: next } : s)),
    )
    try {
      await skillsApi.toggle(skill.name, next)
    } catch {
      setSkills((prev) =>
        prev.map((s) => (s.name === skill.name ? { ...s, enabled: skill.enabled } : s)),
      )
    }
  }

  const sections = useMemo(() => {
    const q = search.trim().toLowerCase()
    const filtered = q
      ? skills.filter(
          (s) =>
            s.display_name.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.triggers.some((t) => t.toLowerCase().includes(q)),
        )
      : skills

    const grouped = new Map<SkillCategory, Skill[]>()
    for (const s of filtered) {
      const arr = grouped.get(s.category) ?? []
      arr.push(s)
      grouped.set(s.category, arr)
    }
    return Array.from(grouped.entries()).map(([cat, items]) => ({
      title: CATEGORY_LABEL[cat],
      data: items,
      enabledCount: items.filter((s) => s.enabled).length,
    }))
  }, [skills, search])

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <View style={styles.searchBar}>
        <Ionicons name="search" size={16} color={Colors.textMuted} />
        <TextInput
          placeholder="搜索技能 / 触发词"
          placeholderTextColor={Colors.textMuted}
          value={search}
          onChangeText={setSearch}
          style={styles.searchInput}
          returnKeyType="search"
        />
        {!!search && (
          <TouchableOpacity onPress={() => setSearch('')}>
            <Ionicons name="close-circle" size={16} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
      </View>
      {loading && skills.length === 0 ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <SectionList
          sections={sections}
          keyExtractor={(s) => s.name}
          stickySectionHeadersEnabled
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
          }
          renderSectionHeader={({ section }) => (
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>{section.title}</Text>
              <Text style={styles.sectionCount}>
                {section.enabledCount} / {section.data.length}
              </Text>
            </View>
          )}
          renderItem={({ item }) => (
            <SkillToggleRow skill={item} onToggle={handleToggle} />
          )}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="sparkles-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>没有匹配的技能</Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginHorizontal: Layout.spacing.md,
    marginVertical: Layout.spacing.sm,
    paddingHorizontal: 12,
    height: 38,
    borderRadius: 10,
    backgroundColor: Colors.surface,
  },
  searchInput: {
    flex: 1,
    color: Colors.text,
    fontSize: Layout.fontSize.sm,
    paddingVertical: 0,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: 8,
    backgroundColor: Colors.surface,
  },
  sectionTitle: { fontSize: Layout.fontSize.sm, fontWeight: '700', color: Colors.text },
  sectionCount: { fontSize: 11, color: Colors.textSecondary },
  empty: { alignItems: 'center', paddingVertical: 60, gap: 12 },
  emptyText: { color: Colors.textSecondary },
})
