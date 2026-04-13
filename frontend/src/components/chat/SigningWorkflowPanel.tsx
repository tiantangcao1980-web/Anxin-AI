/**
 * SigningWorkflowPanel - 合同签署流程面板
 *
 * 展示合同从起草到归档的完整签署进度，
 * 集成电子签章 API（e签宝/法大大），支持发起签署、查看签署链接和状态跟踪。
 */

import { useState, useEffect, useCallback, memo } from'react';
import { icons } from'@/lib/icons';
import {
 cardStyle,
 buttonStyle,
 heading,
 statusBadge,
 iconSize,
 spacing,
 radius,
} from'@/lib/design-tokens';
import { toast } from'sonner';

// ========== 类型定义 ==========

interface Signer {
 signer_id: string;
 name: string;
 sign_type:'personal' |'company';
 status:'pending' |'signed' |'rejected' |'expired';
 signed_at?: string | null;
 reject_reason?: string | null;
}

interface SignFlow {
 flow_id: string;
 contract_id: string;
 status:'created' |'signing' |'completed' |'rejected' |'expired' |'cancelled';
 signers: Signer[];
 created_at?: string | null;
 updated_at?: string | null;
 completed_at?: string | null;
}

interface SigningWorkflowPanelProps {
 /** 合同ID */
 contractId: string;
 /** 合同标题 */
 contractTitle?: string;
 /** 当前工作流阶段（0-5） */
 currentStep?: number;
 /** 已有的签署流程ID */
 flowId?: string | null;
 /** 签署人预设列表 */
 defaultSigners?: Array<{ name: string; sign_type:'personal' |'company' }>;
 /** 回调：签署流程创建成功 */
 onFlowCreated?: (flowId: string) => void;
 /** 回调：签署完成 */
 onCompleted?: () => void;
 /** 紧凑模式 */
 compact?: boolean;
}

// ========== 流程步骤配置 ==========

const WORKFLOW_STEPS = [
 { key:'draft', label:'合同起草', icon: icons.FileText, desc:'创建并编辑合同内容' },
 { key:'ai_review', label:'AI审查', icon: icons.Brain, desc:'AI 智能风险检测与条款分析' },
 { key:'manual_confirm', label:'人工确认', icon: icons.CheckCircle, desc:'相关人员审核确认合同内容' },
 { key:'initiate_sign', label:'发起签署', icon: icons.Send, desc:'向各签署方发送签署邀请' },
 { key:'signing', label:'各方签署', icon: icons.FileSignature, desc:'等待所有签署方完成电子签名' },
 { key:'archive', label:'归档存证', icon: icons.Archive, desc:'合同归档并存证备查' },
] as const;

// ========== API 调用 ==========

const API_BASE = import.meta.env.VITE_API_BASE_URL ||'http://localhost:8003/api/v1';

function getAuthHeaders(): Record<string, string> {
 const token = localStorage.getItem('access_token');
 return {
'Content-Type':'application/json',
 ...(token ? { Authorization: `Bearer ${token}` } : {}),
 };
}

async function apiCreateFlow(
 contractId: string,
 title: string,
 signers: Array<{ name: string; sign_type: string }>,
) {
 const resp = await fetch(`${API_BASE}/esign/flows`, {
 method:'POST',
 headers: getAuthHeaders(),
 body: JSON.stringify({
 contract_id: contractId,
 title: `${title} - 电子签署`,
 signers: signers.map((s) => ({ name: s.name, sign_type: s.sign_type })),
 }),
 });
 if (!resp.ok) {
 const err = await resp.json().catch(() => ({}));
 throw new Error(err.detail ||'创建签署流程失败');
 }
 return resp.json();
}

async function apiGetFlowStatus(flowId: string) {
 const resp = await fetch(`${API_BASE}/esign/flows/${flowId}`, {
 headers: getAuthHeaders(),
 });
 if (!resp.ok) {
 const err = await resp.json().catch(() => ({}));
 throw new Error(err.detail ||'查询签署状态失败');
 }
 return resp.json();
}

