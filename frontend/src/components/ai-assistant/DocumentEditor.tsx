import { useState } from'react';
import { icons } from'@/lib/icons';
import { motion } from'framer-motion';
import { Annotation } from'./AIAssistant';

interface DocumentEditorProps {
 content: string;
 onContentChange: (content: string) => void;
 onAnnotationClick: (annotation: Annotation) => void;
}

const annotations: Annotation[] = [
 {
 id:'1',
 lineNumber: 3,
 type:'warning',
 message:'收件人信息不完整',
 detail:'建议补充收件人的详细地址、法定代表人姓名等信息，以便送达和证据固定。',
 },
 {
 id:'2',
 lineNumber: 7,
 type:'suggestion',
 message:'建议补充合同编号',
 reference:'《律师函写作规范》第8条',
 detail:'在描述合同时应注明合同编号，便于对方核查，增强说服力。',
 },
];

export function DocumentEditor({ content, onContentChange, onAnnotationClick }: DocumentEditorProps) {
 const [isReviewing, setIsReviewing] = useState(false);
 const [showAnnotations, setShowAnnotations] = useState(false);
 const effectiveContent = content ||'';
 const lines = effectiveContent ? effectiveContent.split('\n') : [''];

 const handleReview = () => {
 setIsReviewing(true);
 setTimeout(() => {
 setIsReviewing(false);
 setShowAnnotations(true);
 }, 2000);
 };

 return (
 <div className="h-full flex flex-col bg-background">
 {/* Toolbar */}
 <div className="border-b border-border px-6 py-4 bg-background">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <icons.FileText className="w-5 h-5 text-muted-foreground" />
 <div>
 <h3 className="font-medium text-foreground">文书编辑器</h3>
 <p className="text-xs text-muted-foreground">律师函草稿 - 正在编辑</p>
 </div>
 </div>
 <div className="flex items-center gap-3">
 {showAnnotations && (
 <div className="flex items-center gap-2 px-3 py-1.5 bg-warning/10 rounded-xl border border-warning/20">
 <icons.AlertCircle className="w-4 h-4 text-warning" />
 <span className="text-sm text-warning font-medium">发现 {annotations.length} 个问题</span>
 </div>
 )}
 <button
 onClick={handleReview}
 disabled={isReviewing}
 className="px-4 py-2 bg-primary text-white rounded-xl hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2 text-sm font-medium shadow-sm active:scale-95"
 >
 <icons.Send className="w-4 h-4" />
 {isReviewing ?'审核中...' :'提交 AI 审核'}
 </button>
 </div>
 </div>
 </div>

 {/* Editor */}
 <div className="flex-1 overflow-y-auto p-6 bg-muted">
 <div className="max-w-4xl mx-auto">
 <div className="bg-background border border-border rounded-2xl overflow-hidden shadow-sm">
 <div className="flex">
 {/* Line Numbers */}
 <div className="bg-muted px-3 py-4 border-r border-border select-none">
 {lines.map((_, index) => (
 <div
 key={index}
 className="text-xs text-muted-foreground leading-relaxed h-6 flex items-center justify-end"
 >
 {index + 1}
 </div>
 ))}
 </div>

 {/* Content */}
 <div className="flex-1 px-6 py-4">
 <textarea
 value={effectiveContent}
 onChange={(e) => onContentChange(e.target.value)}
 placeholder="请输入或粘贴需要审阅的法律文书内容..."
 className="w-full min-h-[520px] resize-none bg-transparent text-foreground leading-6 outline-none placeholder:text-muted-foreground"
 spellCheck={false}
 />

 {showAnnotations && (
 <div className="mt-4 pt-4 border-t border-border flex flex-wrap gap-2">
 {annotations.map((annotation) => (
 <motion.button
 key={annotation.id}
 initial={{ scale: 0.9, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 onClick={() => onAnnotationClick(annotation)}
 className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-transform hover:scale-[1.02] ${
 annotation.type ==='error'
 ?'bg-destructive/10 text-destructive border border-destructive/20'
 : annotation.type ==='warning'
 ?'bg-warning/10 text-warning border border-warning/20'
 : annotation.type ==='suggestion'
 ?'bg-primary/10 text-primary border border-primary/20'
 :'bg-violet-50 text-violet-700 border border-violet-200'
 }`}
 >
 <span>第 {annotation.lineNumber} 行</span>
 <span>{annotation.message}</span>
 </motion.button>
 ))}
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 </div>

 {/* Status Bar */}
 <div className="border-t border-border px-6 py-2 bg-background flex items-center justify-between text-xs text-muted-foreground">
 <div className="flex items-center gap-4">
 <span>{lines.length} 行</span>
 <span>{effectiveContent.length} 字符</span>
 </div>
 {showAnnotations && (
 <div className="flex items-center gap-2">
 <icons.CheckCircle className="w-3 h-3 text-success" />
 <span className="text-success">AI 审核完成</span>
 </div>
 )}
 </div>
 </div>
 );
}
