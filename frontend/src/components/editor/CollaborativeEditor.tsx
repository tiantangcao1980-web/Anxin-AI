/**
 * Professional Rich Text Editor Component
 *
 * Enhanced collaborative editor with TipTap for legal document editing
 * Features:
 * - Full rich text editing (font size, color, alignment, headings, lists, tables)
 * - Professional document toolbar (Word/WPS-like)
 * - Real-time collaboration support via Yjs
 * - Comments/annotations system
 * - AI-assisted writing
 * - Page-style layout for professional appearance
 * - Print support
 */

import { useState, useRef, useCallback, useMemo, useEffect } from'react';
import { useEditor, EditorContent, BubbleMenu } from'@tiptap/react';
import StarterKit from'@tiptap/starter-kit';
import Placeholder from'@tiptap/extension-placeholder';
import LinkExt from'@tiptap/extension-link';
import ImageExt from'@tiptap/extension-image';
import Table from'@tiptap/extension-table';
import TableRow from'@tiptap/extension-table-row';
import TableCell from'@tiptap/extension-table-cell';
import TableHeader from'@tiptap/extension-table-header';
import Underline from'@tiptap/extension-underline';
import TextAlign from'@tiptap/extension-text-align';
import Highlight from'@tiptap/extension-highlight';
import { TextStyle } from'@tiptap/extension-text-style';
import Color from'@tiptap/extension-color';
import Collaboration from'@tiptap/extension-collaboration';
import * as Y from'yjs';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { cardStyle, buttonStyle, heading, collaborationAccentColors, editorPalette } from'@/lib/design-tokens';
import { toast } from'sonner';
import { cn } from'@/lib/utils';
import { SlashCommandMenu, useSlashCommand } from'./SlashCommandExtension';

// ==================== Types ====================

export interface EditorUser {
 id: string;
 name: string;
 color: string;
 avatar?: string;
}

export interface EditorComment {
 id: string;
 userId: string;
 userName: string;
 content: string;
 position: { from: number; to: number };
 timestamp: Date;
 resolved: boolean;
}

export interface CollaborativeEditorProps {
 documentId: string;
 user: EditorUser;
 initialContent?: string;
 readOnly?: boolean;
 onChange?: (content: string, html: string) => void;
 onSave?: () => Promise<void>;
 showAIAssist?: boolean;
 onAIAssist?: (content: string) => Promise<string>;
 wsUrl?: string;
 onCommentAdd?: (comment: Omit<EditorComment,'id' |'timestamp'>) => void;
 onCommentResolve?: (commentId: string) => void;
 /** Hide outer toolbar & status bar (when parent provides them) */
 minimal?: boolean;
}

// ==================== Helper Functions ====================

function getUserColor(name: string): string {
 const colors = [
 ...collaborationAccentColors,
 editorPalette.text[4],
 editorPalette.text[8],
 editorPalette.text[10],
 ];
 let hash = 0;
 for (let i = 0; i < name.length; i++) {
 hash = name.charCodeAt(i) + ((hash << 5) - hash);
 }
 return colors[Math.abs(hash) % colors.length];
}

// ==================== Toolbar Components ====================

interface ToolbarButtonProps {
 onClick: () => void;
 active?: boolean;
 disabled?: boolean;
 children: React.ReactNode;
 title?: string;
}

function ToolbarButton({ onClick, active, disabled, children, title }: ToolbarButtonProps) {
 return (
 <button
 onClick={onClick}
 disabled={disabled}
 title={title}
 className={cn(
'p-1.5 rounded transition-[colors,transform] text-foreground/70',
'hover:bg-accent hover:text-foreground active:scale-95',
'disabled:opacity-40 disabled:cursor-not-allowed',
 active &&'bg-primary/10 text-primary font-semibold'
 )}
 >
 {children}
 </button>
 );
}

function ToolbarDivider() {
 return <div className="w-px h-6 bg-border mx-1" />;
}

