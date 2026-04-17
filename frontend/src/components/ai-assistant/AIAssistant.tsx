import { useState, useEffect } from'react';
import { DocumentEditor } from'./DocumentEditor';
import { AnnotationPanel } from'./AnnotationPanel';
import { LegalKnowledgeBase } from'./LegalKnowledgeBase';
import { ProgressTracker } from'./ProgressTracker';
import { Resizable } from're-resizable';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';

export interface Annotation {
 id: string;
 lineNumber: number;
 type:'error' |'warning' |'suggestion' |'learn';
 message: string;
 reference?: string;
 detail?: string;
}

export function AIAssistant() {
 const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
 const [documentContent, setDocumentContent] = useState<string>('');
 const [editorWidth, setEditorWidth] = useState(60); // 百分比
 const [isMobile, setIsMobile] = useState(false);
 const [mobileTab, setMobileTab] = useState<'editor' |'annotation' |'knowledge'>('editor');
 const [showAnnotationSheet, setShowAnnotationSheet] = useState(false);

 // 检测移动端
 useEffect(() => {
 const checkMobile = () => {
 setIsMobile(window.innerWidth < 1024);
 };
 checkMobile();
 window.addEventListener('resize', checkMobile);
 return () => window.removeEventListener('resize', checkMobile);
 }, []);

 // 当选中批注时，在移动端自动打开底部面板
 useEffect(() => {
 if (isMobile && selectedAnnotation) {
 setShowAnnotationSheet(true);
 }
 }, [selectedAnnotation, isMobile]);

 // 移动端布局
 if (isMobile) {
 return (
 <div className="h-full flex flex-col bg-background">
 {/* Progress Tracker - 固定在顶部 */}
 <div className="border-b border-border">
 <ProgressTracker />
 </div>

 {/* Tab Navigation */}
 <div className="border-b border-border bg-background px-2 py-2 flex gap-2 overflow-x-auto">
 <button
 onClick={() => setMobileTab('editor')}
 className={`flex-1 min-w-[100px] px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2 whitespace-nowrap ${
 mobileTab ==='editor'
 ?'bg-primary text-primary-foreground shadow-sm'
 :'bg-muted text-foreground/80 active:bg-border'
 }`}
 >
 <icons.FileText className="w-4 h-4" />
 文档编辑
 </button>
 <button
 onClick={() => setMobileTab('annotation')}
 className={`flex-1 min-w-[100px] px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2 whitespace-nowrap ${
 mobileTab ==='annotation'
 ?'bg-primary text-primary-foreground shadow-sm'
 :'bg-muted text-foreground/80 active:bg-border'
 }`}
 >
 <icons.Lightbulb className="w-4 h-4" />
 智能批注
 </button>
 <button
 onClick={() => setMobileTab('knowledge')}
 className={`flex-1 min-w-[100px] px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center justify-center gap-2 whitespace-nowrap ${
 mobileTab ==='knowledge'
 ?'bg-primary text-primary-foreground shadow-sm'
 :'bg-muted text-foreground/80 active:bg-border'
 }`}
 >
 <icons.BookOpen className="w-4 h-4" />
 知识库
 </button>
 </div>

 {/* Content Area */}
 <div className="flex-1 overflow-hidden">
 {mobileTab ==='editor' && (
 <DocumentEditor
 content={documentContent}
 onContentChange={setDocumentContent}
 onAnnotationClick={setSelectedAnnotation}
 />
 )}
 {mobileTab ==='annotation' && (
 <div className="h-full overflow-y-auto">
 <AnnotationPanel
 selectedAnnotation={selectedAnnotation}
 onClose={() => setSelectedAnnotation(null)}
 />
 </div>
 )}
 {mobileTab ==='knowledge' && (
 <div className="h-full overflow-y-auto bg-muted">
 <LegalKnowledgeBase />
 </div>
 )}
 </div>

 {/* Annotation Detail Bottom Sheet */}
 <AnimatePresence>
 {showAnnotationSheet && selectedAnnotation && (
 <>
 {/* Backdrop */}
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 exit={{ opacity: 0 }}
 onClick={() => setShowAnnotationSheet(false)}
 className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40"
 />

 {/* Bottom Sheet */}
 <motion.div
 initial={{ y:'100%' }}
 animate={{ y: 0 }}
 exit={{ y:'100%' }}
 transition={{ type:'spring', damping: 30, stiffness: 300 }}
 className="fixed inset-x-0 bottom-0 z-50 bg-background rounded-t-3xl shadow-2xl max-h-[70vh] flex flex-col"
 >
 {/* Handle */}
 <div className="flex items-center justify-center py-3 border-b border-border">
 <div className="w-10 h-1 bg-border rounded-full" />
 </div>

 {/* Header */}
 <div className="px-4 py-3 border-b border-border flex items-center justify-between">
 <div className="flex items-center gap-2">
 <div className={`w-2 h-2 rounded-full ${
 selectedAnnotation.type ==='error' ?'bg-destructive' :
 selectedAnnotation.type ==='warning' ?'bg-warning' :
 selectedAnnotation.type ==='suggestion' ?'bg-primary' :
'bg-violet-500'
 }`} />
 <h3 className="font-medium text-foreground">
 {selectedAnnotation.type ==='error' ?'错误' :
 selectedAnnotation.type ==='warning' ?'警告' :
 selectedAnnotation.type ==='suggestion' ?'建议' :
'学习'}
 </h3>
 </div>
 <button
 onClick={() => setShowAnnotationSheet(false)}
 className="p-2 hover:bg-muted rounded-lg transition-colors"
 >
 <icons.X className="w-5 h-5 text-muted-foreground" />
 </button>
 </div>

 {/* Content */}
 <div className="flex-1 overflow-y-auto p-4">
 <p className="text-foreground font-medium mb-2">
 第 {selectedAnnotation.lineNumber} 行
 </p>
 <p className="text-sm text-foreground/80 mb-4">
 {selectedAnnotation.message}
 </p>
 {selectedAnnotation.detail && (
 <div className="bg-muted rounded-xl p-4 mb-3">
 <p className="text-xs font-medium text-muted-foreground mb-2">详细说明</p>
 <p className="text-sm text-foreground/80 leading-relaxed">
 {selectedAnnotation.detail}
 </p>
 </div>
 )}
 {selectedAnnotation.reference && (
 <div className="bg-primary/5 border border-primary/20 rounded-xl p-4">
 <p className="text-xs font-medium text-primary mb-2">法律依据</p>
 <p className="text-sm text-foreground">
 {selectedAnnotation.reference}
 </p>
 </div>
 )}
 </div>
 </motion.div>
 </>
 )}
 </AnimatePresence>
 </div>
 );
 }

 // 桌面端布局
 return (
 <div className="h-full flex">
 {/* Left: Document Editor (Resizable) */}
 <Resizable
 size={{ width: `${editorWidth}%`, height:'100%' }}
 onResizeStop={(e, direction, ref, d) => {
 const newWidth = editorWidth + (d.width / ref.parentElement!.offsetWidth) * 100;
 setEditorWidth(Math.min(Math.max(newWidth, 40), 70)); // 限制在40%-70%
 }}
 minWidth="40%"
 maxWidth="70%"
 enable={{
 top: false,
 right: true,
 bottom: false,
 left: false,
 topRight: false,
 bottomRight: false,
 bottomLeft: false,
 topLeft: false,
 }}
 handleStyles={{
 right: {
 width:'4px',
 right:'-2px',
 cursor:'col-resize',
 },
 }}
 handleClasses={{
 right:'hover:bg-primary transition-colors',
 }}
 className="border-r border-border flex flex-col"
 >
 <DocumentEditor
 content={documentContent}
 onContentChange={setDocumentContent}
 onAnnotationClick={setSelectedAnnotation}
 />
 </Resizable>

 {/* Right: Annotation & Knowledge */}
 <div className="flex-1 flex flex-col">
 {/* Top: Progress Tracker */}
 <div className="border-b border-border">
 <ProgressTracker />
 </div>

 {/* Middle: Annotation Panel */}
 <div className="flex-1 overflow-y-auto border-b border-border">
 <AnnotationPanel
 selectedAnnotation={selectedAnnotation}
 onClose={() => setSelectedAnnotation(null)}
 />
 </div>

 {/* Bottom: Knowledge Base */}
 <div className="h-64 overflow-y-auto bg-muted">
 <LegalKnowledgeBase />
 </div>
 </div>
 </div>
 );
}