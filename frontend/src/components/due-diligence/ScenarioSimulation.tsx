/**
 * ScenarioSimulation - 风险场景推演
 *
 * 优先调用后端 API 进行 AI 推演，失败时降级到本地模板
 * 支持预设场景和自定义场景输入
 */
import { useState, useCallback } from'react'
import { motion, AnimatePresence } from'framer-motion'
import { icons } from'@/lib/icons'
import { cardStyle, heading, buttonStyle, inputStyle } from'@/lib/design-tokens'
import { dueDiligenceApi } from'@/lib/api'
import { toast } from'sonner'
import {
 RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
 ResponsiveContainer, Tooltip, Legend,
} from'recharts'

interface ImpactStep {
 event: string
 probability: number
 severity:'low' |'medium' |'high' |'critical'
}

interface SimulationResult {
 scenario: string
 impact_chain: ImpactStep[]
 risk_delta: Record<string, number>
 recommendations: string[]
 overall_assessment: string
}

interface ScenarioSimulationProps {
 companyName: string
 currentRisk?: {
 operation_risk?: number
 litigation_risk?: number
 credit_risk?: number
 compliance_risk?: number
 relation_risk?: number
 }
}

const SCENARIO_TEMPLATES = [
 { id:'customer_default', label:'主要客户违约', icon: icons.Users, description:'主要客户发生债务违约，无法按期支付应收款项' },
 { id:'regulatory_penalty', label:'监管处罚', icon: icons.ShieldAlert, description:'因合规问题被监管部门处以重大行政处罚' },
 { id:'key_person_leave', label:'核心人员离职', icon: icons.User, description:'核心技术人员或管理层关键人物离职' },
 { id:'policy_change', label:'行业政策变动', icon: icons.FileText, description:'行业政策发生重大调整，影响企业经营模式' },
]

const SEVERITY_CONFIG = {
 low: { label:'低', color:'text-success', bg:'bg-success/10', border:'border-success/20' },
 medium: { label:'中', color:'text-warning', bg:'bg-warning/10', border:'border-warning/20' },
 high: { label:'高', color:'text-destructive', bg:'bg-destructive/10', border:'border-destructive/20' },
 critical: { label:'极高', color:'text-destructive', bg:'bg-destructive/10', border:'border-destructive/20' },
}

const FALLBACK_RESULTS: Record<string, SimulationResult> = {
 customer_default: {
 scenario:'主要客户违约',
 impact_chain: [
 { event:'应收账款无法回收，坏账损失约 30%', probability: 0.8, severity:'high' },
 { event:'现金流紧张，运营资金缺口', probability: 0.7, severity:'high' },
 { event:'可能触发银行贷款违约条款', probability: 0.5, severity:'critical' },
 { event:'供应商信心下降，账期收紧', probability: 0.6, severity:'medium' },
 { event:'员工薪资发放延迟风险', probability: 0.3, severity:'medium' },
 ],
 risk_delta: { operation_risk: 25, litigation_risk: 15, credit_risk: 30, compliance_risk: 5, relation_risk: 20 },
 recommendations: ['立即启动应收账款催收程序，必要时提起诉讼','与银行沟通，提前协商贷款展期方案','优化供应商结构，分散客户集中度风险','制定现金流应急预案，确保核心业务运营'],
 overall_assessment:'该场景将导致企业信用风险和经营风险显著上升，建议提前建立风险缓冲机制，分散客户集中度。',
 },
 regulatory_penalty: {
 scenario:'监管处罚',
 impact_chain: [
 { event:'收到行政处罚决定书，罚款 50-200 万元', probability: 0.9, severity:'high' },
 { event:'企业信用评级下调', probability: 0.7, severity:'medium' },
 { event:'相关资质或许可证被暂扣', probability: 0.4, severity:'critical' },
 { event:'负面舆情扩散，品牌声誉受损', probability: 0.6, severity:'medium' },
 { event:'合作伙伴审查加严，部分合作暂停', probability: 0.5, severity:'medium' },
 ],
 risk_delta: { operation_risk: 15, litigation_risk: 10, credit_risk: 20, compliance_risk: 40, relation_risk: 15 },
 recommendations: ['立即组织内部合规审查，识别整改要点','聘请专业律师团队应对行政复议','制定公关应急方案，控制负面舆情影响','建立长效合规管理制度，防止再犯'],
 overall_assessment:'监管处罚将显著提升合规风险，企业需要迅速响应整改，同时做好舆情管控。',
 },
 key_person_leave: {
 scenario:'核心人员离职',
 impact_chain: [
 { event:'核心技术或管理能力暂时缺失', probability: 0.9, severity:'high' },
 { event:'关键项目进度受阻或延迟', probability: 0.7, severity:'medium' },
 { event:'团队士气受影响，可能引发连锁离职', probability: 0.4, severity:'medium' },
 { event:'竞业限制执行风险，商业秘密泄露隐患', probability: 0.3, severity:'high' },
 ],
 risk_delta: { operation_risk: 30, litigation_risk: 10, credit_risk: 5, compliance_risk: 5, relation_risk: 10 },
 recommendations: ['启动继任者计划，确保核心岗位备份','审查竞业限制协议的法律效力','加强知识管理，避免关键知识流失','与关键客户和合作伙伴做好沟通'],
 overall_assessment:'核心人员离职主要影响经营风险维度，建议建立人才梯队和知识沉淀机制。',
 },
 policy_change: {
 scenario:'行业政策变动',
 impact_chain: [
 { event:'经营模式需要调整以适应新规', probability: 0.8, severity:'medium' },
 { event:'合规成本显著增加', probability: 0.7, severity:'medium' },
 { event:'部分业务线可能被迫收缩或转型', probability: 0.5, severity:'high' },
 { event:'行业竞争格局重新洗牌', probability: 0.4, severity:'medium' },
 ],
 risk_delta: { operation_risk: 20, litigation_risk: 5, credit_risk: 10, compliance_risk: 25, relation_risk: 10 },
 recommendations: ['密切关注政策动态，提前布局合规调整','评估现有业务的合规差距','探索政策红利下的新业务机会','加强行业协会联系，参与政策制定讨论'],
 overall_assessment:'政策变动具有双面性，既是风险也是机遇，关键在于企业的响应速度和转型能力。',
 },
}

