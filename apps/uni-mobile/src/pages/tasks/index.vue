<template>
  <view class="tasks-page">
    <view class="tabs">
      <view
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ active: activeTab === t.key }"
        @tap="activeTab = t.key"
      >
        <text>{{ t.label }}</text>
        <text v-if="t.count > 0" class="badge">{{ t.count }}</text>
      </view>
    </view>

    <scroll-view class="task-list" scroll-y>
      <view v-if="filteredTasks.length === 0" class="empty">
        <text>暂无{{ tabLabel }}任务</text>
      </view>
      <view
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-card"
        @tap="goDetail(task.id)"
      >
        <view class="task-header">
          <text class="task-title">{{ task.title }}</text>
          <text class="task-status" :class="'status-' + task.status">{{ statusLabel(task.status) }}</text>
        </view>
        <text class="task-persona">{{ task.persona }}</text>
        <view class="task-meta">
          <text class="meta-item">⏱ {{ task.createdAt }}</text>
          <text v-if="task.progress !== undefined" class="meta-item">{{ task.progress }}%</text>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

type TaskStatus = 'queued' | 'running' | 'completed' | 'failed'
type TabKey = 'all' | 'running' | 'completed'

interface Task {
  id: string
  title: string
  persona: string
  status: TaskStatus
  progress?: number
  createdAt: string
}

const activeTab = ref<TabKey>('all')

// Demo 版：mock 任务数据
const tasks = ref<Task[]>([
  { id: 't1', title: '审查销售合同 v3.2', persona: '合同管家', status: 'running', progress: 65, createdAt: '10 分钟前' },
  { id: 't2', title: '北京市劳动法咨询回复', persona: '法律顾问', status: 'completed', createdAt: '1 小时前' },
  { id: 't3', title: '行业竞品分析（AI 法律科技）', persona: '市场研究员', status: 'running', progress: 30, createdAt: '30 分钟前' },
  { id: 't4', title: '个税筹划报告', persona: '财税顾问', status: 'queued', createdAt: '刚刚' },
  { id: 't5', title: '公众号文章：合同那些事儿', persona: '内容总监', status: 'completed', createdAt: '昨天 15:20' },
])

const tabs = computed<Array<{ key: TabKey; label: string; count: number }>>(() => [
  { key: 'all', label: '全部', count: tasks.value.length },
  { key: 'running', label: '进行中', count: tasks.value.filter(t => t.status === 'running' || t.status === 'queued').length },
  { key: 'completed', label: '已完成', count: tasks.value.filter(t => t.status === 'completed').length },
])

const filteredTasks = computed(() => {
  if (activeTab.value === 'running') {
    return tasks.value.filter(t => t.status === 'running' || t.status === 'queued')
  }
  if (activeTab.value === 'completed') {
    return tasks.value.filter(t => t.status === 'completed')
  }
  return tasks.value
})

const tabLabel = computed(() => tabs.value.find(t => t.key === activeTab.value)?.label ?? '')

function statusLabel(s: TaskStatus): string {
  return { queued: '排队中', running: '进行中', completed: '已完成', failed: '失败' }[s]
}

function goDetail(taskId: string) {
  uni.showToast({ title: `任务 ${taskId}（demo）`, icon: 'none' })
}
</script>

<style scoped lang="scss">
.tasks-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
}
.tabs {
  display: flex;
  background: #fff;
  border-bottom: 1rpx solid #e5e7eb;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 24rpx;
  font-size: 28rpx;
  color: #6b7280;
  position: relative;
}
.tab.active {
  color: #2563eb;
  font-weight: 600;
}
.tab.active::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: 48rpx;
  height: 4rpx;
  background: #2563eb;
  border-radius: 2rpx;
}
.badge {
  margin-left: 6rpx;
  font-size: 22rpx;
  color: #9ca3af;
}
.task-list {
  flex: 1;
  padding: 20rpx;
}
.empty {
  text-align: center;
  color: #9ca3af;
  font-size: 26rpx;
  padding: 120rpx 0;
}
.task-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
}
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10rpx;
}
.task-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
  flex: 1;
}
.task-status {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 100rpx;
}
.status-running { background: #dbeafe; color: #1e40af; }
.status-completed { background: #d1fae5; color: #065f46; }
.status-queued { background: #fef3c7; color: #92400e; }
.status-failed { background: #fee2e2; color: #991b1b; }
.task-persona {
  font-size: 24rpx;
  color: #6b7280;
}
.task-meta {
  margin-top: 12rpx;
  display: flex;
  gap: 20rpx;
}
.meta-item {
  font-size: 22rpx;
  color: #9ca3af;
}
</style>
