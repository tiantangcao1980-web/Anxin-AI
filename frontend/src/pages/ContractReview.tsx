import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { contractsApi, DocumentParseResult, QuickReviewResult, ContractReviewStreamEvent, ReviewRiskItem, UploadAndReviewResult } from '@/lib/api';
import { toast } from 'sonner';
import { PageContainer } from '@/components/ui/PageContainer';
import { cardStyle, heading, buttonStyle, iconSize, statusBadge, radius, inputStyle } from '@/lib/design-tokens';

type ReviewStep = 'upload' | 'parsing' | 'reviewing' | 'review' | 'complete';

const STEPS: { key: ReviewStep; label: string; shortLabel: string }[] = [
  { key: 'upload', label: '上传文档', shortLabel: '上传' },
  { key: 'parsing', label: '解析文档', shortLabel: '解析' },
  { key: 'reviewing', label: 'AI审查', shortLabel: '审查' },
  { key: 'review', label: '审阅修改', shortLabel: '审阅' },
  { key: 'complete', label: '完成', shortLabel: '完成' },
];

function getStepIndex(step: ReviewStep) {
  return STEPS.findIndex((s) => s.key === step);
}

function getRiskLevelColor(level: string) {
  switch (level.toLowerCase()) {
    case 'critical':
      return 'bg-red-100 dark:bg-red-950/30 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800';
    case 'high':
      return 'bg-orange-100 dark:bg-orange-950/30 text-orange-800 dark:text-orange-300 border-orange-200 dark:border-orange-800';
    case 'medium':
      return 'bg-yellow-100 dark:bg-yellow-950/30 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800';
    case 'low':
      return 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800';
    default:
      return 'bg-muted text-foreground border-border';
  }
}

function getRiskLevelIcon(level: string) {
  switch (level.toLowerCase()) {
    case 'critical':
    case 'high':
      return <icons.XCircle className={`${iconSize.md} text-red-500`} />;
    case 'medium':
      return <icons.AlertTriangle className={`${iconSize.md} text-yellow-500`} />;
    case 'low':
      return <icons.CheckCircle className={`${iconSize.md} text-emerald-600`} />;
    default:
      return <icons.AlertCircle className={`${iconSize.md} text-muted-foreground`} />;
  }
}

function getRiskLevelLabel(level: string) {
  switch (level.toLowerCase()) {
    case 'critical': return '严重';
    case 'high': return '高风险';
    case 'medium': return '中风险';
    case 'low': return '低风险';
    default: return level;
  }
}

function normalizeFullReviewResult(payload: UploadAndReviewResult): QuickReviewResult {
  const review = payload.review_result || {} as UploadAndReviewResult['review_result'];
  return {
    summary: review.summary || '审查完成',
    risk_level: review.risk_level || 'medium',
    risk_score: review.risk_score || 0.5,
    key_risks: review.risks || [],
    suggestions: review.suggestions || [],
    key_terms: review.key_terms || {},
    missing_clauses: review.missing_clauses || [],
    contract_id: payload.contract_id,
  };
}

function renderContractText(
  text: string,
  risks: ReviewRiskItem[],
  acceptedRisks: Set<number>,
  onRiskClick: (index: number) => void
) {
  type Marker = { start: number; end: number; riskIndex: number; original: string; suggested: string };
  const markers: Marker[] = [];

  risks.forEach((risk, i) => {
    if (risk.original_text) {
      const pos = text.indexOf(risk.original_text);
      if (pos >= 0) {
        markers.push({
          start: pos,
          end: pos + risk.original_text.length,
          riskIndex: i,
          original: risk.original_text,
          suggested: risk.suggested_text || '',
        });
      }
    }
  });

  markers.sort((a, b) => a.start - b.start);

  // Remove overlapping markers
  const filtered: Marker[] = [];
  let lastEnd = 0;
  for (const m of markers) {
    if (m.start >= lastEnd) {
      filtered.push(m);
      lastEnd = m.end;
    }
  }

  const elements: React.ReactNode[] = [];
  let cursor = 0;

  filtered.forEach((marker, i) => {
    if (marker.start > cursor) {
      elements.push(<span key={`t${i}`}>{text.slice(cursor, marker.start)}</span>);
    }

    const isAccepted = acceptedRisks.has(marker.riskIndex);

    if (isAccepted && marker.suggested) {
      elements.push(
        <span
          key={`r${i}`}
          className="bg-emerald-100 text-emerald-800 px-1 rounded cursor-pointer border-b-2 border-emerald-400 transition-colors hover:bg-emerald-200"
          onClick={() => onRiskClick(marker.riskIndex)}
          title="已接受的修改"
        >
          {marker.suggested}
        </span>
      );
    } else {
      elements.push(
        <span
          key={`r${i}`}
          className="bg-red-100 dark:bg-red-950/30 text-red-800 dark:text-red-300 px-1 rounded cursor-pointer border-b-2 border-red-400 dark:border-red-600 transition-colors hover:bg-red-200 dark:hover:bg-red-950/50"
          onClick={() => onRiskClick(marker.riskIndex)}
          title="点击查看修改建议"
        >
          {marker.original}
        </span>
      );
    }

    cursor = marker.end;
  });

  if (cursor < text.length) {
    elements.push(<span key="tail">{text.slice(cursor)}</span>);
  }

  return elements;
}