export function ScenarioSimulation({ companyName, currentRisk }: ScenarioSimulationProps) {
 const [selectedScenario, setSelectedScenario] = useState<string | null>(null)
 const [customScenario, setCustomScenario] = useState('')
 const [simulating, setSimulating] = useState(false)
 const [result, setResult] = useState<SimulationResult | null>(null)
 const [revealedSteps, setRevealedSteps] = useState(0)
 const [dataSource, setDataSource] = useState<'api' |'local' | null>(null)

 const animateReveal = async (chain: ImpactStep[]) => {
 for (let i = 0; i <= chain.length; i++) {
 await new Promise(resolve => setTimeout(resolve, 600))
 setRevealedSteps(i)
 }
 }

 const runSimulation = useCallback(async (scenarioId: string) => {
 setSelectedScenario(scenarioId)
 setSimulating(true)
 setResult(null)
 setRevealedSteps(0)
 setDataSource(null)

 try {
 const apiResult = await dueDiligenceApi.simulateScenario(scenarioId, companyName, currentRisk)
 const simData: SimulationResult = {
 scenario: apiResult.scenario || scenarioId,
 impact_chain: apiResult.impact_chain || [],
 risk_delta: apiResult.risk_delta || {},
 recommendations: apiResult.recommendations || [],
 overall_assessment: apiResult.overall_assessment ||'',
 }

 if (simData.impact_chain.length > 0) {
 setDataSource('api')
 await animateReveal(simData.impact_chain)
 setResult(simData)
 setSimulating(false)
 toast.success('AI 场景推演完成')
 return
 }
 } catch {
 // API 不可用，降级到本地模板
 }

 const fallback = FALLBACK_RESULTS[scenarioId]
 if (!fallback) {
 toast.error('暂不支持该场景模拟')
 setSimulating(false)
 return
 }

 setDataSource('local')
 await animateReveal(fallback.impact_chain)
 setResult(fallback)
 setSimulating(false)
 toast.success('场景推演完成')
 }, [companyName, currentRisk])

 const runCustomSimulation = useCallback(async () => {
 if (!customScenario.trim()) return
 setSelectedScenario('custom')
 setSimulating(true)
 setResult(null)
 setRevealedSteps(0)
 setDataSource(null)

 try {
 const apiResult = await dueDiligenceApi.simulateScenario('custom', companyName, {
 ...currentRisk,
 custom_scenario: customScenario,
 })
 const simData: SimulationResult = {
 scenario: customScenario,
 impact_chain: apiResult.impact_chain || [],
 risk_delta: apiResult.risk_delta || {},
 recommendations: apiResult.recommendations || [],
 overall_assessment: apiResult.overall_assessment ||'',
 }

 if (simData.impact_chain.length > 0) {
 setDataSource('api')
 await animateReveal(simData.impact_chain)
 setResult(simData)
 setSimulating(false)
 toast.success('AI 自定义场景推演完成')
 return
 }
 } catch {
 // 降级提示
 }

 toast.info('AI 服务暂不可用，自定义场景推演需要后端 AI 支持。请使用预设场景。')
 setSimulating(false)
 }, [customScenario, companyName, currentRisk])

 const currentRiskData = currentRisk ? [
 { dimension:'经营风险', current: currentRisk.operation_risk || 0, after: (currentRisk.operation_risk || 0) + (result?.risk_delta?.operation_risk || 0) },
 { dimension:'诉讼风险', current: currentRisk.litigation_risk || 0, after: (currentRisk.litigation_risk || 0) + (result?.risk_delta?.litigation_risk || 0) },
 { dimension:'信用风险', current: currentRisk.credit_risk || 0, after: (currentRisk.credit_risk || 0) + (result?.risk_delta?.credit_risk || 0) },
 { dimension:'合规风险', current: currentRisk.compliance_risk || 0, after: (currentRisk.compliance_risk || 0) + (result?.risk_delta?.compliance_risk || 0) },
 { dimension:'关联风险', current: currentRisk.relation_risk || 0, after: (currentRisk.relation_risk || 0) + (result?.risk_delta?.relation_risk || 0) },
 ] : []

 const activeResult = result || (selectedScenario && selectedScenario !=='custom' ? FALLBACK_RESULTS[selectedScenario] : null)

 return (
 <div className="space-y-6">
 {/* 场景选择 */}
 <div>
 <h3 className={`${heading.section} mb-3`}>选择推演场景</h3>
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
 {SCENARIO_TEMPLATES.map(tmpl => {
 const Icon = tmpl.icon
 const isActive = selectedScenario === tmpl.id
 return (
 <motion.button
 key={tmpl.id}
 whileHover={{ scale: 1.02 }}
 whileTap={{ scale: 0.98 }}
 onClick={() => runSimulation(tmpl.id)}
 disabled={simulating}
 className={`p-4 rounded-xl border text-left transition-all ${
 isActive
 ?'border-primary bg-primary/5 ring-2 ring-primary/20'
 :'border-border hover:border-primary/30 hover:bg-muted/30'
 } ${simulating ?'opacity-60 cursor-wait' :''}`}
 >
 <Icon className={`w-5 h-5 mb-2 ${isActive ?'text-primary' :'text-muted-foreground'}`} />
 <p className={`text-sm font-medium ${isActive ?'text-primary' :'text-foreground'}`}>{tmpl.label}</p>
 <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">{tmpl.description}</p>
 </motion.button>
 )
 })}
 </div>
 </div>

 {/* 自定义场景 */}
 <div className="flex gap-2">
 <input
 type="text"
 value={customScenario}
 onChange={e => setCustomScenario(e.target.value)}
 onKeyDown={e => e.key ==='Enter' && runCustomSimulation()}
 placeholder="输入自定义风险场景（如：核心专利被无效、原材料价格暴涨 50%）..."
 className={`${inputStyle.search} flex-1`}
 />
 <button
 onClick={runCustomSimulation}
 disabled={!customScenario.trim() || simulating}
 className={buttonStyle.primary}
 >
 推演
 </button>
 </div>

 {/* 推演结果 */}
 {(simulating || activeResult) && (
 <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
 {/* 影响链 */}
 <div className={cardStyle.base}>
 <div className="flex items-center justify-between mb-4">
 <h3 className={heading.section}>影响链推演</h3>
 {dataSource && (
 <span className={`text-[10px] px-2 py-0.5 rounded-full ${
 dataSource ==='api'
 ?'bg-primary/10 text-primary'
 :'bg-muted text-muted-foreground'
 }`}>
 {dataSource ==='api' ?'AI 推演' :'模板推演'}
 </span>
 )}
 </div>
 <div className="relative space-y-3">
 <div className="absolute left-4 top-6 bottom-6 w-0.5 bg-border" />

 {activeResult?.impact_chain.map((step, i) => {
 const sc = SEVERITY_CONFIG[step.severity]
 const isRevealed = i < revealedSteps

 return (
 <AnimatePresence key={i}>
 {isRevealed && (
 <motion.div
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: 0.1 }}
 className="relative pl-10"
 >
 <div className={`absolute left-2 w-5 h-5 rounded-full border-2 border-background flex items-center justify-center text-[8px] font-bold text-white ${
 step.severity ==='critical' ?'bg-destructive' : step.severity ==='high' ?'bg-destructive' : step.severity ==='medium' ?'bg-warning' :'bg-success'
 }`}>
 {i + 1}
 </div>
 <div className={`p-3 rounded-lg border ${sc.bg} ${sc.border}`}>
 <div className="flex items-center justify-between mb-1">
 <span className={`text-xs font-medium ${sc.color}`}>
 {sc.label}风险 · 概率 {(step.probability * 100).toFixed(0)}%
 </span>
 </div>
 <p className="text-sm text-foreground">{step.event}</p>
 <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
 <motion.div
 initial={{ width: 0 }}
 animate={{ width: `${step.probability * 100}%` }}
 transition={{ duration: 0.5, delay: 0.2 }}
 className={`h-full rounded-full ${
 step.severity ==='critical' ?'bg-destructive' : step.severity ==='high' ?'bg-destructive' : step.severity ==='medium' ?'bg-warning' :'bg-success'
 }`}
 />
 </div>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 )
 })}

 {simulating && (
 <div className="relative pl-10">
 <div className="absolute left-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
 <icons.Loader2 className="w-3 h-3 text-white animate-spin" />
 </div>
 <p className="text-xs text-muted-foreground py-2">正在推演下一步影响...</p>
 </div>
 )}
 </div>
 </div>

 {/* 右侧：风险对比 + 建议 */}
 <div className="space-y-4">
 {result && currentRiskData.length > 0 && (
 <div className={cardStyle.base}>
 <h3 className={`${heading.section} mb-4`}>风险变化对比</h3>
 <ResponsiveContainer width="100%" height={250}>
 <RadarChart data={currentRiskData}>
 <PolarGrid strokeDasharray="3 3" />
 <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 10 }} />
 <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
 <Radar name="当前风险" dataKey="current" stroke="hsl(var(--primary))" fill="hsl(var(--primary))" fillOpacity={0.2} strokeWidth={2} />
 <Radar name="推演后风险" dataKey="after" stroke="#FF3B30" fill="#FF3B30" fillOpacity={0.15} strokeWidth={2} strokeDasharray="5 5" />
 <Legend />
 <Tooltip />
 </RadarChart>
 </ResponsiveContainer>

 <div className="grid grid-cols-5 gap-1 mt-3">
 {currentRiskData.map(d => {
 const delta = d.after - d.current
 return (
 <div key={d.dimension} className="text-center">
 <p className="text-[10px] text-muted-foreground">{d.dimension.replace('风险','')}</p>
 <p className={`text-xs font-bold ${delta > 20 ?'text-destructive' : delta > 10 ?'text-warning' :'text-success'}`}>
 +{delta}
 </p>
 </div>
 )
 })}
 </div>
 </div>
 )}

 {result && (
 <motion.div
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 className={cardStyle.base}
 >
 <h3 className={`${heading.section} mb-3`}>应对建议</h3>
 <div className="space-y-2">
 {result.recommendations.map((rec, i) => (
 <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-primary/5">
 <span className="w-5 h-5 rounded-full bg-primary text-white text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-bold">
 {i + 1}
 </span>
 <p className="text-xs text-foreground leading-relaxed">{rec}</p>
 </div>
 ))}
 </div>

 <div className="mt-4 p-3 rounded-lg bg-muted/50 border border-border">
 <p className="text-xs font-medium text-foreground mb-1">总体评估</p>
 <p className="text-xs text-muted-foreground leading-relaxed">{result.overall_assessment}</p>
 </div>
 </motion.div>
 )}
 </div>
 </div>
 )}

 {/* 空状态 */}
 {!simulating && !activeResult && (
 <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
 <icons.Cpu className="w-12 h-12 mb-3 opacity-20" />
 <p className="text-sm">选择一个风险场景开始推演</p>
 <p className="text-xs mt-1 opacity-60">AI 将基于调查数据模拟影响链条和风险变化</p>
 </div>
 )}
 </div>
 )
}
