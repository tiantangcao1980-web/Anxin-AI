/**
 * Canvas 画布编辑器 — v2 集成协作富文本编辑器
 *
 * 功能升级：
 * - 集成 TipTap 富文本编辑器
 * - 实时协作编辑（基于 Yjs）
 * - AI 行内建议与优化
 * - 律师批注系统
 * - 双向 AI 交互
 * - 版本历史
 */

import { useState, useRef, useCallback, memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { CollaborativeEditor, SimpleEditor, type EditorUser } from '@/components/editor';
import { InlineSuggestion } from './InlineSuggestion';
import { useChatStore } from '@/lib/store';
import type { CanvasContent, CanvasSuggestion } from '@/lib/store';
import { chatApi } from '@/lib/api';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';

/**
 * 将 Markdown 文本转为 HTML（覆盖法律文书常用格式）
 * 用于富文本编辑器初始化和文档导出
 */
function markdownToHtml(md: string): string {
  if (!md) return '';

  let html = md;

  // 1. 转义 HTML 特殊字符
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // 2. 标题 — 必须在行首，支持 h1-h4
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // 3. 粗体 & 斜体（先处理 *** 再处理 ** 和 *）
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 4. 分隔线
  html = html.replace(/^---+$/gm, '<hr/>');

  // 5. 有序列表（连续的 "1. xxx" 行）
  html = html.replace(/(^(?:\d+\.\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map(line => {
      const content = line.replace(/^\d+\.\s+/, '');
      return `<li>${content}</li>`;
    }).join('');
    return `<ol>${items}</ol>\n`;
  });

  // 6. 无序列表（连续的 "- xxx" 行）
  html = html.replace(/(^(?:[-*]\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map(line => {
      const content = line.replace(/^[-*]\s+/, '');
      return `<li>${content}</li>`;
    }).join('');
    return `<ul>${items}</ul>\n`;
  });

  // 7. 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 8. 段落 — 连续的非空行组合为 <p>，空行分隔段落
  const lines = html.split('\n');
  const result: string[] = [];
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      const text = paragraph.join('<br/>');
      // 如果段落内容已经是块级元素则不包裹 <p>
      if (/^<(h[1-4]|ul|ol|li|hr|blockquote|div|table|pre)/.test(text)) {
        result.push(text);
      } else {
        result.push(`<p>${text}</p>`);
      }
      paragraph = [];
    }
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === '') {
      flushParagraph();
    } else if (/^<(h[1-4]|ul|ol|hr|blockquote|div|table|pre)/.test(trimmed)) {
      flushParagraph();
      result.push(trimmed);
    } else {
      paragraph.push(trimmed);
    }
  }
  flushParagraph();

  return result.join('\n');
}

/**
 * 检测内容是否包含 Markdown 标记
 */
function isMarkdownContent(content: string): boolean {
  // 检测常见 Markdown 标记
  return /^#{1,4}\s|^\d+\.\s|\*\*|^[-*]\s/m.test(content);
}

interface CanvasEditorProps {
  canvas: CanvasContent | null;
  onContentChange: (content: string) => void;
  onTitleChange: (title: string) => void;
  onModeChange: (mode: CanvasContent['type']) => void;
  onAIOptimize: () => void;
  onSuggestionAction: (id: string, action: 'accept' | 'reject') => void;
  onForwardToLawyer?: () => void;
  onInitiateSigning?: () => void;
  onSaveAsDocument?: () => void;
  /** 文档快捷操作（生成摘要、翻译全文、风险检查等） */
  onDocumentAction?: (actionId: string, payload?: { content?: string }) => void;
  /** 保存到文档库 */
  onSaveToList?: () => void;
  /** 关闭文档 */
  onCloseDocument?: () => void;
  isSaved?: boolean;
  isProcessing?: boolean;
  isOptimizing?: boolean;
  /** 当前用户ID */
  userId?: string;
  /** 当前对话ID（用于协作文档识别） */
  conversationId?: string;
}