export default function ContractReview({ embedded = false }: { embedded?: boolean }) {
  const [step, setStep] = useState<ReviewStep>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [contractText, setContractText] = useState('');
  const [parseResult, setParseResult] = useState<DocumentParseResult | null>(null);
  const [reviewResult, setReviewResult] = useState<QuickReviewResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAgent, setCurrentAgent] = useState('');
  const [agentMessage, setAgentMessage] = useState('');
  const [detectedRisks, setDetectedRisks] = useState<ReviewRiskItem[]>([]);
  const [missingClauses, setMissingClauses] = useState<string[]>([]);
  const [keyTerms, setKeyTerms] = useState<Record<string, string>>({});

  // review step states
  const [acceptedRisks, setAcceptedRisks] = useState<Set<number>>(new Set());
  const [contractId, setContractId] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [appliedCount, setAppliedCount] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const riskRefs = useRef<(HTMLDivElement | null)[]>([]);

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, []);

  const handleFileSelect = async (selectedFile: File) => {
    setFile(selectedFile);
    setStep('parsing');
    setIsProcessing(true);
    setCurrentAgent('文档解析');
    setAgentMessage('正在解析文档内容...');
    setReviewResult(null);
    setDetectedRisks([]);
    setMissingClauses([]);
    setKeyTerms({});
    setAcceptedRisks(new Set());
    setContractId('');
    setAppliedCount(0);

    try {
      const result = await contractsApi.parseDocument(selectedFile);

      if (!result.success) {
        toast.error(result.error || '文档解析失败');
        setStep('upload');
        return;
      }

      setParseResult(result);
      setContractText(result.text);
      toast.success(`文档解析成功: ${result.contract_type}`);
      setStep('reviewing');
      setCurrentAgent('合同审查Agent');
      setAgentMessage('正在生成可编辑审查结果...');

      try {
        const uploadResult = await contractsApi.uploadAndReview(selectedFile, selectedFile.name);
        const fullReviewResult = normalizeFullReviewResult(uploadResult);
        setContractId(uploadResult.contract_id);
        setReviewResult(fullReviewResult);
        setDetectedRisks(fullReviewResult.key_risks);
        setMissingClauses(fullReviewResult.missing_clauses || []);
        setKeyTerms(fullReviewResult.key_terms || {});
        setStep('review');
        toast.success('合同审查完成');
      } catch (reviewError: any) {
        toast.warning(reviewError?.message || '完整审查失败，已切换到流式审查');
        await startReview(result.text, result.contract_type);
      }
    } catch (error: any) {
      toast.error(error.message || '解析失败');
      setStep('upload');
    } finally {
      setIsProcessing(false);
    }
  };

  const startReview = async (text: string, contractType?: string) => {
    setStep('reviewing');
    setIsProcessing(true);
    setDetectedRisks([]);
    setMissingClauses([]);
    setKeyTerms({});
    setAcceptedRisks(new Set());
    setAppliedCount(0);

    let streamRisks: ReviewRiskItem[] = [];
    let streamMissing: string[] = [];
    let streamKeyTerms: Record<string, string> = {};
    let streamSuggestions: string[] = [];

    try {
      await contractsApi.streamReview(
        { text },
        (event: ContractReviewStreamEvent) => {
          switch (event.type) {
            case 'start':
              setAgentMessage(event.message || '开始处理...');
              break;
            case 'analyzing':
              setCurrentAgent(event.agent || '合同审查Agent');
              setAgentMessage(event.message || '分析中...');
              break;
            case 'reviewing':
              setCurrentAgent(event.agent || '风险评估Agent');
              setAgentMessage(event.message || '识别风险...');
              break;
            case 'risks':
              if (event.data) {
                streamRisks = event.data;
                setDetectedRisks(event.data);
              }
              break;
            case 'missing_clauses':
              if (event.data) {
                setMissingClauses(event.data);
                streamMissing = event.data;
              }
              break;
            case 'key_terms':
              if (event.data) {
                setKeyTerms(event.data);
                streamKeyTerms = event.data;
              }
              break;
            case 'suggestions':
              if (event.data) {
                streamSuggestions = event.data;
              }
              break;
            case 'done':
              const result: QuickReviewResult = {
                summary: event.summary || '',
                risk_level: event.risk_level || 'medium',
                risk_score: event.risk_score || 0.5,
                key_risks: streamRisks,
                suggestions: streamSuggestions,
                key_terms: streamKeyTerms,
                missing_clauses: streamMissing,
              };
              setReviewResult(result);
              setDetectedRisks(streamRisks);
              setStep('review');
              break;
            case 'error':
              toast.error(event.message || '审查失败');
              break;
          }
        },
        (error) => {
          fallbackReview(text, contractType);
        }
      );
    } catch {
      await fallbackReview(text, contractType);
    }

    setIsProcessing(false);
  };

  const fallbackReview = async (text: string, contractType?: string) => {
    try {
      setCurrentAgent('合同审查Agent');
      setAgentMessage('正在进行快速审查...');

      const result = await contractsApi.quickReview(text, contractType);
      setReviewResult(result);
      setDetectedRisks(result.key_risks);
      if (result.contract_id) {
        setContractId(result.contract_id);
      }
      setStep('review');
    } catch (error: any) {
      toast.error(error.message || '审查失败');
      setStep('upload');
    }
  };

  const resetReview = () => {
    setStep('upload');
    setFile(null);
    setContractText('');
    setParseResult(null);
    setReviewResult(null);
    setDetectedRisks([]);
    setAcceptedRisks(new Set());
    setContractId('');
    setAppliedCount(0);
  };

  const toggleAcceptRisk = (index: number) => {
    setAcceptedRisks((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const suggestableRisks = detectedRisks
    .map((r, i) => ({ risk: r, index: i }))
    .filter(({ risk }) => !!risk.suggested_text);

  const suggestableRisksCount = suggestableRisks.length;

  const acceptAllRisks = () => {
    const allIndexes = new Set(suggestableRisks.map(({ index }) => index));
    setAcceptedRisks(allIndexes);
    toast.success(`已选中全部 ${suggestableRisksCount} 项修改建议`);
  };

  const applyAcceptedSuggestions = async () => {
    if (acceptedRisks.size === 0) return;

    setIsApplying(true);

    try {
      // If we have a contractId and risks have IDs, call the backend API
      const acceptedRiskIds = Array.from(acceptedRisks)
        .map((i) => detectedRisks[i]?.id)
        .filter(Boolean) as string[];

      if (contractId && acceptedRiskIds.length > 0) {
        const result = await contractsApi.applySuggestions(contractId, acceptedRiskIds);
        if (result.modified_text) {
          setContractText(result.modified_text);
        }
      } else {
        // Local text replacement for paste-mode / no contractId
        let text = contractText;
        // Apply in reverse order to preserve positions
        const sorted = Array.from(acceptedRisks)
          .map((i) => ({ index: i, risk: detectedRisks[i] }))
          .filter(({ risk }) => risk.original_text && risk.suggested_text)
          .sort((a, b) => {
            const posA = text.indexOf(a.risk.original_text!);
            const posB = text.indexOf(b.risk.original_text!);
            return posB - posA;
          });

        for (const { risk } of sorted) {
          text = text.replace(risk.original_text!, risk.suggested_text!);
        }
        setContractText(text);
      }

      setAppliedCount(acceptedRisks.size);
      toast.success(`已应用 ${acceptedRisks.size} 项修改`);
      setStep('complete');
    } catch (error: any) {
      toast.error(error.message || '应用修改失败');
    } finally {
      setIsApplying(false);
    }
  };

  const handleSave = async () => {
    if (!contractId) {
      toast.error('请先上传文档后再保存');
      return;
    }
    setIsSaving(true);
    try {
      await contractsApi.saveContractFile(contractId);
      toast.success('合同已保存到服务器');
    } catch (error: any) {
      toast.error(error.message || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = async (format: 'pdf' | 'docx') => {
    if (!contractId) {
      toast.error('请先上传文档后再下载');
      return;
    }
    setIsDownloading(true);
    try {
      await contractsApi.downloadContract(contractId, format);
      toast.success(`${format.toUpperCase()} 下载成功`);
    } catch (error: any) {
      toast.error(error.message || '下载失败');
    } finally {
      setIsDownloading(false);
    }
  };

  const scrollToRisk = (index: number) => {
    riskRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const currentStepIndex = getStepIndex(step);

  // ============ Render ============

  const renderStepBar = (compact: boolean) => (
    <div className={`flex items-center ${compact ? 'gap-2' : 'gap-4'}`}>
      {STEPS.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <div
            className={`flex items-center gap-${compact ? '1.5' : '2'} px-${compact ? '2.5' : '3'} py-${compact ? '0.5' : '1'} rounded-full text-${compact ? 'xs' : 'sm'} font-medium ${
              step === s.key
                ? 'bg-primary text-white'
                : currentStepIndex > i
                  ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400'
                  : 'bg-muted text-muted-foreground'
            }`}
          >
            {!compact && (
              <span className="w-5 h-5 flex items-center justify-center rounded-full bg-white/20 text-xs">
                {currentStepIndex > i ? (
                  <icons.Check className={iconSize.xs} />
                ) : (
                  i + 1
                )}
              </span>
            )}
            {compact ? (
              <span>{i + 1}</span>
            ) : null}
            <span>{compact ? s.shortLabel : s.label}</span>
          </div>
          {i < STEPS.length - 1 && (
            <icons.ChevronRight className={`${compact ? `${iconSize.xs} mx-1` : `${iconSize.sm} mx-2`} text-muted-foreground`} />
          )}
        </div>
      ))}
    </div>
  );

  const renderUploadStep = () => (
    <motion.div
      key="upload"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-2xl mx-auto"
    >
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed border-border ${radius.dialog} p-12 text-center bg-background hover:border-primary hover:bg-primary/5 transition-all cursor-pointer`}
      >
        <div className={`w-16 h-16 mx-auto mb-4 bg-primary/10 ${radius.dialog} flex items-center justify-center`}>
          <icons.Upload className={`${iconSize.xl} text-primary`} />
        </div>
        <h3 className={`${heading.section} mb-2`}>
          拖放合同文件到这里
        </h3>
        <p className={`${heading.muted} mb-4`}>或点击选择文件</p>
        <p className={heading.micro}>
          支持 PDF、Word (.docx)、TXT 格式，最大 20MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.docx,.doc,.txt,.md"
          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
        />
      </div>

      <div className="mt-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex-1 h-px bg-border" />
          <span className="text-sm text-muted-foreground">或者直接粘贴合同文本</span>
          <div className="flex-1 h-px bg-border" />
        </div>
        <textarea
          value={contractText}
          onChange={(e) => setContractText(e.target.value)}
          placeholder="在此粘贴合同文本内容..."
          className={`w-full h-48 p-4 ${inputStyle.search} ${radius.card} resize-none`}
        />
        {contractText && (
          <button
            onClick={() => startReview(contractText)}
            className={`mt-4 w-full py-3 ${buttonStyle.primary} ${radius.card} flex items-center justify-center gap-2`}
          >
            <icons.Sparkles className={iconSize.md} />
            开始智能审查
          </button>
        )}
      </div>
    </motion.div>
  );

  const renderProcessingStep = () => (
    <motion.div
      key="processing"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-lg mx-auto text-center"
    >
      <div className={`${cardStyle.base} !p-8 ${radius.dialog}`}>
        <div className={`w-20 h-20 mx-auto mb-6 bg-primary ${radius.dialog} flex items-center justify-center`}>
          <icons.Loader2 className={`${iconSize['2xl']} text-white animate-spin`} />
        </div>
        <h3 className={`${heading.page} text-center mb-2`}>
          {step === 'parsing' ? '正在解析文档' : '智能审查中'}
        </h3>
        <div className="flex items-center justify-center gap-2 text-primary mb-4">
          <icons.Sparkles className={iconSize.sm} />
          <span>{currentAgent}</span>
        </div>
        <p className="text-muted-foreground">{agentMessage}</p>

        {file && (
          <div className={`mt-6 p-4 bg-muted ${radius.card} flex items-center gap-3`}>
            <icons.FileText className={`${iconSize.xl} text-primary`} />
            <div className="text-left flex-1">
              <p className="font-medium text-foreground truncate">{file.name}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
        )}

        {detectedRisks.length > 0 && (
          <div className="mt-6 text-left">
            <p className={`${heading.muted} mb-2`}>
              已检测到 {detectedRisks.length} 个风险点
            </p>
            <div className="space-y-2">
              {detectedRisks.slice(0, 3).map((risk, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`p-3 rounded-lg border ${getRiskLevelColor(risk.level)}`}
                >
                  <div className="flex items-center gap-2">
                    {getRiskLevelIcon(risk.level)}
                    <span className="font-medium">{risk.title}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );

  const renderReviewStep = () => (
    <motion.div
      key="review"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="flex flex-col h-full"
    >
      {/* Summary bar */}
      {reviewResult && (
        <div data-review-summary className={`${cardStyle.base} !p-4 mb-4 flex items-center justify-between`}>
          <div className="flex items-center gap-4">
            <div className={`px-3 py-1.5 ${radius.button} text-sm font-medium flex items-center gap-1.5 ${getRiskLevelColor(reviewResult.risk_level)}`}>
              <icons.Shield className={iconSize.sm} />
              {{ low: '低风险', medium: '中等风险', high: '高风险', critical: '严重风险' }[reviewResult.risk_level] || '未知'}
            </div>
            <div className="text-sm text-muted-foreground">
              风险评分: <span className="font-medium text-foreground">{(reviewResult.risk_score * 100).toFixed(0)}%</span>
            </div>
            <div className="h-2 w-32 bg-muted rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${reviewResult.risk_score * 100}%` }}
                transition={{ duration: 0.5 }}
                className={`h-full ${
                  reviewResult.risk_score > 0.7 ? 'bg-red-500' :
                  reviewResult.risk_score > 0.5 ? 'bg-orange-500' :
                  reviewResult.risk_score > 0.3 ? 'bg-yellow-500' : 'bg-emerald-600'
                }`}
              />
            </div>
          </div>
          <p className="text-sm text-muted-foreground max-w-md truncate">{reviewResult.summary}</p>
        </div>
      )}

      {/* Split panel */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-0">
        {/* Left: Contract text preview */}
        <div className={`${cardStyle.base} !p-0 flex flex-col min-h-0`}>
          <div className="px-5 py-3 border-b border-border flex items-center gap-2">
            <icons.FileText className={`${iconSize.sm} text-primary`} />
            <h3 className={heading.card}>合同文本预览</h3>
            {file && (
              <span className="text-xs text-muted-foreground ml-auto">{file.name}</span>
            )}
          </div>
          <div className="flex-1 overflow-auto p-5">
            <div className="text-sm leading-7 text-foreground whitespace-pre-wrap">
              {renderContractText(contractText, detectedRisks, acceptedRisks, scrollToRisk)}
            </div>
          </div>
        </div>

        {/* Right: Risk cards */}
        <div className={`${cardStyle.base} !p-0 flex flex-col min-h-0`}>
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <icons.AlertTriangle className={`${iconSize.sm} text-yellow-500`} />
              <h3 className={heading.card}>
                风险条款 ({detectedRisks.length})
              </h3>
            </div>
            {suggestableRisksCount > 0 && (
              <span className="text-xs text-muted-foreground">
                已选 {acceptedRisks.size}/{suggestableRisksCount}
              </span>
            )}
          </div>
          <div data-review-risk-list className="flex-1 overflow-auto p-4 space-y-3">
            {detectedRisks.map((risk, index) => {
              const isAccepted = acceptedRisks.has(index);
              return (
                <motion.div
                  key={index}
                  ref={(el) => { riskRefs.current[index] = el; }}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className={`p-4 ${radius.card} border transition-all ${
                    isAccepted ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-950/30' : getRiskLevelColor(risk.level)
                  }`}
                >
                  {/* Title row */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      {getRiskLevelIcon(risk.level)}
                      <span className="font-medium text-foreground truncate">{risk.title}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${getRiskLevelColor(risk.level)}`}>
                        {risk.type}
                      </span>
                    </div>
                    {isAccepted && <icons.CheckCircle className={`${iconSize.md} text-emerald-600 flex-shrink-0`} />}
                  </div>

                  <p className="text-sm text-foreground/80 mb-3">{risk.description}</p>

                  {/* Original vs suggested comparison */}
                  {risk.original_text && (
                    <div className="space-y-2 mb-3">
                      <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
                        <div className={`flex items-center gap-1.5 ${heading.micro} text-red-600 font-medium mb-1`}>
                          <icons.XCircle className={iconSize.sm} />
                          原文
                        </div>
                        <p className="text-sm text-red-800 dark:text-red-300 line-through">{risk.original_text}</p>
                      </div>

                      {risk.suggested_text && (
                        <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg">
                          <div className={`flex items-center gap-1.5 ${heading.micro} text-emerald-600 font-medium mb-1`}>
                            <icons.CheckCircle className={iconSize.sm} />
                            建议修改
                          </div>
                          <p className="text-sm text-emerald-800 dark:text-emerald-300">{risk.suggested_text}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Text suggestion for risks without original_text */}
                  {!risk.original_text && risk.suggestion && (
                    <div className="p-2 bg-primary/5 rounded-lg mb-3">
                      <p className="text-sm text-primary">{risk.suggestion}</p>
                    </div>
                  )}

                  {/* Accept / reject buttons */}
                  {risk.suggested_text && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => toggleAcceptRisk(index)}
                        className={`flex-1 py-2 ${radius.button} text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
                          isAccepted
                            ? 'bg-emerald-600 text-white'
                            : `${statusBadge.success} hover:bg-emerald-100 dark:hover:bg-emerald-950/50`
                        }`}
                      >
                        <icons.Check className={iconSize.sm} />
                        {isAccepted ? '已接受' : '接受修改'}
                      </button>
                      {isAccepted && (
                        <button
                          onClick={() => toggleAcceptRisk(index)}
                          className={`${buttonStyle.ghost} border border-border`}
                        >
                          撤回
                        </button>
                      )}
                    </div>
                  )}
                </motion.div>
              );
            })}

            {detectedRisks.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <icons.CheckCircle className={`${iconSize['2xl']} mx-auto mb-3 text-emerald-600`} />
                <p>未检测到明显风险条款</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom action bar */}
      <div data-review-actions className="bg-background border-t border-border rounded-b-xl px-6 py-4 mt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {suggestableRisksCount > 0 && (
              <>
                <button
                  onClick={acceptAllRisks}
                  className={`px-4 py-2.5 bg-emerald-600 text-white ${radius.button} text-sm font-medium hover:bg-emerald-700 transition-colors flex items-center gap-2`}
                >
                  <icons.CheckCircle className={iconSize.sm} />
                  一键接受全部 ({suggestableRisksCount})
                </button>
                <button
                  onClick={applyAcceptedSuggestions}
                  disabled={acceptedRisks.size === 0 || isApplying}
                  className={`${buttonStyle.primary} disabled:opacity-50 flex items-center gap-2`}
                >
                  {isApplying ? (
                    <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                  ) : (
                    <icons.Sparkles className={iconSize.sm} />
                  )}
                  应用修改 ({acceptedRisks.size})
                </button>
                <span className="text-sm text-muted-foreground">
                  已选择 {acceptedRisks.size}/{suggestableRisksCount} 项修改
                </span>
              </>
            )}
            {suggestableRisksCount === 0 && detectedRisks.length > 0 && (
              <button
                onClick={() => setStep('complete')}
                className={`${buttonStyle.primary} flex items-center gap-2`}
              >
                <icons.Check className={iconSize.sm} />
                确认完成
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={isSaving || !contractId}
              title={!contractId ? '请先上传文档' : ''}
              className={`${buttonStyle.secondary} border border-border disabled:opacity-50 flex items-center gap-2`}
            >
              {isSaving ? (
                <icons.Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <icons.Save className={iconSize.sm} />
              )}
              保存到服务器
            </button>
            <button
              onClick={() => handleDownload('pdf')}
              disabled={isDownloading || !contractId}
              title={!contractId ? '请先上传文档' : ''}
              className={`${buttonStyle.secondary} border border-border disabled:opacity-50 flex items-center gap-2`}
            >
              <icons.Download className={iconSize.sm} />
              PDF
            </button>
            <button
              onClick={() => handleDownload('docx')}
              disabled={isDownloading || !contractId}
              title={!contractId ? '请先上传文档' : ''}
              className={`${buttonStyle.secondary} border border-border disabled:opacity-50 flex items-center gap-2`}
            >
              <icons.Download className={iconSize.sm} />
              DOCX
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );

  const renderCompleteStep = () => (
    <motion.div
      key="complete"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-4xl mx-auto"
    >
      {/* Success card */}
      <div className={`${cardStyle.base} !p-8 ${radius.dialog} mb-6 text-center`}>
        <div className={`w-20 h-20 mx-auto mb-4 bg-emerald-100 dark:bg-emerald-950/30 ${radius.dialog} flex items-center justify-center`}>
          <icons.CheckCircle className={`${iconSize['2xl']} text-emerald-600`} />
        </div>
        <h3 className={`${heading.page} text-center mb-2`}>审查完成</h3>
        <p className="text-muted-foreground mb-4">
          {appliedCount > 0
            ? `已应用 ${appliedCount} 项修改建议，共检测到 ${detectedRisks.length} 个风险条款`
            : `共检测到 ${detectedRisks.length} 个风险条款`}
        </p>

        {reviewResult && (
          <div className="flex items-center justify-center gap-6 mt-4">
            <div className={`px-4 py-2 ${radius.card} ${getRiskLevelColor(reviewResult.risk_level)}`}>
              <div className="flex items-center gap-2">
                <icons.Shield className={iconSize.md} />
                <span className="font-medium">
                  {{ low: '低风险', medium: '中等风险', high: '高风险', critical: '严重风险' }[reviewResult.risk_level] || '未知'}
                </span>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              风险评分: <span className="font-semibold text-foreground">{(reviewResult.risk_score * 100).toFixed(0)}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      {reviewResult?.summary && (
        <div className={`${cardStyle.base} ${radius.dialog} mb-6`}>
          <h3 className={`${heading.section} mb-3`}>审查摘要</h3>
          <p className="text-foreground/80">{reviewResult.summary}</p>
        </div>
      )}

      {/* Modified contract text */}
      {contractText && (
        <div className={`${cardStyle.base} ${radius.dialog} mb-6`}>
          <h3 className={`${heading.section} mb-3 flex items-center gap-2`}>
            <icons.FileText className={`${iconSize.md} text-primary`} />
            {appliedCount > 0 ? '修改后的合同文本' : '合同文本'}
          </h3>
          <div className={`max-h-96 overflow-auto p-4 bg-muted ${radius.card}`}>
            <p className="text-sm leading-7 text-foreground whitespace-pre-wrap">{contractText}</p>
          </div>
        </div>
      )}

      {/* Risk list */}
      {detectedRisks.length > 0 && (
        <div className={`${cardStyle.base} ${radius.dialog} mb-6`}>
          <h3 className={`${heading.section} mb-4`}>
            风险条款 ({detectedRisks.length})
          </h3>
          <div className="space-y-3">
            {detectedRisks.map((risk, i) => (
              <div
                key={i}
                className={`p-4 ${radius.card} border ${getRiskLevelColor(risk.level)}`}
              >
                <div className="flex items-start gap-3">
                  {getRiskLevelIcon(risk.level)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-foreground">{risk.title}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${getRiskLevelColor(risk.level)}`}>
                        {getRiskLevelLabel(risk.level)}
                      </span>
                    </div>
                    <p className="text-sm text-foreground/80">{risk.description}</p>
                    {risk.legal_basis && (
                      <div className="flex items-start gap-2 p-2 mt-1.5 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <icons.Scale className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                        <p className="text-xs text-blue-700 dark:text-blue-300">{risk.legal_basis}</p>
                      </div>
                    )}
                    {risk.suggestion && (
                      <div className="flex items-start gap-2 p-2 mt-1.5 bg-background/50 rounded-lg">
                        <icons.Sparkles className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-primary">{risk.suggestion}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing Clauses */}
      {missingClauses.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20">
          <h4 className="font-semibold text-sm text-amber-800 dark:text-amber-200 mb-3 flex items-center gap-2">
            <icons.AlertTriangle className="w-4 h-4" />
            缺失的重要条款
          </h4>
          <ul className="space-y-1.5">
            {missingClauses.map((clause, i) => (
              <li key={i} className="text-sm text-amber-700 dark:text-amber-300 flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">•</span>
                {clause}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4 flex-wrap">
        <button
          onClick={() => setStep('review')}
          className={`${buttonStyle.secondary} ${radius.card} px-6 py-3 border border-border flex items-center justify-center gap-2`}
        >
          <icons.Eye className={iconSize.md} />
          返回审阅
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || !contractId}
          className={`${buttonStyle.secondary} ${radius.card} px-6 py-3 border border-border disabled:opacity-50 flex items-center justify-center gap-2`}
        >
          {isSaving ? <icons.Loader2 className={`${iconSize.md} animate-spin`} /> : <icons.Save className={iconSize.md} />}
          保存到服务器
        </button>
        <button
          onClick={() => handleDownload('pdf')}
          disabled={isDownloading || !contractId}
          className={`${buttonStyle.secondary} ${radius.card} px-6 py-3 border border-border disabled:opacity-50 flex items-center justify-center gap-2`}
        >
          <icons.Download className={iconSize.md} />
          下载 PDF
        </button>
        <button
          onClick={() => handleDownload('docx')}
          disabled={isDownloading || !contractId}
          className={`${buttonStyle.secondary} ${radius.card} px-6 py-3 border border-border disabled:opacity-50 flex items-center justify-center gap-2`}
        >
          <icons.Download className={iconSize.md} />
          下载 DOCX
        </button>
        <button
          onClick={resetReview}
          className={`${buttonStyle.primary} ${radius.card} px-6 py-3 flex items-center justify-center gap-2 ml-auto`}
        >
          <icons.RefreshCw className={iconSize.md} />
          审查新合同
        </button>
      </div>
    </motion.div>
  );

  return (
    <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0 bg-muted">
      {/* Header - non-embedded */}
      {!embedded && (
        <div className="bg-background border-b border-border px-4 sm:px-5 lg:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className={heading.page}>合同智能审查</h1>
              <p className={`${heading.muted} mt-1`}>
                上传合同文档，AI 自动识别风险条款并提供修改建议
              </p>
            </div>
            {step !== 'upload' && (
              <button
                onClick={resetReview}
                className={`flex items-center gap-2 ${buttonStyle.ghost} text-primary`}
              >
                <icons.RefreshCw className={iconSize.sm} />
                重新审查
              </button>
            )}
          </div>
          <div className="mt-4">{renderStepBar(false)}</div>
        </div>
      )}

      {/* Header - embedded */}
      {embedded && (
        <div className="bg-background border-b border-border px-4 sm:px-5 lg:px-6 py-3">
          <div className="flex items-center justify-between">
            {renderStepBar(true)}
            {step !== 'upload' && (
              <button
                onClick={resetReview}
                className={`flex items-center gap-1.5 ${buttonStyle.sm} text-primary hover:bg-muted border border-transparent hover:border-border`}
              >
                <icons.RefreshCw className="w-3.5 h-3.5" />
                重新审查
              </button>
            )}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className={`flex-1 overflow-auto p-4 sm:p-5 lg:p-6 ${step === 'review' ? 'flex flex-col' : ''}`}>
        <AnimatePresence mode="wait">
          {step === 'upload' && renderUploadStep()}
          {(step === 'parsing' || step === 'reviewing') && renderProcessingStep()}
          {step === 'review' && renderReviewStep()}
          {step === 'complete' && renderCompleteStep()}
        </AnimatePresence>
      </div>
    </PageContainer>
  );
}
