/**
 * Persona 能力清单（移动端 P17-C）
 *
 * 列出该 persona 全部 capability,点击触发 mock,把结果推到一个 modal-like
 * 区块（这里用底部展开块,简化为页内显示）。
 */

import React, { useCallback, useState } from 'react'
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native'
import { Stack, router, useLocalSearchParams } from 'expo-router'
import { Colors } from '../../../src/constants/colors'
import { Layout } from '../../../src/constants/layout'
import { CapabilityCard } from '../../../src/components/v3/personas-mobile/CapabilityCard'
import { MarkdownRenderer } from '../../../src/components/v3/personas-mobile/MarkdownRenderer'
import { getPersonaMeta, type PersonaCapability } from '../../../src/lib/personas/registry'
import { chatWithPersona } from '../../../src/lib/api/personas'

export default function PersonaCapabilitiesScreen() {
  const params = useLocalSearchParams<{ personaId: string }>()
  const personaId = String(params.personaId || '')
  const persona = getPersonaMeta(personaId)
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [resultLabel, setResultLabel] = useState<string | null>(null)
  const [resultContent, setResultContent] = useState<string | null>(null)

  const handleTrigger = useCallback(
    async (cap: PersonaCapability) => {
      if (pendingId) return
      setPendingId(cap.id)
      setResultLabel(cap.label)
      setResultContent(null)
      try {
        // 真实接入：把该能力的 sample prompt 发往 `POST /personas/{id}/chat`
        // （personas.py:101）。后端暂无「按 capability_id 直接路由」的通用 endpoint，
        // 故复用通用对话；各 persona 专属结构化 endpoint 的逐能力映射留待 P17-E。
        const result = await chatWithPersona(personaId, {
          message: `[${cap.label}] ${cap.prompt}`,
        })
        setResultContent(result.content)
      } catch (e) {
        setResultContent(`❌ 调用失败: ${e instanceof Error ? e.message : String(e)}`)
      } finally {
        setPendingId(null)
      }
    },
    [personaId, pendingId],
  )

  if (!persona) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <Stack.Screen options={{ title: '能力清单' }} />
        <View style={styles.center}>
          <Text style={styles.errorText}>未找到该智能体</Text>
          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.linkText}>返回</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen
        options={{
          title: `${persona.emoji} 能力清单`,
          headerBackTitle: persona.display_name,
        }}
      />
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.heroBlock}>
          <Text style={styles.heroTitle}>共 {persona.capabilities.length} 项能力</Text>
          <Text style={styles.heroDesc}>点击任一能力即可一键触发,无需描述需求。</Text>
        </View>
        <View style={styles.listBlock}>
          {persona.capabilities.map((cap) => (
            <CapabilityCard
              key={cap.id}
              capability={cap}
              pending={pendingId === cap.id}
              onTrigger={handleTrigger}
            />
          ))}
        </View>

        {(resultLabel || resultContent) && (
          <View style={styles.resultBlock}>
            <View style={styles.resultHeader}>
              <Text style={styles.resultTitle}>📤 {resultLabel} 结果</Text>
              {pendingId && <ActivityIndicator size="small" color={Colors.primary} />}
            </View>
            {resultContent ? (
              <MarkdownRenderer content={resultContent} />
            ) : (
              <Text style={styles.resultPlaceholder}>等待中...</Text>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollContent: {
    paddingBottom: Layout.spacing.xl,
  },
  heroBlock: {
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
  },
  heroTitle: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
    color: Colors.text,
  },
  heroDesc: {
    marginTop: 4,
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    lineHeight: 20,
  },
  listBlock: {
    paddingHorizontal: Layout.spacing.md,
    paddingTop: Layout.spacing.md,
  },
  resultBlock: {
    marginTop: Layout.spacing.lg,
    marginHorizontal: Layout.spacing.md,
    padding: Layout.spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Layout.borderRadius.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  resultHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Layout.spacing.sm,
  },
  resultTitle: {
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    color: Colors.text,
  },
  resultPlaceholder: {
    color: Colors.textMuted,
    fontSize: Layout.fontSize.sm,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Layout.spacing.md,
  },
  errorText: {
    color: Colors.textSecondary,
    fontSize: Layout.fontSize.md,
  },
  linkText: {
    color: Colors.primary,
    fontSize: Layout.fontSize.sm,
    fontWeight: '600',
  },
})
