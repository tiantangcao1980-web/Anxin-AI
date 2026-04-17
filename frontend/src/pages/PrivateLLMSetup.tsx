import { useState, useEffect } from'react'
import { icons } from'@/lib/icons'
import { toast } from'sonner'
import { cardStyle, buttonStyle, heading, iconSize, inputStyle, statusBadge, statusColor } from'@/lib/design-tokens'
import { PageContainer, PageSection } from'@/components/ui/PageContainer'
import { Button } from'@/components/ui/button'
import { Input } from'@/components/ui/input'
import { Label } from'@/components/ui/label'
import { Badge } from'@/components/ui/badge'
import { Skeleton } from'@/components/ui/skeleton'
import { Progress } from'@/components/ui/progress'
import { ErrorState } from'@/components/common'
import { aiAssistantApi } from'@/lib/api'

// ====================================================================
// 类型定义
// ====================================================================

interface DetectedService {
 id: string
 name: string
 icon: keyof typeof icons
 status:'running' |'not_found'
 port?: number
 installUrl?: string
}

interface RecommendedModel {
 id: string
 name: string
 vram: string
 description: string
 installCommand: string
 size: string
}

interface TestResult {
 status:'idle' |'testing' |'success' |'failed'
 latency?: number
 modelInfo?: string
 error?: string
}

interface DeployGuide {
 provider: string
 steps: string[]
}

// ====================================================================

type PageState ='loading' |'error' |'ready'

