import { useState, useEffect } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, iconSize, inputStyle, statusBadge, statusColor } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'

// ====================================================================
// @mock-data FALLBACK: 后端就绪后从 API 获取
// ====================================================================

interface DetectedService {
  id: string
  name: string
  icon: keyof typeof icons
  status: 'running' | 'not_found'
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
  status: 'idle' | 'testing' | 'success' | 'failed'
  latency?: number
  modelInfo?: string
  error?: string
}

interface DeployGuide {
  provider: string
  steps: string[]
}

const mockDetectedServices: DetectedService[] = [
  { id: 'ollama', name: 'Ollama', icon: 'Terminal', status: 'running', port: 11434 },
  { id: 'vllm', name: 'vLLM', icon: 'Server', status: 'not_found', installUrl: 'https://docs.vllm.ai/' },
  { id: 'localai', name: 'LocalAI', icon: 'Cpu', status: 'not_found', installUrl: 'https://localai.io/' },
  { id: 'lmstudio', name: 'LM Studio', icon: 'Brain', status: 'running', port: 1234 },
]

const mockRecommendedModels: RecommendedModel[] = [
  {
    id: 'qwen2.5-7b',
    name: 'Qwen2.5-7B',
    vram: '4GB VRAM',
    size: '4.4GB',
    description: '通用法律场景，性能与资源平衡',
    installCommand: 'ollama pull qwen2.5:7b',
  },
  {
    id: 'qwen2.5-14b',
    name: 'Qwen2.5-14B',
    vram: '8GB VRAM',
    size: '8.9GB',
    description: '高质量法律分析，更强推理能力',
    installCommand: 'ollama pull qwen2.5:14b',
  },
  {
    id: 'glm-4-9b',
    name: 'GLM-4-9B',
    vram: '6GB VRAM',
    size: '5.5GB',
    description: '中文优化，适合中文法律场景',
    installCommand: 'ollama pull glm4:9b',
  },
  {
    id: 'deepseek-v2-lite',
    name: 'DeepSeek-V2-Lite',
    vram: '4GB VRAM',
    size: '3.8GB',
    description: '高效推理，低资源消耗',
    installCommand: 'ollama pull deepseek-v2:lite',
  },
  {
    id: 'yi-34b',
    name: 'Yi-34B',
    vram: '20GB VRAM',
    size: '19.5GB',
    description: '最高精度，适合复杂法律分析',
    installCommand: 'ollama pull yi:34b',
  },
]

const mockDeployGuides: DeployGuide[] = [
  {
    provider: 'Ollama',
    steps: [
      'curl -fsSL https://ollama.com/install.sh | sh',
      'ollama serve',
      'ollama pull qwen2.5:7b',
      'curl http://localhost:11434/api/generate -d \'{"model":"qwen2.5:7b","prompt":"你好"}\'',
    ],
  },
  {
    provider: 'vLLM',
    steps: [
      'pip install vllm',
      'python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-7B --port 8000',
      'curl http://localhost:8000/v1/models',
    ],
  },
  {
    provider: 'LM Studio',
    steps: [
      '从 https://lmstudio.ai/ 下载安装 LM Studio',
      '在模型库中搜索并下载 Qwen2.5-7B',
      '启动本地服务器（端口 1234）',
      '在安心法务中配置端点: http://localhost:1234/v1',
    ],
  },
]

// ====================================================================

type PageState = 'loading' | 'error' | 'ready'

