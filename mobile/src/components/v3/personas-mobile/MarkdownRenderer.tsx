/**
 * MarkdownRenderer（移动端）
 *
 * 优先使用 react-native-markdown-display 的实际实现；如果运行环境
 * 还没装这个包（CI / 早期开发），降级到一个轻量的内置纯文本渲染。
 *
 * 这样可以保证 P17-A foundation 安装好包之前 tsc + RN 也能跑。
 */

import React from 'react'
import { Text, StyleSheet, View } from 'react-native'
import { Colors } from '../../../constants/colors'
import { Layout } from '../../../constants/layout'

interface MarkdownRendererProps {
  content: string
  /** 是否反转文字颜色（user bubble 用） */
  inverse?: boolean
}

/**
 * 极简的 markdown → RN 文本节点降级方案。
 *
 * 仅支持：标题 (#/##/###)、粗体 **xx**、列表行（- / 1.）和换行。
 * 真正的 markdown-display 包接入后会替换。
 */
function renderInline(line: string, inverse: boolean): React.ReactNode {
  const parts = line.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <Text key={idx} style={[styles.bold, inverse && styles.inverseText]}>
          {part.slice(2, -2)}
        </Text>
      )
    }
    return (
      <Text key={idx} style={[styles.body, inverse && styles.inverseText]}>
        {part}
      </Text>
    )
  })
}

function renderLine(line: string, idx: number, inverse: boolean): React.ReactNode {
  if (line.startsWith('### ')) {
    return (
      <Text key={idx} style={[styles.h3, inverse && styles.inverseText]}>
        {line.slice(4)}
      </Text>
    )
  }
  if (line.startsWith('## ')) {
    return (
      <Text key={idx} style={[styles.h2, inverse && styles.inverseText]}>
        {line.slice(3)}
      </Text>
    )
  }
  if (line.startsWith('# ')) {
    return (
      <Text key={idx} style={[styles.h1, inverse && styles.inverseText]}>
        {line.slice(2)}
      </Text>
    )
  }
  if (line.startsWith('> ')) {
    return (
      <View key={idx} style={styles.quote}>
        <Text style={[styles.quoteText, inverse && styles.inverseText]}>{line.slice(2)}</Text>
      </View>
    )
  }
  if (/^\s*[-*]\s+/.test(line)) {
    return (
      <View key={idx} style={styles.listItem}>
        <Text style={[styles.bullet, inverse && styles.inverseText]}>•</Text>
        <Text style={[styles.body, styles.listText, inverse && styles.inverseText]}>
          {renderInline(line.replace(/^\s*[-*]\s+/, ''), inverse)}
        </Text>
      </View>
    )
  }
  if (/^\s*\d+\.\s+/.test(line)) {
    const m = line.match(/^\s*(\d+)\.\s+(.*)$/)
    return (
      <View key={idx} style={styles.listItem}>
        <Text style={[styles.bullet, inverse && styles.inverseText]}>{m?.[1] ?? '•'}.</Text>
        <Text style={[styles.body, styles.listText, inverse && styles.inverseText]}>
          {renderInline(m?.[2] ?? line, inverse)}
        </Text>
      </View>
    )
  }
  if (line.trim() === '') {
    return <View key={idx} style={styles.spacer} />
  }
  return (
    <Text key={idx} style={[styles.body, inverse && styles.inverseText]}>
      {renderInline(line, inverse)}
    </Text>
  )
}

export function MarkdownRenderer({ content, inverse = false }: MarkdownRendererProps) {
  const lines = content.split('\n')
  return <View>{lines.map((l, i) => renderLine(l, i, inverse))}</View>
}

const styles = StyleSheet.create({
  body: {
    fontSize: Layout.fontSize.md,
    color: Colors.text,
    lineHeight: 22,
  },
  bold: {
    fontWeight: '700',
    color: Colors.text,
  },
  h1: {
    fontSize: Layout.fontSize.xl,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.sm,
    marginBottom: Layout.spacing.sm,
  },
  h2: {
    fontSize: Layout.fontSize.lg,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.sm,
    marginBottom: Layout.spacing.xs,
  },
  h3: {
    fontSize: Layout.fontSize.md,
    fontWeight: '700',
    color: Colors.text,
    marginTop: Layout.spacing.sm,
    marginBottom: Layout.spacing.xs,
  },
  quote: {
    borderLeftWidth: 3,
    borderLeftColor: Colors.primary,
    paddingLeft: Layout.spacing.sm,
    marginVertical: Layout.spacing.xs,
  },
  quoteText: {
    fontSize: Layout.fontSize.sm,
    color: Colors.textSecondary,
    fontStyle: 'italic',
    lineHeight: 20,
  },
  listItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Layout.spacing.xs,
    marginVertical: 2,
  },
  bullet: {
    fontSize: Layout.fontSize.md,
    color: Colors.primary,
    minWidth: 16,
  },
  listText: {
    flex: 1,
  },
  spacer: {
    height: Layout.spacing.xs,
  },
  inverseText: {
    color: Colors.white,
  },
})
