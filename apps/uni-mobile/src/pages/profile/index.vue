<template>
  <view class="profile-page">
    <!-- 用户卡片 -->
    <view class="user-card">
      <view class="avatar">
        <text>{{ user.avatar }}</text>
      </view>
      <view class="user-info">
        <text class="user-name">{{ user.name }}</text>
        <text class="user-email">{{ user.email }}</text>
      </view>
      <view class="plan-badge">
        <text>{{ user.plan }}</text>
      </view>
    </view>

    <!-- 订阅信息 -->
    <view class="section">
      <view class="section-header">
        <text class="section-title">我的订阅</text>
      </view>
      <view class="sub-card" @tap="goSubscription">
        <view class="sub-row">
          <text class="sub-label">当前套餐</text>
          <text class="sub-value">{{ user.plan }}</text>
        </view>
        <view class="sub-row">
          <text class="sub-label">到期时间</text>
          <text class="sub-value">{{ user.expireAt }}</text>
        </view>
        <view class="sub-action">
          <text>续费 / 升级</text>
          <text class="arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 功能入口 -->
    <view class="section">
      <view class="menu">
        <view class="menu-item" v-for="m in menuItems" :key="m.label" @tap="goMenu(m)">
          <text class="menu-icon">{{ m.icon }}</text>
          <text class="menu-label">{{ m.label }}</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- 设置 -->
    <view class="section">
      <view class="menu">
        <view class="menu-item" @tap="goMenu({ key: 'settings', label: '通用设置' })">
          <text class="menu-icon">⚙️</text>
          <text class="menu-label">通用设置</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item" @tap="goAbout">
          <text class="menu-icon">ℹ️</text>
          <text class="menu-label">关于</text>
          <text class="menu-arrow">›</text>
        </view>
        <view class="menu-item logout" @tap="logout">
          <text class="menu-icon">🚪</text>
          <text class="menu-label">退出登录</text>
        </view>
      </view>
    </view>

    <view class="demo-badge">
      <text>演示版 · v0.1.0-demo</text>
    </view>
  </view>
</template>

<script setup lang="ts">
const user = {
  avatar: '安',
  name: '张先生（演示账号）',
  email: 'demo@anxinai.com',
  plan: '专业版',
  expireAt: '2026-06-30',
}

const menuItems = [
  { key: 'contracts', icon: '📄', label: '我的合同' },
  { key: 'kb', icon: '📚', label: '知识库' },
  { key: 'messages', icon: '💬', label: '消息中心' },
  { key: 'desktop', icon: '🖥️', label: '桌面端控制' },
]

function goSubscription() {
  uni.showToast({ title: '跳转订阅页（demo）', icon: 'none' })
}

function goMenu(m: { key: string; label: string }) {
  if (m.key === 'desktop') {
    uni.navigateTo({ url: '/pages/desktop-control/index' })
    return
  }
  uni.showToast({ title: `${m.label}（demo）`, icon: 'none' })
}

function goAbout() {
  uni.showModal({
    title: '关于安心智能助手',
    content: '版本：v0.1.0-demo\n品牌：安心智能助手 V3\n主办方：安心科技\n\n本应用为对内演示版。',
    showCancel: false,
  })
}

function logout() {
  uni.showModal({
    title: '确认退出？',
    content: '退出后需要重新登录',
    success(res) {
      if (res.confirm) {
        uni.reLaunch({ url: '/pages/auth/login' })
      }
    },
  })
}
</script>

<style scoped lang="scss">
.profile-page {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 32rpx;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 40rpx 32rpx;
  background: linear-gradient(135deg, #2563eb, #3b82f6);
}
.avatar {
  width: 96rpx;
  height: 96rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
  color: #fff;
  font-weight: 600;
}
.user-info {
  flex: 1;
}
.user-name {
  display: block;
  font-size: 32rpx;
  font-weight: 600;
  color: #fff;
}
.user-email {
  display: block;
  margin-top: 4rpx;
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
}
.plan-badge {
  padding: 8rpx 16rpx;
  background: rgba(255, 255, 255, 0.25);
  border-radius: 100rpx;
  text {
    font-size: 22rpx;
    color: #fff;
  }
}

.section {
  margin: 24rpx 24rpx 0;
}
.section-header {
  padding: 0 12rpx 12rpx;
}
.section-title {
  font-size: 26rpx;
  color: #6b7280;
}

.sub-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
}
.sub-row {
  display: flex;
  justify-content: space-between;
  padding: 10rpx 0;
}
.sub-label {
  font-size: 26rpx;
  color: #6b7280;
}
.sub-value {
  font-size: 28rpx;
  color: #1f2937;
  font-weight: 500;
}
.sub-action {
  margin-top: 16rpx;
  padding-top: 16rpx;
  border-top: 1rpx solid #f3f4f6;
  display: flex;
  justify-content: space-between;
  color: #2563eb;
  font-size: 26rpx;
}
.sub-action .arrow {
  color: #2563eb;
}

.menu {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 28rpx 24rpx;
  border-bottom: 1rpx solid #f3f4f6;
}
.menu-item:last-child {
  border-bottom: none;
}
.menu-icon {
  font-size: 32rpx;
  width: 40rpx;
  text-align: center;
}
.menu-label {
  flex: 1;
  font-size: 28rpx;
  color: #1f2937;
}
.menu-arrow {
  color: #9ca3af;
}
.menu-item.logout .menu-label {
  color: #ef4444;
}

.demo-badge {
  margin-top: 40rpx;
  text-align: center;
  text {
    font-size: 22rpx;
    color: #9ca3af;
  }
}
</style>