async function apiGetSignUrl(flowId: string, signerId: string) {
 const resp = await fetch(`${API_BASE}/esign/flows/${flowId}/sign-url/${signerId}`, {
 headers: getAuthHeaders(),
 });
 if (!resp.ok) {
 const err = await resp.json().catch(() => ({}));
 throw new Error(err.detail ||'获取签署链接失败');
 }
 return resp.json();
}

// ========== 签署人状态徽章 ==========

function SignerStatusBadge({ status }: { status: Signer['status'] }) {
 const config: Record<string, { label: string; style: string }> = {
 pending: { label:'待签署', style: statusBadge.neutral },
 signed: { label:'已签署', style: statusBadge.success },
 rejected: { label:'已拒签', style: statusBadge.error },
 expired: { label:'已过期', style: statusBadge.warning },
 };
 const { label, style } = config[status] || config.pending;
 return (
 <span className={`inline-flex items-center px-2 py-0.5 text-xs font-medium ${radius.badge} ${style}`}>
 {label}
 </span>
 );
}

// ========== 流程状态徽章 ==========

function FlowStatusBadge({ status }: { status: SignFlow['status'] }) {
 const config: Record<string, { label: string; style: string }> = {
 created: { label:'已创建', style: statusBadge.info },
 signing: { label:'签署中', style: statusBadge.warning },
 completed: { label:'已完成', style: statusBadge.success },
 rejected: { label:'已拒签', style: statusBadge.error },
 expired: { label:'已过期', style: statusBadge.neutral },
 cancelled: { label:'已取消', style: statusBadge.neutral },
 };
 const { label, style } = config[status] || config.created;
 return (
 <span className={`inline-flex items-center px-2.5 py-1 text-xs font-medium ${radius.badge} ${style}`}>
 {label}
 </span>
 );
}

// ========== 主组件 ==========

