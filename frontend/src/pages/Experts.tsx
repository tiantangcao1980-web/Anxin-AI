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
  const [experts, setExperts] = useState<Expert[]>([])
  const [filter, setFilter] = useState<Specialty>('all')
  const [selectedExpert, setSelectedExpert] = useState<Expert | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadExperts = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await expertsApi.list({ page_size: 100 })
      setExperts((data.items || []).map(apiToExpert))
    } catch (err) {
      setExperts([])
      setError(err instanceof Error ? err.message : '加载律师数据失败')
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
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <icons.AlertTriangle className="w-10 h-10 text-destructive/60 mb-3" />
            <p className="text-sm text-foreground mb-1">律师数据加载失败</p>
            <p className="text-xs text-muted-foreground mb-4">{error}</p>
            <button onClick={() => void loadExperts()} className="px-4 py-2 rounded-lg bg-primary text-white text-sm">
              重新加载
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <icons.Experts className="w-10 h-10 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-foreground mb-1">暂无律师数据</p>
            <p className="text-xs text-muted-foreground">运行种子数据后即可验证律师列表。</p>
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
