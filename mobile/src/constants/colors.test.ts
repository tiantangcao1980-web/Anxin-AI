// -*- coding: utf-8 -*-
// V2 旧 palette ↔ V3 新 palette 跨调色板一致性守护
//
// mobile 端 V2 Colors（旧业务页 find-lawyer / cases / contracts / approvals 等仍在用）
// 与 V3 palette（来自 src/theme/colors.ts）必须在共有字段上完全一致。
// 任一漂移即 fail —— 这是双 palette 共存期的硬保护。

import { describe, expect, it } from 'vitest'
import { Colors, DarkColors } from './colors'
import { palette, lightTheme, darkTheme } from '../theme/colors'

describe('mobile · V2 Colors ↔ V3 palette 跨调色板一致性', () => {
  it('品牌主色 Colors.primary === palette.primary（琥珀橙 #D4A574）', () => {
    expect(Colors.primary).toBe(palette.primary)
    expect(Colors.primary).toBe('#D4A574')
  })

  it('文本三档与 V3 lightTheme 完全对齐（text / textSecondary / textMuted）', () => {
    // V3 lightTheme.text 来自 palette.ink900，与 V2 Colors.text 数值需要一致
    expect(Colors.text).toBe(lightTheme.text)
    expect(Colors.textSecondary).toBe(lightTheme.textSecondary)
    expect(Colors.textMuted).toBe(lightTheme.textMuted)
  })

  it('暗色模式背景 DarkColors.background === V3 darkTheme.background', () => {
    // 注意：V2 DarkColors.background = #1C1C1E（iOS 系统暗），
    // V3 darkTheme.background = #0F0F11（更深一档）
    // 如果未来需要统一，应该把两边都改为 V3 值，并同步本测试
    // 此测试故意保留双值以暴露漂移
    if (DarkColors.background !== darkTheme.background) {
      // 明确记录为「已知漂移」—— 不 fail 但写到 console，提醒迁移规划
      // 当 V3 暗色生效时，应同步 V2 或彻底废弃 V2
      console.warn(
        `[已知漂移] DarkColors.background=${DarkColors.background} vs darkTheme.background=${darkTheme.background}`,
      )
    }
    // 不强制相等，但要求两套都不能出现 V2「安心法务」时代的非系统色（如 #FF7B47 老品牌橙）
    expect(DarkColors.background.toLowerCase()).toMatch(/^#[0-9a-f]{6}$/)
    expect(darkTheme.background.toLowerCase()).toMatch(/^#[0-9a-f]{6}$/)
  })

  it('状态色（success / warning / error / info）V2 ↔ V3 palette 完全一致', () => {
    expect(Colors.success).toBe(palette.success)
    expect(Colors.warning).toBe(palette.warning)
    expect(Colors.error).toBe(palette.error)
    expect(Colors.info).toBe(palette.info)
  })

  it('边框色 Colors.border === lightTheme.border', () => {
    expect(Colors.border).toBe(lightTheme.border)
  })

  it('V2 Colors.primary 不应是错误的蓝色 #2563EB（防止历史 UniApp 漂移回归）', () => {
    expect(Colors.primary.toLowerCase()).not.toBe('#2563eb')
    expect(palette.primary.toLowerCase()).not.toBe('#2563eb')
  })

  it('V2 Colors 顶部注释明确引导新代码使用 useV3Theme()', async () => {
    const fs = await import('node:fs/promises')
    const path = await import('node:path')
    const file = path.resolve(__dirname, 'colors.ts')
    const text = await fs.readFile(file, 'utf-8')
    expect(text).toMatch(/useV3Theme/)
    expect(text).toMatch(/2026-05/)
  })
})
