import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusColor } from '@/lib/design-tokens'
import { expertsApi, type ExpertItem } from '@/lib/api'
import { PageContainer } from '@/components/ui/PageContainer'

type Specialty = 'all' | 'civil' | 'criminal' | 'corporate' | 'ip' | 'labor' | 'admin'

interface Expert {
  id: string
  name: string
  title: string
  specialty: Exclude<Specialty, 'all'>[]
  yearsOfExperience: number
  rating: number
  casesHandled: number
  description: string
  achievements: string[]
}

const specialtyConfig: Record<string, { label: string; color: string }> = {
  civil: { label: '民商事', color: statusColor.info },
  criminal: { label: '刑事', color: statusColor.error },
  corporate: { label: '公司法', color: statusColor.success },
  ip: { label: '知识产权', color: 'text-primary bg-primary/5' },
  labor: { label: '劳动法', color: statusColor.warning },
  admin: { label: '行政法', color: statusColor.neutral },
}

const mockExperts: Expert[] = [
  { id: '1', name: '张明远', title: '高级合伙人', specialty: ['corporate', 'civil'], yearsOfExperience: 18, rating: 4.9, casesHandled: 326, description: '专注于公司并购重组、股权纠纷领域，曾主导多起大型并购交易的法律服务。', achievements: ['全国优秀律师', '十大公司法律师', '50+亿级并购项目'] },
  { id: '2', name: '李婉清', title: '合伙人', specialty: ['labor', 'civil'], yearsOfExperience: 12, rating: 4.8, casesHandled: 215, description: '劳动争议领域专家，为多家知名企业提供劳动用工合规服务。', achievements: ['劳动法专业委员会委员', '年度最佳劳动法律师'] },
  { id: '3', name: '王浩然', title: '高级合伙人', specialty: ['criminal'], yearsOfExperience: 20, rating: 4.9, casesHandled: 180, description: '刑事辩护领域资深律师，擅长经济犯罪、职务犯罪辩护。', achievements: ['刑辩委员会副主任', '无罪辩护成功率35%'] },
  { id: '4', name: '陈思涵', title: '合伙人', specialty: ['ip', 'corporate'], yearsOfExperience: 10, rating: 4.7, casesHandled: 156, description: '知识产权诉讼与非诉专家，服务于科技、文化创意产业。', achievements: ['知识产权专业律师', '代理200+专利案件'] },
  { id: '5', name: '赵志刚', title: '资深律师', specialty: ['admin', 'civil'], yearsOfExperience: 15, rating: 4.6, casesHandled: 198, description: '行政法与政府法律顾问专家，在行政复议、行政诉讼方面经验丰富。', achievements: ['政府法律顾问', '行政法委员会委员'] },
  { id: '6', name: '刘雅琳', title: '合伙人', specialty: ['civil', 'corporate'], yearsOfExperience: 14, rating: 4.8, casesHandled: 245, description: '房地产与建设工程领域专家，代理多起标的额过亿的建设工程纠纷案件。', achievements: ['建工法专业委员会委员', '地产法务十佳律师'] },
]

function apiToExpert(item: ExpertItem): Expert {
  return {
    id: item.id,
    name: item.name,
    title: item.title || '',
    specialty: (item.specialty || []) as Exclude<Specialty, 'all'>[],
    yearsOfExperience: item.yearsOfExperience,
    rating: item.rating,
    casesHandled: item.casesHandled,
    description: item.description || '',
    achievements: item.achievements || [],
  }
}

