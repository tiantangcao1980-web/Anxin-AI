/**
 * LegalCases - 诉讼分析面板
 *
 * 展示统计概览卡片 + 案件列表（支持筛选）
 * 数据来源：调查数据中的 litigation 维度
 */
import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, inputStyle } from '@/lib/design-tokens'

interface LegalCasesProps {
  data?: {
    total_cases?: number
    as_plaintiff?: number
    as_defendant?: number
    execution_cases?: number
    dishonest_records?: number
    major_cases?: Array<{
      case_no?: string
      caseNo?: string
      case_type?: string
      type?: string
      role?: string
      status?: string
      result?: string
      amount?: string
      date?: string
      filing_date?: string
    }>
  }
}

const defaultCases = [
  { id: 1, caseNo: '(2023)京0108民初12345号', type: '合同纠纷', role: '被告', status: '已结案', result: '调解结案', amount: '50万元', date: '2023-11-20' },
  { id: 2, caseNo: '(2023)京0108民初23456号', type: '劳动争议', role: '被告', status: '已结案', result: '败诉', amount: '8万元', date: '2023-12-15' },
  { id: 3, caseNo: '(2024)京0108民初34567号', type: '知识产权', role: '原告', status: '审理中', result: '待判决', amount: '200万元', date: '2024-01-10' },
]

type RoleFilter = 'all' | '原告' | '被告'

export function LegalCases({ data }: LegalCasesProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')

  const cases = useMemo(() => {
    if (data?.major_cases && data.major_cases.length > 0) {
      return data.major_cases.map((c, i) => ({
        id: i + 1,
        caseNo: c.case_no || c.caseNo || '未公布',
        type: c.case_type || c.type || '未知',
        role: c.role || '未知',
        status: c.status || '未知',
        result: c.result || '待判决',
        amount: c.amount || '未披露',
        date: c.date || c.filing_date || '未知',
      }))
    }
    return defaultCases
  }, [data])

  const totalCases = data?.total_cases || cases.length
  const asPlaintiff = data?.as_plaintiff || cases.filter(c => c.role === '原告').length
  const asDefendant = data?.as_defendant || cases.filter(c => c.role === '被告').length
  const executionCases = data?.execution_cases || 0
  const dishonestRecords = data?.dishonest_records || 0

  const filteredCases = useMemo(() => {
    return cases.filter(c => {
      if (roleFilter !== 'all' && c.role !== roleFilter) return false
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        return c.caseNo.toLowerCase().includes(q) || c.type.toLowerCase().includes(q) || c.result.toLowerCase().includes(q)
      }
      return true
    })
  }, [cases, roleFilter, searchQuery])

  const statCards = [
    { label: '涉诉总数', value: totalCases, unit: '起', icon: icons.Scale, color: 'text-primary', bg: 'bg-primary/5' },
    { label: '作为被告', value: asDefendant, unit: '起', icon: icons.AlertTriangle, color: asDefendant > 0 ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground', bg: asDefendant > 0 ? 'bg-red-50 dark:bg-red-950/30' : 'bg-muted/50' },
    { label: '作为原告', value: asPlaintiff, unit: '起', icon: icons.ShieldCheck, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: '执行案件', value: executionCases, unit: '起', icon: icons.FileText, color: executionCases > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground', bg: executionCases > 0 ? 'bg-amber-50 dark:bg-amber-950/30' : 'bg-muted/50' },
    { label: '失信记录', value: dishonestRecords, unit: '条', icon: icons.XCircle, color: dishonestRecords > 0 ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground', bg: dishonestRecords > 0 ? 'bg-red-50 dark:bg-red-950/30' : 'bg-muted/50' },
  ]

  return (
    <div className="space-y-4">
      {/* 统计概览 */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {statCards.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`${cardStyle.compact} text-center`}
            >
              <div className={`w-8 h-8 mx-auto mb-2 rounded-full ${card.bg} flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${card.color}`} />
              </div>
              <p className={`text-xl font-bold ${card.color}`}>{card.value}</p>
              <p className={heading.muted}>{card.label}</p>
            </motion.div>
          )
        })}
      </div>

      {/* 案件列表 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className={cardStyle.base}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <icons.Scale className="w-5 h-5 text-primary" />
            <h3 className={heading.section}>案件列表</h3>
            <span className={heading.muted}>共 {filteredCases.length} 起</span>
          </div>

          <div className="flex items-center gap-2">
            {/* 角色筛选 */}
            <div className="flex rounded-lg overflow-hidden border border-border">
              {(['all', '原告', '被告'] as RoleFilter[]).map(f => (
                <button
                  key={f}
                  onClick={() => setRoleFilter(f)}
                  className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                    roleFilter === f ? 'bg-primary text-white' : 'bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {f === 'all' ? '全部' : f}
                </button>
              ))}
            </div>

            {/* 搜索 */}
            <div className="relative">
              <icons.Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="搜索案号/类型..."
                className={`${inputStyle.search} pl-8 py-1.5 text-xs w-[180px]`}
              />
            </div>
          </div>
        </div>

        {filteredCases.length > 0 ? (
          <div className="space-y-3">
            {filteredCases.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06 }}
                className="border border-border rounded-lg p-4 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <icons.FileText className="w-4 h-4 text-muted-foreground" />
                      <span className="font-mono text-xs text-muted-foreground">{item.caseNo}</span>
                    </div>
                    <h4 className={heading.card}>{item.type}</h4>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    item.status === '已结案'
                      ? 'bg-muted text-foreground'
                      : 'bg-primary/10 text-primary'
                  }`}>
                    {item.status}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className={`${heading.muted} mb-1`}>诉讼角色</p>
                    <p className={`font-medium text-xs ${item.role === '被告' ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                      {item.role}
                    </p>
                  </div>
                  <div>
                    <p className={`${heading.muted} mb-1`}>判决结果</p>
                    <p className="font-medium text-xs text-foreground">{item.result}</p>
                  </div>
                  <div>
                    <p className={`${heading.muted} mb-1`}>涉案金额</p>
                    <p className="font-medium text-xs text-foreground">{item.amount}</p>
                  </div>
                  <div>
                    <p className={`${heading.muted} mb-1`}>立案日期</p>
                    <p className="font-medium text-xs text-foreground">{item.date}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <icons.Scale className="w-10 h-10 mb-3 opacity-20" />
            <p className="text-sm">{searchQuery || roleFilter !== 'all' ? '未找到匹配的案件' : '暂无诉讼记录'}</p>
          </div>
        )}
      </motion.div>
    </div>
  )
}
