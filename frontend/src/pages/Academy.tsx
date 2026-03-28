import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusColor } from '@/lib/design-tokens'
import { coursesApi, type CourseItem } from '@/lib/api'
import { PageContainer } from '@/components/ui/PageContainer'

type CourseCategory = 'all' | 'regulation' | 'case_study' | 'practice' | 'exam'

interface Course {
  id: string
  title: string
  instructor: string
  category: Exclude<CourseCategory, 'all'>
  duration: string
  lessons: number
  progress: number
  description: string
  level: '入门' | '进阶' | '高级'
  tags: string[]
}

const categoryConfig: Record<string, { label: string; color: string }> = {
  regulation: { label: '法规解读', color: statusColor.info },
  case_study: { label: '案例分析', color: statusColor.success },
  practice: { label: '实务技能', color: statusColor.warning },
  exam: { label: '考试辅导', color: 'text-primary bg-primary/5' },
}

const levelColor: Record<string, string> = {
  '入门': statusColor.success,
  '进阶': statusColor.warning,
  '高级': statusColor.error,
}

const mockCourses: Course[] = [
  { id: '1', title: '民法典合同编实务精讲', instructor: '张明远', category: 'regulation', duration: '12小时', lessons: 24, progress: 75, description: '系统讲解民法典合同编核心条文，结合最新司法解释和典型案例。', level: '进阶', tags: ['民法典', '合同'] },
  { id: '2', title: '劳动争议案件代理实务', instructor: '李婉清', category: 'practice', duration: '8小时', lessons: 16, progress: 100, description: '从接案到庭审的全流程实操训练，含仲裁和诉讼两条路径。', level: '进阶', tags: ['劳动法', '仲裁'] },
  { id: '3', title: '刑事辩护技巧入门', instructor: '王浩然', category: 'case_study', duration: '10小时', lessons: 20, progress: 30, description: '以真实案例为教材，教授会见、阅卷、质证、辩护的核心技巧。', level: '入门', tags: ['刑辩', '辩护技巧'] },
  { id: '4', title: '知识产权诉讼攻防策略', instructor: '陈思涵', category: 'case_study', duration: '6小时', lessons: 12, progress: 0, description: '专利、商标、著作权诉讼的攻防要点与举证策略。', level: '高级', tags: ['知产', '诉讼'] },
  { id: '5', title: '公司法修订要点解读', instructor: '张明远', category: 'regulation', duration: '4小时', lessons: 8, progress: 50, description: '全面解析2024公司法修订的重大变化及对企业的影响。', level: '入门', tags: ['公司法', '法规'] },
  { id: '6', title: '法律职业资格考试冲刺', instructor: '综合讲师团', category: 'exam', duration: '40小时', lessons: 60, progress: 15, description: '涵盖主客观题全科目的高效备考课程。', level: '入门', tags: ['法考', '备考'] },
  { id: '7', title: '合同审查与风险防控', instructor: '刘雅琳', category: 'practice', duration: '6小时', lessons: 12, progress: 0, description: '教你快速识别合同风险点，掌握条款修改和谈判策略。', level: '进阶', tags: ['合同审查', '风控'] },
  { id: '8', title: '建设工程纠纷裁判规则', instructor: '刘雅琳', category: 'case_study', duration: '8小时', lessons: 16, progress: 0, description: '结合最高法指导案例，解读建设工程合同纠纷的裁判思路。', level: '高级', tags: ['建工', '裁判规则'] },
]

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
    level: (item.level as '入门' | '进阶' | '高级') || '入门',
    tags: item.tags || [],
  }
}

