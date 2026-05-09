<template>
  <view class="anxin-page">
    <view class="anxin-card">
      <text class="title">登录</text>
      <text class="body anxin-muted">微信登录和账号登录会通过统一 auth service 接入，local/top-secret 模式下会在发起网络前阻断。</text>
    </view>
  </view>
</template>

<script setup lang="ts"></script>

<style scoped lang="scss">
.title {
  display: block;
  font-size: 32rpx;
  font-weight: 600;
}

.body {
  display: block;
  margin-top: 16rpx;
}
</style>