export default function PrivateLLMSetup() {
  const [state, setState] = useState<PageState>('loading')
  const [currentStep, setCurrentStep] = useState(0)
  const [services, setServices] = useState<DetectedService[]>([])
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [endpoint, setEndpoint] = useState('http://localhost:11434')
  const [modelName, setModelName] = useState('')
  const [testResult, setTestResult] = useState<TestResult>({ status: 'idle' })
  const [showGuide, setShowGuide] = useState(false)
  const [guideProvider, setGuideProvider] = useState('Ollama')
  const [detecting, setDetecting] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setServices(mockDetectedServices)
      setState('ready')
    }, 600)
    return () => clearTimeout(timer)
  }, [])

  const handleDetect = async () => {
    setDetecting(true)
    // @mock-data FALLBACK: 模拟检测
    await new Promise(r => setTimeout(r, 1500))
    setServices(mockDetectedServices)
    setDetecting(false)
    toast.success('环境检测完成')
  }

  const handleTestConnection = async () => {
    setTestResult({ status: 'testing' })
    // @mock-data FALLBACK: 模拟测试
    await new Promise(r => setTimeout(r, 2000))
    setTestResult({
      status: 'success',
      latency: 128,
      modelInfo: `${modelName || 'qwen2.5:7b'} · 7B params · Q4_K_M`,
    })
    toast.success('连接测试成功')
  }

  const handleSave = async () => {
    // @mock-data FALLBACK
    toast.success('私有 LLM 配置已保存')
  }

  const steps = ['环境检测', '选择模型', '测试连接']

  if (state === 'loading') {
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

  if (state === 'error') {
    return (
      <PageContainer title="私有 LLM 配置" description="配置本地大语言模型服务">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>加载失败</p>
          <p className={heading.muted}>请检查网络后重试</p>
          <Button className="mt-4" onClick={() => setState('loading')}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
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
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all text-sm font-medium ${
                    i === currentStep
                      ? 'bg-primary text-primary-foreground'
                      : i < currentStep
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted text-muted-foreground'
                  }`}
                >
                  <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-bold shrink-0"
                    style={{
                      borderColor: i <= currentStep ? 'currentColor' : undefined,
                    }}
                  >
                    {i < currentStep ? <icons.Check className="w-3 h-3" /> : i + 1}
                  </span>
                  <span className="hidden sm:inline">{label}</span>
                </button>
                {i < steps.length - 1 && (
                  <div className={`flex-1 h-px ${i < currentStep ? 'bg-primary' : 'bg-border'}`} />
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
                  {detecting ? '检测中...' : '重新检测'}
                </Button>
              }
            >
              <div className="space-y-2">
                {services.map(svc => {
                  const Icon = icons[svc.icon]
                  const isRunning = svc.status === 'running'
                  return (
                    <div
                      key={svc.id}
                      className={`flex items-center gap-3 p-3 rounded-lg border ${
                        isRunning ? 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/20' : 'border-border bg-muted/30'
                      }`}
                    >
                      <Icon className={`${iconSize.md} ${isRunning ? 'text-emerald-600' : 'text-muted-foreground'}`} />
                      <div className="flex-1 min-w-0">
                        <p className={heading.card}>{svc.name}</p>
                        {isRunning && svc.port && (
                          <p className={heading.micro}>端口: {svc.port}</p>
                        )}
                      </div>
                      <Badge className={isRunning ? statusBadge.success : statusBadge.neutral}>
                        {isRunning ? '运行中' : '未检测到'}
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
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {mockRecommendedModels.map(model => {
                  const isSelected = selectedModel === model.id
                  return (
                    <button
                      key={model.id}
                      onClick={() => {
                        setSelectedModel(model.id)
                        setModelName(model.name.toLowerCase().replace('-', ':'))
                      }}
                      className={`p-4 rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                          : 'border-border hover:border-primary/30 hover:bg-muted/50'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-sm font-semibold text-foreground">{model.name}</p>
                        <Badge variant="secondary" className="text-xs shrink-0 ml-2">{model.size}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mb-2">{model.description}</p>
                      <div className="flex items-center gap-2 mb-3">
                        <Badge className={statusBadge.info}>{model.vram}</Badge>
                      </div>
                      <div className="bg-foreground/5 rounded-lg p-2">
                        <code className="text-xs font-mono text-foreground/80 break-all">
                          {model.installCommand}
                        </code>
                      </div>
                    </button>
                  )
                })}
              </div>

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
                  disabled={testResult.status === 'testing'}
                >
                  {testResult.status === 'testing' ? (
                    <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                  ) : (
                    <icons.Zap className={iconSize.sm} />
                  )}
                  {testResult.status === 'testing' ? '测试中...' : '测试连接'}
                </Button>

                {/* 测试结果 */}
                {testResult.status === 'success' && (
                  <div className={`p-4 rounded-xl border ${statusColor.success} border-emerald-200 dark:border-emerald-800`}>
                    <div className="flex items-center gap-2 mb-2">
                      <icons.CheckCircle className={`${iconSize.md} text-emerald-600`} />
                      <p className="text-sm font-semibold">连接成功</p>
                    </div>
                    <div className="space-y-1 text-sm">
                      <p>延迟: <span className="font-mono">{testResult.latency}ms</span></p>
                      <p>模型: {testResult.modelInfo}</p>
                    </div>
                  </div>
                )}

                {testResult.status === 'failed' && (
                  <div className={`p-4 rounded-xl border ${statusColor.error} border-red-200 dark:border-red-800`}>
                    <div className="flex items-center gap-2 mb-2">
                      <icons.AlertCircle className={`${iconSize.md} text-red-600`} />
                      <p className="text-sm font-semibold">连接失败</p>
                    </div>
                    <p className="text-sm">{testResult.error || '无法连接到指定端点'}</p>
                  </div>
                )}
              </div>

              <div className="flex justify-between pt-4">
                <Button variant="outline" onClick={() => setCurrentStep(1)}>
                  <icons.ChevronLeft className={iconSize.sm} />
                  上一步
                </Button>
                {testResult.status === 'success' && (
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
            onClick={() => setShowGuide(!showGuide)}
            className="flex items-center gap-2 w-full text-left"
          >
            {showGuide ? (
              <icons.ChevronUp className={iconSize.sm + ' text-muted-foreground'} />
            ) : (
              <icons.ChevronDown className={iconSize.sm + ' text-muted-foreground'} />
            )}
            <span className={heading.section}>部署指南</span>
            <span className={heading.micro}>— 按提供商查看分步安装命令</span>
          </button>

          {showGuide && (
            <div className="mt-4 space-y-4">
              {/* Provider 切换 */}
              <div className="flex gap-2">
                {mockDeployGuides.map(guide => (
                  <Button
                    key={guide.provider}
                    variant={guideProvider === guide.provider ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setGuideProvider(guide.provider)}
                  >
                    {guide.provider}
                  </Button>
                ))}
              </div>

              {/* 步骤 */}
              {mockDeployGuides
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
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  )
}