export default function Academy() {
  const [courses, setCourses] = useState<Course[]>(mockCourses)
  const [category, setCategory] = useState<CourseCategory>('all')
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null)
  const [loading, setLoading] = useState(true)

  const loadCourses = useCallback(async () => {
    setLoading(true)
    try {
      const data = await coursesApi.list({ page_size: 100 })
      if (data.items?.length > 0) {
        setCourses(data.items.map(apiToCourse))
      } else {
        setCourses(mockCourses)
      }
    } catch {
      setCourses(mockCourses)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadCourses() }, [loadCourses])

  const filtered = category === 'all' ? courses : courses.filter(c => c.category === category)

  if (selectedCourse) {
    return (
      <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
        <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-4 flex items-center gap-3">
          <button onClick={() => setSelectedCourse(null)} className="p-1 rounded hover:bg-muted">
            <icons.ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className={heading.page}>{selectedCourse.title}</h1>
        </div>
        <div className="flex-1 overflow-y-auto px-4 sm:px-5 lg:px-6 py-6 max-w-2xl">
          <div className="flex items-center gap-3 mb-4">
            <span className={`text-xs px-2 py-0.5 rounded-full ${categoryConfig[selectedCourse.category]?.color || ''}`}>
              {categoryConfig[selectedCourse.category]?.label || selectedCourse.category}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${levelColor[selectedCourse.level] || ''}`}>
              {selectedCourse.level}
            </span>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed mb-6">{selectedCourse.description}</p>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className={cardStyle.base + ' text-center'}>
              <icons.User className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
              <p className="text-sm font-medium text-foreground">{selectedCourse.instructor}</p>
              <p className="text-xs text-muted-foreground">讲师</p>
            </div>
            <div className={cardStyle.base + ' text-center'}>
              <icons.Clock className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
              <p className="text-sm font-medium text-foreground">{selectedCourse.duration}</p>
              <p className="text-xs text-muted-foreground">总时长</p>
            </div>
            <div className={cardStyle.base + ' text-center'}>
              <icons.List className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
              <p className="text-sm font-medium text-foreground">{selectedCourse.lessons} 课时</p>
              <p className="text-xs text-muted-foreground">课程章节</p>
            </div>
          </div>

          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className={heading.section}>学习进度</h3>
              <span className="text-xs text-muted-foreground">{selectedCourse.progress}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${selectedCourse.progress}%` }} />
            </div>
          </div>

          <h3 className={heading.section + ' mb-3'}>课程大纲</h3>
          <div className="space-y-2">
            {Array.from({ length: Math.min(selectedCourse.lessons, 8) }, (_, i) => {
              const completed = i < Math.floor(selectedCourse.lessons * selectedCourse.progress / 100)
              return (
                <div key={i} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${completed ? 'bg-primary/5' : 'bg-muted/30'}`}>
                  {completed ? (
                    <icons.CheckCircle className="w-4 h-4 text-primary flex-shrink-0" />
                  ) : (
                    <icons.Circle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  )}
                  <span className={`text-sm ${completed ? 'text-foreground' : 'text-muted-foreground'}`}>
                    第 {i + 1} 课
                  </span>
                </div>
              )
            })}
            {selectedCourse.lessons > 8 && (
              <p className="text-xs text-muted-foreground text-center py-2">还有 {selectedCourse.lessons - 8} 个课时...</p>
            )}
          </div>

          <div className="flex gap-2 mt-6">
            {selectedCourse.tags.map(tag => (
              <span key={tag} className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">{tag}</span>
            ))}
          </div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
      <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-5">
        <h1 className={heading.page + ' mb-4'}>
          <icons.Academy className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          司法学院
        </h1>
        <div className="flex gap-2">
          {[{ key: 'all' as const, label: '全部' }, ...Object.entries(categoryConfig).map(([k, v]) => ({ key: k as CourseCategory, label: v.label }))].map(c => (
            <button key={c.key} onClick={() => setCategory(c.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                category === c.key ? 'bg-primary text-white' : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 sm:px-5 lg:px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">加载课程...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(course => (
              <div key={course.id} onClick={() => setSelectedCourse(course)} className={cardStyle.interactive}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex gap-1.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${categoryConfig[course.category]?.color || ''}`}>
                      {categoryConfig[course.category]?.label || course.category}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${levelColor[course.level] || ''}`}>
                      {course.level}
                    </span>
                  </div>
                </div>
                <h3 className={heading.card + ' mb-1'}>{course.title}</h3>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{course.description}</p>

                {course.progress > 0 && (
                  <div className="mb-3">
                    <div className="w-full h-1.5 rounded-full bg-muted">
                      <div className={`h-full rounded-full ${course.progress === 100 ? 'bg-emerald-500' : 'bg-primary'}`}
                        style={{ width: `${course.progress}%` }} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {course.progress === 100 ? '已完成' : `${course.progress}% 进度`}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{course.instructor}</span>
                  <span>{course.lessons} 课时 · {course.duration}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
