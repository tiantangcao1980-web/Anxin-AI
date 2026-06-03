// -*- coding: utf-8 -*-
import { View, Text, StyleSheet, Switch } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Colors } from '@/constants/colors'
import { Layout } from '@/constants/layout'
import type { ScheduledTask } from '@/lib/api/scheduledTasks'

/**
 * ScheduledTaskRow — 定时任务行
 *
 * 移动端做法:
 *   - 状态用左侧色条 + 中部胶囊体现 (active/paused/failed)
 *   - 关键 cron 信息单行人类可读
 *   - 快速暂停/恢复 Switch (即时反馈)
 */

interface Props {
  task: ScheduledTask
  onToggle: (task: ScheduledTask, next: boolean) => void
}

const STATUS_LABEL: Record<ScheduledTask['status'], string> = {
  active: '运行中',
  paused: '已暂停',
  failed: '失败',
}

const STATUS_TONE: Record<ScheduledTask['status'], string> = {
  active: Colors.success,
  paused: Colors.textMuted,
  failed: Colors.error,
}

export function ScheduledTaskRow({ task, onToggle }: Props) {
  const tone = STATUS_TONE[task.status]
  return (
    <View style={styles.row}>
      <View style={[styles.bar, { backgroundColor: tone }]} />
      <View style={styles.body}>
        <View style={styles.titleRow}>
          <Text style={styles.title} numberOfLines={1}>
            {task.name}
          </Text>
          <View style={[styles.pill, { backgroundColor: tone + '20' }]}>
            <Text style={[styles.pillText, { color: tone }]}>
              {STATUS_LABEL[task.status]}
            </Text>
          </View>
        </View>

        <View style={styles.metaRow}>
          <Ionicons name="time-outline" size={12} color={Colors.textMuted} />
          <Text style={styles.meta}>{task.cron_human}</Text>
          <Text style={styles.dot}>·</Text>
          <Text style={styles.meta}>下次 {fmtTime(task.next_run_at)}</Text>
        </View>

        <View style={styles.metaRow}>
          {task.last_run_ok === false && (
            <>
              <Ionicons name="alert-circle" size={12} color={Colors.error} />
              <Text style={[styles.meta, { color: Colors.error }]}>上次执行失败</Text>
            </>
          )}
          {task.last_run_ok === true && (
            <>
              <Ionicons name="checkmark-circle" size={12} color={Colors.success} />
              <Text style={styles.meta}>上次成功 · {fmtTime(task.last_run_at!)}</Text>
            </>
          )}
          {task.last_run_ok === null && (
            <Text style={styles.meta}>尚未执行</Text>
          )}
        </View>
      </View>
      <Switch
        value={task.status === 'active'}
        onValueChange={(v) => onToggle(task, v)}
        trackColor={{ false: Colors.border, true: Colors.primary + '60' }}
        thumbColor={task.status === 'active' ? Colors.primary : Colors.surface}
      />
    </View>
  )
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return iso
  }
}
function pad(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Layout.spacing.sm,
    paddingHorizontal: Layout.spacing.md,
    paddingVertical: Layout.spacing.md,
    backgroundColor: Colors.background,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  bar: { width: 3, alignSelf: 'stretch', borderRadius: 2 },
  body: { flex: 1 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { flex: 1, fontSize: Layout.fontSize.md, fontWeight: '600', color: Colors.text },
  pill: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  pillText: { fontSize: 10, fontWeight: '600' },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 4 },
  meta: { fontSize: Layout.fontSize.xs, color: Colors.textSecondary },
  dot: { color: Colors.textMuted, fontSize: Layout.fontSize.xs },
})
