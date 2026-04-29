// -*- coding: utf-8 -*-
/**
 * 智能体 tab 占位页（V3 P17-A 输出，待 P17-B 替换）。
 *
 * P17-B 接入计划：
 *   - 调用 personasApi.list() 拉取 10 个 persona
 *   - 按 PersonaDomain 分组卡片网格
 *   - 点击进入 persona 工作台
 */

import React from 'react'
import { PlaceholderScreen } from '@/components/Layout'

export default function PersonasTabScreen() {
  return (
    <PlaceholderScreen
      title="智能体加载中..."
      hint={'P17-B 完成后将显示 10 个 persona 列表\n（综合协调 / 合规经营 / 增长获客 / 出海跨境）'}
    />
  )
}
