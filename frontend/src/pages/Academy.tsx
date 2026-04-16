import { useState, useEffect, useCallback } from'react'
import { icons } from'@/lib/icons'
import { cardStyle, heading, statusColor } from'@/lib/design-tokens'
import { coursesApi, type CourseItem } from'@/lib/api'
import { PageContainer } from'@/components/ui/PageContainer'
import { ErrorState } from'@/components/common'

type CourseCategory ='all' |'regulation' |'case_study' |'practice' |'exam'

interface Course {
 id: string
 title: string
 instructor: string
 category: Exclude<CourseCategory,'all'>
 duration: string
 lessons: number
 progress: number
 description: string
 level:'入门' |'进阶' |'高级'
 tags: string[]
}

const categoryConfig: Record<string, { label: string; color: string }> = {
 regulation: { label:'法规解读', color: statusColor.info },
 case_study: { label:'案例分析', color: statusColor.success },
 practice: { label:'实务技能', color: statusColor.warning },
 exam: { label:'考试辅导', color:'text-primary bg-primary/5' },
}

const levelColor: Record<string, string> = {
'入门': statusColor.success,
'进阶': statusColor.warning,
'高级': statusColor.error,
}

function apiToCourse(item: CourseItem): Course {
 return {
 id: item.id,
 title: item.title,
 instructor: item.instructor ||'',
 category: (item.category as Exclude<CourseCategory,'all'>) ||'regulation',
 duration: item.duration ||'',
 lessons: item.lessons,
 progress: item.progress,
 description: item.description ||'',
 level: (item.level as'入门' |'进阶' |'高级') ||'入门',
 tags: item.tags || [],
 }
}

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
 setError(err instanceof Error ? err.message :'加载课程失败')
 } finally {
 setLoading(false)
 }
 }, [])

 useEffect(() => { loadCourses() }, [loadCourses])

 const filtered = category ==='all' ? courses : courses.filter(c => c.category === category)

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
 <span className={`text-xs px-2 py-0.5 rounded-full ${categoryConfig[selectedCourse.category]?.color ||''}`}>
 {categoryConfig[selectedCourse.category]?.label || selectedCourse.category}
 </span>
 <span className={`text-xs px-2 py-0.5 rounded-full ${levelColor[selectedCourse.level] ||''}`}>
 {selectedCourse.level}
 </span>
 </div>

 <p className="text-sm text-muted-foreground leading-relaxed mb-6">{selectedCourse.description}</p>

 <div className="grid grid-cols-3 gap-4 mb-6">
 <div className={cardStyle.base +' text-center'}>
 <icons.User className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
 <p className="text-sm font-medium text-foreground">{selectedCourse.instructor}</p>
 <p className="text-xs text-muted-foreground">讲师</p>
 </div>
 <div className={cardStyle.base +' text-center'}>
 <icons.Clock className="w-5 h-5 mx-auto text-muted-foreground mb-1" />
 <p className="text-sm font-medium text-foreground">{selectedCourse.duration}</p>
 <p className="text-xs text-muted-foreground">总时长</p>
 </div>
 <div className={cardStyle.base +' text-center'}>
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

 <h3 className={heading.section +' mb-3'}>课程大纲</h3>
 <div className="space-y-2">
 {Array.from({ length: Math.min(selectedCourse.lessons, 8) }, (_, i) => {
 const completed = i < Math.floor(selectedCourse.lessons * selectedCourse.progress / 100)
 return (
 <div key={i} className={`flex items-center gap-3 px-3 py-2 rounded-lg ${completed ?'bg-primary/5' :'bg-muted/30'}`}>
 {completed ? (
 <icons.CheckCircle className="w-4 h-4 text-primary flex-shrink-0" />
 ) : (
 <icons.Circle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
 )}
 <span className={`text-sm ${completed ?'text-foreground' :'text-muted-foreground'}`}>
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
 <h1 className={heading.page +' mb-4'}>
 <icons.Academy className="w-5 h-5 inline-block mr-2 -mt-0.5" />
 司法学院
 </h1>
 <div className="flex gap-2">
 {[{ key:'all' as const, label:'全部' }, ...Object.entries(categoryConfig).map(([k, v]) => ({ key: k as CourseCategory, label: v.label }))].map(c => (
 <button key={c.key} onClick={() => setCategory(c.key)}
 className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
 category === c.key ?'bg-primary text-primary-foreground' :'bg-muted text-muted-foreground hover:text-foreground'
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
 ) : error ? (
 <ErrorState
 title="课程数据加载失败"
 message={error}
 onRetry={() => void loadCourses()}
 />
 ) : filtered.length === 0 ? (
 <div className="flex flex-col items-center justify-center py-20">
 <icons.Academy className="w-10 h-10 text-muted-foreground/50 mb-3" />
 <p className="text-sm text-foreground mb-1">暂无课程数据</p>
 <p className="text-xs text-muted-foreground">运行种子数据后即可验证司法学院页面。</p>
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {filtered.map(course => (
 <div key={course.id} onClick={() => setSelectedCourse(course)} className={cardStyle.interactive}>
 <div className="flex items-center justify-between mb-3">
 <div className="flex gap-1.5">
 <span className={`text-xs px-1.5 py-0.5 rounded-full ${categoryConfig[course.category]?.color ||''}`}>
 {categoryConfig[course.category]?.label || course.category}
 </span>
 <span className={`text-xs px-1.5 py-0.5 rounded-full ${levelColor[course.level] ||''}`}>
 {course.level}
 </span>
 </div>
 </div>
 <h3 className={heading.card +' mb-1'}>{course.title}</h3>
 <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{course.description}</p>

 {course.progress > 0 && (
 <div className="mb-3">
 <div className="w-full h-1.5 rounded-full bg-muted">
 <div className={`h-full rounded-full ${course.progress === 100 ?'bg-success' :'bg-primary'}`}
 style={{ width: `${course.progress}%` }} />
 </div>
 <p className="text-xs text-muted-foreground mt-1">
 {course.progress === 100 ?'已完成' : `${course.progress}% 进度`}
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