export const CanvasEditor = memo(function CanvasEditor({
  canvas,
  onContentChange,
  onTitleChange,
  onModeChange,
  onAIOptimize,
  onSuggestionAction,
  onForwardToLawyer,
  onInitiateSigning,
  onSaveAsDocument,
  onDocumentAction,
  onSaveToList,
  onCloseDocument,
  isSaved = true,
  isProcessing = false,
  isOptimizing = false,
  userId = 'user-1',
  conversationId,
}: CanvasEditorProps) {
  const [showPreview, setShowPreview] = useState(true);
  const [editorMode, setEditorMode] = useState<'rich' | 'markdown'>('rich');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [versions, setVersions] = useState<Array<{ id: string; time: Date; content: string }>>([]);

  // 当前用户信息
  const currentUser: EditorUser = {
    id: userId,
    name: '当前用户',
    color: '#3B82F6',
  };

  // 保存版本历史
  const saveVersion = useCallback((content: string) => {
    const newVersion = {
      id: `v-${Date.now()}`,
      time: new Date(),
      content,
    };
    setVersions((prev) => [...prev.slice(-9), newVersion]); // 保留最近10个版本
  }, []);

  // 恢复版本
  const restoreVersion = useCallback((versionId: string) => {
    const version = versions.find((v) => v.id === versionId);
    if (version && canvas) {
      onContentChange(version.content);
      toast.success('版本已恢复');
      setShowHistory(false);
    }
  }, [versions, canvas, onContentChange]);

  // 处理内容变化
  const handleContentChange = useCallback((content: string) => {
    onContentChange(content);
    // 节流保存版本
    const timeoutId = setTimeout(() => {
      saveVersion(content);
    }, 5000);
    return () => clearTimeout(timeoutId);
  }, [onContentChange, saveVersion]);

  // AI 辅助
  const handleAIAssist = async (content: string): Promise<string> => {
    try {
      const response = await fetch('/api/v1/chat/ai-optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      const data = await response.json();
      return data.optimized || content;
    } catch (error) {
      console.error('AI 优化失败:', error);
      throw error;
    }
  };

  // 下载菜单控制
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);

  /**
   * 将 Markdown/HTML 内容转换为格式化 HTML 文档（用于 docx/pdf 导出）
   */
  const buildHtmlDocument = useCallback(() => {
    if (!canvas) return '';
    const title = canvas.title || '文档';
    // 使用统一的 Markdown → HTML 转换
    const body = markdownToHtml(canvas.content);

    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>${title}</title>
<style>
  body { font-family: "SimSun", "宋体", serif; font-size: 14px; line-height: 1.8; padding: 40px; max-width: 800px; margin: 0 auto; color: #333; }
  h1 { font-size: 22px; text-align: center; margin-bottom: 24px; font-weight: bold; }
  h2 { font-size: 18px; margin-top: 24px; margin-bottom: 12px; font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 6px; }
  h3 { font-size: 16px; margin-top: 18px; margin-bottom: 8px; font-weight: bold; }
  h4 { font-size: 14px; margin-top: 14px; margin-bottom: 6px; font-weight: bold; }
  p { margin: 8px 0; text-indent: 2em; }
  ul, ol { padding-left: 2em; margin: 8px 0; }
  li { margin: 4px 0; }
  hr { border: none; border-top: 1px solid #ddd; margin: 16px 0; }
  strong { font-weight: bold; }
  em { font-style: italic; }
  code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  td, th { border: 1px solid #333; padding: 6px 10px; }
</style></head><body>${body}</body></html>`;
  }, [canvas]);

  // 下载为 DOCX（基于 HTML 转换，兼容 Word 打开）
  const handleDownloadDocx = useCallback(() => {
    if (!canvas) return;
    const html = buildHtmlDocument();
    const blob = new Blob(
      ['\ufeff', html],
      { type: 'application/msword;charset=utf-8' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${canvas.title || '文档'}.doc`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadMenu(false);
    toast.success('DOCX 文件已下载');
  }, [canvas, buildHtmlDocument]);

  // 下载为 PDF（使用浏览器打印功能）
  const handleDownloadPdf = useCallback(() => {
    if (!canvas) return;
    const html = buildHtmlDocument();
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      // 等待内容加载完成后触发打印
      printWindow.onload = () => {
        printWindow.print();
      };
      // 兜底：如果 onload 不触发，延迟打印
      setTimeout(() => {
        try { printWindow.print(); } catch (_e) { /* ignore */ }
      }, 500);
    } else {
      toast.error('浏览器阻止了弹窗，请允许弹窗后重试');
    }
    setShowDownloadMenu(false);
  }, [canvas, buildHtmlDocument]);

  if (!canvas) {
    return (
      <div className="h-full flex items-center justify-center bg-muted/50">
        <div className="text-center space-y-6 px-8">
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-24 h-24 mx-auto bg-primary rounded-2xl flex items-center justify-center shadow-lg"
          >
            <icons.PenTool className="w-12 h-12 text-white" />
          </motion.div>
          <div>
            <h3 className="text-xl font-semibold text-foreground mb-2">AI 智能画布</h3>
            <p className="text-muted-foreground leading-relaxed max-w-md mx-auto">
              AI 生成文书、合同时将自动在此打开<br />
              支持富文本编辑、实时协作、AI 优化
            </p>
          </div>
          <div className="pt-4 flex flex-wrap gap-3 justify-center">
            {['富文本编辑', '实时协作', 'AI 优化', '律师批注'].map((tag) => (
              <span
                key={tag}
                className="px-4 py-2 bg-background rounded-full text-sm text-muted-foreground border border-border shadow-sm"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const pendingSuggestions = (canvas.suggestions || []).filter((s) => s.status === 'pending');

  return (
    <div className={cn(
      'h-full flex flex-col bg-background',
      isFullscreen && 'fixed inset-0 z-50'
    )}>
      {/* 统一工具栏 */}
      <div className="border-b border-border bg-background flex-shrink-0 px-3 py-2 space-y-1.5">
        {/* 第一行：标题 + 状态 + 操作 */}
        <div className="flex items-center gap-2">
          <icons.FileText className="w-4 h-4 text-primary flex-shrink-0" />
          <input
            type="text"
            value={canvas.title}
            onChange={(e) => onTitleChange(e.target.value)}
            className="flex-1 min-w-0 text-sm font-semibold text-foreground bg-transparent border-none focus:outline-none truncate"
            placeholder="文档标题..."
          />
          <span className={`text-[10px] flex items-center gap-1 flex-shrink-0 ${isSaved ? 'text-emerald-600' : 'text-amber-500'}`}>
            {isSaved ? <><icons.CheckCircle2 className="w-3 h-3" />已同步</> : '编辑中...'}
          </span>
          {onSaveToList && (
            <button
              onClick={onSaveToList}
              className="p-1 rounded-md text-muted-foreground hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 transition-colors flex-shrink-0"
              title="保存到文档库"
            >
              <icons.Save className="w-3.5 h-3.5" />
            </button>
          )}
          {onCloseDocument && (
            <button
              onClick={onCloseDocument}
              className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors flex-shrink-0"
              title="关闭文档"
            >
              <icons.X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* 第二行：所有操作按钮 */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          {/* 编辑模式切换 */}
          <div className="flex items-center bg-muted rounded-md p-0.5 flex-shrink-0">
            <button
              onClick={() => setEditorMode('rich')}
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium transition-all',
                editorMode === 'rich'
                  ? 'bg-background text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              富文本
            </button>
            <button
              onClick={() => setEditorMode('markdown')}
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium transition-all',
                editorMode === 'markdown'
                  ? 'bg-background text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Markdown
            </button>
          </div>

          <div className="w-px h-3.5 bg-border flex-shrink-0" />

          {/* AI 文档操作 */}
          {onDocumentAction && (
            <>
              {[
                { id: 'summarize', label: '摘要', icon: icons.Wand2, desc: '生成结构化摘要' },
                { id: 'translate', label: '翻译', icon: icons.Globe, desc: '翻译为目标语言' },
                { id: 'risk_check', label: '风险', icon: icons.Shield, desc: '识别法律风险点' },
              ].map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.id}
                    onClick={() => onDocumentAction(action.id, { content: canvas.content })}
                    disabled={isProcessing}
                    className="flex items-center gap-1 px-1.5 py-1 text-xs text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-md transition-colors whitespace-nowrap disabled:opacity-40 flex-shrink-0"
                    title={action.desc}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{action.label}</span>
                  </button>
                );
              })}
            </>
          )}

          {/* AI 优化 */}
          <button
            onClick={onAIOptimize}
            disabled={isOptimizing || isProcessing}
            className="flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary rounded-md hover:bg-primary/15 transition-all disabled:opacity-50 text-xs font-medium flex-shrink-0"
          >
            <icons.Sparkles className={cn('w-3 h-3', isOptimizing && 'animate-spin')} />
            {isOptimizing ? '优化中' : '润色'}
          </button>

          {/* 待处理建议 */}
          {pendingSuggestions.length > 0 && (
            <button
              onClick={() => onSuggestionAction(pendingSuggestions[0].id, 'accept')}
              className="flex items-center gap-1 px-1.5 py-1 bg-yellow-50 dark:bg-yellow-950/30 text-yellow-700 dark:text-yellow-300 rounded-md border border-yellow-200 dark:border-yellow-800 text-xs hover:bg-yellow-100 dark:hover:bg-yellow-900/30 flex-shrink-0"
            >
              <icons.Sparkles className="w-3 h-3" />
              {pendingSuggestions.length}
            </button>
          )}

          {/* 版本历史 */}
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={cn(
              'p-1 rounded-md transition-colors flex-shrink-0',
              showHistory ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
            )}
            title="版本历史"
          >
            <icons.Clock className="w-3.5 h-3.5" />
          </button>

          <div className="flex-1 min-w-1" />

          {/* 下载 */}
          <div className="relative flex-shrink-0">
            <button
              onClick={() => setShowDownloadMenu(!showDownloadMenu)}
              className="flex items-center gap-1 px-1.5 py-1 rounded-md hover:bg-muted text-muted-foreground transition-colors text-xs"
              title="下载文件"
            >
              <icons.Download className="w-3.5 h-3.5" />
              <icons.ChevronDown className="w-2.5 h-2.5" />
            </button>
            {showDownloadMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowDownloadMenu(false)} />
                <div className="absolute right-0 top-full mt-1 bg-background border border-border rounded-lg shadow-lg py-1 w-max z-20">
                  <button
                    onClick={handleDownloadDocx}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-muted transition-colors whitespace-nowrap"
                  >
                    <icons.FileText className="w-3.5 h-3.5 text-primary flex-shrink-0" />
                    下载为 Word (.doc)
                  </button>
                  <button
                    onClick={handleDownloadPdf}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs text-foreground hover:bg-muted transition-colors whitespace-nowrap"
                  >
                    <icons.FileOutput className="w-3.5 h-3.5 text-destructive flex-shrink-0" />
                    下载为 PDF
                  </button>
                </div>
              </>
            )}
          </div>

          {/* 转律师 */}
          {onForwardToLawyer && (
            <button
              onClick={onForwardToLawyer}
              className="flex items-center gap-1 px-2 py-1 bg-primary/5 text-primary rounded-md hover:bg-primary/10 text-xs font-medium transition-colors flex-shrink-0"
            >
              <icons.Users className="w-3 h-3" />
              转律师
            </button>
          )}
        </div>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 编辑器 */}
        <div className="flex-1 overflow-hidden">
          {editorMode === 'rich' ? (
            // 富文本协作编辑器（Markdown 内容自动转为 HTML）
            <CollaborativeEditor
              documentId={`canvas-${conversationId || 'default'}`}
              user={currentUser}
              initialContent={isMarkdownContent(canvas.content) ? markdownToHtml(canvas.content) : canvas.content}
              readOnly={false}
              onChange={handleContentChange}
              showAIAssist={true}
              onAIAssist={handleAIAssist}
              wsUrl={import.meta.env.VITE_WS_URL || 'ws://localhost:8005/api/v1/chat/ws'}
              minimal
            />
          ) : (
            // Markdown 简易编辑器
            <div className="flex h-full">
              {/* 编辑区 */}
              <div className={cn('flex flex-col', showPreview ? 'w-1/2 border-r border-border' : 'w-full')}>
                <div className="px-4 py-2 bg-muted/50 border-b border-border flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">Markdown 编辑</span>
                  <button
                    onClick={() => setShowPreview(!showPreview)}
                    className="text-sm text-primary hover:text-primary/80"
                  >
                    {showPreview ? <icons.Edit3 className="w-4 h-4 inline" /> : <icons.Eye className="w-4 h-4 inline" />}
                    {showPreview ? ' 隐藏预览' : ' 显示预览'}
                  </button>
                </div>
                <textarea
                  value={canvas.content}
                  onChange={(e) => onContentChange(e.target.value)}
                  className="flex-1 p-6 font-mono text-sm text-foreground bg-background resize-none outline-none leading-relaxed"
                  placeholder="在此输入 Markdown 内容..."
                  spellCheck={false}
                />
                {/* AI 建议 */}
                {pendingSuggestions.length > 0 && (
                  <div className="border-t border-border max-h-48 overflow-y-auto p-4">
                    <AnimatePresence>
                      {pendingSuggestions.map((s) => (
                        <InlineSuggestion
                          key={s.id}
                          suggestion={s}
                          onAccept={(id) => onSuggestionAction(id, 'accept')}
                          onReject={(id) => onSuggestionAction(id, 'reject')}
                        />
                      ))}
                    </AnimatePresence>
                  </div>
                )}
              </div>

              {/* 预览区 */}
              {showPreview && (
                <div className="w-1/2 overflow-y-auto p-6 bg-background">
                  <div className="prose prose-sm max-w-none prose-headings:text-foreground prose-p:text-foreground">
                    <ReactMarkdown>{canvas.content}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 版本历史侧边栏 */}
      <AnimatePresence>
        {showHistory && (
          <motion.div
            initial={{ x: 320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 320, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="w-80 border-l border-border bg-muted/50 overflow-hidden flex flex-col"
          >
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-foreground">版本历史</h3>
                <button
                  onClick={() => setShowHistory(false)}
                  className="p-1 hover:bg-muted rounded"
                >
                  <icons.XCircle className="w-5 h-5 text-muted-foreground" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {versions.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">暂无历史版本</p>
              ) : (
                <div className="space-y-2">
                  {versions.map((v) => (
                    <div
                      key={v.id}
                      className="p-3 bg-background rounded-lg border border-border hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-muted-foreground">
                          {v.time.toLocaleString()}
                        </span>
                        <button
                          onClick={() => restoreVersion(v.id)}
                          className="text-xs text-primary hover:text-primary/80"
                        >
                          恢复
                        </button>
                      </div>
                      <p className="text-sm text-foreground line-clamp-2">
                        {v.content.slice(0, 100)}...
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});

CanvasEditor.displayName = 'CanvasEditor';
