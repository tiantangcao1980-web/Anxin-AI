/**
 * ClarificationBubble — 引导式需求确认组件 v2
 *
 * 改进点（用户反馈）：
 * 1. 每个问题都支持「自己输入」选项，不局限于预设选项
 * 2. 选择后不立即锁定 — 可切换重选
 * 3. 未回答全部问题也可提交（已回答的先发送，鼓励继续补充）
 * 4. 提交后显示友好的"已确认"状态 + 处理中指示
 * 5. 整体更强的引导语气：引导用户逐步完善需求
 */

import { useState, useRef } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';

interface ClarificationBubbleProps {
 message: string;
 questions: { question: string; options: string[] }[];
 originalContent: string;
 onSubmit?: (originalContent: string, selections: Record<string, string>) => void;
 disabled: boolean;
}

export function ClarificationBubble({
 message,
 questions,
 originalContent,
 onSubmit,
 disabled,
}: ClarificationBubbleProps) {
 const [selections, setSelections] = useState<Record<string, string>>({});
 const [customInputs, setCustomInputs] = useState<Record<string, string>>({});
 const [showCustomInput, setShowCustomInput] = useState<Record<string, boolean>>({});
 const [submitted, setSubmitted] = useState(false);
 const customInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

 const handleSelect = (question: string, option: string) => {
 if (submitted) return;
 // 点击相同选项取消选择
 if (selections[question] === option) {
 setSelections(prev => {
 const next = { ...prev };
 delete next[question];
 return next;
 });
 return;
 }
 setSelections(prev => ({ ...prev, [question]: option }));
 // 选中预设选项时关闭自定义输入
 setShowCustomInput(prev => ({ ...prev, [question]: false }));
 };

 const handleToggleCustomInput = (question: string) => {
 if (submitted) return;
 const newState = !showCustomInput[question];
 setShowCustomInput(prev => ({ ...prev, [question]: newState }));
 if (newState) {
 // 清除预设选择
 setSelections(prev => {
 const next = { ...prev };
 delete next[question];
 return next;
 });
 setTimeout(() => customInputRefs.current[question]?.focus(), 100);
 }
 };

 const handleCustomInputChange = (question: string, value: string) => {
 setCustomInputs(prev => ({ ...prev, [question]: value }));
 if (value.trim()) {
 setSelections(prev => ({ ...prev, [question]: value.trim() }));
 } else {
 setSelections(prev => {
 const next = { ...prev };
 delete next[question];
 return next;
 });
 }
 };

 const handleSubmit = () => {
 if (submitted || disabled) return;
 const valid = Object.fromEntries(Object.entries(selections).filter(([_, v]) => v));
 if (Object.keys(valid).length === 0) return;
 setSubmitted(true);
 onSubmit?.(originalContent, valid);
 };

 const normalizedQuestions = (Array.isArray(questions) ? questions : [])
 .map((q, index) => {
 const question = typeof q?.question ==='string' && q.question.trim()
 ? q.question.trim()
 : `问题 ${index + 1}`;
 const options = Array.isArray(q?.options)
 ? q.options
 .filter((opt): opt is string => typeof opt ==='string')
 .map(opt => opt.trim())
 .filter(Boolean)
 : [];
 return { question, options };
 });

 const answeredCount = Object.values(selections).filter(v => v).length;
 const allAnswered = normalizedQuestions.length > 0 && answeredCount === normalizedQuestions.length;
 const hasAnyAnswer = answeredCount > 0;

 // 提交后的紧凑视图
 if (submitted) {
 return (
 <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
 <div className="w-8 h-8 rounded-full bg-success/10 border border-success/20 flex items-center justify-center flex-shrink-0">
 <icons.CheckCircle className="h-4 w-4 text-success" />
 </div>
 <div className="flex flex-col gap-1 max-w-[80%]">
 <div className="bg-success/10 border border-success/20 rounded-2xl rounded-tl-none px-4 py-3">
 <div className="flex items-center gap-1.5 mb-2">
 <span className="text-xs font-semibold text-success">需求已确认</span>
 <icons.Loader2 className="w-3 h-3 animate-spin text-success" />
 <span className="text-[10px] text-success">正在处理...</span>
 </div>
 <div className="flex flex-wrap gap-1.5">
 {Object.entries(selections).filter(([_, v]) => v).map(([q, a]) => (
 <span key={q} className="inline-flex items-center gap-1 px-2 py-1 bg-background rounded-lg text-[11px] text-foreground border border-success/20">
 <icons.CheckCircle className="w-2.5 h-2.5 text-success" />
 {a.length > 20 ? a.slice(0, 20) +'...' : a}
 </span>
 ))}
 </div>
 </div>
 </div>
 </motion.div>
 );
 }

 return (
 <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
 <div className="w-8 h-8 rounded-full bg-warning/10 border border-warning/20 flex items-center justify-center flex-shrink-0">
 <icons.HelpCircle className="h-4 w-4 text-warning" />
 </div>
 <div className="flex flex-col gap-1.5 max-w-[85%]">
 <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground ml-1">
 <icons.Sparkles className="h-3 w-3 text-warning" /> 需求确认
 </div>
 <div className="bg-background border border-border rounded-2xl rounded-tl-none px-4 py-3.5 shadow-sm">
 <p className="text-sm text-foreground mb-3 leading-relaxed">{message}</p>
 <div className="space-y-4">
 {normalizedQuestions.map((q, qi) => {
 const isAnswered = !!selections[q.question];
 const isCustomMode = showCustomInput[q.question];
 return (
 <div key={qi}>
 <p className="text-xs font-medium text-foreground mb-2 flex items-center gap-1.5">
 <span className={`w-4.5 h-4.5 rounded-full text-[10px] font-bold flex items-center justify-center flex-shrink-0 ${
 isAnswered ?'bg-primary text-primary-foreground' :'bg-muted text-muted-foreground'
 }`}>{qi + 1}</span>
 {q.question}
 </p>
 <div className="flex flex-wrap gap-1.5">
 {q.options.map((opt, oi) => {
 const isSelected = selections[q.question] === opt && !isCustomMode;
 return (
 <button
 key={oi}
 onClick={() => handleSelect(q.question, opt)}
 className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
 isSelected
 ?'bg-primary text-primary-foreground border-primary shadow-sm'
 :'bg-background text-muted-foreground border-border hover:border-primary/50 hover:text-primary hover:bg-primary/5 cursor-pointer active:scale-95'
 }`}
 >
 {opt}
 </button>
 );
 })}
 {/* 自己输入按钮 */}
 <button
 onClick={() => handleToggleCustomInput(q.question)}
 className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
 isCustomMode
 ?'bg-primary/5 text-primary border-primary/30'
 :'bg-background text-muted-foreground/60 border-dashed border-border hover:border-primary/50 hover:text-primary cursor-pointer'
 }`}
 >
 <icons.Edit className="w-3 h-3 inline mr-1" />
 自己输入
 </button>
 </div>
 {/* 自定义输入框 */}
 <AnimatePresence>
 {isCustomMode && (
 <motion.div
 initial={{ opacity: 0, height: 0 }}
 animate={{ opacity: 1, height:'auto' }}
 exit={{ opacity: 0, height: 0 }}
 className="overflow-hidden"
 >
 <input
 ref={(el) => { customInputRefs.current[q.question] = el; }}
 value={customInputs[q.question] ||''}
 onChange={(e) => handleCustomInputChange(q.question, e.target.value)}
 onKeyDown={(e) => {
 if (e.key ==='Enter' && hasAnyAnswer) handleSubmit();
 }}
 placeholder="请输入您的具体情况..."
 className="mt-2 w-full px-3 py-2 text-xs bg-muted/50 border border-border rounded-xl focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/10 text-foreground placeholder:text-muted-foreground transition-colors"
 />
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
 })}
 </div>

 {/* 提交按钮 — 有任意回答即可提交 */}
 <div className="mt-4 space-y-2">
 {hasAnyAnswer && (
 <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
 <button
 onClick={handleSubmit}
 disabled={disabled}
 className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-[background-color,transform] active:scale-[0.98] shadow-sm"
 >
 {allAnswered ? (
 <>确认需求，开始处理 <icons.ChevronRight className="w-4 h-4" /></>
 ) : (
 <>先处理已确认的 ({answeredCount}/{normalizedQuestions.length}) <icons.ChevronRight className="w-4 h-4" /></>
 )}
 </button>
 </motion.div>
 )}
 <p className="text-[10px] text-muted-foreground text-center leading-relaxed">
 {allAnswered
 ?'所有信息已填写完毕，点击上方按钮确认'
 : `已完成 ${answeredCount}/${normalizedQuestions.length} · 您可以先提交已有信息，AI 会继续引导补充`
 }
 </p>
 </div>
 </div>
 </div>
 </motion.div>
 );
}
