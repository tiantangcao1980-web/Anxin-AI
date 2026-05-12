<template>
  <view class="anxin-page">
    <view class="hero">
      <text class="hero-title">安心智能助手</text>
      <text class="hero-sub">AI 驱动的法务 / 运营 / 财税一体化</text>
    </view>

    <view class="persona-grid">
      <view
        v-for="p in personas"
        :key="p.id"
        class="persona-card"
        @tap="goChat(p.id)"
      >
        <text class="persona-emoji">{{ p.emoji }}</text>
        <text class="persona-name">{{ p.name }}</text>
        <text class="persona-desc">{{ p.desc }}</text>
      </view>
    </view>

    <view class="quick-actions">
      <view class="action-row" @tap="goTasks">
        <text class="action-label">📋 我的任务</text>
        <text class="action-arrow">›</text>
      </view>
      <view class="action-row" @tap="goKb">
        <text class="action-label">📚 法规知识库</text>
        <text class="action-arrow">›</text>
      </view>
    </view>

    <view class="demo-badge">
      <text>演示版 · Demo</text>
    </view>
  </view>
</template>

<script setup lang="ts">
const personas = [
  { id: 'legal_advisor', emoji: '⚖️', name: '法律顾问', desc: '合同审查 · 合规答疑' },
  { id: 'contract_steward', emoji: '📄', name: '合同管家', desc: '起草 · 审查 · 风险' },
  { id: 'tax_finance', emoji: '💰', name: '财税顾问', desc: '个税 · 企税 · 筹划' },
  { id: 'market_researcher', emoji: '🔍', name: '市场研究员', desc: '公司 · 行业 · 竞品' },
  { id: 'content_director', emoji: '✍️', name: '内容总监', desc: '文章 · 视频 · 品牌' },
  { id: 'ecommerce', emoji: '🛒', name: '跨境电商', desc: '选品 · 议价 · 合规' },
]

function goChat(personaId: string) {
  uni.navigateTo({ url: `/pages/chat/index?persona=${personaId}` })
}
function goTasks() {
  uni.switchTab({ url: '/pages/tasks/index' })
}
function goKb() {
  uni.showToast({ title: '知识库 demo', icon: 'none' })
}
</script>

<style scoped lang="scss">
.hero {
  padding: 40rpx 32rpx 32rpx;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
  border-radius: 0 0 24rpx 24rpx;
}
.hero-title {
  display: block;
  font-size: 44rpx;
  font-weight: 700;
  color: #fff;
}
.hero-sub {
  display: block;
  margin-top: 8rpx;
  font-size: 26rpx;
  color: rgba(255, 255, 255, 0.85);
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  padding: 24rpx;
}
.persona-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 20rpx;
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.persona-emoji {
  font-size: 44rpx;
}
.persona-name {
  font-size: 30rpx;
  font-weight: 600;
  color: #1f2937;
}
.persona-desc {
  font-size: 22rpx;
  color: #6b7280;
}

.quick-actions {
  margin: 0 24rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}
.action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28rpx 24rpx;
  border-bottom: 1rpx solid #f3f4f6;
}
.action-label {
  font-size: 28rpx;
  color: #1f2937;
}
.action-arrow {
  color: #9ca3af;
  font-size: 32rpx;
}

.demo-badge {
  margin: 32rpx auto;
  padding: 8rpx 20rpx;
  background: #fef3c7;
  border-radius: 100rpx;
  width: fit-content;
  text {
    font-size: 22rpx;
    color: #92400e;
  }
}
</style>
