// -*- coding: utf-8 -*-
/**
 * 能力 tab 占位页（V3 P17-A 输出，待 P17-D 替换）。
 *
 * P17-D 接入计划：
 *   - 5 个能力中心入口：合同 / 尽调 / 财税 / 营销 / 出海
 *   - 每个入口下挂载对应 persona 的快捷工具网格
 */

import React from 'react'
import { PlaceholderScreen } from '@/components/Layout'

export default function CapabilitiesTabScreen() {
  return (
    <PlaceholderScreen
      title="能力加载中..."
      hint={'P17-D 完成后将显示 5 个能力中心\n（合同 / 尽调 / 财税 / 营销 / 出海）'}
    />
  )
}
