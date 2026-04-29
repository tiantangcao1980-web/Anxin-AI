// -*- coding: utf-8 -*-
// PLACEHOLDER for P21-B —— 任务中心 tabBar 入口。
// P21-B 会用真实任务列表 UI 覆盖；当前仅保证 build 通过。
import { View, Text } from '@tarojs/components'

export default function TasksIndex() {
  return (
    <View style='padding: 96rpx 48rpx; text-align: center;'>
      <Text style='display: block; font-size: 96rpx; margin-bottom: 32rpx;'>📋</Text>
      <Text style='display: block; font-size: 32rpx; color: #1D2129; font-weight: 600;'>
        任务中心
      </Text>
      <Text style='display: block; font-size: 24rpx; color: #86909C; margin-top: 16rpx;'>
        P21-B 即将就位
      </Text>
    </View>
  )
}
