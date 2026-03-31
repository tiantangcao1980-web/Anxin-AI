/**
 * Canvas 画布编辑器 — v3 精简统一版
 *
 * - 统一使用 TipTap 富文本编辑器（移除 Markdown 模式切换）
 * - AI 文档操作（摘要/翻译/风险/润色）集成到工具栏
 * - 自动从内容提取标题 + 支持手动修改
 * - 版本历史侧边栏
 */

import { useState, useRef, useCallback, memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { CollaborativeEditor, type EditorUser } from '@/components/editor';
import { InlineSuggestion } from './InlineSuggestion';
import type { CanvasContent } from '@/lib/store';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

/**
 * 将 Markdown 文本转为 HTML（覆盖法律文书常用格式）
 */
function markdownToHtml(md: string): string {
  if (!md) return '';

  let html = md;

  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  html = html.replace(/^---+$/gm, '<hr/>');

  html = html.replace(/(^(?:\d+\.\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map(line => {
      const content = line.replace(/^\d+\.\s+/, '');
      return `<li>${content}</li>`;
    }).join('');
    return `<ol>${items}</ol>\n`;
  });

  html = html.replace(/(^(?:[-*]\s+.+\n?)+)/gm, (block) => {
    const items = block.trim().split('\n').map(line => {
      const content = line.replace(/^[-*]\s+/, '');
      return `<li>${content}</li>`;
    }).join('');
    return `<ul>${items}</ul>\n`;
  });

  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  const lines = html.split('\n');
  const result: string[] = [];
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length > 0) {
      const text = paragraph.join('<br/>');
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

function isMarkdownContent(content: string): boolean {
  return /^#{1,4}\s|^\d+\.\s|\*\*|^[-*]\s/m.test(content);
}

/**
 * 从文档内容中提取标题
 */
function extractTitleFromContent(content: string): string {
  if (!content) return '';
  const headingMatch = content.match(/^#\s+(.+)$/m);
  if (headingMatch) return headingMatch[1].trim().slice(0, 50);

  const docTypeMatch = content.match(/^(.{2,30}(?:合同|协议|意见书|律师函|起诉状|答辩状|仲裁申请书|通知书|声明|备忘录|报告|方案))/m);
  if (docTypeMatch) return docTypeMatch[1].trim();

  const firstLine = content.split('\n').find(l => l.trim().length > 0);
  if (firstLine) return firstLine.trim().slice(0, 40);

  return '';
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
  onDocumentAction?: (actionId: string, payload?: { content?: string }) => void;
  onSaveToList?: () => void;
  onCloseDocument?: () => void;
  isSaved?: boolean;
  isProcessing?: boolean;
  isOptimizing?: boolean;
  userId?: string;
  conversationId?: string;
}

const AI_ACTIONS = [
  { id: 'summarize', label: '摘要', icon: icons.FileText, desc: '生成结构化摘要' },
  { id: 'translate', label: '翻译', icon: icons.Globe, desc: '智能中英互译' },
  { id: 'risk_check', label: '风险检查', icon: icons.Shield, desc: '识别法律风险点' },
  { id: 'optimize', label: '润色', icon: icons.Sparkles, desc: '优化措辞和结构' },
] as const;

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
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);
  const [versions, setVersions] = useState<Array<{ id: string; time: Date; content: string }>>([]);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [editorKey, setEditorKey] = useState(0);
  const [inlineProcessing, setInlineProcessing] = useState(false);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const currentUser: EditorUser = {
    id: userId,
    name: '当前用户',
    color: '#3B82F6',
  };

  // 自动从内容提取标题（仅当标题为默认值时）
  useEffect(() => {
    if (!canvas || isEditingTitle) return;
    const defaultTitles = ['未命名文档', '文档', '法律文书', ''];
    if (defaultTitles.includes(canvas.title) && canvas.content?.trim()) {
      const extracted = extractTitleFromContent(canvas.content);
      if (extracted && extracted !== canvas.title) {
        onTitleChange(extracted);
      }
    }
  }, [canvas?.content]);

  const saveVersion = useCallback((content: string) => {
    setVersions((prev) => [
      ...prev.slice(-9),
      { id: `v-${Date.now()}`, time: new Date(), content },
    ]);
  }, []);

  const restoreVersion = useCallback((versionId: string) => {
    const version = versions.find((v) => v.id === versionId);
    if (version && canvas) {
      onContentChange(version.content);
      setEditorKey(k => k + 1);
      toast.success('版本已恢复');
      setShowHistory(false);
    }
  }, [versions, canvas, onContentChange]);

  const versionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleContentChange = useCallback((content: string) => {
    onContentChange(content);
    if (versionTimerRef.current) clearTimeout(versionTimerRef.current);
    versionTimerRef.current = setTimeout(() => saveVersion(content), 5000);
  }, [onContentChange, saveVersion]);

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

  // 下载菜单
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const downloadBtnRef = useRef<HTMLButtonElement>(null);
  const [downloadMenuPos, setDownloadMenuPos] = useState<{ top: number; right: number } | null>(null);

  // AI 操作菜单
  const [showAIMenu, setShowAIMenu] = useState(false);
  const aiBtnRef = useRef<HTMLButtonElement>(null);
  const [aiMenuPos, setAIMenuPos] = useState<{ top: number; left: number } | null>(null);

  const buildHtmlDocument = useCallback(() => {
    if (!canvas) return '';
    const title = canvas.title || '文档';
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
    toast.success('Word 文件已下载');
  }, [canvas, buildHtmlDocument]);

  const handleDownloadPdf = useCallback(() => {
    if (!canvas) return;
    const html = buildHtmlDocument();
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.onload = () => printWindow.print();
      setTimeout(() => {
        try { printWindow.print(); } catch (_e) { /* ignore */ }
      }, 500);
    } else {
      toast.error('浏览器阻止了弹窗，请允许弹窗后重试');
    }
    setShowDownloadMenu(false);
  }, [canvas, buildHtmlDocument]);

  /**
   * 统一处理 AI 文档操作 — 结果直接渲染在编辑器内容区
   */
  const handleAction = useCallback(async (actionId: string) => {
    if (!canvas?.content?.trim()) {
      toast.error('文档内容为空，请先输入内容');
      return;
    }

    setActiveAction(actionId);
    setShowAIMenu(false);
    setInlineProcessing(true);

    const content = canvas.content;
    const labels: Record<string, string> = {
      summarize: '正在生成摘要...',
      translate: '正在翻译...',
      risk_check: '正在检查风险...',
      optimize: '正在润色...',
    };
    toast(labels[actionId] || '处理中...', { duration: 2000 });

    try {
      const response = await fetch('/api/v1/chat/ai-optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, action: actionId }),
      });
      const data = await response.json();
      const result = data.optimized || data.result;

      if (!result) {
        buildInlineResult(actionId, content);
        return;
      }

      if (actionId === 'optimize') {
        saveVersion(content);
        onContentChange(result);
        setEditorKey(k => k + 1);
        toast.success('润色完成，原版本已保存到历史');
      } else if (actionId === 'translate') {
        const translated = result;
        const combined = `${content}\n\n---\n\n**【译文 / Translation】**\n\n${translated}`;
        saveVersion(content);
        onContentChange(combined);
        setEditorKey(k => k + 1);
        toast.success('翻译完成，译文已追加到原文下方');
      } else if (actionId === 'summarize') {
        const combined = `**【结构化摘要】**\n\n${result}\n\n---\n\n${content}`;
        saveVersion(content);
        onContentChange(combined);
        setEditorKey(k => k + 1);
        toast.success('摘要已插入到文档顶部');
      } else if (actionId === 'risk_check') {
        const combined = `${content}\n\n---\n\n**【风险检查报告】**\n\n${result}`;
        saveVersion(content);
        onContentChange(combined);
        setEditorKey(k => k + 1);
        toast.success('风险检查完成，报告已追加到文档末尾');
      }
    } catch {
      buildInlineResult(actionId, content);
    } finally {
      setInlineProcessing(false);
    }

    setTimeout(() => setActiveAction(null), 1500);
  }, [canvas, onContentChange, saveVersion]);

  /**
   * 后端不可用时，本地生成示例结果（演示用）
   */
  const buildInlineResult = useCallback((actionId: string, content: string) => {
    const plainText = content.replace(/<[^>]+>/g, '').replace(/[#*_~`]/g, '').trim();

    if (actionId === 'translate') {
      const isChinese = /[\u4e00-\u9fff]/.test(plainText);
      const placeholder = isChinese
        ? `[Translation of the above Chinese text will appear here once connected to AI service]`
        : `[以上英文内容的中文翻译将在连接 AI 服务后显示在此处]`;
      const label = isChinese ? '译文 / Translation' : '中文翻译';
      saveVersion(content);
      onContentChange(`${content}\n\n---\n\n**【${label}】**\n\n${placeholder}`);
      setEditorKey(k => k + 1);
      toast.success('翻译占位已生成（需连接 AI 服务获取实际翻译）');
    } else if (actionId === 'summarize') {
      const lines = plainText.split(/\n+/).filter(l => l.trim());
      const summary = lines.slice(0, 3).map((l, i) => `${i + 1}. ${l.slice(0, 80)}`).join('\n');
      saveVersion(content);
      onContentChange(`**【结构化摘要】**\n\n${summary || '（文档内容较短，无需摘要）'}\n\n---\n\n${content}`);
      setEditorKey(k => k + 1);
      toast.success('摘要已生成');
    } else if (actionId === 'risk_check') {
      saveVersion(content);
      onContentChange(`${content}\n\n---\n\n**【风险检查报告】**\n\n⚠️ 需连接 AI 服务进行深度风险分析。以下为初步检查：\n\n1. 请检查合同各方的权利义务是否对等\n2. 请确认违约责任条款是否完备\n3. 请核实争议解决条款是否合理\n4. 请检查是否遗漏了保密条款或不可抗力条款`);
      setEditorKey(k => k + 1);
      toast.success('风险检查模板已生成');
    } else if (actionId === 'optimize') {
      toast.info('润色功能需连接 AI 服务');
    }
  }, [onContentChange, saveVersion]);

  // 标题编辑
  const handleTitleFocus = useCallback(() => {
    setIsEditingTitle(true);
  }, []);

  const handleTitleBlur = useCallback(() => {
    setIsEditingTitle(false);
    if (canvas && !canvas.title.trim()) {
      const extracted = extractTitleFromContent(canvas.content);
      onTitleChange(extracted || '未命名文档');
    }
  }, [canvas, onTitleChange]);

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
  const wordCount = canvas.content.replace(/\s/g, '').length;

  return (
    <div className={cn(
      'h-full flex flex-col bg-background',
      isFullscreen && 'fixed inset-0 z-50'
    )}>
      {/* 工具栏 */}
      <div className="border-b border-border bg-background flex-shrink-0 px-3 py-2 space-y-1">
        {/* 第一行：标题 + 状态 */}
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-primary/10 flex items-center justify-center flex-shrink-0">
            <icons.FileText className="w-3.5 h-3.5 text-primary" />
          </div>
          <input
            ref={titleInputRef}
            type="text"
            value={canvas.title}
            onChange={(e) => onTitleChange(e.target.value)}
            onFocus={handleTitleFocus}
            onBlur={handleTitleBlur}
            className={cn(
              'flex-1 min-w-0 text-sm font-semibold bg-transparent border-none outline-none truncate transition-colors',
              isEditingTitle
                ? 'text-foreground bg-muted/50 rounded px-1.5 -mx-1.5'
                : 'text-foreground'
            )}
            placeholder="输入文档标题..."
          />
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className={cn(
              'text-[10px] flex items-center gap-1 px-1.5 py-0.5 rounded-full',
              isSaved
                ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30'
                : 'text-amber-600 bg-amber-50 dark:bg-amber-950/30'
            )}>
              {isSaved ? <><icons.CheckCircle2 className="w-2.5 h-2.5" />已保存</> : '编辑中...'}
            </span>
            <span className="text-[10px] text-muted-foreground/60 ml-1">{wordCount} 字</span>
          </div>
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

        {/* 第二行：操作按钮 */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-none">
          {/* AI 智能操作入口 */}
          <div className="flex-shrink-0">
            <button
              ref={aiBtnRef}
              onClick={() => {
                if (!showAIMenu && aiBtnRef.current) {
                  const rect = aiBtnRef.current.getBoundingClientRect();
                  setAIMenuPos({ top: rect.bottom + 4, left: rect.left });
                }
                setShowAIMenu(!showAIMenu);
              }}
              disabled={isProcessing || isOptimizing || inlineProcessing}
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all',
                isProcessing || isOptimizing || inlineProcessing
                  ? 'bg-primary/10 text-primary/60 cursor-not-allowed'
                  : 'bg-primary/10 text-primary hover:bg-primary/15'
              )}
            >
              <icons.Sparkles className={cn('w-3.5 h-3.5', (isProcessing || isOptimizing || inlineProcessing) && 'animate-spin')} />
              {isProcessing || isOptimizing || inlineProcessing ? '处理中...' : 'AI 助手'}
              <icons.ChevronDown className="w-2.5 h-2.5" />
            </button>
            {showAIMenu && aiMenuPos && (
              <>
                <div className="fixed inset-0 z-50" onClick={() => setShowAIMenu(false)} />
                <div
                  className="fixed bg-background border border-border rounded-xl shadow-xl py-1.5 w-52 z-[51]"
                  style={{ top: aiMenuPos.top, left: aiMenuPos.left }}
                >
                  {AI_ACTIONS.map((action) => {
                    const Icon = action.icon;
                    const isActive = activeAction === action.id;
                    return (
                      <button
                        key={action.id}
                        onClick={() => handleAction(action.id)}
                        disabled={isProcessing || isOptimizing || inlineProcessing}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors',
                          isActive
                            ? 'bg-primary/10 text-primary'
                            : 'text-foreground hover:bg-muted/60'
                        )}
                      >
                        <div className={cn(
                          'p-1 rounded-md flex-shrink-0',
                          isActive ? 'bg-primary/10' : 'bg-muted/50'
                        )}>
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1 text-left">
                          <p className="font-medium leading-tight">{action.label}</p>
                          <p className="text-[10px] text-muted-foreground leading-tight mt-0.5">{action.desc}</p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          {/* 待处理建议 */}
          {pendingSuggestions.length > 0 && (
            <button
              onClick={() => onSuggestionAction(pendingSuggestions[0].id, 'accept')}
              className="flex items-center gap-1 px-2 py-1 bg-yellow-50 dark:bg-yellow-950/30 text-yellow-700 dark:text-yellow-300 rounded-md border border-yellow-200 dark:border-yellow-800 text-xs hover:bg-yellow-100 dark:hover:bg-yellow-900/30 flex-shrink-0"
            >
              <icons.Sparkles className="w-3 h-3" />
              {pendingSuggestions.length} 条建议
            </button>
          )}

          <div className="w-px h-3.5 bg-border flex-shrink-0 mx-0.5" />

          {/* 版本历史 */}
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={cn(
              'flex items-center gap-1 px-1.5 py-1 rounded-md transition-colors text-xs flex-shrink-0',
              showHistory ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
            )}
            title="版本历史"
          >
            <icons.Clock className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">历史</span>
          </button>

          <div className="flex-1 min-w-1" />

          {/* 下载 */}
          <div className="flex-shrink-0">
            <button
              ref={downloadBtnRef}
              onClick={() => {
                if (!showDownloadMenu && downloadBtnRef.current) {
                  const rect = downloadBtnRef.current.getBoundingClientRect();
                  setDownloadMenuPos({
                    top: rect.bottom + 4,
                    right: window.innerWidth - rect.right,
                  });
                }
                setShowDownloadMenu(!showDownloadMenu);
              }}
              className="flex items-center gap-1 px-1.5 py-1 rounded-md hover:bg-muted text-muted-foreground transition-colors text-xs"
              title="下载文件"
            >
              <icons.Download className="w-3.5 h-3.5" />
              <icons.ChevronDown className="w-2.5 h-2.5" />
            </button>
            {showDownloadMenu && downloadMenuPos && (
              <>
                <div className="fixed inset-0 z-50" onClick={() => setShowDownloadMenu(false)} />
                <div
                  className="fixed bg-background border border-border rounded-lg shadow-xl py-1 w-max z-[51]"
                  style={{ top: downloadMenuPos.top, right: downloadMenuPos.right }}
                >
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
      <div className="flex-1 flex overflow-hidden relative">
        {/* AI 处理中遮罩 */}
        <AnimatePresence>
          {inlineProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10 bg-background/60 backdrop-blur-[2px] flex items-center justify-center"
            >
              <div className="flex items-center gap-2.5 px-4 py-2.5 bg-background rounded-xl border border-border shadow-lg">
                <icons.Sparkles className="w-4 h-4 text-primary animate-spin" />
                <span className="text-sm font-medium text-foreground">AI 正在处理...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 编辑器 */}
        <div className="flex-1 overflow-hidden">
          <CollaborativeEditor
            key={`editor-${editorKey}`}
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
        </div>

        {/* 版本历史侧边栏 */}
        <AnimatePresence>
          {showHistory && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 288, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="border-l border-border bg-muted/50 overflow-hidden flex flex-col flex-shrink-0"
            >
              <div className="w-72 h-full flex flex-col">
                <div className="px-4 py-3 border-b border-border flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <icons.Clock className="w-4 h-4 text-primary" />
                      <h3 className="text-sm font-semibold text-foreground">版本历史</h3>
                    </div>
                    <button
                      onClick={() => setShowHistory(false)}
                      className="p-1 hover:bg-muted rounded-md transition-colors"
                    >
                      <icons.X className="w-4 h-4 text-muted-foreground" />
                    </button>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-1">编辑时自动保存版本快照</p>
                </div>
                <div className="flex-1 overflow-y-auto p-3">
                  {versions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mb-3">
                        <icons.Clock className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <p className="text-sm text-muted-foreground">暂无历史版本</p>
                      <p className="text-[11px] text-muted-foreground/60 mt-1">编辑文档后将自动生成版本</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {versions.map((v, idx) => {
                        const isExpanded = expandedVersionId === v.id;
                        return (
                          <div
                            key={v.id}
                            className={`p-3 bg-background rounded-lg border transition-colors group ${
                              isExpanded ? 'border-primary/40 ring-1 ring-primary/10' : 'border-border hover:border-primary/30'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[11px] text-muted-foreground font-medium">
                                {idx === versions.length - 1 ? '最新版本' : `版本 ${idx + 1}`}
                              </span>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setExpandedVersionId(isExpanded ? null : v.id)}
                                  className="text-[11px] text-muted-foreground hover:text-foreground transition-colors font-medium"
                                >
                                  {isExpanded ? '收起' : '预览'}
                                </button>
                                <button
                                  onClick={() => restoreVersion(v.id)}
                                  className="text-[11px] text-primary hover:text-primary/80 opacity-0 group-hover:opacity-100 transition-opacity font-medium"
                                >
                                  恢复
                                </button>
                              </div>
                            </div>
                            <p className={`text-xs text-foreground/80 leading-relaxed ${isExpanded ? 'whitespace-pre-wrap max-h-60 overflow-y-auto' : 'line-clamp-2'}`}>
                              {isExpanded ? v.content : (v.content.slice(0, 100) + (v.content.length > 100 ? '...' : ''))}
                            </p>
                            <span className="text-[10px] text-muted-foreground/60 mt-1.5 block">
                              {v.time.toLocaleString()} · {v.content.length} 字
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});

CanvasEditor.displayName = 'CanvasEditor';
