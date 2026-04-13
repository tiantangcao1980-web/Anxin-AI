/**
 * 找律师页面 — 滴滴模式匿名匹配
 *
 * 用户流程：
 * 1. 描述法律问题 → AI 分析 → 生成匿名摘要
 * 2. 匹配律师 → 匿名聊天
 * 3. 满意 → 一键委托 → 签约 → 支付
 */

import { useState, useCallback, useEffect } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { lawyerMatchingApi, anonymousChatApi } from'@/lib/api';
import { toast } from'sonner';
import { PageContainer } from'@/components/ui/PageContainer';
import AnonymousChatRoom from'@/components/chat/AnonymousChatRoom';

type Step ='describe' |'matching' |'chatting' |'delegate';

// 法律领域选项
const LEGAL_DOMAINS = [
 { value:'contract', label:'合同纠纷', icon: icons.FileText },
 { value:'labor', label:'劳动争议', icon: icons.Users },
 { value:'ip', label:'知识产权', icon: icons.ShieldCheck },
 { value:'corporate', label:'公司治理', icon: icons.Building },
 { value:'litigation', label:'民事诉讼', icon: icons.Scale },
 { value:'compliance', label:'合规审查', icon: icons.ClipboardCheck },
 { value:'criminal', label:'刑事案件', icon: icons.ShieldAlert },
 { value:'other', label:'其他问题', icon: icons.HelpCircle },
];

const URGENCY_OPTIONS = [
 { value:'low', label:'一般咨询', desc:'不着急，想了解一下', color:'text-muted-foreground' },
 { value:'medium', label:'需要尽快', desc:'最近需要处理', color:'text-warning' },
 { value:'high', label:'紧急', desc:'尽快处理', color:'text-destructive' },
 { value:'urgent', label:'非常紧急', desc:'3分钟内匹配律师', color:'text-destructive' },
];

