/**
 * SkillsPage — V3 技能（P5-F 真业务化）
 *
 * 参考 Accio Work "技能" 页布局：
 *   - 左侧：分类侧栏（13 域 + 全部）+ 计数
 *   - 顶栏：标题 + 副标题 + 搜索 + persona 过滤 + 上传 SKILL.md
 *   - 中部：当前 category 的 skills，按"已启用"和"未启用"两段展示
 *   - 右侧：详情抽屉（点击卡片标题或"详情"按钮触发）
 *   - 试运行弹窗：从详情抽屉触发
 */

import { useEffect, useMemo, useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'

import { SkillCard } from '@/components/v3/skills/SkillCard'
import { SkillCategorySidebar } from '@/components/v3/skills/SkillCategorySidebar'
import { SkillSearchBar } from '@/components/v3/skills/SkillSearchBar'
import { SkillDetailDrawer } from '@/components/v3/skills/SkillDetailDrawer'
import { SkillUploadDialog } from '@/components/v3/skills/SkillUploadDialog'
import { SkillExecuteDialog } from '@/components/v3/skills/SkillExecuteDialog'
import { SecureSkillInstallButton } from '@/components/v3/skills/SecureSkillInstallButton'

import type { Skill, SkillCategory } from '@/lib/api/skills'
import { useSkillsStore } from '@/lib/store/skillsStore'

export default function SkillsPage() {
  const skills = useSkillsStore((s) => s.skills)
  const selectedSkill = useSkillsStore((s) => s.selectedSkill)
  const detailLoading = useSkillsStore((s) => s.detailLoading)
  const loading = useSkillsStore((s) => s.loading)
  const loadError = useSkillsStore((s) => s.loadError)
  const searchQuery = useSkillsStore((s) => s.searchQuery)
  const selectedCategory = useSkillsStore((s) => s.selectedCategory)
  const selectedPersona = useSkillsStore((s) => s.selectedPersona)

  const loadSkills = useSkillsStore((s) => s.loadSkills)
  const selectSkill = useSkillsStore((s) => s.selectSkill)
  const toggleSkill = useSkillsStore((s) => s.toggleSkill)
  const setCategory = useSkillsStore((s) => s.setCategory)
  const setPersona = useSkillsStore((s) => s.setPersona)
  const setSearch = useSkillsStore((s) => s.setSearch)

  const getFilteredSkills = useSkillsStore((s) => s.getFilteredSkills)
  const getCategoryCount = useSkillsStore((s) => s.getCategoryCount)
  const getPersonaCount = useSkillsStore((s) => s.getPersonaCount)

  const [uploadOpen, setUploadOpen] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [executeTarget, setExecuteTarget] = useState<Skill | null>(null)

  useEffect(() => {
    loadSkills()
  }, [loadSkills])

  // 列表 / 三个过滤项变化时重算（getFilteredSkills 是 store 稳定引用，
  // 但显式列出依赖以让 react-hooks/exhaustive-deps 满意）
  const filtered = useMemo(
    () => getFilteredSkills(),
    [skills, searchQuery, selectedCategory, selectedPersona, getFilteredSkills],
  )

  const enabled = filtered.filter((s) => s.enabled)
  const disabled = filtered.filter((s) => !s.enabled)

  const categoryCount = useMemo(() => getCategoryCount(), [skills, getCategoryCount])
  const personaCount = useMemo(() => getPersonaCount(), [skills, getPersonaCount])

  const openDetail = async (s: Skill) => {
    setDetailOpen(true)
    await selectSkill(s.name)
  }

  const handleToggle = async (s: Skill, next: boolean) => {
    try {
      await toggleSkill(s.name, next)
      toast.success(`${s.display_name} 已${next ? '启用' : '禁用'}`)
    } catch (e) {
      toast.error(`操作失败：${e instanceof Error ? e.message : '未知错误'}`)
    }
  }

  const reload = () => loadSkills()

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col gap-5 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <icons.Sparkles className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              技能
            </h1>
            <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
              按域启用原子化技能 — 法律 / 财税 / 运营 / 调研 / 营销 / 内容 / 设计 /
              办公文档 / 跨境电商 / 销售 / 情报 / 决策 / 系统。开关即生效。
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={reload} disabled={loading}>
            <icons.RefreshCcw className={loading ? 'animate-spin' : ''} />
            刷新
          </Button>
          <SecureSkillInstallButton size="sm" onInstalled={reload} />
          <Button size="sm" variant="ghost" onClick={() => setUploadOpen(true)}>
            <icons.Upload className="size-4" />
            旧版上传
          </Button>
        </div>
      </header>

      {/* 计数条 */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 font-medium text-foreground">
          {skills.length} 个技能
        </span>
        <span>· 已启用 {skills.filter((s) => s.enabled).length} 个</span>
        <span>· 当前过滤后 {filtered.length} 个</span>
      </div>

      {/* 搜索 + persona */}
      <SkillSearchBar
        search={searchQuery}
        onSearchChange={setSearch}
        persona={selectedPersona}
        onPersonaChange={setPersona}
        personaCounts={personaCount}
      />

      {/* 错误提示 */}
      {loadError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败：{loadError}
        </div>
      )}

      {/* 主体：sidebar + content */}
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start">
        <SkillCategorySidebar
          value={selectedCategory}
          onChange={(c) => setCategory(c as 'all' | SkillCategory)}
          counts={categoryCount}
          totalCount={skills.length}
        />

        <main className="min-w-0 flex-1 space-y-6">
          {loading && skills.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
              正在加载技能列表...
            </div>
          ) : filtered.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
              没有匹配的技能 — 试试切换分类、清空搜索词或解除角色过滤
            </div>
          ) : (
            <>
              {enabled.length > 0 && (
                <Section
                  title="已启用"
                  badge={`${enabled.length}`}
                  badgeClass="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                >
                  <SkillGrid
                    items={enabled}
                    onOpenDetail={openDetail}
                    onToggle={handleToggle}
                  />
                </Section>
              )}
              {disabled.length > 0 && (
                <Section
                  title="未启用"
                  badge={`${disabled.length}`}
                  badgeClass="bg-muted text-muted-foreground"
                >
                  <SkillGrid
                    items={disabled}
                    onOpenDetail={openDetail}
                    onToggle={handleToggle}
                  />
                </Section>
              )}
            </>
          )}
        </main>
      </div>

      {/* 抽屉 + 弹窗 */}
      <SkillDetailDrawer
        open={detailOpen}
        onOpenChange={(o) => {
          setDetailOpen(o)
          if (!o) selectSkill(null)
        }}
        skill={selectedSkill}
        loading={detailLoading}
        onToggle={(next) => {
          if (selectedSkill) handleToggle(selectedSkill, next)
        }}
        onExecute={() => {
          if (selectedSkill) setExecuteTarget(selectedSkill)
        }}
      />

      <SkillExecuteDialog
        open={!!executeTarget}
        onOpenChange={(o) => {
          if (!o) setExecuteTarget(null)
        }}
        skill={executeTarget}
      />

      <SkillUploadDialog open={uploadOpen} onOpenChange={setUploadOpen} />
    </div>
  )
}

interface SectionProps {
  title: string
  badge?: string
  badgeClass?: string
  children: React.ReactNode
}

function Section({ title, badge, badgeClass, children }: SectionProps) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        {badge && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              badgeClass ?? 'bg-muted text-muted-foreground'
            }`}
          >
            {badge}
          </span>
        )}
      </div>
      {children}
    </section>
  )
}

interface SkillGridProps {
  items: Skill[]
  onOpenDetail: (s: Skill) => void
  onToggle: (s: Skill, next: boolean) => void
}

function SkillGrid({ items, onOpenDetail, onToggle }: SkillGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      {items.map((s) => (
        <SkillCard
          key={s.name}
          skill={s}
          onOpenDetail={() => onOpenDetail(s)}
          onToggle={(next) => onToggle(s, next)}
        />
      ))}
    </div>
  )
}
