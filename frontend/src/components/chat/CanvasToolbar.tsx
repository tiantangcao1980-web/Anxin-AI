/**
 * Canvas 顶部工具栏
 * 
 * 包含：标题 | 格式按钮 | 模式切换 | AI 优化 | 转发律师 | 发起签约 | 复制 | 下载
 */

import { memo } from'react';
import { icons } from'@/lib/icons';
import type { CanvasContent } from'@/lib/store';

interface CanvasToolbarProps {
 canvas: CanvasContent;
 onTitleChange: (title: string) => void;
 onModeChange: (mode: CanvasContent['type']) => void;
 onAIOptimize: () => void;
 onAcceptAll: () => void;
 onCopy: () => void;
 onDownload: () => void;
 onFormatAction?: (action: string) => void;
 hasSuggestions: boolean;
 onForwardToLawyer?: () => void;
 onInitiateSigning?: () => void;
 onSaveAsDocument?: () => void;
 isSaved?: boolean;
 isOptimizing?: boolean;
}

const modeOptions: { value: CanvasContent['type']; label: string; icon: React.ElementType }[] = [
 { value:'document', label:'文档', icon: icons.FileText },
 { value:'code', label:'代码', icon: icons.Code },
 { value:'table', label:'表格', icon: icons.Table },
];

export const CanvasToolbar = memo(function CanvasToolbar({
 canvas,
 onTitleChange,
 onModeChange,
 onAIOptimize,
 onAcceptAll,
 onCopy,
 onDownload,
 onFormatAction,
 hasSuggestions,
 onForwardToLawyer,
 onInitiateSigning,
 onSaveAsDocument,
 isSaved = true,
 isOptimizing = false,
}: CanvasToolbarProps) {
 return (
 <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-background">
 {/* 标题 */}
 <input
 value={canvas.title}
 onChange={(e) => onTitleChange(e.target.value)}
 className="text-sm font-medium text-foreground bg-transparent border-none outline-none flex-shrink-0 max-w-[200px] truncate focus:ring-0"
 placeholder="文档标题"
 />

 <div className="w-px h-5 bg-border mx-1" />

 {/* 格式按钮（仅 document 模式） */}
 {canvas.type ==='document' && onFormatAction && (
 <div className="flex items-center gap-0.5">
 <ToolButton icon={icons.Bold} onClick={() => onFormatAction('bold')} title="加粗" />
 <ToolButton icon={icons.Italic} onClick={() => onFormatAction('italic')} title="斜体" />
 <ToolButton icon={icons.List} onClick={() => onFormatAction('list')} title="列表" />
 </div>
 )}

 {/* 模式切换 */}
 <div className="relative group ml-auto">
 <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-muted-foreground bg-muted rounded-lg hover:bg-muted transition-colors border border-border">
 {modeOptions.find((m) => m.value === canvas.type)?.label ||'文档'}
 <icons.ChevronDown className="w-3 h-3" />
 </button>
 <div className="absolute right-0 top-full mt-1 bg-background border border-border rounded-lg shadow-lg py-1 min-w-[100px] hidden group-hover:block z-10">
 {modeOptions.map((mode) => {
 const Icon = mode.icon;
 return (
 <button
 key={mode.value}
 onClick={() => onModeChange(mode.value)}
 className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-muted transition-colors ${
 canvas.type === mode.value ?'text-primary font-medium' :'text-muted-foreground'
 }`}
 >
 <Icon className="w-3.5 h-3.5" />
 {mode.label}
 </button>
 );
 })}
 </div>
 </div>

 <div className="w-px h-5 bg-border" />

 {/* 操作按钮 */}
 <button
 onClick={onAIOptimize}
 disabled={isOptimizing}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-primary rounded-lg hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
 >
 {isOptimizing ? <icons.Loader2 className="w-3.5 h-3.5 animate-spin" /> : <icons.Wand2 className="w-3.5 h-3.5" />}
 {isOptimizing ?'AI 优化中...' :'AI 优化'}
 </button>

 {hasSuggestions && (
 <button
 onClick={onAcceptAll}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-success bg-success/10 rounded-lg hover:bg-success/20 transition-colors border border-success/20"
 >
 <icons.CheckCheck className="w-3.5 h-3.5" />
 接受全部
 </button>
 )}

 <div className="w-px h-5 bg-border" />

 {/* 转发律师 */}
 {onForwardToLawyer && (
 <button
 onClick={onForwardToLawyer}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary bg-primary/5 rounded-lg hover:bg-primary/10 transition-colors border border-primary/20"
 title="转发给律师审查"
 >
 <icons.Users className="w-3.5 h-3.5" />
 转发律师
 </button>
 )}

 {/* 发起签约 */}
 {onInitiateSigning && (
 <button
 onClick={onInitiateSigning}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-success bg-success/10 rounded-lg hover:bg-success/20 transition-colors border border-success/20"
 title="发起签约/盖章流程"
 >
 <icons.FileSignature className="w-3.5 h-3.5" />
 签约盖章
 </button>
 )}

 <div className="w-px h-5 bg-border" />

 {/* 保存按钮 */}
 {onSaveAsDocument && (
 <button
 onClick={onSaveAsDocument}
 className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-foreground bg-muted rounded-lg hover:bg-muted transition-colors border border-border"
 title="保存到文档库"
 >
 <icons.Save className="w-3.5 h-3.5" />
 保存
 </button>
 )}

 {/* 保存状态指示 */}
 <span className={`text-[10px] flex items-center gap-1 ${isSaved ?'text-success' :'text-warning'}`}>
 {isSaved ? <><icons.CheckCircle2 className="w-3 h-3" />已保存</> :'编辑中...'}
 </span>

 <ToolButton icon={icons.Copy} onClick={onCopy} title="复制" />
 <ToolButton icon={icons.Download} onClick={onDownload} title="下载" />
 </div>
 );
});

function ToolButton({
 icon: Icon,
 onClick,
 title,
}: {
 icon: React.ElementType;
 onClick: () => void;
 title: string;
}) {
 return (
 <button
 onClick={onClick}
 title={title}
 className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors"
 >
 <Icon className="w-4 h-4" />
 </button>
 );
}