export default function FindLawyer() {
 const [step, setStep] = useState<Step>('describe');
 const [description, setDescription] = useState('');
 const [selectedDomain, setSelectedDomain] = useState('');
 const [urgency, setUrgency] = useState('medium');
 const [isSubmitting, setIsSubmitting] = useState(false);
 const [consultationId, setConsultationId] = useState<string | null>(null);
 const [anonymousSummary, setAnonymousSummary] = useState('');
 const [chatRoomId, setChatRoomId] = useState<string | null>(null);
 const [chatToken, setChatToken] = useState<string | null>(null);
 const [isCreatingRoom, setIsCreatingRoom] = useState(false);
 const [selectedLawyer, setSelectedLawyer] = useState<any>(null);
 const [isDelegating, setIsDelegating] = useState(false);
 const [lawyers, setLawyers] = useState<any[]>([]);
 const [loadingLawyers, setLoadingLawyers] = useState(false);
 const [lawyerLoadError, setLawyerLoadError] = useState('');

 const loadLawyers = useCallback(async () => {
 if (step !=='matching' || !consultationId) return;
 setLoadingLawyers(true);
 setLawyerLoadError('');
 try {
 const result = await lawyerMatchingApi.listLawyers({
 domain: selectedDomain || undefined,
 page: 1,
 page_size: 20,
 });
 setLawyers(result.items || []);
 } catch (e: any) {
 setLawyers([]);
 setLawyerLoadError(e.message ||'律师列表加载失败');
 } finally {
 setLoadingLawyers(false);
 }
 }, [consultationId, selectedDomain, step]);

 useEffect(() => {
 loadLawyers();
 }, [loadLawyers]);

 const handleSubmit = useCallback(async () => {
 if (!description.trim() || description.length < 10) {
 toast.error('请详细描述您的法律问题（至少10个字）');
 return;
 }
 setIsSubmitting(true);
 try {
 const result = await lawyerMatchingApi.createConsultation({
 description,
 legal_domain: selectedDomain || undefined,
 urgency,
 });
 setConsultationId(result.consultation_id);
 setAnonymousSummary(result.anonymous_summary);
 setStep('matching');
 toast.success('已提交，正在为您匹配律师...');
 } catch (e: any) {
 toast.error(e.message ||'提交失败，请重试');
 } finally {
 setIsSubmitting(false);
 }
 }, [description, selectedDomain, urgency]);

 // 进入匿名聊天室
 const handleEnterChat = useCallback(async () => {
 setIsCreatingRoom(true);
 try {
 const result = await anonymousChatApi.createRoom({
 consultation_id: consultationId || undefined,
 lawyer_name: selectedLawyer?.real_name,
 });
 setChatRoomId(result.room_id);
 setChatToken(result.user_token);
 setStep('chatting');
 } catch (e: any) {
 toast.error(e.message ||'创建聊天室失败');
 } finally {
 setIsCreatingRoom(false);
 }
 }, [consultationId]);

 // 退出聊天室
 const handleLeaveChat = useCallback(() => {
 setChatRoomId(null);
 setChatToken(null);
 setStep('matching');
 }, []);

 // 一键委托
 const handleDelegate = useCallback(async () => {
 if (!selectedLawyer) {
 toast.error('请先选择一位律师');
 return;
 }
 setIsDelegating(true);
 try {
 if (!consultationId) {
 throw new Error('咨询记录不存在，请重新发起咨询');
 }
 await lawyerMatchingApi.createDelegation(consultationId, {
 title: `${selectedLawyer.real_name} 委托申请`,
 description: anonymousSummary || description,
 service_type:'instant',
 });
 toast.success('委托请求已提交，律师将尽快与您联系');
 setStep('describe');
 setDescription('');
 setSelectedDomain('');
 setSelectedLawyer(null);
 setConsultationId(null);
 setAnonymousSummary('');
 setLawyers([]);
 } catch (e: any) {
 toast.error(e.message ||'委托提交失败，当前需要律师先完成接单');
 } finally {
 setIsDelegating(false);
 }
 }, [anonymousSummary, consultationId, description, selectedDomain, selectedLawyer]);

 // 如果在聊天步骤，展示全屏聊天室
 if (step ==='chatting' && chatRoomId && chatToken) {
 return (
 <PageContainer title="匿名咨询" description="与律师匿名沟通">
 <div className="max-w-3xl mx-auto h-[calc(100vh-200px)] min-h-[500px]">
 <AnonymousChatRoom
 roomId={chatRoomId}
 token={chatToken}
 role="user"
 onClose={handleLeaveChat}
 />
 </div>
 </PageContainer>
 );
 }

 return (
 <PageContainer
 title="找律师"
 description="AI 智能匹配 · 匿名咨询 · 隐私保护"
 >
 <div className="max-w-3xl mx-auto">
 {/* 步骤指示器 */}
 <div className="flex items-center justify-center gap-2 mb-8">
 {[
 { key:'describe', label:'描述问题' },
 { key:'matching', label:'匹配律师' },
 { key:'chatting', label:'匿名咨询' },
 { key:'delegate', label:'一键委托' },
 ].map((s, i) => (
 <div key={s.key} className="flex items-center gap-2">
 <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
 step === s.key
 ?'bg-primary text-primary-foreground'
 : i < ['describe','matching','chatting','delegate'].indexOf(step)
 ?'bg-success text-white'
 :'bg-muted text-muted-foreground'
 }`}>
 {i < ['describe','matching','chatting','delegate'].indexOf(step)
 ? <icons.Check className="w-4 h-4" />
 : i + 1
 }
 </div>
 <span className={`text-xs font-medium hidden sm:inline ${
 step === s.key ?'text-foreground' :'text-muted-foreground'
 }`}>{s.label}</span>
 {i < 3 && <div className="w-4 sm:w-8 h-px bg-border shrink-0" />}
 </div>
 ))}
 </div>

 <AnimatePresence mode="wait">
 {/* Step 1: 描述问题 */}
 {step ==='describe' && (
 <motion.div
 key="describe"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 className="space-y-6"
 >
 {/* 隐私保护提示 */}
 <div className="flex items-start gap-3 p-4 bg-primary/5 border border-primary/10 rounded-xl">
 <icons.ShieldCheck className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
 <div>
 <p className="text-sm font-medium text-foreground">匿名隐私保护</p>
 <p className="text-xs text-muted-foreground mt-1">
 AI 将自动脱敏您的描述，律师仅能看到匿名案情摘要。在您主动选择委托之前，律师不会知道您的任何个人信息。
 </p>
 </div>
 </div>

 {/* 法律领域选择 */}
 <div>
 <label className="text-sm font-medium text-foreground mb-3 block">选择法律领域（可选）</label>
 <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
 {LEGAL_DOMAINS.map(d => {
 const Icon = d.icon;
 return (
 <button
 key={d.value}
 onClick={() => setSelectedDomain(selectedDomain === d.value ?'' : d.value)}
 className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all text-center ${
 selectedDomain === d.value
 ?'border-primary bg-primary/5 text-primary'
 :'border-border bg-background text-muted-foreground hover:border-primary/30 hover:bg-muted/50'
 }`}
 >
 <Icon className="w-5 h-5" />
 <span className="text-xs font-medium">{d.label}</span>
 </button>
 );
 })}
 </div>
 </div>

 {/* 问题描述 */}
 <div>
 <label className="text-sm font-medium text-foreground mb-2 block">详细描述您的法律问题</label>
 <textarea
 value={description}
 onChange={(e) => setDescription(e.target.value)}
 placeholder="请尽可能详细地描述您遇到的法律问题，AI 会自动分析并生成匿名摘要发送给律师..."
 className="w-full h-40 p-4 bg-muted/50 border border-border rounded-xl text-sm text-foreground placeholder:text-muted-foreground resize-none focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all"
 />
 <p className="text-xs text-muted-foreground mt-1 text-right">{description.length} / 5000</p>
 </div>

 {/* 紧急程度 */}
 <div>
 <label className="text-sm font-medium text-foreground mb-3 block">紧急程度</label>
 <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
 {URGENCY_OPTIONS.map(u => (
 <button
 key={u.value}
 onClick={() => setUrgency(u.value)}
 className={`p-3 rounded-xl border text-left transition-all ${
 urgency === u.value
 ?'border-primary bg-primary/5'
 :'border-border bg-background hover:border-primary/30'
 }`}
 >
 <p className={`text-sm font-medium ${urgency === u.value ?'text-primary' : u.color}`}>{u.label}</p>
 <p className="text-xs text-muted-foreground mt-0.5">{u.desc}</p>
 </button>
 ))}
 </div>
 </div>

 {/* 提交按钮 */}
 <button
 onClick={handleSubmit}
 disabled={isSubmitting || description.length < 10}
 className="w-full py-3 bg-primary text-primary-foreground font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
 >
 {isSubmitting ? (
 <><icons.Loader2 className="w-4 h-4 animate-spin" /> AI 分析中...</>
 ) : (
 <><icons.Search className="w-4 h-4" /> 开始匹配律师</>
 )}
 </button>
 </motion.div>
 )}

 {/* Step 2: 匹配律师 */}
 {step ==='matching' && (
 <motion.div
 key="matching"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 className="space-y-6"
 >
 {/* AI 分析结果预览 */}
 {anonymousSummary && (
 <div className="p-4 bg-primary/5 border border-primary/10 rounded-xl">
 <p className="text-xs font-medium text-muted-foreground mb-2">AI 匿名摘要（律师将看到）：</p>
 <p className="text-sm text-foreground">{anonymousSummary}</p>
 </div>
 )}

 <p className="text-xs text-muted-foreground text-center">
 匹配过程中您的个人信息完全隐藏，律师仅能看到 AI 生成的匿名摘要
 </p>

 {/* 律师卡片列表 */}
 <div className="space-y-3">
 <h3 className="text-sm font-medium text-foreground">为您推荐的律师</h3>
 {loadingLawyers ? (
 <div className="p-6 rounded-xl border border-border bg-background text-sm text-muted-foreground flex items-center justify-center gap-2">
 <icons.Loader2 className="w-4 h-4 animate-spin" />
 正在加载律师列表...
 </div>
 ) : lawyerLoadError ? (
 <div className="p-6 rounded-xl border border-destructive/20 bg-destructive/5 text-sm text-destructive">
 <p>{lawyerLoadError}</p>
 <button onClick={loadLawyers} className="mt-3 text-sm font-medium underline underline-offset-4">
 重新加载
 </button>
 </div>
 ) : lawyers.length === 0 ? (
 <div className="p-6 rounded-xl border border-border bg-background text-sm text-muted-foreground">
 暂无符合条件的律师，您可以返回修改领域后重试。
 </div>
 ) : (
 lawyers.map(lawyer => {
 const badge = lawyer.is_online ?'在线' : lawyer.is_verified ?'已认证' :'待确认';
 const speciality = lawyer.specializations?.[0] || selectedDomain ||'综合法务';
 return (
 <div
 key={lawyer.id}
 onClick={() => setSelectedLawyer(lawyer)}
 className={`p-4 rounded-xl border transition-all cursor-pointer ${
 selectedLawyer?.id === lawyer.id
 ?'border-primary bg-primary/5 ring-2 ring-primary/20'
 :'border-border bg-background hover:border-primary/30 hover:bg-muted/50'
 }`}
 >
 <div className="flex items-center gap-3">
 <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
 <icons.User className="w-6 h-6 text-muted-foreground" />
 </div>
 <div className="flex-1">
 <div className="flex items-center gap-2">
 <span className="text-sm font-medium text-foreground">{lawyer.real_name}</span>
 <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">{badge}</span>
 </div>
 <p className="text-xs text-muted-foreground mt-0.5">
 {speciality} | {lawyer.years_of_practice || 0}年执业 | {lawyer.total_cases || 0}+案件
 </p>
 {lawyer.law_firm && (
 <p className="text-xs text-muted-foreground mt-1">{lawyer.law_firm}</p>
 )}
 </div>
 <div className="text-right">
 <div className="flex items-center gap-1 text-warning">
 <icons.Star className="w-3.5 h-3.5" />
 <span className="text-sm font-medium">{(lawyer.rating || 0).toFixed(1)}</span>
 </div>
 </div>
 </div>
 </div>
 );
 })
 )}
 </div>

 <div className="flex items-center justify-center gap-4">
 <button
 onClick={() => setStep('describe')}
 className="text-sm text-muted-foreground hover:text-foreground transition-colors"
 >
 返回修改
 </button>
 <button
 onClick={handleEnterChat}
 disabled={isCreatingRoom || !selectedLawyer}
 className="px-6 py-2.5 bg-muted text-foreground font-medium rounded-xl hover:bg-muted/80 disabled:opacity-50 transition-all flex items-center gap-2"
 >
 {isCreatingRoom ? (
 <><icons.Loader2 className="w-4 h-4 animate-spin" /> 创建聊天室...</>
 ) : (
 <><icons.MessageSquare className="w-4 h-4" /> 匿名咨询</>
 )}
 </button>
 <button
 onClick={() => setStep('delegate')}
 disabled={!selectedLawyer}
 className="px-6 py-2.5 bg-primary text-primary-foreground font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-all flex items-center gap-2"
 >
 <icons.Check className="w-4 h-4" /> 一键委托
 </button>
 </div>
 </motion.div>
 )}

 {/* Step 4: 一键委托 */}
 {step ==='delegate' && (
 <motion.div
 key="delegate"
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -20 }}
 className="space-y-6 max-w-md mx-auto"
 >
 <div className="text-center">
 <div className="w-16 h-16 mx-auto bg-success/10 rounded-full flex items-center justify-center mb-4">
 <icons.CheckCircle className="w-8 h-8 text-success" />
 </div>
 <h3 className="text-lg font-medium text-foreground">确认委托</h3>
 <p className="text-sm text-muted-foreground mt-2">确认后将向律师发送委托请求</p>
 </div>

 {selectedLawyer && (
 <div className="p-4 bg-muted/50 border border-border rounded-xl">
 <div className="flex items-center gap-3">
 <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
 <icons.User className="w-5 h-5 text-primary" />
 </div>
 <div>
 <p className="text-sm font-medium text-foreground">{selectedLawyer.real_name}</p>
 <p className="text-xs text-muted-foreground">
 {selectedLawyer.specializations?.[0] ||'综合法务'} | {selectedLawyer.years_of_practice || 0}年执业
 </p>
 </div>
 </div>
 </div>
 )}

 <div className="p-4 bg-warning/10 border border-warning/20 rounded-xl">
 <p className="text-xs text-warning">
 委托后，您的联系方式将对律师可见。律师将在24小时内与您取得联系。如有问题请联系客服。
 </p>
 </div>

 <div className="flex gap-3">
 <button
 onClick={() => setStep('matching')}
 className="flex-1 py-2.5 bg-muted text-foreground font-medium rounded-xl hover:bg-muted/80 transition-all"
 >
 返回选择
 </button>
 <button
 onClick={handleDelegate}
 disabled={isDelegating}
 className="flex-1 py-2.5 bg-primary text-primary-foreground font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
 >
 {isDelegating ? (
 <><icons.Loader2 className="w-4 h-4 animate-spin" /> 提交中...</>
 ) : (
'确认委托'
 )}
 </button>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 </PageContainer>
 );
}
