/**
 * Skills zustand store (V3 技能 P5-F)
 *
 * 集中管理 skill 列表 + 当前 category / persona / search 过滤 + 选中详情。
 *
 * 通过 API 层 (VITE_SKILLS_MOCK=true) 透明切换 mock。
 */

import { create } from 'zustand'

import {
  skillsApi,
  type Skill,
  type SkillCategory,
  type SkillExecuteResult,
  type SkillUploadResult,
} from '@/lib/api/skills'

export type SkillCategoryFilter = 'all' | SkillCategory
export type SkillPersonaFilter = 'all' | string

interface SkillsState {
  // 数据
  skills: Skill[]
  selectedSkill: Skill | null

  // UI 筛选
  searchQuery: string
  selectedCategory: SkillCategoryFilter
  selectedPersona: SkillPersonaFilter

  // 加载态
  loading: boolean
  detailLoading: boolean
  loadError: string | null

  // ===== actions =====
  loadSkills: () => Promise<void>
  selectSkill: (name: string | null) => Promise<void>
  toggleSkill: (name: string, enabled: boolean) => Promise<void>
  uploadSkill: (file: File) => Promise<SkillUploadResult>
  executeSkill: (name: string, payload: unknown) => Promise<SkillExecuteResult>
  setCategory: (c: SkillCategoryFilter) => void
  setPersona: (p: SkillPersonaFilter) => void
  setSearch: (q: string) => void

  // ===== selectors =====
  /** 按 category + persona + search 过滤 skill 列表 */
  getFilteredSkills: () => Skill[]
  /** 各 category 的 skill 数量 map */
  getCategoryCount: () => Record<string, number>
  /** 各 persona 的 skill 数量 map */
  getPersonaCount: () => Record<string, number>
  /** 已启用 / 未启用拆分 */
  getSplitByEnabled: () => { enabled: Skill[]; disabled: Skill[] }
}

export const useSkillsStore = create<SkillsState>((set, get) => ({
  skills: [],
  selectedSkill: null,
  searchQuery: '',
  selectedCategory: 'all',
  selectedPersona: 'all',
  loading: false,
  detailLoading: false,
  loadError: null,

  loadSkills: async () => {
    set({ loading: true, loadError: null })
    try {
      const skills = await skillsApi.list()
      set({ skills, loading: false })
    } catch (e) {
      set({
        loading: false,
        loadError: e instanceof Error ? e.message : '加载技能列表失败',
      })
    }
  },

  selectSkill: async (name) => {
    if (!name) {
      set({ selectedSkill: null })
      return
    }
    set({ detailLoading: true })
    try {
      const skill = await skillsApi.get(name)
      set({ selectedSkill: skill, detailLoading: false })
    } catch (e) {
      set({
        detailLoading: false,
        loadError: e instanceof Error ? e.message : '加载技能详情失败',
      })
    }
  },

  toggleSkill: async (name, enabled) => {
    // 乐观更新
    set((s) => ({
      skills: s.skills.map((k) => (k.name === name ? { ...k, enabled } : k)),
      selectedSkill:
        s.selectedSkill?.name === name ? { ...s.selectedSkill, enabled } : s.selectedSkill,
    }))
    try {
      const updated = await skillsApi.toggle(name, enabled)
      set((s) => ({
        skills: s.skills.map((k) => (k.name === name ? { ...k, ...updated } : k)),
      }))
    } catch (e) {
      // 回滚
      set((s) => ({
        skills: s.skills.map((k) =>
          k.name === name ? { ...k, enabled: !enabled } : k,
        ),
        loadError: e instanceof Error ? e.message : '切换失败',
      }))
      throw e
    }
  },

  uploadSkill: async (file) => {
    const result = await skillsApi.upload(file)
    set((s) => {
      const idx = s.skills.findIndex((k) => k.name === result.skill.name)
      if (idx === -1) return { skills: [...s.skills, result.skill] }
      const next = s.skills.slice()
      next[idx] = result.skill
      return { skills: next }
    })
    return result
  },

  executeSkill: async (name, payload) => {
    return skillsApi.execute(name, payload)
  },

  setCategory: (c) => set({ selectedCategory: c }),
  setPersona: (p) => set({ selectedPersona: p }),
  setSearch: (q) => set({ searchQuery: q }),

  // ===== selectors =====
  getFilteredSkills: () => {
    const { skills, selectedCategory, selectedPersona, searchQuery } = get()
    const q = searchQuery.trim().toLowerCase()
    return skills.filter((s) => {
      if (selectedCategory !== 'all' && s.category !== selectedCategory) return false
      if (selectedPersona !== 'all') {
        if (!s.personas.includes(selectedPersona) && !s.personas.includes('全部')) {
          return false
        }
      }
      if (!q) return true
      return (
        s.display_name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.name.toLowerCase().includes(q) ||
        s.triggers.some((t) => t.toLowerCase().includes(q)) ||
        s.keywords.some((k) => k.toLowerCase().includes(q))
      )
    })
  },

  getCategoryCount: () => {
    const counts: Record<string, number> = {}
    get().skills.forEach((s) => {
      counts[s.category] = (counts[s.category] || 0) + 1
    })
    return counts
  },

  getPersonaCount: () => {
    const counts: Record<string, number> = {}
    get().skills.forEach((s) => {
      s.personas.forEach((p) => {
        counts[p] = (counts[p] || 0) + 1
      })
    })
    return counts
  },

  getSplitByEnabled: () => {
    const list = get().getFilteredSkills()
    return {
      enabled: list.filter((s) => s.enabled),
      disabled: list.filter((s) => !s.enabled),
    }
  },
}))