export default function Experts() {
  const [experts, setExperts] = useState<Expert[]>(mockExperts)
  const [filter, setFilter] = useState<Specialty>('all')
  const [selectedExpert, setSelectedExpert] = useState<Expert | null>(null)
  const [loading, setLoading] = useState(true)

  const loadExperts = useCallback(async () => {
    setLoading(true)
    try {
      const data = await expertsApi.list({ page_size: 100 })
      if (data.items?.length > 0) {
        setExperts(data.items.map(apiToExpert))
      } else {
        setExperts(mockExperts)
      }
    } catch {
      setExperts(mockExperts)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadExperts() }, [loadExperts])

  const filtered = filter === 'all' ? experts : experts.filter(e => e.specialty.includes(filter as any))

  if (selectedExpert) {
    return (
      <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
        <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-4 flex items-center gap-3">
          <button onClick={() => setSelectedExpert(null)} className="p-1 rounded hover:bg-muted">
            <icons.ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className={heading.page}>{selectedExpert.name}</h1>
        </div>
        <div className="flex-1 overflow-y-auto px-4 sm:px-5 lg:px-6 py-6 max-w-2xl">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-xl font-bold text-primary">{selectedExpert.name[0]}</span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">{selectedExpert.name}</h2>
              <p className="text-sm text-muted-foreground">{selectedExpert.title}</p>
              <div className="flex gap-2 mt-1">
                {selectedExpert.specialty.map(s => (
                  <span key={s} className={`text-xs px-1.5 py-0.5 rounded-full ${specialtyConfig[s]?.color}`}>
                    {specialtyConfig[s]?.label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 sm:gap-4 gap-2 mb-6">
            <div className={cardStyle.base + ' text-center'}>
              <p className="text-2xl font-bold text-foreground">{selectedExpert.yearsOfExperience}</p>
              <p className="text-xs text-muted-foreground">执业年限</p>
            </div>
            <div className={cardStyle.base + ' text-center'}>
              <p className="text-2xl font-bold text-foreground">{selectedExpert.casesHandled}</p>
              <p className="text-xs text-muted-foreground">案件数量</p>
            </div>
            <div className={cardStyle.base + ' text-center'}>
              <div className="flex items-center justify-center gap-1">
                <icons.Star className="w-4 h-4 text-amber-500" />
                <span className="text-2xl font-bold text-foreground">{selectedExpert.rating}</span>
              </div>
              <p className="text-xs text-muted-foreground">评分</p>
            </div>
          </div>

          <div className="mb-6">
            <h3 className={heading.section + ' mb-2'}>个人简介</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{selectedExpert.description}</p>
          </div>

          <div>
            <h3 className={heading.section + ' mb-2'}>荣誉成就</h3>
            <div className="space-y-2">
              {selectedExpert.achievements.map((a, i) => (
                <div key={i} className="flex items-center gap-2">
                  <icons.Trophy className="w-4 h-4 text-amber-500" />
                  <span className="text-sm text-foreground">{a}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
      <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-5">
        <h1 className={heading.page + ' mb-4'}>
          <icons.Experts className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          律师精英
        </h1>
        <div className="flex gap-2 flex-wrap">
          {[{ key: 'all' as const, label: '全部' }, ...Object.entries(specialtyConfig).map(([k, v]) => ({ key: k as Specialty, label: v.label }))].map(s => (
            <button key={s.key} onClick={() => setFilter(s.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filter === s.key ? 'bg-primary text-white' : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 sm:px-5 lg:px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">加载律师数据...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map(expert => (
              <div key={expert.id} onClick={() => setSelectedExpert(expert)} className={cardStyle.interactive}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                    <span className="text-lg font-bold text-primary">{expert.name[0]}</span>
                  </div>
                  <div className="min-w-0">
                    <h3 className={heading.card}>{expert.name}</h3>
                    <p className="text-xs text-muted-foreground">{expert.title}</p>
                  </div>
                </div>
                <div className="flex gap-1.5 mb-3 flex-wrap">
                  {expert.specialty.map(s => (
                    <span key={s} className={`text-xs px-1.5 py-0.5 rounded-full ${specialtyConfig[s]?.color}`}>
                      {specialtyConfig[s]?.label}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{expert.description}</p>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{expert.yearsOfExperience}年经验</span>
                  <span>{expert.casesHandled}件案件</span>
                  <div className="flex items-center gap-1">
                    <icons.Star className="w-3 h-3 text-amber-500" />
                    <span>{expert.rating}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