export default function PrivateLLMSetup() {
 const [state, setState] = useState<PageState>('loading')
 const [errorMsg, setErrorMsg] = useState<string>('')
 const [currentStep, setCurrentStep] = useState(0)
 const [services, setServices] = useState<DetectedService[]>([])
 const [models, setModels] = useState<RecommendedModel[]>([])
 const [deployGuides, setDeployGuides] = useState<DeployGuide[]>([])
 const [selectedModel, setSelectedModel] = useState<string>('')
 const [endpoint, setEndpoint] = useState('http://localhost:11434')
 const [modelName, setModelName] = useState('')
 const [testResult, setTestResult] = useState<TestResult>({ status:'idle' })
 const [showGuide, setShowGuide] = useState(false)
 const [guideProvider, setGuideProvider] = useState('')
 const [detecting, setDetecting] = useState(false)

 useEffect(() => {
 let cancelled = false
 async function fetchData() {
 setState('loading')
 try {
 const [detectData, modelsData] = await Promise.all([
 aiAssistantApi.detectLocalLLM(),
 aiAssistantApi.getRecommendedModels(),
 ])
 if (cancelled) return

 // 检测到的服务
 const svcList = Array.isArray(detectData) ? detectData : detectData?.services || []
 setServices(svcList.map((s: any) => ({
 id: s.id ||'',
 name: s.name ||'',
 icon: s.icon ||'Terminal',
 status: s.status ||'not_found',
 port: s.port,
 installUrl: s.install_url || s.installUrl,
 })))

 // 推荐模型
 const modelList = Array.isArray(modelsData) ? modelsData : modelsData?.models || []
 setModels(modelList.map((m: any) => ({
 id: m.id ||'',
 name: m.name ||'',
 vram: m.vram ||'',
 description: m.description ||'',
 installCommand: m.install_command || m.installCommand ||'',
 size: m.size ||'',
 })))

 setState('ready')
 } catch (err: any) {
 if (!cancelled) {
 console.error('私有LLM配置加载失败:', err)
 setErrorMsg(err?.message ||'数据加载失败，请稍后重试')
 setState('error')
 }
 }
 }
 fetchData()
 return () => { cancelled = true }
 }, [])

 const handleDetect = async () => {
 setDetecting(true)
 try {
 const detectData = await aiAssistantApi.detectLocalLLM()
 const svcList = Array.isArray(detectData) ? detectData : detectData?.services || []
 setServices(svcList.map((s: any) => ({
 id: s.id ||'',
 name: s.name ||'',
 icon: s.icon ||'Terminal',
 status: s.status ||'not_found',
 port: s.port,
 installUrl: s.install_url || s.installUrl,
 })))
 toast.success('环境检测完成')
 } catch (err: any) {
 toast.error(err?.message ||'检测失败，请稍后重试')
 } finally {
 setDetecting(false)
 }
 }

 const handleTestConnection = async () => {
 setTestResult({ status:'testing' })
 try {
 const result = await aiAssistantApi.testConnection({
 endpoint,
 model: modelName || undefined,
 })
 setTestResult({
 status:'success',
 latency: result?.latency || result?.response_time,
 modelInfo: result?.model_info || result?.modelInfo || `${modelName ||'unknown'} connected`,
 })
 toast.success('连接测试成功')
 } catch (err: any) {
 setTestResult({
 status:'failed',
 error: err?.message ||'无法连接到指定端点',
 })
 toast.error('连接测试失败')
 }
 }

 const handleSave = async () => {
 try {
 await aiAssistantApi.updateConfig({
 private_llm: {
 endpoint,
 model: modelName,
 },
 })
 toast.success('私有 LLM 配置已保存')
 } catch (err: any) {
 toast.error(err?.message ||'保存失败，请稍后重试')
 }
 }

 const handleShowGuide = async (provider: string) => {
 setGuideProvider(provider)
 // 如果还没有加载该 provider 的指南，就从 API 获取
 const existing = deployGuides.find(g => g.provider === provider)
 if (!existing) {
 try {
 const guideData = await aiAssistantApi.getDeploymentGuide(provider.toLowerCase())
 const steps = guideData?.steps || []
 setDeployGuides(prev => [...prev, { provider, steps }])
 } catch {
 // 如果加载失败，添加空指南
 setDeployGuides(prev => [...prev, { provider, steps: ['暂无部署指南'] }])
 }
 }
 }

 const steps = ['环境检测','选择模型','测试连接']

 // 初始化 guideProvider
 useEffect(() => {
 if (services.length > 0 && !guideProvider) {
 setGuideProvider(services[0]?.name ||'Ollama')
 }
 }, [services, guideProvider])

 if (state ==='loading') {
 return (
 <PageContainer title="私有 LLM 配置" description="配置本地大语言模型服务">
 <div className="space-y-6">
 <Skeleton className="h-16 w-full rounded-xl" />
 <Skeleton className="h-64 w-full rounded-xl" />
 <Skeleton className="h-48 w-full rounded-xl" />
 </div>
 </PageContainer>
 )
 }

 if (state ==='error') {
 return (
 <PageContainer title="私有 LLM 配置" description="配置本地大语言模型服务">
 <ErrorState
 title="加载失败"
 message={errorMsg ||'请检查网络后重试'}
 onRetry={() => window.location.reload()}
 />
 </PageContainer>
 )
 }

 return (
 <PageContainer title="私有 LLM 配置" description="三步配置本地大语言模型，数据不出本地">
 <div className="space-y-6">
 {/* ===== Stepper ===== */}
 <div className={cardStyle.base}>
 <div className="flex items-center gap-2">
 {steps.map((label, i) => (
 <div key={label} className="flex items-center gap-2 flex-1">
 <button
 onClick={() => setCurrentStep(i)}
 className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm font-medium ${
 i === currentStep
 ?'bg-primary text-primary-foreground'
 : i < currentStep
 ?'bg-primary/10 text-primary'
 :'bg-muted text-muted-foreground'
 }`}
 >
 <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0"
 style={{
 borderColor: i <= currentStep ?'currentColor' : undefined,
 }}
 >
 {i < currentStep ? <icons.Check className="w-3 h-3" /> : i + 1}
 </span>
 <span className="hidden sm:inline">{label}</span>
 </button>
 {i < steps.length - 1 && (
 <div className={`flex-1 h-px ${i < currentStep ?'bg-primary' :'bg-border'}`} />
 )}
 </div>
 ))}
 </div>
 </div>

 {/* ===== Step 1: 环境检测 ===== */}
 {currentStep === 0 && (
 <div className={cardStyle.base}>
 <PageSection
 title="环境检测"
 description="自动检测本地 LLM 服务运行状态"
 actions={
 <Button variant="outline" size="sm" onClick={handleDetect} disabled={detecting}>
 {detecting ? (
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 ) : (
 <icons.Refresh className={iconSize.sm} />
 )}
 {detecting ?'检测中...' :'重新检测'}
 </Button>
 }
 >
 {services.length > 0 ? (
 <div className="space-y-2">
 {services.map(svc => {
 const Icon = icons[svc.icon] || icons.Terminal
 const isRunning = svc.status ==='running'
 return (
 <div
 key={svc.id}
 className={`flex items-center gap-3 p-3 rounded-lg border ${
 isRunning ?'border-success/20 bg-success/10' :'border-border bg-muted/30'
 }`}
 >
 <Icon className={`${iconSize.md} ${isRunning ?'text-success' :'text-muted-foreground'}`} />
 <div className="flex-1 min-w-0">
 <p className={heading.card}>{svc.name}</p>
 {isRunning && svc.port && (
 <p className={heading.micro}>端口: {svc.port}</p>
 )}
 </div>
 <Badge className={isRunning ? statusBadge.success : statusBadge.neutral}>
 {isRunning ?'运行中' :'未检测到'}
 </Badge>
 {!isRunning && svc.installUrl && (
 <a
 href={svc.installUrl}
 target="_blank"
 rel="noopener noreferrer"
 className="text-xs text-primary hover:underline flex items-center gap-1"
 >
 安装指南
 <icons.ExternalLink className="w-3 h-3" />
 </a>
 )}
 </div>
 )
 })}
 </div>
 ) : (
 <div className="py-8 text-center text-sm text-muted-foreground">未检测到本地 LLM 服务</div>
 )}

 <div className="flex justify-end pt-4">
 <Button className={buttonStyle.primary} onClick={() => setCurrentStep(1)}>
 下一步
 <icons.ChevronRight className={iconSize.sm} />
 </Button>
 </div>
 </PageSection>
 </div>
 )}

 {/* ===== Step 2: 选择模型 ===== */}
 {currentStep === 1 && (
 <div className={cardStyle.base}>
 <PageSection title="选择模型" description="推荐适合法律场景的本地模型">
 {models.length > 0 ? (
 <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
 {models.map(model => {
 const isSelected = selectedModel === model.id
 return (
 <button
 key={model.id}
 onClick={() => {
 setSelectedModel(model.id)
 setModelName(model.name.toLowerCase().replace('-',':'))
 }}
 className={`p-4 rounded-xl border text-left transition-colors ${
 isSelected
 ?'border-primary bg-primary/5 ring-2 ring-primary/20'
 :'border-border hover:border-primary/30 hover:bg-muted/50'
 }`}
 >
 <div className="flex items-start justify-between mb-2">
 <p className="text-sm font-medium text-foreground">{model.name}</p>
 <Badge variant="secondary" className="text-xs shrink-0 ml-2">{model.size}</Badge>
 </div>
 <p className="text-xs text-muted-foreground mb-2">{model.description}</p>
 <div className="flex items-center gap-2 mb-3">
 <Badge className={statusBadge.info}>{model.vram}</Badge>
 </div>
 {model.installCommand && (
 <div className="bg-foreground/5 rounded-lg p-2">
 <code className="text-xs font-mono text-foreground/80 break-all">
 {model.installCommand}
 </code>
 </div>
 )}
 </button>
 )
 })}
 </div>
 ) : (
 <div className="py-8 text-center text-sm text-muted-foreground">暂无推荐模型</div>
 )}

 <div className="flex justify-between pt-4">
 <Button variant="outline" onClick={() => setCurrentStep(0)}>
 <icons.ChevronLeft className={iconSize.sm} />
 上一步
 </Button>
 <Button className={buttonStyle.primary} onClick={() => setCurrentStep(2)}>
 下一步
 <icons.ChevronRight className={iconSize.sm} />
 </Button>
 </div>
 </PageSection>
 </div>
 )}

 {/* ===== Step 3: 测试连接 ===== */}
 {currentStep === 2 && (
 <div className={cardStyle.base}>
 <PageSection title="测试连接" description="验证本地 LLM 服务可用性">
 <div className="space-y-4 max-w-xl">
 <div className="space-y-2">
 <Label className={heading.card}>服务端点</Label>
 <Input
 className={inputStyle.search}
 placeholder="http://localhost:11434"
 value={endpoint}
 onChange={e => setEndpoint(e.target.value)}
 />
 </div>

 <div className="space-y-2">
 <Label className={heading.card}>模型名称</Label>
 <Input
 className={inputStyle.search}
 placeholder="qwen2.5:7b"
 value={modelName}
 onChange={e => setModelName(e.target.value)}
 />
 </div>

 <Button
 className={buttonStyle.primary}
 onClick={handleTestConnection}
 disabled={testResult.status ==='testing'}
 >
 {testResult.status ==='testing' ? (
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 ) : (
 <icons.Zap className={iconSize.sm} />
 )}
 {testResult.status ==='testing' ?'测试中...' :'测试连接'}
 </Button>

 {/* 测试结果 */}
 {testResult.status ==='success' && (
 <div className={`p-4 rounded-xl border ${statusColor.success} border-success/20`}>
 <div className="flex items-center gap-2 mb-2">
 <icons.CheckCircle className={`${iconSize.md} text-success`} />
 <p className="text-sm font-medium">连接成功</p>
 </div>
 <div className="space-y-1 text-sm">
 {testResult.latency && <p>延迟: <span className="font-mono">{testResult.latency}ms</span></p>}
 {testResult.modelInfo && <p>模型: {testResult.modelInfo}</p>}
 </div>
 </div>
 )}

 {testResult.status ==='failed' && (
 <div className={`p-4 rounded-xl border ${statusColor.error} border-destructive/20`}>
 <div className="flex items-center gap-2 mb-2">
 <icons.AlertCircle className={`${iconSize.md} text-destructive`} />
 <p className="text-sm font-medium">连接失败</p>
 </div>
 <p className="text-sm">{testResult.error ||'无法连接到指定端点'}</p>
 </div>
 )}
 </div>

 <div className="flex justify-between pt-4">
 <Button variant="outline" onClick={() => setCurrentStep(1)}>
 <icons.ChevronLeft className={iconSize.sm} />
 上一步
 </Button>
 {testResult.status ==='success' && (
 <Button className={buttonStyle.primary} onClick={handleSave}>
 <icons.Check className={iconSize.sm} />
 保存配置
 </Button>
 )}
 </div>
 </PageSection>
 </div>
 )}

 {/* ===== 底部折叠: 部署指南 ===== */}
 <div className={cardStyle.base}>
 <button
 onClick={() => {
 setShowGuide(!showGuide)
 if (!showGuide && guideProvider) {
 handleShowGuide(guideProvider)
 }
 }}
 className="flex items-center gap-2 w-full text-left"
 >
 {showGuide ? (
 <icons.ChevronUp className={iconSize.sm +' text-muted-foreground'} />
 ) : (
 <icons.ChevronDown className={iconSize.sm +' text-muted-foreground'} />
 )}
 <span className={heading.section}>部署指南</span>
 <span className={heading.micro}>-- 按提供商查看分步安装命令</span>
 </button>

 {showGuide && (
 <div className="mt-4 space-y-4">
 {/* Provider 切换 */}
 <div className="flex gap-2">
 {(services.length > 0
 ? [...new Set(services.map(s => s.name))]
 : ['Ollama','vLLM','LM Studio']
 ).map(provider => (
 <Button
 key={provider}
 variant={guideProvider === provider ?'default' :'outline'}
 size="sm"
 onClick={() => handleShowGuide(provider)}
 >
 {provider}
 </Button>
 ))}
 </div>

 {/* 步骤 */}
 {deployGuides
 .filter(g => g.provider === guideProvider)
 .map(guide => (
 <div key={guide.provider} className="space-y-3">
 {guide.steps.map((step, i) => (
 <div key={i} className="flex gap-3">
 <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 text-xs font-bold text-primary">
 {i + 1}
 </div>
 <div className="flex-1 bg-foreground/5 rounded-lg p-3">
 <code className="text-sm font-mono text-foreground/80 break-all whitespace-pre-wrap">
 {step}
 </code>
 </div>
 </div>
 ))}
 </div>
 ))}

 {deployGuides.filter(g => g.provider === guideProvider).length === 0 && (
 <div className="py-4 text-center text-sm text-muted-foreground">
 <icons.Loader2 className={`${iconSize.sm} animate-spin inline mr-2`} />
 加载部署指南中...
 </div>
 )}
 </div>
 )}
 </div>
 </div>
 </PageContainer>
 )
}
