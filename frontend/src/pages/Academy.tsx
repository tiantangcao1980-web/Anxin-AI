/**
 * Academy · 司法学院（Editorial Luxury 改造 · Phase 1）
 *
 * 旧版用 PageContainer + cardStyle.interactive 3 列卡片墙 + statusColor chip 色块。
 * 新版：ListPageTemplate 列表 + DetailPageTemplate 详情。
 * 区分手段：tone-only chip + 衬线大字 + 进度细线，无背景色块。
 */

import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, CheckCircle, Circle, Clock, List, User } from 'lucide-react'

import { ListPageTemplate, ListPageStatus } from '@/components/ui/ListPageTemplate'
import { DetailPageTemplate, PanelSection } from '@/components/ui/PageTemplates'
import { coursesApi, type CourseItem } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type CourseCategory = 'all' | 'regulation' | 'case_study' | 'practice' | 'exam'
type Level = '入门' | '进阶' | '高级'

interface Course {
  id: string
  title: string
  instructor: string
  category: Exclude<CourseCategory, 'all'>
  duration: string
  lessons: number
  progress: number
  description: string
  level: Level
  tags: string[]
}

const CATEGORY_META: Record<Exclude<CourseCategory, 'all'>, { label: string; labelEn: string }> = {
  regulation: { label: '法规解读', labelEn: 'Regulation' },
  case_study: { label: '案例分析', labelEn: 'Case Study' },
  practice:   { label: '实务技能', labelEn: 'Practice' },
  exam:       { label: '考试辅导', labelEn: 'Exam Prep' },
}

const LEVEL_TONE: Record<Level, 'success' | 'warning' | 'error'> = {
  入门: 'success',
  进阶: 'warning',
  高级: 'error',
}

function apiToCourse(item: CourseItem): Course {
  return {
    id: item.id,
    title: item.title,
    instructor: item.instructor || '',
    category: (item.category as Exclude<CourseCategory, 'all'>) || 'regulation',
    duration: item.duration || '',
    lessons: item.lessons,
    progress: item.progress,
    description: item.description || '',
    level: (item.level as Level) || '入门',
    tags: item.tags || [],
  }
}

function CategoryChip({ category }: { category: Exclude<CourseCategory, 'all'> }) {
  const meta = CATEGORY_META[category]
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
      <span>{meta.labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/70">{meta.label}</span>
    </span>
  )
}

function LevelChip({ level }: { level: Level }) {
  const tone = LEVEL_TONE[level]
  const toneClass = {
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <span className={cn('inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em]', toneClass)}>
      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
      <span>{level}</span>
    </span>
  )
}