const SigningWorkflowPanel = memo(function SigningWorkflowPanel({
 contractId,
 contractTitle ='合同签署',
 currentStep = 0,
 flowId: initialFlowId = null,
 defaultSigners = [],
 onFlowCreated,
 onCompleted,
 compact = false,
}: SigningWorkflowPanelProps) {
 const [activeStep, setActiveStep] = useState(currentStep);
 const [flowId, setFlowId] = useState<string | null>(initialFlowId);
 const [flow, setFlow] = useState<SignFlow | null>(null);
 const [loading, setLoading] = useState(false);
 const [polling, setPolling] = useState(false);
 const [signerUrlLoading, setSignerUrlLoading] = useState<string | null>(null);

 // 查询签署流程状态
 const refreshFlowStatus = useCallback(async () => {
 if (!flowId) return;
 try {
 const data = await apiGetFlowStatus(flowId);
 setFlow({
 flow_id: data.flow_id,
 contract_id: data.contract_id,
 status: data.status,
 signers: data.signers || [],
 created_at: data.created_at,
 updated_at: data.updated_at,
 completed_at: data.completed_at,
 });

 // 根据签署状态自动推进工作流步骤
 if (data.status ==='completed') {
 setActiveStep(5); // 归档存证
 onCompleted?.();
 } else if (data.status ==='signing') {
 setActiveStep(4); // 各方签署
 } else if (data.status ==='created') {
 setActiveStep(3); // 发起签署
 }
 } catch (err: unknown) {
 console.error('查询签署状态失败:', err);
 }
 }, [flowId, onCompleted]);

 // 初始化时和 flowId 变更时查询状态
 useEffect(() => {
 if (flowId) {
 refreshFlowStatus();
 }
 }, [flowId, refreshFlowStatus]);

 // 签署中自动轮询（每 10 秒）
 useEffect(() => {
 if (!flowId || !flow) return;
 if (flow.status !=='created' && flow.status !=='signing') return;

 setPolling(true);
 const timer = setInterval(refreshFlowStatus, 10000);
 return () => {
 clearInterval(timer);
 setPolling(false);
 };
 }, [flowId, flow?.status, refreshFlowStatus]);

 // 发起签署
 const handleCreateFlow = useCallback(async () => {
 if (defaultSigners.length === 0) {
 toast.error('请先添加签署人');
 return;
 }

 setLoading(true);
 try {
 const data = await apiCreateFlow(contractId, contractTitle, defaultSigners);
 setFlowId(data.flow_id);
 setActiveStep(3);
 toast.success('签署流程已创建');
 onFlowCreated?.(data.flow_id);
 } catch (err: unknown) {
 const msg = err instanceof Error ? err.message :'创建失败';
 toast.error(msg);
 } finally {
 setLoading(false);
 }
 }, [contractId, contractTitle, defaultSigners, onFlowCreated]);

 // 获取签署链接
 const handleGetSignUrl = useCallback(
 async (signerId: string) => {
 if (!flowId) return;
 setSignerUrlLoading(signerId);
 try {
 const data = await apiGetSignUrl(flowId, signerId);
 // 复制到剪贴板
 await navigator.clipboard.writeText(data.sign_url);
 toast.success('签署链接已复制到剪贴板');
 } catch (err: unknown) {
 const msg = err instanceof Error ? err.message :'获取链接失败';
 toast.error(msg);
 } finally {
 setSignerUrlLoading(null);
 }
 },
 [flowId],
 );

 // ========== 渲染 ==========

 return (
 <div className={`${cardStyle.base} ${compact ?'p-4' :''}`}>
 {/* 头部 */}
 <div className="flex items-center justify-between mb-5">
 <div className="flex items-center gap-2">
 <icons.FileSignature className={`${iconSize.md} text-primary`} />
 <h3 className={heading.section}>合同签署流程</h3>
 </div>
 {flow && <FlowStatusBadge status={flow.status} />}
 {polling && (
 <span className="flex items-center gap-1 text-xs text-muted-foreground">
 <icons.Loader2 className={`${iconSize.xs} animate-spin`} />
 自动刷新中
 </span>
 )}
 </div>

 {/* 步骤指示器 */}
 <div className="relative mb-6">
 {/* 连接线 */}
 <div className="absolute top-4 left-4 right-4 h-0.5 bg-border" />
 <div
 className="absolute top-4 left-4 h-0.5 bg-primary transition-all duration-500"
 style={{ width: `${(activeStep / (WORKFLOW_STEPS.length - 1)) * 100}%`, maxWidth:'calc(100% - 2rem)' }}
 />

 {/* 步骤节点 */}
 <div className="relative flex justify-between">
 {WORKFLOW_STEPS.map((step, idx) => {
 const StepIcon = step.icon;
 const isActive = idx === activeStep;
 const isCompleted = idx < activeStep;
 const isPending = idx > activeStep;

 return (
 <div key={step.key} className="flex flex-col items-center" style={{ width: compact ? 56 : 72 }}>
 <div
 className={[
'relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all duration-300',
 isCompleted
 ?'bg-primary border-primary text-primary-foreground'
 : isActive
 ?'bg-primary/10 border-primary text-primary ring-4 ring-primary/10'
 :'bg-background border-border text-muted-foreground',
 ].join('')}
 >
 {isCompleted ? (
 <icons.Check className={iconSize.sm} />
 ) : (
 <StepIcon className={iconSize.sm} />
 )}
 </div>
 <span
 className={[
'mt-2 text-center leading-tight',
 compact ?'text-[10px]' :'text-xs',
 isActive
 ?'text-primary font-medium'
 : isCompleted
 ?'text-foreground'
 :'text-muted-foreground',
 ].join('')}
 >
 {step.label}
 </span>
 </div>
 );
 })}
 </div>
 </div>

 {/* 当前步骤描述 */}
 {!compact && (
 <div className="bg-muted/50 rounded-lg px-4 py-3 mb-5">
 <p className="text-sm text-foreground font-medium">{WORKFLOW_STEPS[activeStep]?.label}</p>
 <p className="text-xs text-muted-foreground mt-0.5">{WORKFLOW_STEPS[activeStep]?.desc}</p>
 </div>
 )}

 {/* 签署人列表 */}
 {flow && flow.signers.length > 0 && (
 <div className="mb-5">
 <h4 className={`${heading.card} mb-3`}>签署方</h4>
 <div className="space-y-2">
 {flow.signers.map((signer) => (
 <div
 key={signer.signer_id}
 className="flex items-center justify-between px-3 py-2.5 bg-muted/30 rounded-lg border border-border/50"
 >
 <div className="flex items-center gap-2.5">
 {signer.sign_type ==='company' ? (
 <icons.Building className={`${iconSize.sm} text-muted-foreground`} />
 ) : (
 <icons.User className={`${iconSize.sm} text-muted-foreground`} />
 )}
 <div>
 <p className="text-sm text-foreground font-medium">{signer.name}</p>
 {signer.signed_at && (
 <p className="text-[11px] text-muted-foreground">
 签署时间: {new Date(signer.signed_at).toLocaleString('zh-CN')}
 </p>
 )}
 {signer.reject_reason && (
 <p className="text-[11px] text-destructive">拒签原因: {signer.reject_reason}</p>
 )}
 </div>
 </div>
 <div className="flex items-center gap-2">
 <SignerStatusBadge status={signer.status} />
 {signer.status ==='pending' && flow.status !=='cancelled' && (
 <button
 onClick={() => handleGetSignUrl(signer.signer_id)}
 disabled={signerUrlLoading === signer.signer_id}
 className={`${buttonStyle.sm} text-primary hover:bg-primary/5 transition-colors`}
 title="复制签署链接"
 >
 {signerUrlLoading === signer.signer_id ? (
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 ) : (
 <icons.Link className={iconSize.sm} />
 )}
 </button>
 )}
 </div>
 </div>
 ))}
 </div>
 </div>
 )}

 {/* 未创建流程时显示预设签署人 */}
 {!flow && defaultSigners.length > 0 && (
 <div className="mb-5">
 <h4 className={`${heading.card} mb-3`}>预设签署方</h4>
 <div className="space-y-2">
 {defaultSigners.map((signer, idx) => (
 <div
 key={idx}
 className="flex items-center gap-2.5 px-3 py-2 bg-muted/30 rounded-lg border border-border/50"
 >
 {signer.sign_type ==='company' ? (
 <icons.Building className={`${iconSize.sm} text-muted-foreground`} />
 ) : (
 <icons.User className={`${iconSize.sm} text-muted-foreground`} />
 )}
 <span className="text-sm text-foreground">{signer.name}</span>
 <span className="text-xs text-muted-foreground">
 ({signer.sign_type ==='company' ?'企业' :'个人'})
 </span>
 </div>
 ))}
 </div>
 </div>
 )}

 {/* 操作按钮 */}
 <div className="flex items-center gap-3">
 {/* 发起签署按钮 - 仅在步骤 3（发起签署）之前且未创建流程时显示 */}
 {!flow && activeStep >= 2 && (
 <button
 onClick={handleCreateFlow}
 disabled={loading || defaultSigners.length === 0}
 className={`${buttonStyle.primary} flex items-center gap-2`}
 >
 {loading ? (
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 ) : (
 <icons.Send className={iconSize.sm} />
 )}
 发起签署
 </button>
 )}

 {/* 刷新状态按钮 */}
 {flow && flow.status !=='completed' && flow.status !=='cancelled' && (
 <button onClick={refreshFlowStatus} className={`${buttonStyle.secondary} flex items-center gap-2`}>
 <icons.RefreshCw className={iconSize.sm} />
 刷新状态
 </button>
 )}

 {/* 完成归档提示 */}
 {flow?.status ==='completed' && (
 <div className="flex items-center gap-2 text-sm text-success">
 <icons.CheckCircle className={iconSize.md} />
 所有签署方已完成签署，合同已归档
 </div>
 )}
 </div>
 </div>
 );
});

export default SigningWorkflowPanel;
