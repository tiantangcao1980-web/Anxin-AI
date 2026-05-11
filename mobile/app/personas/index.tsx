/**
 * Personas 入口（移动端 P17-C）
 *
 * 10 个 user-facing persona,2 列网格,pull-to-refresh。
 * 点击任一卡片进入 `/personas/[personaId]`。
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  View,
  Text,
  FlatList,
  RefreshControl,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native'
import { router, Stack } from 'expo-router'
import { Colors } from '../../src/constants/colors'
import { Layout } from '../../src/constants/layout'
import { PersonaCard } from '../../src/components/v3/personas-mobile/PersonaCard'
import { PERSONAS, type PersonaMeta } from '../../src/lib/personas/registry'
import { mockListPersonas } from '../../src/lib/api/__mocks__/personas.mock'

export default function PersonasIndexScreen() {
  const [personas, setPersonas] = useState<PersonaMeta[]>(PERSONAS)
  const [refreshing, setRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const list = await mockListPersonas()
      setPersonas(list)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleRefresh = () => {
    setRefreshing(true)
    load()
  }

  const handleEnter = (persona: PersonaMeta) => {
    router.push({ pathname: '/personas/[personaId]', params: { personaId: persona.persona_id } })
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen options={{ title: '智能体' }} />
      <View style={styles.heroBlock}>
        <Text style={styles.heroEyebrow}>V3 智能体工作台</Text>
        <Text style={styles.heroTitle}>10 位智能体随时待命</Text>
        <Text style={styles.heroDesc}>
          法务 / 财税 / 调研 / 获客 / 内容 / 出海 一手通办,选一位开始。
        </Text>
      </View>

      {loading && personas.length === 0 ? (
        <View style={styles.center}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <FlatList
          data={personas}
          keyExtractor={(p) => p.persona_id}
          numColumns={2}
          columnWrapperStyle={styles.row}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => (
            <PersonaCard persona={item} onPress={() => handleEnter(item)} />
          )}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={Colors.primary}
            />
          }
          showsVerticalScrollIndicator={false}
          ItemSeparatorComponent={() => <View style={{ height: 0 }} />}
        />
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  heroBlock: {
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
    paddingBottom: Layout.spacing.sm,
  },
  heroEyebrow: {
    fontSize: Layout.fontSize.xs,
    color: Colors.primary,
    fontWeight: '600',
  },
  heroTitle: {
    marginTop: 4,
    fontSize: Layout.fontSize.xxl,
    fontWeight: '700',
    color: Colors.text,
  },
  heroDesc: {
    marginTop: Layout.spacing.xs,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
  listContent: {
    paddingHorizontal: Layout.spacing.md,
    paddingBottom: Layout.spacing.xl,
  },
  row: {
    gap: Layout.spacing.sm,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
})
