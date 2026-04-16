/**
 * 律师在线协助面板
 * 
 * 功能：
 * 1. 在线律师列表（状态：在线/忙碌/离线）
 * 2. 一键转发当前文档/画布内容给律师
 * 3. 律师协助请求状态追踪
 * 4. 律师修改意见展示与应用（结合画布编辑）
 * 5. 历史协助记录
 */

import { useState, useRef, memo, useCallback, useEffect } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { useChatStore } from'@/lib/store';
import type { OnlineLawyer, LawyerAssistRequest, LawyerComment } from'@/lib/store';
import { toast } from'sonner';
import { v4 as uuidv4 } from'uuid';

// 律师端实时聊天消息
interface LawyerChatMessage {
 id: string;
 sender:'user' |'lawyer';
 senderName: string;
 content: string;
 timestamp: number;
 type:'text' |'action' |'system';
}

interface LawyerAssistPanelProps {
 onApplyToCanvas?: (content: string) => void;
}

export const LawyerAssistPanel = memo(function LawyerAssistPanel({
 onApplyToCanvas,
}: LawyerAssistPanelProps) {
 const store = useChatStore();
 const {
 onlineLawyers,
 activeAssistRequest,
 setActiveAssistRequest,
 assistHistory,
 addAssistHistory,
 canvasContent,
 lawyerPanelOpen,
 setLawyerPanelOpen,
 addLawyerComment,
 } = store;

 const [selectedLawyer, setSelectedLawyer] = useState<OnlineLawyer | null>(null);
 const [requestType, setRequestType] = useState<'review' |'edit' |'consult' |'approve'>('review');
 const [requestNote, setRequestNote] = useState('');
 const [showHistory, setShowHistory] = useState(false);
 const [showLawyerSelect, setShowLawyerSelect] = useState(false);

 // 律师端聊天
 const [chatMessages, setChatMessages] = useState<LawyerChatMessage[]>([]);
 const [chatInput, setChatInput] = useState('');
 const [activeView, setActiveView] = useState<'comments' |'chat'>('comments');
 const chatEndRef = useRef<HTMLDivElement>(null);

 // 聊天自动滚动
 useEffect(() => {
 chatEndRef.current?.scrollIntoView({ behavior:'smooth' });
 }, [chatMessages]);

 // 发送聊天消息
 const handleSendChat = useCallback(() => {
 if (!chatInput.trim()) return;
 const msg: LawyerChatMessage = {
 id: uuidv4(),
 sender:'user',
 senderName:'我',
 content: chatInput.trim(),
 timestamp: Date.now(),
 type:'text',
 };
 setChatMessages(prev => [...prev, msg]);
 setChatInput('');

 // 模拟律师回复
 setTimeout(() => {
 const reply: LawyerChatMessage = {
 id: uuidv4(),
 sender:'lawyer',
 senderName: activeAssistRequest?.lawyerName ||'律师',
 content:'收到，我已在画布中标注了相关修改建议，请查看。如有疑问我们可以继续沟通。',
 timestamp: Date.now(),
 type:'text',
 };
 setChatMessages(prev => [...prev, reply]);
 }, 2000);
 }, [chatInput, activeAssistRequest]);

 // 发起律师协助请求
 const handleSendRequest = useCallback(() => {
 if (!selectedLawyer) {
 toast.error('请先选择一位律师');
 return;
 }
 if (!canvasContent?.content) {
 toast.error('画布中暂无内容，请先生成或编辑文档');
 return;
 }

 const request: LawyerAssistRequest = {
 id: uuidv4(),
 lawyerId: selectedLawyer.id,
 lawyerName: selectedLawyer.name,
 type: requestType,
 documentTitle: canvasContent.title ||'未命名文档',
 content: canvasContent.content,
 status:'pending',
 createdAt: Date.now(),
 lawyerComments: [],
 };

 setActiveAssistRequest(request);
 setShowLawyerSelect(false);
 toast.success(`已向 ${selectedLawyer.name} 发送协助请求`);

 // 模拟律师接受请求（实际项目中通过 WebSocket 推送）
 setTimeout(() => {
 setActiveAssistRequest({ ...request, status:'accepted', respondedAt: Date.now() });
 toast.success(`${selectedLawyer.name} 已接受您的请求`);
 }, 2000);

 // 模拟律师处理中
 setTimeout(() => {
 setActiveAssistRequest({
 ...request,
 status:'in_progress',
 respondedAt: Date.now(),
 });
 }, 4000);

 // 模拟律师回复修改意见
 setTimeout(() => {
 const comments: LawyerComment[] = [
 {
 id: uuidv4(),
 lawyerId: selectedLawyer.id,
 lawyerName: selectedLawyer.name,
 content:'第三条违约责任条款建议加强，当前约定的违约金比例偏低，建议调整为合同总金额的20%-30%。',
 type:'revision',
 timestamp: Date.now(),
 lineRange: { start: 15, end: 22 },
 },
 {
 id: uuidv4(),
 lawyerId: selectedLawyer.id,
 lawyerName: selectedLawyer.name,
 content:'知识产权归属条款表述清晰，符合法律规定，建议保留。',
 type:'approval',
 timestamp: Date.now(),
 lineRange: { start: 30, end: 35 },
 },
 {
 id: uuidv4(),
 lawyerId: selectedLawyer.id,
 lawyerName: selectedLawyer.name,
 content:'建议在争议解决条款中增加调解前置程序，有助于降低诉讼成本。',
 type:'suggestion',
 timestamp: Date.now(),
 lineRange: { start: 45, end: 50 },
 },
 ];

 const completedRequest: LawyerAssistRequest = {
 ...request,
 status:'completed',
 respondedAt: Date.now() - 6000,
 completedAt: Date.now(),
 lawyerComments: comments,
 };
 setActiveAssistRequest(completedRequest);
 addAssistHistory(completedRequest);
 toast.success(`${selectedLawyer.name} 已完成审查，请查看修改意见`);
 }, 8000);
 }, [selectedLawyer, canvasContent, requestType, setActiveAssistRequest, addAssistHistory]);

 const statusConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
 online: { label:'在线', color:'text-success bg-success/10', icon: icons.Circle },
 busy: { label:'忙碌', color:'text-warning bg-warning/10', icon: icons.Clock },
 offline: { label:'离线', color:'text-muted-foreground bg-muted/50', icon: icons.XCircle },
 };

 const requestTypeLabels: Record<string, { label: string; desc: string }> = {
 review: { label:'文书审查', desc:'请律师审查并标注修改意见' },
 edit: { label:'协同编辑', desc:'邀请律师实时编辑画布中的文档' },
 consult: { label:'法律咨询', desc:'就当前文档向律师提问咨询' },
 approve: { label:'审批确认', desc:'请律师审批确认当前文档可用' },
 };

 const commentTypeStyles: Record<string, { color: string; icon: React.ElementType; label: string }> = {
 suggestion: { color:'text-primary bg-primary/5 border-primary/20', icon: icons.MessageSquare, label:'建议' },
 approval: { color:'text-success bg-success/10 border-success/20', icon: icons.CheckCircle, label:'通过' },
 revision: { color:'text-warning bg-warning/10 border-warning/20', icon: icons.Edit3, label:'修改' },
 question: { color:'text-primary bg-primary/5 border-primary/20', icon: icons.AlertTriangle, label:'问题' },
 };

 // ========== 活跃请求视图 ==========
 if (activeAssistRequest) {
 const isCompleted = activeAssistRequest.status ==='completed';
 const comments = activeAssistRequest.lawyerComments || [];

 return (
 <div className="h-full flex flex-col">
 {/* 请求头部 */}
 <div className="px-4 py-3 bg-background border-b border-border flex items-center gap-3">
 <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
 <icons.User className="w-5 h-5 text-primary" />
 </div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-medium text-foreground">{activeAssistRequest.lawyerName}</p>
 <p className="text-xs text-muted-foreground">
 {requestTypeLabels[activeAssistRequest.type]?.label} · {activeAssistRequest.documentTitle}
 </p>
 </div>
 <div className="flex items-center gap-2">
 {/* 状态标签 */}
 {activeAssistRequest.status ==='pending' && (
 <span className="flex items-center gap-1 text-xs text-warning bg-warning/10 px-2 py-1 rounded-full border border-warning/20">
 <icons.Loader2 className="w-3 h-3 animate-spin" /> 等待接受
 </span>
 )}
 {activeAssistRequest.status ==='accepted' && (
 <span className="flex items-center gap-1 text-xs text-primary bg-primary/5 px-2 py-1 rounded-full border border-primary/20">
 <icons.CheckCircle className="w-3 h-3" /> 已接受
 </span>
 )}
 {activeAssistRequest.status ==='in_progress' && (
 <span className="flex items-center gap-1 text-xs text-primary bg-primary/5 px-2 py-1 rounded-full border border-primary/20">
 <icons.Loader2 className="w-3 h-3 animate-spin" /> 处理中
 </span>
 )}
 {isCompleted && (
 <span className="flex items-center gap-1 text-xs text-success bg-success/10 px-2 py-1 rounded-full border border-success/20">
 <icons.CheckCircle className="w-3 h-3" /> 已完成
 </span>
 )}
 <button
 onClick={() => setActiveAssistRequest(null)}
 className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded"
 >
 <icons.X className="w-4 h-4" />
 </button>
 </div>
 </div>

 {/* 操作按钮栏（处理中或已完成时） */}
 {(activeAssistRequest.status ==='in_progress' || isCompleted) && (
 <div className="px-4 py-2 bg-muted/50 border-b border-border">
 <div className="flex items-center gap-2 mb-2">
 <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground bg-background rounded-lg border border-border hover:bg-muted transition-colors">
 <icons.Phone className="w-3.5 h-3.5" /> 语音通话
 </button>
 <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground bg-background rounded-lg border border-border hover:bg-muted transition-colors">
 <icons.Camera className="w-3.5 h-3.5" /> 视频会议
 </button>
 <div className="flex-1" />
 {isCompleted && (
 <button
 onClick={() => {
 store.setDocumentOverlay('none');
 toast.success('已切换到画布查看律师标注');
 }}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary-foreground bg-primary rounded-lg hover:bg-primary/90 transition-colors shadow-sm"
 >
 <icons.ExternalLink className="w-3.5 h-3.5" /> 画布查看变更
 </button>
 )}
 </div>
 {/* 视图切换：修改意见 / 实时沟通 */}
 <div className="flex bg-background rounded-lg p-0.5 border border-border">
 <button
 onClick={() => setActiveView('comments')}
 className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-[colors,shadow] ${
 activeView ==='comments' ?'bg-primary/5 text-primary shadow-sm' :'text-muted-foreground hover:text-foreground'
 }`}
 >
 <icons.Edit3 className="w-3 h-3" />
 修改意见 {comments.length > 0 && `(${comments.length})`}
 </button>
 <button
 onClick={() => setActiveView('chat')}
 className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-medium rounded-md transition-[colors,shadow] ${
 activeView ==='chat' ?'bg-primary/5 text-primary shadow-sm' :'text-muted-foreground hover:text-foreground'
 }`}
 >
 <icons.MessageSquare className="w-3 h-3" />
 实时沟通 {chatMessages.length > 0 && `(${chatMessages.length})`}
 </button>
 </div>
 </div>
 )}

 {/* ========== 修改意见视图 ========== */}
 {activeView ==='comments' && (
 <div className="flex-1 overflow-y-auto p-4 space-y-3">
 {comments.length === 0 && !isCompleted && (
 <div className="text-center py-12">
 <icons.Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-3" />
 <p className="text-sm text-muted-foreground">律师正在审查文档...</p>
 <p className="text-xs text-muted-foreground mt-1">请稍候，结果将自动更新</p>
 </div>
 )}

 {comments.map((comment, idx) => {
 const style = commentTypeStyles[comment.type] || commentTypeStyles.suggestion;
 const Icon = style.icon;
 return (
 <motion.div
 key={comment.id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: idx * 0.1 }}
 className={`rounded-xl border p-4 ${style.color}`}
 >
 <div className="flex items-center gap-2 mb-2">
 <Icon className="w-4 h-4" />
 <span className="text-xs font-semibold">{style.label}</span>
 {comment.lineRange && (
 <button
 onClick={() => {
 store.setDocumentOverlay('none');
 toast.success(`已定位到第 ${comment.lineRange!.start} 行`);
 }}
 className="text-[10px] px-1.5 py-0.5 bg-background/60 rounded-full hover:bg-background/80 cursor-pointer transition-colors"
 >
 行 {comment.lineRange.start}-{comment.lineRange.end} ↗
 </button>
 )}
 <span className="text-[10px] ml-auto opacity-70">
 {new Date(comment.timestamp).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 </div>
 <p className="text-sm leading-relaxed">{comment.content}</p>
 {comment.type ==='revision' && (
 <div className="flex gap-2 mt-3">
 <button
 onClick={() => {
 store.setDocumentOverlay('none');
 toast.success('修改意见已应用到画布');
 }}
 className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-background text-warning rounded-lg border border-warning/20 hover:bg-warning/20 transition-colors"
 >
 <icons.CheckCircle className="w-3 h-3" /> 应用修改
 </button>
 <button className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-background text-muted-foreground rounded-lg border border-border hover:bg-muted transition-colors">
 <icons.XCircle className="w-3 h-3" /> 忽略
 </button>
 </div>
 )}
 </motion.div>
 );
 })}

 {/* 完成后的操作 */}
 {isCompleted && comments.length > 0 && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="mt-4 p-4 bg-success/10 rounded-xl border border-success/20"
 >
 <div className="flex items-center gap-2 mb-2">
 <icons.CheckCircle className="w-5 h-5 text-success" />
 <span className="text-sm font-medium text-success">审查完成</span>
 </div>
 <p className="text-xs text-success mb-3">
 {activeAssistRequest.lawyerName} 已完成文档审查，共提出 {comments.length} 条意见。
 </p>
 <div className="flex flex-wrap gap-2">
 <button
 onClick={() => {
 store.setDocumentOverlay('none');
 toast.success('所有修改意见已一键应用到画布');
 }}
 className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-success text-primary-foreground rounded-2xl hover:bg-success/20 transition-colors shadow-sm"
 >
 <icons.CheckCircle className="w-3.5 h-3.5" /> 一键接受全部
 </button>
 <button
 onClick={() => store.setDocumentOverlay('none')}
 className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-background text-success rounded-2xl border border-success/20 hover:bg-success/20 transition-colors"
 >
 <icons.Eye className="w-3.5 h-3.5" /> 逐条查看
 </button>
 <button
 onClick={() => store.setDocumentOverlay('signing')}
 className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium bg-background text-primary rounded-2xl border border-primary/20 hover:bg-primary/5 transition-colors"
 >
 <icons.ArrowRight className="w-3.5 h-3.5" /> 进入签约流程
 </button>
 </div>
 </motion.div>
 )}
 </div>
 )}

 {/* ========== 实时沟通视图 ========== */}
 {activeView ==='chat' && (
 <div className="flex-1 flex flex-col">
 {/* 聊天消息区域 */}
 <div className="flex-1 overflow-y-auto p-4 space-y-3">
 {chatMessages.length === 0 && (
 <div className="text-center py-8">
 <icons.MessageSquare className="w-8 h-8 text-muted-foreground/50 mx-auto mb-2" />
 <p className="text-sm text-muted-foreground">与律师实时沟通</p>
 <p className="text-[10px] text-muted-foreground/50 mt-1">发送消息开始对话</p>
 </div>
 )}

 {/* 系统提示 — 转发文档时自动生成 */}
 {chatMessages.length === 0 && activeAssistRequest && (
 <div className="flex justify-center">
 <div className="px-3 py-1.5 bg-muted rounded-full">
 <p className="text-[10px] text-muted-foreground">
 已将「{activeAssistRequest.documentTitle}」转发给 {activeAssistRequest.lawyerName}
 </p>
 </div>
 </div>
 )}

 {chatMessages.map((msg) => (
 <motion.div
 key={msg.id}
 initial={{ opacity: 0, y: 5 }}
 animate={{ opacity: 1, y: 0 }}
 className={`flex gap-2 ${msg.sender ==='user' ?'flex-row-reverse' :''}`}
 >
 <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-semibold ${
 msg.sender ==='user'
 ?'bg-primary text-primary-foreground'
 :'bg-primary/10 text-primary'
 }`}>
 {msg.senderName[0]}
 </div>
 <div className={`max-w-[75%] ${msg.sender ==='user' ?'items-end' :'items-start'}`}>
 <div className={`rounded-2xl px-3 py-2 text-sm ${
 msg.sender ==='user'
 ?'bg-primary text-primary-foreground rounded-tr-none'
 :'bg-muted text-foreground rounded-tl-none'
 }`}>
 {msg.content}
 </div>
 <p className={`text-[10px] mt-0.5 ${msg.sender ==='user' ?'text-right' :''} text-muted-foreground`}>
 {new Date(msg.timestamp).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </p>
 </div>
 </motion.div>
 ))}
 <div ref={chatEndRef} />
 </div>

 {/* 聊天输入区 */}
 <div className="p-3 border-t border-border bg-background">
 <div className="flex items-end gap-2">
 <div className="flex-1">
 <textarea
 value={chatInput}
 onChange={(e) => setChatInput(e.target.value)}
 onKeyDown={(e) => {
 if (e.key ==='Enter' && !e.shiftKey) { e.preventDefault(); handleSendChat(); }
 }}
 placeholder="输入消息..."
 className="w-full px-3 py-2 text-sm bg-muted/50 border border-border rounded-xl resize-none outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/30"
 rows={1}
 style={{ minHeight:'36px', maxHeight:'80px' }}
 />
 </div>
 <button
 onClick={handleSendChat}
 disabled={!chatInput.trim()}
 className="p-2 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-colors"
 >
 <icons.Send className="w-4 h-4" />
 </button>
 </div>
 </div>
 </div>
 )}
 </div>
 );
 }

 // ========== 律师选择 + 发起请求视图 ==========
 return (
 <div className="h-full flex flex-col">
 {/* 标题栏 */}
 <div className="px-4 py-3 bg-background border-b border-border">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <button
 onClick={() => store.setDocumentOverlay('none')}
 className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded mr-1"
 title="返回文档"
 >
 <icons.X className="w-4 h-4" />
 </button>
 <icons.Users className="w-5 h-5 text-primary" />
 <span className="text-sm font-medium text-foreground">律师协助</span>
 </div>
 {assistHistory.length > 0 && (
 <button
 onClick={() => setShowHistory(!showHistory)}
 className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
 >
 <icons.Clock className="w-3 h-3" />
 历史 ({assistHistory.length})
 {showHistory ? <icons.ChevronDown className="w-3 h-3" /> : <icons.ChevronRight className="w-3 h-3" />}
 </button>
 )}
 </div>
 </div>

 <div className="flex-1 overflow-y-auto">
 {/* 历史记录折叠区 */}
 <AnimatePresence>
 {showHistory && assistHistory.length > 0 && (
 <motion.div
 initial={{ height: 0, opacity: 0 }}
 animate={{ height:'auto', opacity: 1 }}
 exit={{ height: 0, opacity: 0 }}
 className="overflow-hidden border-b border-border"
 >
 <div className="p-3 space-y-2 bg-muted/30">
 {assistHistory.slice(0, 5).map((req) => (
 <div key={req.id} className="flex items-center gap-3 p-2.5 bg-background rounded-lg border border-border">
 <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center">
 <icons.User className="w-3.5 h-3.5 text-muted-foreground" />
 </div>
 <div className="flex-1 min-w-0">
 <p className="text-xs font-medium text-foreground truncate">{req.lawyerName} · {req.documentTitle}</p>
 <p className="text-[10px] text-muted-foreground">
 {new Date(req.createdAt).toLocaleDateString()} · {req.lawyerComments?.length || 0} 条意见
 </p>
 </div>
 <span className="text-[10px] px-1.5 py-0.5 bg-success/10 text-success rounded-full">已完成</span>
 </div>
 ))}
 </div>
 </motion.div>
 )}
 </AnimatePresence>

 {/* 请求类型选择 */}
 <div className="p-4">
 <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-caption">协助类型</p>
 <div className="grid grid-cols-2 gap-2">
 {Object.entries(requestTypeLabels).map(([key, val]) => (
 <button
 key={key}
 onClick={() => setRequestType(key as any)}
 className={`p-3 rounded-xl text-left border transition-[colors,shadow] ${
 requestType === key
 ?'border-primary/30 bg-primary/5 shadow-sm'
 :'border-border bg-background hover:border-muted-foreground'
 }`}
 >
 <p className={`text-xs font-semibold ${requestType === key ?'text-primary' :'text-foreground'}`}>
 {val.label}
 </p>
 <p className={`text-[10px] mt-0.5 ${requestType === key ?'text-primary' :'text-muted-foreground'}`}>
 {val.desc}
 </p>
 </button>
 ))}
 </div>
 </div>

 {/* 当前文档信息 */}
 {canvasContent && (
 <div className="mx-4 p-3 bg-muted/50 rounded-xl border border-border mb-4">
 <div className="flex items-center gap-2 mb-1">
 <icons.FileText className="w-4 h-4 text-muted-foreground" />
 <span className="text-xs font-medium text-foreground">待转发文档</span>
 </div>
 <p className="text-sm font-medium text-foreground truncate">{canvasContent.title ||'未命名文档'}</p>
 <p className="text-[10px] text-muted-foreground mt-0.5">
 {canvasContent.content.length} 字 · {canvasContent.type ==='contract' ?'合同' :'文档'}
 </p>
 </div>
 )}

 {/* 备注输入 */}
 <div className="px-4 mb-4">
 <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-caption">备注说明（可选）</p>
 <textarea
 value={requestNote}
 onChange={(e) => setRequestNote(e.target.value)}
 placeholder="向律师补充说明需要重点关注的问题..."
 className="w-full px-3 py-2.5 text-sm bg-background border border-border rounded-xl resize-none outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/30"
 rows={2}
 />
 </div>

 {/* 在线律师列表 */}
 <div className="px-4 pb-4">
 <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-caption">选择律师</p>
 <div className="space-y-2">
 {onlineLawyers.map((lawyer) => {
 const sConfig = statusConfig[lawyer.status];
 const StatusIcon = sConfig.icon;
 const isSelected = selectedLawyer?.id === lawyer.id;
 const isAvailable = lawyer.status !=='offline';

 return (
 <motion.button
 key={lawyer.id}
 onClick={() => isAvailable && setSelectedLawyer(isSelected ? null : lawyer)}
 whileTap={isAvailable ? { scale: 0.98 } : undefined}
 className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-[colors,shadow] text-left ${
 isSelected
 ?'border-primary bg-primary/5 shadow-md shadow-primary/10'
 : isAvailable
 ?'border-border bg-background hover:border-muted-foreground hover:shadow-sm'
 :'border-border bg-muted/50 opacity-60 cursor-not-allowed'
 }`}
 disabled={!isAvailable}
 >
 {/* 头像 */}
 <div className="relative">
 <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold ${
 isSelected ?'bg-primary/20 text-primary' :'bg-muted text-muted-foreground'
 }`}>
 {lawyer.name[0]}
 </div>
 <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-background ${
 lawyer.status ==='online' ?'bg-success' : lawyer.status ==='busy' ?'bg-warning' :'bg-muted-foreground'
 }`} />
 </div>

 <div className="flex-1 min-w-0">
 <div className="flex items-center gap-2">
 <span className="text-sm font-medium text-foreground">{lawyer.name}</span>
 <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${sConfig.color}`}>
 {sConfig.label}
 </span>
 </div>
 {lawyer.firm && (
 <div className="flex items-center gap-1 mt-0.5">
 <icons.Briefcase className="w-3 h-3 text-muted-foreground" />
 <span className="text-[10px] text-muted-foreground">{lawyer.firm}</span>
 </div>
 )}
 <div className="flex flex-wrap gap-1 mt-1">
 {lawyer.specialties.slice(0, 3).map(s => (
 <span key={s} className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded-full">{s}</span>
 ))}
 </div>
 </div>

 <div className="flex flex-col items-end gap-1 flex-shrink-0">
 <div className="flex items-center gap-0.5">
 <icons.Star className="w-3 h-3 text-warning fill-amber-400" />
 <span className="text-xs font-medium text-foreground">{lawyer.rating}</span>
 </div>
 <span className="text-[10px] text-muted-foreground">{lawyer.responseTime}</span>
 </div>

 {isSelected && (
 <icons.CheckCircle className="w-5 h-5 text-primary flex-shrink-0" />
 )}
 </motion.button>
 );
 })}
 </div>
 </div>
 </div>

 {/* 底部发送按钮 */}
 <div className="p-4 border-t border-border bg-background">
 <button
 onClick={handleSendRequest}
 disabled={!selectedLawyer || !canvasContent}
 className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground text-sm font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-[colors,transform] shadow-sm active:scale-[0.98]"
 >
 <icons.Send className="w-4 h-4" />
 {selectedLawyer
 ? `转发给 ${selectedLawyer.name}`
 :'请先选择律师'
 }
 {selectedLawyer && <icons.ArrowRight className="w-4 h-4" />}
 </button>
 {!canvasContent && (
 <p className="text-[10px] text-center text-warning mt-2">
 画布中暂无文档内容，请先生成或打开文档
 </p>
 )}
 </div>
 </div>
 );
});
