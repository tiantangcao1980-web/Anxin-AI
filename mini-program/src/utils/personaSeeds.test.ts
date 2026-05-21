// personaSeeds 完整性 smoke 测试
//
// PERSONA_SEEDS 是 home 首屏在离线/未登录时的兜底，必须保证：
//   - 10 个 persona 全部存在（与 frontend personas.mock.ts 对齐）
//   - 每个 persona 都有 emoji / display_name / description / domain
//   - DOMAIN_LIST 与 personas 的 domain 字段一致

import { describe, expect, it } from 'vitest'
import { DOMAIN_LIST, PERSONA_SEEDS, RECOMMENDED_PROMPTS } from './personaSeeds'

describe('personaSeeds · V3 home 兜底数据', () => {
  it('PERSONA_SEEDS 至少 10 个 persona', () => {
    expect(PERSONA_SEEDS.length).toBeGreaterThanOrEqual(10)
  })

  it('每个 persona 的 persona_id 唯一', () => {
    const ids = PERSONA_SEEDS.map((p) => p.persona_id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('每个 persona 都有 emoji + display_name + description + capabilities', () => {
    for (const p of PERSONA_SEEDS) {
      expect(p.emoji).toBeTruthy()
      expect(p.display_name.length).toBeGreaterThan(0)
      expect(p.description.length).toBeGreaterThan(0)
      expect(Array.isArray(p.capabilities)).toBe(true)
      expect(p.capabilities.length).toBeGreaterThan(0)
    }
  })

  it('DOMAIN_LIST 中的 domain 都在 PERSONA_SEEDS 里能找到至少一个 persona', () => {
    const personaDomains = new Set(PERSONA_SEEDS.map((p) => p.domain))
    for (const d of DOMAIN_LIST) {
      expect(personaDomains.has(d.domain)).toBe(true)
    }
  })

  it('RECOMMENDED_PROMPTS 都指向真实存在的 persona_id', () => {
    const seedIds = new Set(PERSONA_SEEDS.map((p) => p.persona_id))
    for (const prompt of RECOMMENDED_PROMPTS) {
      expect(seedIds.has(prompt.persona_id)).toBe(true)
      expect(prompt.text.length).toBeGreaterThan(0)
    }
  })

  it('persona 文案中不应包含 V2 法务专属术语 "找律师"', () => {
    // V3 已扩展到 8 大业务域；"找律师"作为法务子页保留，但不应作为 home 引导文案
    for (const p of PERSONA_SEEDS) {
      expect(p.description).not.toContain('找律师')
    }
  })
})
