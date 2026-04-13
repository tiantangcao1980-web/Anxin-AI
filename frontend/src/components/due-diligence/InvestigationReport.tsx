/**
 * InvestigationReport - 调查报告生成与展示
 *
 * 优先调用后端 report_engine 生成报告，失败时使用本地模板
 * 支持：在线预览、PDF 导出（浏览器打印）、文本复制
 */
import { useState, useCallback, useRef } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { cardStyle, heading, buttonStyle, statusBadge } from'@/lib/design-tokens'
import { dueDiligenceApi } from'@/lib/api'
import { toast } from'sonner'

interface ReportSection {
 id: string
 title: string
 icon: any
 content: string
 status?:'pass' |'warning' |'fail'
}

interface InvestigationReportProps {
 companyName: string
 investigationData: any
 onBack?: () => void
}

export function InvestigationReport({ companyName, investigationData, onBack }: InvestigationReportProps) {
 const [generating, setGenerating] = useState(false)
 const [activeSection, setActiveSection] = useState('summary')
 const [reportGenerated, setReportGenerated] = useState(false)
 const [apiReport, setApiReport] = useState<any>(null)
 const [dataSource, setDataSource] = useState<'api' |'local' | null>(null)
 const reportRef = useRef<HTMLDivElement>(null)

 const data = investigationData || {}
 const risk = data.risk || {}
 const litigation = data.litigation || {}
 const credit = data.credit || {}
 const basicInfo = data.basicInfo || {}

 const riskScore = Math.round(
 ((risk.operation_risk || 0) + (risk.litigation_risk || 0) + (risk.credit_risk || 0) + (risk.compliance_risk || 0) + (risk.relation_risk || 0)) / 5
 )

 const buildLocalSections = (): ReportSection[] => [
 {
 id:'summary',
 title:'执行摘要',
 icon: icons.FileText,
 content: `本报告对 ${companyName} 进行了全面的尽职调查分析。调查涵盖企业基本信息、风险评估、诉讼分析、信用合规及关联关系等多个维度。` +
 `\n\n综合风险评分为 ${riskScore} 分（满分 100），整体风险等级为${riskScore > 60 ?'高' : riskScore > 35 ?'中' :'低'}风险。` +
 (risk.risk_points?.length ? `\n\n主要风险点：\n${risk.risk_points.map((p: string, i: number) => `${i + 1}. ${p}`).join('\n')}` :''),
 },
 {
 id:'company',
 title:'企业概况',
 icon: icons.Building2,
 content: `企业名称：${basicInfo.name || companyName}\n` +
 `法定代表人：${basicInfo.legal_representative ||'-'}\n` +
 `注册资本：${basicInfo.registered_capital ||'-'}\n` +
 `成立日期：${basicInfo.established_date ||'-'}\n` +
 `经营状态：${basicInfo.status ||'-'}\n` +
 `经营范围：${basicInfo.business_scope ||'-'}\n` +
 `注册地址：${basicInfo.address ||'-'}`,
 },
 {
 id:'risk',
 title:'风险评估',
 icon: icons.ShieldAlert,
 status: riskScore > 60 ?'fail' : riskScore > 35 ?'warning' :'pass',
 content: `五维风险评分：\n` +
 ` 经营风险：${risk.operation_risk || 0}/100\n` +
 ` 诉讼风险：${risk.litigation_risk || 0}/100\n` +
 ` 信用风险：${risk.credit_risk || 0}/100\n` +
 ` 合规风险：${risk.compliance_risk || 0}/100\n` +
 ` 关联风险：${risk.relation_risk || 0}/100\n\n` +
 `综合风险评分：${riskScore}/100\n` +
 `风险等级：${risk.overall_rating || (riskScore > 60 ?'高风险' : riskScore > 35 ?'中风险' :'低风险')}`,
 },
 {
 id:'litigation',
 title:'诉讼分析',
 icon: icons.Scale,
 status: (litigation.total_cases || 0) > 5 ?'fail' : (litigation.total_cases || 0) > 0 ?'warning' :'pass',
 content: `涉诉总数：${litigation.total_cases || litigation.major_cases?.length || 0} 起\n` +
 `作为原告：${litigation.as_plaintiff || 0} 起\n` +
 `作为被告：${litigation.as_defendant || 0} 起\n` +
 `执行案件：${litigation.execution_cases || 0} 起\n` +
 `失信记录：${litigation.dishonest_records || 0} 条` +
 (litigation.major_cases?.length ? `\n\n主要案件：\n${litigation.major_cases.slice(0, 5).map((c: any, i: number) =>
 `${i + 1}. ${c.case_no || c.caseNo ||'未公布'} - ${c.case_type || c.type ||'未知'} (${c.role ||'未知'}, ${c.status ||'未知'})`
 ).join('\n')}` :''),
 },
 {
 id:'compliance',
 title:'信用合规',
 icon: icons.FileCheck,
 status: !credit.credit_rating ?'pass' : ['AAA','AA','A'].includes(credit.credit_rating?.toUpperCase?.()) ?'pass' :'warning',
 content: `信用评级：${credit.credit_rating ||'-'}\n` +
 `行政处罚：${credit.administrative_penalties || 0} 条\n` +
 `税务违规：${credit.tax_violations || 0} 条\n` +
 `环保处罚：${credit.environmental_penalties || 0} 条\n` +
 `经营异常：${credit.abnormal_operations || 0} 条\n` +
 `严重违法：${credit.serious_violations || 0} 条`,
 },
 {
 id:'recommendations',
 title:'建议措施',
 icon: icons.Sparkles,
 content: risk.recommendations?.length
 ? risk.recommendations.map((r: string, i: number) => `${i + 1}. ${r}`).join('\n')
 :'1. 定期监控企业风险指标变化\n2. 关注涉诉案件进展\n3. 持续跟踪信用评级动态\n4. 建立合规预警机制\n5. 评估关联企业风险传导',
 },
 ]

 /** 从 API 报告数据转换为 section 列表 */
 const parseApiSections = (report: any): ReportSection[] => {
 if (report?.sections && Array.isArray(report.sections)) {
 return report.sections.map((s: any) => ({
 id: s.id || s.title,
 title: s.title,
 icon: icons.FileText,
 content: s.content || s.html ||'',
 status: s.status,
 }))
 }
 if (report?.html) {
 return [{
 id:'full',
 title:'完整报告',
 icon: icons.FileText,
 content: report.html,
 }]
 }
 return []
 }

 const sections: ReportSection[] = apiReport
 ? (parseApiSections(apiReport).length > 0 ? parseApiSections(apiReport) : buildLocalSections())
 : buildLocalSections()

 const handleGenerateReport = useCallback(async () => {
 setGenerating(true)
 try {
 const result = await dueDiligenceApi.generateReport(companyName)
 if (result) {
 setApiReport(result)
 setDataSource('api')
 toast.success('AI 调查报告已生成')
 } else {
 throw new Error('空响应')
 }
 } catch {
 setDataSource('local')
 toast.success('调查报告已生成')
 }
 setGenerating(false)
 setReportGenerated(true)
 }, [companyName])

 const handleExportPDF = () => {
 if (reportRef.current) {
 const printWindow = window.open('','_blank')
 if (printWindow) {
 printWindow.document.write(`
 <html><head><title>${companyName} - 尽职调查报告</title>
 <style>
 body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 40px; color: #333; line-height: 1.8; }
 h1 { font-size: 24px; border-bottom: 2px solid #007AFF; padding-bottom: 8px; }
 h2 { font-size: 18px; color: #007AFF; margin-top: 24px; }
 pre { white-space: pre-wrap; font-family: inherit; }
 .section { margin-bottom: 24px; padding: 16px; border: 1px solid #e5e5e5; border-radius: 8px; }
 .status-pass { color: #34C759; } .status-warning { color: #FF9500; } .status-fail { color: #FF3B30; }
 .footer { text-align: center; color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #e5e5e5; padding-top: 16px; }
 </style></head><body>
 <h1>${companyName} — 尽职调查报告</h1>
 <p style="color: #666;">报告生成时间：${new Date().toLocaleString('zh-CN')}</p>
 ${sections.map(s => `
 <div class="section">
 <h2>${s.title} ${s.status ? `<span class="status-${s.status}">[${s.status ==='pass' ?'正常' : s.status ==='warning' ?'关注' :'异常'}]</span>` :''}</h2>
 <pre>${s.content}</pre>
 </div>
 `).join('')}
 <div class="footer">
 <p>本报告由安心智能法律服务平台 AI 辅助生成，仅供参考</p>
 </div>
 </body></html>
 `)
 printWindow.document.close()
 printWindow.print()
 }
 }
 }

 const handleCopyReport = async () => {
 const text = sections.map(s => `## ${s.title}\n\n${s.content}`).join('\n\n---\n\n')
 const fullText = `# ${companyName} — 尽职调查报告\n\n生成时间：${new Date().toLocaleString('zh-CN')}\n\n${text}\n\n---\n本报告由安心智能法律服务平台 AI 辅助生成，仅供参考`
 try {
 await navigator.clipboard.writeText(fullText)
 toast.success('报告已复制到剪贴板')
 } catch {
 toast.error('复制失败，请手动选择文本复制')
 }
 }

 const statusIcon = (status?: string) => {
 switch (status) {
 case'pass': return <icons.CheckCircle className="w-4 h-4 text-success" />
 case'warning': return <icons.AlertCircle className="w-4 h-4 text-warning" />
 case'fail': return <icons.XCircle className="w-4 h-4 text-destructive" />
 default: return null
 }
 }

 return (
 <div className="space-y-4" ref={reportRef}>
 {/* 工具栏 */}
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <h3 className={heading.section}>{companyName} — 调查报告</h3>
 {reportGenerated && (
 <span className={`text-xs px-2 py-0.5 rounded-full ${statusBadge.success}`}>已生成</span>
 )}
 {dataSource && (
 <span className={`text-[10px] px-2 py-0.5 rounded-full ${
 dataSource ==='api' ?'bg-primary/10 text-primary' :'bg-muted text-muted-foreground'
 }`}>
 {dataSource ==='api' ?'AI 生成' :'模板生成'}
 </span>
 )}
 </div>
 <div className="flex items-center gap-2">
 {!reportGenerated ? (
 <button onClick={handleGenerateReport} disabled={generating} className={`${buttonStyle.primary} flex items-center gap-1.5`}>
 {generating ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Sparkles className="w-4 h-4" />}
 {generating ?'生成中...' :'生成报告'}
 </button>
 ) : (
 <>
 <button onClick={handleExportPDF} className={`${buttonStyle.secondary} flex items-center gap-1.5`}>
 <icons.Download className="w-4 h-4" />
 导出 PDF
 </button>
 <button onClick={handleCopyReport} className={`${buttonStyle.ghost} flex items-center gap-1.5`}>
 <icons.Copy className="w-4 h-4" />
 复制
 </button>
 </>
 )}
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
 {/* 章节导航 */}
 <div className="lg:col-span-1">
 <div className={`${cardStyle.base} sticky top-4`}>
 <h4 className={`${heading.card} mb-3`}>报告目录</h4>
 <nav className="space-y-1">
 {sections.map(section => {
 const Icon = section.icon
 return (
 <button
 key={section.id}
 onClick={() => {
 setActiveSection(section.id)
 document.getElementById(`report-${section.id}`)?.scrollIntoView({ behavior:'smooth', block:'start' })
 }}
 className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs font-medium transition-all ${
 activeSection === section.id
 ?'bg-primary/10 text-primary'
 :'text-muted-foreground hover:bg-muted hover:text-foreground'
 }`}
 >
 <Icon className="w-3.5 h-3.5 shrink-0" />
 <span className="flex-1 text-left">{section.title}</span>
 {statusIcon(section.status)}
 </button>
 )
 })}
 </nav>
 </div>
 </div>

 {/* 报告内容 */}
 <div className="lg:col-span-3 space-y-4">
 {sections.map(section => (
 <motion.div
 key={section.id}
 id={`report-${section.id}`}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 className={`${cardStyle.base} ${activeSection === section.id ?'ring-2 ring-primary/20' :''}`}
 >
 <div className="flex items-center gap-2 mb-4">
 <section.icon className="w-5 h-5 text-primary" />
 <h3 className={heading.section}>{section.title}</h3>
 {section.status && (
 <span className={`text-xs px-2 py-0.5 rounded-full ${
 section.status ==='pass' ? statusBadge.success
 : section.status ==='warning' ? statusBadge.warning
 : statusBadge.error
 }`}>
 {section.status ==='pass' ?'正常' : section.status ==='warning' ?'关注' :'异常'}
 </span>
 )}
 </div>
 <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
 {section.content}
 </div>
 </motion.div>
 ))}

 <div className="text-xs text-muted-foreground text-center py-4 border-t border-border">
 <p>本报告由安心智能法律服务平台 AI 辅助生成，仅供参考</p>
 <p className="mt-0.5">生成时间：{new Date().toLocaleString('zh-CN')}</p>
 </div>
 </div>
 </div>
 </div>
 )
}