// Font size select
function FontSizeSelect({ editor }: { editor: any }) {
 const sizes = ['12px','14px','16px','18px','20px','24px','28px','32px','36px'];
 return (
 <select
 className="h-7 px-1.5 text-xs border border-border rounded bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 cursor-pointer"
 title="字号"
 onChange={(e) => {
 if (e.target.value) {
 editor?.chain().focus().setMark('textStyle', { fontSize: e.target.value }).run();
 }
 }}
 defaultValue=""
 >
 <option value="" disabled>字号</option>
 {sizes.map(s => (
 <option key={s} value={s}>{parseInt(s)}</option>
 ))}
 </select>
 );
}

// Color picker
function ColorPicker({ editor, type }: { editor: any; type:'text' |'highlight' }) {
 const colors = editorPalette.text;
 const [open, setOpen] = useState(false);

 return (
 <div className="relative">
 <ToolbarButton
 onClick={() => setOpen(!open)}
 title={type ==='text' ?'字体颜色' :'高亮颜色'}
 >
 <div className="flex flex-col items-center">
 {type ==='text' ? (
 <span className="text-xs font-semibold leading-none">A</span>
 ) : (
 <icons.Highlighter className="w-3.5 h-3.5" />
 )}
 <div className="w-4 h-0.5 rounded-full mt-0.5" style={{
 backgroundColor: type ==='text' ? (editor?.getAttributes('textStyle')?.color || editorPalette.printText) : editorPalette.highlight
 }} />
 </div>
 </ToolbarButton>
 {open && (
 <>
 <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
 <div className="absolute top-full left-0 mt-1 p-2 bg-popover border border-border rounded-lg shadow-lg z-50 grid grid-cols-4 gap-1">
 {colors.map(color => (
 <button
 key={color}
 className="w-6 h-6 rounded border border-border hover:scale-110 transition-transform"
 style={{ backgroundColor: color }}
 onClick={() => {
 if (type ==='text') {
 editor?.chain().focus().setColor(color).run();
 } else {
 editor?.chain().focus().toggleHighlight({ color }).run();
 }
 setOpen(false);
 }}
 />
 ))}
 <button
 className="w-6 h-6 rounded border border-border text-[10px] hover:bg-accent"
 onClick={() => {
 if (type ==='text') {
 editor?.chain().focus().unsetColor().run();
 } else {
 editor?.chain().focus().unsetHighlight().run();
 }
 setOpen(false);
 }}
 title="清除"
 >
 <icons.X className="w-3 h-3 mx-auto" />
 </button>
 </div>
 </>
 )}
 </div>
 );
}

// ==================== Main Editor Component ====================

