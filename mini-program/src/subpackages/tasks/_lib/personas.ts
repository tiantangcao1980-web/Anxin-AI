// -*- coding: utf-8 -*-
/**
 * persona_id → emoji / display_name 映射（任务页只读）
 *
 * 数据源：utils/personaSeeds.ts。这里包一层是因为：
 *   - 任务列表 / 详情页需要快速查 emoji + name
 *   - 创建页需要 picker 选项数组
 */

import { PERSONA_SEEDS } from '../../../utils/personaSeeds'

export interface PersonaOption {
  id: string
  emoji: string
  name: string
  domain?: string
}

export const PERSONA_OPTIONS: PersonaOption[] = PERSONA_SEEDS.map((p) => ({
  id: p.persona_id,
  emoji: p.emoji,
  name: p.display_name,
  domain: p.domain,
}))

const _map = new Map<string, PersonaOption>(PERSONA_OPTIONS.map((p) => [p.id, p]))

export function findPersona(id: string): PersonaOption {
  return (
    _map.get(id) ?? {
      id,
      emoji: '🤖',
      name: id,
    }
  )
}