/* ------------ 详情视图 ------------ */
function CourseDetail({ course, onBack }: { course: Course; onBack: () => void }) {
  const completedCount = Math.floor((course.lessons * course.progress) / 100)
  return (
    <DetailPageTemplate
      tracker={['Knowledge', '司法学院', CATEGORY_META[course.category].label]}
      title={course.title}
      description={course.description}
      actions={
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4 stroke-[1.5]" />
          <span>返回列表</span>
        </button>
      }
    >
      {/* meta 行 */}
      <div className="flex items-center gap-6 mb-10">
        <CategoryChip category={course.category} />
        <LevelChip level={course.level} />
      </div>

      {/* KPI */}
      <div className="grid grid-cols-3 gap-px bg-border mb-10 border-t border-l border-border">
        <div className="bg-card px-5 py-4 border-r border-b border-border">
          <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <User className="w-3 h-3 stroke-[1.5]" />
            Instructor
          </div>
          <div className="text-[18px] text-foreground mt-1">{course.instructor || '—'}</div>
        </div>
        <div className="bg-card px-5 py-4 border-r border-b border-border">
          <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <Clock className="w-3 h-3 stroke-[1.5]" />
            Duration
          </div>
          <div className="text-[18px] text-foreground mt-1">{course.duration || '—'}</div>
        </div>
        <div className="bg-card px-5 py-4 border-r border-b border-border">
          <div className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            <List className="w-3 h-3 stroke-[1.5]" />
            Lessons
          </div>
          <div className="font-serif text-[28px] leading-[1.1] text-foreground mt-1 tabular-nums">
            {course.lessons}
          </div>
        </div>
      </div>

      {/* 进度 */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Progress
          </span>
          <span className="text-[13px] text-foreground tabular-nums">
            {course.progress}% · {completedCount} / {course.lessons}
          </span>
        </div>
        <div className="w-full h-px bg-border relative">
          <div
            className="absolute top-0 left-0 h-px bg-primary transition-[width]"
            style={{ width: `${course.progress}%` }}
          />
        </div>
      </div>

      {/* 大纲 */}
      <PanelSection tracker="Outline" title="课程大纲">
        <ol className="space-y-px">
          {Array.from({ length: Math.min(course.lessons, 8) }, (_, i) => {
            const completed = i < completedCount
            return (
              <li key={i} className="flex items-center gap-4 py-3 border-b border-border/60 last:border-b-0">
                {completed ? (
                  <CheckCircle className="w-4 h-4 text-success stroke-[1.5] shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-muted-foreground/50 stroke-[1.5] shrink-0" />
                )}
                <span className="font-serif text-[13px] text-muted-foreground w-10 tabular-nums">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span className={cn('text-[14px]', completed ? 'text-foreground' : 'text-muted-foreground')}>
                  第 {i + 1} 课
                </span>
              </li>
            )
          })}
          {course.lessons > 8 && (
            <li className="text-[12px] text-muted-foreground text-center py-3 italic">
              还有 {course.lessons - 8} 个课时…
            </li>
          )}
        </ol>
      </PanelSection>

      {course.tags.length > 0 && (
        <footer className="mt-10 pt-6 border-t border-border flex flex-wrap items-center gap-4">
          <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Tags
          </span>
          {course.tags.map((tag) => (
            <span key={tag} className="text-[13px] text-foreground/80 border border-border px-2.5 py-0.5">
              {tag}
            </span>
          ))}
        </footer>
      )}
    </DetailPageTemplate>
  )
}

/* ------------ 主页面 ------------ */
export default function Academy() {
  const [courses, setCourses] = useState<Course[]>([])
  const [category, setCategory] = useState<CourseCategory>('all')
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCourses = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await coursesApi.list({ page_size: 100 })
      setCourses((data.items || []).map(apiToCourse))
    } catch (err) {
      setCourses([])
      setError(err instanceof Error ? err.message : '加载课程失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadCourses() }, [loadCourses])

  const filtered = category === 'all' ? courses : courses.filter((c) => c.category === category)

  if (selectedCourse) {
    return <CourseDetail course={selectedCourse} onBack={() => setSelectedCourse(null)} />
  }

  const counts: Record<CourseCategory, number> = {
    all: courses.length,
    regulation: courses.filter((c) => c.category === 'regulation').length,
    case_study: courses.filter((c) => c.category === 'case_study').length,
    practice:   courses.filter((c) => c.category === 'practice').length,
    exam:       courses.filter((c) => c.category === 'exam').length,
  }

  return (
    <ListPageTemplate
      tracker={['Knowledge', '司法学院']}
      title="司法学院"
      description="法规 · 案例 · 实务 · 考辅 — 系统化学习路径。"
      tabs={[
        { key: 'all',        label: '全部',     count: counts.all },
        { key: 'regulation', label: '法规解读', count: counts.regulation },
        { key: 'case_study', label: '案例分析', count: counts.case_study },
        { key: 'practice',   label: '实务技能', count: counts.practice },
        { key: 'exam',       label: '考试辅导', count: counts.exam },
      ]}
      activeTab={category}
      onTabChange={(k) => setCategory(k as CourseCategory)}
      loading={loading}
      error={error}
      empty={!loading && !error && filtered.length === 0}
      emptyState={
        <ListPageStatus
          tracker="Empty"
          title={category === 'all' ? '暂无课程' : '该分类暂无课程'}
          description={
            category === 'all'
              ? '运行种子数据后即可看到课程，或换其他分类。'
              : '试试切换其他分类。'
          }
          action={
            category === 'all' && (
              <button
                onClick={() => void loadCourses()}
                className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
              >
                重新加载
              </button>
            )
          }
        />
      }
    >
      {filtered.map((course, i) => (
        <li key={course.id}>
          <button
            type="button"
            onClick={() => setSelectedCourse(course)}
            className="group w-full text-left flex items-start gap-6 py-6 px-3 -mx-3 border-b border-border/60 transition-colors hover:bg-surface-2/40"
          >
            <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
              {String(i + 1).padStart(3, '0')}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-4 flex-wrap mb-2">
                <CategoryChip category={course.category} />
                <LevelChip level={course.level} />
              </div>
              <h3 className="font-serif text-[18px] leading-tight text-foreground">{course.title}</h3>
              <p className="text-[13px] text-muted-foreground line-clamp-2 mt-2 leading-relaxed">
                {course.description}
              </p>
              {course.progress > 0 && (
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex-1 h-px bg-border relative max-w-[200px]">
                    <div
                      className={cn(
                        'absolute top-0 left-0 h-px transition-[width]',
                        course.progress === 100 ? 'bg-success' : 'bg-primary',
                      )}
                      style={{ width: `${course.progress}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-muted-foreground tabular-nums">
                    {course.progress === 100 ? '已完成' : `${course.progress}%`}
                  </span>
                </div>
              )}
              <div className="text-[12px] text-muted-foreground mt-3 flex items-center gap-3 flex-wrap">
                <span>{course.instructor || '—'}</span>
                <span>· {course.lessons} 课时</span>
                {course.duration && <span>· {course.duration}</span>}
              </div>
            </div>
          </button>
        </li>
      ))}
    </ListPageTemplate>
  )
}