export function CollaborativeEditor({
 documentId,
 user,
 initialContent,
 readOnly = false,
 onChange,
 onSave,
 showAIAssist = true,
 onAIAssist,
 wsUrl ='ws://localhost:1234',
 onCommentAdd,
 onCommentResolve,
 minimal = false,
}: CollaborativeEditorProps) {
 const [ydoc] = useState(() => new Y.Doc());
 const [connectedUsers, setConnectedUsers] = useState<EditorUser[]>([user]);
 const [comments, setComments] = useState<EditorComment[]>([]);
 const [isSaving, setIsSaving] = useState(false);
 const [isAIAssisting, setIsAIAssisting] = useState(false);
 const [showComments, setShowComments] = useState(false);
 const [lastSaved, setLastSaved] = useState<Date | null>(null);
 const [zoomLevel, setZoomLevel] = useState(100);
 const saveTimeoutRef = useRef<NodeJS.Timeout>();


 // Get Y.js fragment
 const yXmlFragment = useMemo(() => ydoc.getXmlFragment('prosemirror'), [ydoc]);

 // Initialize editor with enhanced extensions
 const editor = useEditor({
 extensions: [
 StarterKit.configure({
 heading: { levels: [1, 2, 3] },
 history: false,
 }),
 Placeholder.configure({
 placeholder:'开始输入法律文书内容...',
 }),
 LinkExt.configure({
 openOnClick: false,
 HTMLAttributes: {
 class:'text-primary underline hover:text-primary/80',
 },
 }),
 ImageExt.configure({
 HTMLAttributes: {
 class:'max-w-full h-auto rounded-lg',
 },
 }),
 Table.configure({
 resizable: true,
 HTMLAttributes: {
 class:'border-collapse w-full',
 },
 }),
 TableRow,
 TableCell,
 TableHeader,
 Underline,
 TextAlign.configure({
 types: ['heading','paragraph'],
 }),
 TextStyle,
 Color,
 Highlight.configure({
 multicolor: true,
 }),
 Collaboration.configure({
 document: ydoc,
 }),
 ],
 content: initialContent,
 editable: !readOnly,
 onUpdate: ({ editor }) => {
 const html = editor.getHTML();
 const text = editor.getText();
 onChange?.(text, html);

 // Auto save
 if (saveTimeoutRef.current) {
 clearTimeout(saveTimeoutRef.current);
 }
 saveTimeoutRef.current = setTimeout(() => {
 handleSave();
 }, 3000);
 },
 });

 // Load initial content when editor is ready
 useEffect(() => {
 if (editor && initialContent && editor.isEmpty) {
 editor.commands.setContent(initialContent);
 }
 }, [editor, initialContent]);

 // Keyboard shortcuts
 useEffect(() => {
 const handleKeyDown = (e: KeyboardEvent) => {
 if ((e.metaKey || e.ctrlKey) && e.key ==='s') {
 e.preventDefault();
 handleSave();
 }
 if ((e.metaKey || e.ctrlKey) && e.key ==='p') {
 e.preventDefault();
 handlePrint();
 }
 };
 window.addEventListener('keydown', handleKeyDown);
 return () => window.removeEventListener('keydown', handleKeyDown);
 }, [editor]);

 // Save document
 const handleSave = async () => {
 if (!editor || isSaving) return;
 setIsSaving(true);
 try {
 await onSave?.();
 setLastSaved(new Date());
 toast.success('文档已保存');
 } catch (error) {
 toast.error('保存失败');
 } finally {
 setIsSaving(false);
 }
 };

 // AI Assist
 const handleAIAssist = async () => {
 if (!editor || isAIAssisting || !onAIAssist) return;

 const content = editor.getText();
 if (content.length < 10) {
 toast.error('内容过短，无法优化');
 return;
 }

 setIsAIAssisting(true);
 try {
 const optimized = await onAIAssist(content);
 editor.commands.setContent(optimized);
 toast.success('AI优化完成');
 } catch (error) {
 toast.error('AI优化失败');
 } finally {
 setIsAIAssisting(false);
 }
 };

 // Add comment
 const handleAddComment = () => {
 if (!editor) return;

 const { from, to } = editor.state.selection;
 const selectedText = editor.state.doc.textBetween(from, to);

 if (!selectedText) {
 toast.error('请先选中文字再添加批注');
 return;
 }

 const comment = window.prompt('输入批注内容：');
 if (!comment) return;

 const newComment: EditorComment = {
 id: `comment-${Date.now()}`,
 userId: user.id,
 userName: user.name,
 content: comment,
 position: { from, to },
 timestamp: new Date(),
 resolved: false,
 };

 setComments([...comments, newComment]);
 onCommentAdd?.(newComment);
 toast.success('批注已添加');
 };

 // Insert table
 const handleInsertTable = () => {
 editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
 };

 // Insert horizontal rule
 const handleInsertHR = () => {
 editor?.chain().focus().setHorizontalRule().run();
 };

 // Print document
 const handlePrint = () => {
 if (!editor) return;
 const html = editor.getHTML();
 const printWindow = window.open('','_blank');
 if (printWindow) {
 printWindow.document.write(`
 <!DOCTYPE html>
 <html>
 <head>
 <title>打印文档</title>
 <style>
 @page { margin: 2.54cm; size: A4; }
 body {
 font-family:"SimSun","宋体", serif;
 font-size: 14px;
 line-height: 1.8;
 color: ${editorPalette.printText};
 }
 h1 { font-size: 22px; text-align: center; font-weight: bold; margin-bottom: 20px; }
 h2 { font-size: 16px; font-weight: bold; margin: 16px 0 8px; }
 h3 { font-size: 15px; font-weight: bold; margin: 12px 0 6px; }
 p { text-indent: 2em; margin: 6px 0; }
 table { width: 100%; border-collapse: collapse; margin: 10px 0; }
 td, th { border: 1px solid ${editorPalette.printBorder}; padding: 6px 8px; }
 th { background-color: ${editorPalette.printHeaderBg}; font-weight: bold; }
 </style>
 </head>
 <body>${html}</body>
 </html>
 `);
 printWindow.document.close();
 printWindow.print();
 }
 };

 // Download as HTML
 const handleDownload = () => {
 if (!editor) return;
 const html = editor.getHTML();
 const fullHtml = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>${documentId}</title>
<style>
 body { font-family:"SimSun","宋体", serif; font-size: 14px; line-height: 1.8; max-width: 800px; margin: 40px auto; padding: 0 20px; }
 h1 { text-align: center; font-size: 22px; }
 h2 { font-size: 16px; margin-top: 20px; }
 table { width: 100%; border-collapse: collapse; }
 td, th { border: 1px solid ${editorPalette.printBorder}; padding: 6px 8px; }
</style>
</head>
<body>${html}</body>
</html>`;
 const blob = new Blob([fullHtml], { type:'text/html;charset=utf-8' });
 const url = URL.createObjectURL(blob);
 const a = document.createElement('a');
 a.href = url;
 a.download = `${documentId}.html`;
 a.click();
 URL.revokeObjectURL(url);
 toast.success('文档已下载');
 };

 // Slash command menu
 const slashCmd = useSlashCommand(editor);

 const characterCount = editor ? editor.getText().length : 0;
 const wordCount = editor ? editor.getText().replace(/\s/g,'').length : 0;

 return (
 <div className="flex flex-col h-full bg-background">
 {!minimal && (
 <>
 {/* ===== Professional Toolbar ===== */}
 <div className="border-b border-border bg-muted/50">
 {/* Row 1: Main actions */}
 <div className="flex items-center px-2 py-1 gap-1 border-b border-border/50">
 <div className="flex items-center gap-1">
 <ToolbarButton
 onClick={() => editor?.chain().focus().undo().run()}
 disabled={!editor?.can().undo()}
 title="撤销 (Ctrl+Z)"
 >
 <icons.Undo className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().redo().run()}
 disabled={!editor?.can().redo()}
 title="重做 (Ctrl+Y)"
 >
 <icons.Redo className="w-4 h-4" />
 </ToolbarButton>
 </div>

 <ToolbarDivider />

 {/* Heading select */}
 <select
 className="h-7 px-1.5 text-xs border border-border rounded bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 cursor-pointer min-w-[80px]"
 value={
 editor?.isActive('heading', { level: 1 }) ?'h1' :
 editor?.isActive('heading', { level: 2 }) ?'h2' :
 editor?.isActive('heading', { level: 3 }) ?'h3' :'p'
 }
 onChange={(e) => {
 const val = e.target.value;
 if (val ==='p') editor?.chain().focus().setParagraph().run();
 else if (val ==='h1') editor?.chain().focus().toggleHeading({ level: 1 }).run();
 else if (val ==='h2') editor?.chain().focus().toggleHeading({ level: 2 }).run();
 else if (val ==='h3') editor?.chain().focus().toggleHeading({ level: 3 }).run();
 }}
 >
 <option value="p">正文</option>
 <option value="h1">标题 1</option>
 <option value="h2">标题 2</option>
 <option value="h3">标题 3</option>
 </select>

 <ToolbarDivider />

 {/* Text formatting */}
 <div className="flex items-center gap-0.5">
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleBold().run()}
 active={editor?.isActive('bold')}
 title="加粗 (Ctrl+B)"
 >
 <icons.Bold className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleItalic().run()}
 active={editor?.isActive('italic')}
 title="斜体 (Ctrl+I)"
 >
 <icons.Italic className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleUnderline().run()}
 active={editor?.isActive('underline')}
 title="下划线 (Ctrl+U)"
 >
 <icons.Underline className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleStrike().run()}
 active={editor?.isActive('strike')}
 title="删除线"
 >
 <icons.Strikethrough className="w-4 h-4" />
 </ToolbarButton>
 </div>

 <ToolbarDivider />

 {/* Color */}
 <div className="flex items-center gap-0.5">
 <ColorPicker editor={editor} type="text" />
 <ColorPicker editor={editor} type="highlight" />
 </div>

 <ToolbarDivider />

 {/* Alignment */}
 <div className="flex items-center gap-0.5">
 <ToolbarButton
 onClick={() => editor?.chain().focus().setTextAlign('left').run()}
 active={editor?.isActive({ textAlign:'left' })}
 title="左对齐"
 >
 <icons.AlignLeft className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().setTextAlign('center').run()}
 active={editor?.isActive({ textAlign:'center' })}
 title="居中对齐"
 >
 <icons.AlignCenter className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().setTextAlign('right').run()}
 active={editor?.isActive({ textAlign:'right' })}
 title="右对齐"
 >
 <icons.AlignRight className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().setTextAlign('justify').run()}
 active={editor?.isActive({ textAlign:'justify' })}
 title="两端对齐"
 >
 <icons.AlignJustify className="w-4 h-4" />
 </ToolbarButton>
 </div>

 <ToolbarDivider />

 {/* Lists */}
 <div className="flex items-center gap-0.5">
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleBulletList().run()}
 active={editor?.isActive('bulletList')}
 title="无序列表"
 >
 <icons.List className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleOrderedList().run()}
 active={editor?.isActive('orderedList')}
 title="有序列表"
 >
 <icons.ListOrdered className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor?.chain().focus().toggleBlockquote().run()}
 active={editor?.isActive('blockquote')}
 title="引用"
 >
 <icons.Quote className="w-4 h-4" />
 </ToolbarButton>
 </div>

 <ToolbarDivider />

 {/* Insert */}
 <div className="flex items-center gap-0.5">
 <ToolbarButton
 onClick={handleInsertTable}
 title="插入表格"
 >
 <icons.Table className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={handleInsertHR}
 title="插入分割线"
 >
 <icons.HorizontalRule className="w-4 h-4" />
 </ToolbarButton>
 </div>

 {/* Right actions */}
 <div className="flex items-center gap-1 ml-auto">
 {connectedUsers.length > 0 && (
 <div className="flex items-center gap-1 px-2 py-0.5 bg-background rounded-md border border-border">
 <icons.Users className="w-3.5 h-3.5 text-muted-foreground" />
 <div className="flex -space-x-1.5">
 {connectedUsers.slice(0, 3).map((u) => (
 <div
 key={u.id}
 className="w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-medium border-2 border-background"
 style={{ backgroundColor: u.color }}
 title={u.name}
 >
 {u.name.charAt(0)}
 </div>
 ))}
 {connectedUsers.length > 3 && (
 <div className="w-5 h-5 rounded-full flex items-center justify-center bg-muted text-[10px] font-medium border-2 border-background text-muted-foreground">
 +{connectedUsers.length - 3}
 </div>
 )}
 </div>
 </div>
 )}
 {onAIAssist && !readOnly && (
 <ToolbarButton
 onClick={handleAIAssist}
 disabled={isAIAssisting}
 title="AI 智能优化"
 >
 <icons.Sparkles className={cn('w-4 h-4', isAIAssisting &&'animate-spin')} />
 </ToolbarButton>
 )}
 <ToolbarButton onClick={handlePrint} title="打印 (Ctrl+P)">
 <icons.Printer className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton onClick={handleDownload} title="下载">
 <icons.Download className="w-4 h-4" />
 </ToolbarButton>
 </div>
 </div>
 </div>

 {/* Status bar */}
 <div className="flex items-center justify-between px-3 py-1 bg-muted/30 border-b border-border text-[11px] text-muted-foreground">
 <div className="flex items-center gap-3">
 <span>{wordCount} 字</span>
 <span>{characterCount} 字符</span>
 {lastSaved && (
 <span className="flex items-center gap-1">
 <icons.Clock className="w-3 h-3" />
 最后保存 {lastSaved.toLocaleTimeString('zh-CN', { hour:'2-digit', minute:'2-digit' })}
 </span>
 )}
 {isSaving && <span className="text-primary animate-pulse">保存中...</span>}
 </div>
 <div className="flex items-center gap-2">
 {/* Zoom */}
 <div className="flex items-center gap-1">
 <button
 onClick={() => setZoomLevel(Math.max(50, zoomLevel - 10))}
 className="hover:text-foreground transition-colors"
 title="缩小"
 >
 <icons.Minus className="w-3 h-3" />
 </button>
 <span className="min-w-[36px] text-center">{zoomLevel}%</span>
 <button
 onClick={() => setZoomLevel(Math.min(200, zoomLevel + 10))}
 className="hover:text-foreground transition-colors"
 title="放大"
 >
 <icons.Plus className="w-3 h-3" />
 </button>
 </div>
 <ToolbarDivider />
 {!readOnly && (
 <>
 <button
 onClick={() => setShowComments(!showComments)}
 className={cn(
'flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-accent transition-colors',
 showComments &&'bg-accent text-foreground'
 )}
 title="批注"
 >
 <icons.MessageSquare className="w-3 h-3" />
 <span>批注</span>
 {comments.filter(c => !c.resolved).length > 0 && (
 <span className="bg-primary text-primary-foreground rounded-full px-1 text-[9px] min-w-[14px] text-center">
 {comments.filter(c => !c.resolved).length}
 </span>
 )}
 </button>
 <button
 onClick={handleSave}
 disabled={isSaving}
 className="flex items-center gap-1 px-2 py-0.5 bg-primary text-primary-foreground rounded text-xs hover:bg-primary/90 disabled:opacity-50 transition-colors"
 >
 <icons.Save className="w-3 h-3" />
 保存
 </button>
 </>
 )}
 </div>
 </div>
 </>
 )}

 {/* ===== Editor Area - Page Layout ===== */}
 <div className="flex-1 flex overflow-hidden bg-muted/20">
 <div className={cn('flex-1 overflow-auto', showComments &&'pr-0')}>
 <div
 className="mx-auto my-6"
 style={{
 transform: `scale(${zoomLevel / 100})`,
 transformOrigin:'top center',
 }}
 >
 {/* A4 Page simulation */}
 <div className={cn(
 minimal ?'p-4' :'bg-background shadow-lg rounded-sm border border-border/50',
 !minimal &&'w-[210mm] min-h-[297mm] mx-auto py-[2.54cm] px-[3.17cm]'
 )}>
 <AnimatePresence>
 {!editor && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 exit={{ opacity: 0 }}
 className="flex items-center justify-center h-full"
 >
 <div className="text-center text-muted-foreground">
 <icons.FileText className="w-12 h-12 mx-auto mb-4" />
 <p>正在加载编辑器...</p>
 </div>
 </motion.div>
 )}
 </AnimatePresence>

 {editor && (
 <EditorContent
 editor={editor}
 className={cn(
'min-h-full focus:outline-none',
'prose prose-sm max-w-none',
 // Professional document styling
'[&_.ProseMirror]:min-h-[250mm] [&_.ProseMirror]:outline-none',
'[&_.ProseMirror_h1]:text-center [&_.ProseMirror_h1]:text-xl [&_.ProseMirror_h1]:font-semibold [&_.ProseMirror_h1]:mb-6',
'[&_.ProseMirror_h2]:text-base [&_.ProseMirror_h2]:font-semibold [&_.ProseMirror_h2]:mt-6 [&_.ProseMirror_h2]:mb-3',
'[&_.ProseMirror_h3]:text-sm [&_.ProseMirror_h3]:font-semibold [&_.ProseMirror_h3]:mt-4 [&_.ProseMirror_h3]:mb-2',
'[&_.ProseMirror_p]:leading-relaxed [&_.ProseMirror_p]:mb-2',
'[&_.ProseMirror_table]:border-collapse [&_.ProseMirror_table]:w-full [&_.ProseMirror_table]:my-4',
'[&_.ProseMirror_td]:border [&_.ProseMirror_td]:border-border [&_.ProseMirror_td]:p-2',
'[&_.ProseMirror_th]:border [&_.ProseMirror_th]:border-border [&_.ProseMirror_th]:p-2 [&_.ProseMirror_th]:bg-muted [&_.ProseMirror_th]:font-semibold',
'[&_.ProseMirror_blockquote]:border-l-4 [&_.ProseMirror_blockquote]:border-primary/30 [&_.ProseMirror_blockquote]:pl-4 [&_.ProseMirror_blockquote]:italic',
'[&_.ProseMirror_hr]:border-border [&_.ProseMirror_hr]:my-6',
 )}
 />
 )}
 </div>
 </div>
 </div>

 {/* ===== Comments Sidebar ===== */}
 <AnimatePresence>
 {showComments && (
 <motion.div
 initial={{ width: 0, opacity: 0 }}
 animate={{ width: 320, opacity: 1 }}
 exit={{ width: 0, opacity: 0 }}
 transition={{ type:'spring', damping: 30, stiffness: 300 }}
 className="border-l border-border bg-background overflow-hidden flex-shrink-0"
 >
 <div className="w-80 h-full overflow-y-auto">
 <div className="p-4">
 <div className="flex items-center justify-between mb-4">
 <h3 className="font-semibold text-sm text-foreground">批注</h3>
 <div className="flex items-center gap-1">
 {!readOnly && (
 <button
 onClick={handleAddComment}
 className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
 >
 <icons.Plus className="w-3 h-3" />
 添加批注
 </button>
 )}
 </div>
 </div>

 {comments.length === 0 ? (
 <div className="text-center py-12">
 <icons.MessageSquare className="w-10 h-10 mx-auto text-muted-foreground/30 mb-3" />
 <p className="text-sm text-muted-foreground">暂无批注</p>
 <p className="text-xs text-muted-foreground mt-1">选中文字后点击"添加批注"</p>
 </div>
 ) : (
 <div className="space-y-3">
 {comments.map((comment) => (
 <div
 key={comment.id}
 className={cn(
'p-3 rounded-lg border transition-colors',
 comment.resolved
 ?'bg-muted/50 border-border opacity-60'
 :'bg-warning/10 border-warning/20'
 )}
 >
 <div className="flex items-start justify-between mb-1.5">
 <div className="flex items-center gap-1.5">
 <div
 className="w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-medium"
 style={{ backgroundColor: getUserColor(comment.userName) }}
 >
 {comment.userName.charAt(0)}
 </div>
 <span className="font-medium text-xs text-foreground">{comment.userName}</span>
 </div>
 <span className="text-[10px] text-muted-foreground">
 {new Date(comment.timestamp).toLocaleString('zh-CN', { month:'numeric', day:'numeric', hour:'2-digit', minute:'2-digit' })}
 </span>
 </div>
 <p className="text-sm text-foreground/80 mb-2">{comment.content}</p>
 {!comment.resolved && user.id === comment.userId && onCommentResolve && (
 <button
 onClick={() => {
 onCommentResolve(comment.id);
 setComments(comments.map((c) =>
 c.id === comment.id ? { ...c, resolved: true } : c
 ));
 }}
 className="text-xs text-success hover:text-success flex items-center gap-1"
 >
 <icons.Check className="w-3 h-3" />
 标记为已解决
 </button>
 )}
 </div>
 ))}
 </div>
 )}
 </div>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>

 {/* ===== Slash Command Menu ===== */}
 {!readOnly && (
 <SlashCommandMenu
 editor={editor}
 isOpen={slashCmd.isOpen}
 onClose={slashCmd.close}
 position={slashCmd.position}
 query={slashCmd.query}
 />
 )}
 </div>
 );
}

// ==================== Simple Editor (No Collaboration) ====================

export interface SimpleEditorProps {
 content: string;
 onChange: (content: string) => void;
 placeholder?: string;
 readOnly?: boolean;
 onSave?: () => void;
}

export function SimpleEditor({
 content,
 onChange,
 placeholder ='开始输入内容...',
 readOnly = false,
 onSave,
}: SimpleEditorProps) {
 const editor = useEditor({
 extensions: [
 StarterKit.configure({
 heading: { levels: [1, 2, 3] },
 }),
 Placeholder.configure({
 placeholder,
 }),
 LinkExt.configure({
 openOnClick: false,
 }),
 Underline,
 TextAlign.configure({
 types: ['heading','paragraph'],
 }),
 TextStyle,
 Color,
 ],
 content,
 editable: !readOnly,
 onUpdate: ({ editor }) => {
 onChange(editor.getHTML());
 },
 });

 if (!editor) {
 return (
 <div className="flex items-center justify-center h-64 text-muted-foreground">
 正在加载编辑器...
 </div>
 );
 }

 return (
 <div className={`${cardStyle.base} overflow-hidden`}>
 {/* Toolbar */}
 {!readOnly && (
 <div className="border-b border-border p-1.5 flex items-center gap-0.5 bg-muted/50 flex-wrap">
 <ToolbarButton
 onClick={() => editor.chain().focus().toggleBold().run()}
 active={editor.isActive('bold')}
 title="加粗"
 >
 <icons.Bold className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor.chain().focus().toggleItalic().run()}
 active={editor.isActive('italic')}
 title="斜体"
 >
 <icons.Italic className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor.chain().focus().toggleUnderline().run()}
 active={editor.isActive('underline')}
 title="下划线"
 >
 <icons.Underline className="w-4 h-4" />
 </ToolbarButton>

 <ToolbarDivider />

 <ToolbarButton
 onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
 active={editor.isActive('heading', { level: 1 })}
 title="标题 1"
 >
 <icons.Heading1 className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
 active={editor.isActive('heading', { level: 2 })}
 title="标题 2"
 >
 <icons.Heading2 className="w-4 h-4" />
 </ToolbarButton>

 <ToolbarDivider />

 <ToolbarButton
 onClick={() => editor.chain().focus().toggleBulletList().run()}
 active={editor.isActive('bulletList')}
 title="无序列表"
 >
 <icons.List className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor.chain().focus().toggleOrderedList().run()}
 active={editor.isActive('orderedList')}
 title="有序列表"
 >
 <icons.ListOrdered className="w-4 h-4" />
 </ToolbarButton>

 <ToolbarDivider />

 <ToolbarButton
 onClick={() => editor.chain().focus().setTextAlign('left').run()}
 active={editor.isActive({ textAlign:'left' })}
 title="左对齐"
 >
 <icons.AlignLeft className="w-4 h-4" />
 </ToolbarButton>
 <ToolbarButton
 onClick={() => editor.chain().focus().setTextAlign('center').run()}
 active={editor.isActive({ textAlign:'center' })}
 title="居中"
 >
 <icons.AlignCenter className="w-4 h-4" />
 </ToolbarButton>

 {onSave && (
 <>
 <div className="flex-1" />
 <button
 onClick={onSave}
 className="flex items-center gap-1 px-3 py-1 bg-primary text-primary-foreground rounded text-xs hover:bg-primary/90 transition-colors"
 >
 <icons.Save className="w-3 h-3" />
 保存
 </button>
 </>
 )}
 </div>
 )}

 {/* Editor */}
 <EditorContent
 editor={editor}
 className="prose max-w-none p-4 min-h-[200px]"
 />
 </div>
 );
}
