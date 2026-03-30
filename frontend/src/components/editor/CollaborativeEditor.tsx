/**
 * Simple Rich Text Editor Component
 *
 * Basic collaborative editor with TipTap
 * Features:
 * - Rich text editing (bold, italic, headings, lists)
 * - Basic collaboration support
 * - Comments system
 * - AI assist
 */

import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import Collaboration from '@tiptap/extension-collaboration';
import CollaborationCursor from '@tiptap/extension-collaboration-cursor';
import * as Y from 'yjs';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, buttonStyle, heading } from '@/lib/design-tokens';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

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
  onCommentAdd?: (comment: Omit<EditorComment, 'id' | 'timestamp'>) => void;
  onCommentResolve?: (commentId: string) => void;
  /** Hide outer toolbar & status bar (when parent provides them) */
  minimal?: boolean;
}

// ==================== Helper Functions ====================

function getUserColor(name: string): string {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
    '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
    '#F8B500', '#FF6F61', '#6B5B95', '#88B04B'
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

// ==================== Toolbar Button Component ====================

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
        'p-2 rounded-lg transition-all',
        'hover:bg-muted active:scale-95',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        active && 'bg-primary/10 text-primary'
      )}
    >
      {children}
    </button>
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
  wsUrl = 'ws://localhost:1234',
  onCommentAdd,
  onCommentResolve,
  minimal = false,
}: CollaborativeEditorProps) {
  const [ydoc] = useState(() => new Y.Doc());
  const [connectedUsers, setConnectedUsers] = useState<EditorUser[]>([user]);
  const [comments, setComments] = useState<EditorComment[]>([]);
  const [showPreview, setShowPreview] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isAIAssisting, setIsAIAssisting] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout>();

  // Get Y.js fragment
  const yXmlFragment = useMemo(() => ydoc.getXmlFragment('prosemirror'), [ydoc]);

  // Initialize editor
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        history: false, // Disabled when using Collaboration
      }),
      Placeholder.configure({
        placeholder: '开始输入内容...',
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          class: 'text-primary underline hover:text-primary/80',
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: 'max-w-full h-auto rounded-lg',
        },
      }),
      Table.configure({
        resizable: true,
        HTMLAttributes: {
          class: 'border-collapse w-full',
        },
      }),
      TableRow,
      TableCell,
      TableHeader,
      Collaboration.configure({
        document: ydoc,
      }),
      // CollaborationCursor requires a real provider with awareness — skip until WebSocket is set up
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
      }, 2000);
    },
  });

  // 当编辑器就绪后，如果 Yjs 文档为空则加载 initialContent
  useEffect(() => {
    if (editor && initialContent && editor.isEmpty) {
      // Yjs Collaboration 会忽略 content prop，需要手动设置
      editor.commands.setContent(initialContent);
    }
  }, [editor, initialContent]);

  // Save document
  const handleSave = async () => {
    if (!editor || isSaving) return;
    setIsSaving(true);
    try {
      await onSave?.();
      setLastSaved(new Date());
      toast.success('Document saved');
    } catch (error) {
      toast.error('Save failed');
    } finally {
      setIsSaving(false);
    }
  };

  // AI Assist
  const handleAIAssist = async () => {
    if (!editor || isAIAssisting || !onAIAssist) return;

    const content = editor.getText();
    if (content.length < 10) {
      toast.error('Content too short to optimize');
      return;
    }

    setIsAIAssisting(true);
    try {
      const optimized = await onAIAssist(content);
      editor.commands.setContent(optimized);
      toast.success('AI optimization complete');
    } catch (error) {
      toast.error('AI optimization failed');
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
      toast.error('Please select text to comment');
      return;
    }

    const comment = window.prompt('Enter comment:');
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
    toast.success('Comment added');
  };

  // Download document
  const handleDownload = () => {
    if (!editor) return;

    const html = editor.getHTML();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${documentId}.html`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Document downloaded');
  };

  const characterCount = editor ? editor.getText().length : 0;
  const wordCount = editor ? editor.getText().split(/\s+/).filter(Boolean).length : 0;

  return (
    <div className="flex flex-col h-full bg-background">
      {!minimal && (
        <>
          {/* Toolbar */}
          <div className="border-b border-border p-1.5 flex items-center gap-0.5 flex-wrap bg-muted">
            <div className="flex items-center gap-0.5 pr-2 border-r border-border">
              <ToolbarButton
                onClick={() => editor?.chain().focus().undo().run()}
                disabled={!editor?.can().undo()}
                title="撤销"
              >
                <icons.Undo className="w-4 h-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().redo().run()}
                disabled={!editor?.can().redo()}
                title="重做"
              >
                <icons.Redo className="w-4 h-4" />
              </ToolbarButton>
            </div>

            <div className="flex items-center gap-0.5 px-2 border-r border-border">
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
                active={editor?.isActive('heading', { level: 1 })}
                title="标题 1"
              >
                <icons.Heading1 className="w-4 h-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
                active={editor?.isActive('heading', { level: 2 })}
                title="标题 2"
              >
                <icons.Heading2 className="w-4 h-4" />
              </ToolbarButton>
            </div>

            <div className="flex items-center gap-0.5 px-2 border-r border-border">
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleBold().run()}
                active={editor?.isActive('bold')}
                title="加粗"
              >
                <icons.Bold className="w-4 h-4" />
              </ToolbarButton>
              <ToolbarButton
                onClick={() => editor?.chain().focus().toggleItalic().run()}
                active={editor?.isActive('italic')}
                title="斜体"
              >
                <icons.Italic className="w-4 h-4" />
              </ToolbarButton>
            </div>

            <div className="flex items-center gap-0.5 px-2">
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
            </div>

            <div className="flex items-center gap-1 ml-auto">
              {connectedUsers.length > 0 && (
                <div className="flex items-center gap-1 px-1.5 py-0.5 bg-background rounded-md border border-border">
                  <icons.Users className="w-3.5 h-3.5 text-muted-foreground" />
                  <div className="flex -space-x-1">
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
                  </div>
                </div>
              )}
              {onAIAssist && !readOnly && (
                <ToolbarButton
                  onClick={handleAIAssist}
                  disabled={isAIAssisting}
                  title="AI 优化"
                >
                  <icons.Sparkles className={cn('w-4 h-4', isAIAssisting && 'animate-spin')} />
                </ToolbarButton>
              )}
            </div>
          </div>

          {/* Status bar */}
          <div className="flex items-center justify-between px-3 py-1 bg-muted border-b border-border text-[11px] text-muted-foreground">
            <div className="flex items-center gap-3">
              <span>{characterCount} 字符</span>
              <span>{wordCount} 词</span>
              {lastSaved && (
                <span className="flex items-center gap-1">
                  <icons.Clock className="w-3 h-3" />
                  {lastSaved.toLocaleTimeString()}
                </span>
              )}
              {isSaving && <span className="text-primary">保存中...</span>}
            </div>
            <div className="flex items-center gap-1.5">
              {!readOnly && (
                <>
                  <button
                    onClick={() => setShowComments(!showComments)}
                    className={cn(
                      'flex items-center gap-1 px-1.5 py-0.5 rounded hover:bg-muted/80 transition-colors',
                      showComments && 'bg-muted/80'
                    )}
                    title="批注"
                  >
                    <icons.MessageSquare className="w-3 h-3" />
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className={`flex items-center gap-1 ${buttonStyle.primary} px-2 py-0.5 disabled:opacity-50`}
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

      {/* Editor area */}
      <div className="flex-1 flex overflow-hidden">
        <div className={cn('flex-1 overflow-auto', showComments && 'pr-80')}>
          <div className={cn(
            minimal ? 'p-4' : 'max-w-4xl mx-auto p-8',
            showPreview && 'prose prose-sm sm:prose lg:prose-lg xl:prose-xl mx-auto'
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
                    <p>Loading editor...</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {editor && (
              <EditorContent
                editor={editor}
                className={cn(
                  'min-h-full focus:outline-none',
                  !showPreview && (minimal
                    ? 'prose prose-sm max-w-none'
                    : 'prose prose-sm sm:prose lg:prose-lg xl:prose-xl max-w-none'
                  )
                )}
              />
            )}
          </div>
        </div>

        {/* Comments sidebar */}
        <AnimatePresence>
          {showComments && (
            <motion.div
              initial={{ x: 320, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 320, opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="w-80 border-l border-border bg-muted overflow-y-auto"
            >
              <div className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className={heading.section}>Comments</h3>
                  {!readOnly && (
                    <button
                      onClick={handleAddComment}
                      className={buttonStyle.ghost}
                    >
                      + Add
                    </button>
                  )}
                </div>

                {comments.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">No comments yet</p>
                ) : (
                  <div className="space-y-3">
                    {comments.map((comment) => (
                      <div
                        key={comment.id}
                        className={cn(
                          'p-3 rounded-lg border',
                          comment.resolved
                            ? `${cardStyle.flat} opacity-60`
                            : 'bg-yellow-50 border-yellow-200'
                        )}
                      >
                        <div className="flex items-start justify-between mb-1">
                          <span className="font-medium text-sm text-foreground">{comment.userName}</span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(comment.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{comment.content}</p>
                        {!comment.resolved && user.id === comment.userId && onCommentResolve && (
                          <button
                            onClick={() => {
                              onCommentResolve(comment.id);
                              setComments(comments.map((c) =>
                                c.id === comment.id ? { ...c, resolved: true } : c
                              ));
                            }}
                            className="text-xs text-emerald-600 hover:text-emerald-700"
                          >
                            Mark as resolved
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
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
  placeholder = '开始输入内容...',
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
      Link.configure({
        openOnClick: false,
      }),
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
        Loading editor...
      </div>
    );
  }

  return (
    <div className={`${cardStyle.base} overflow-hidden`}>
      {/* Toolbar */}
      {!readOnly && (
        <div className="border-b border-border p-2 flex items-center gap-1 bg-muted">
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBold().run()}
            active={editor.isActive('bold')}
          >
            <icons.Bold className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleItalic().run()}
            active={editor.isActive('italic')}
          >
            <icons.Italic className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
            active={editor.isActive('heading', { level: 2 })}
          >
            <icons.Heading2 className="w-4 h-4" />
          </ToolbarButton>
          <ToolbarButton
            onClick={() => editor.chain().focus().toggleBulletList().run()}
            active={editor.isActive('bulletList')}
          >
            <icons.List className="w-4 h-4" />
          </ToolbarButton>
          {onSave && (
            <>
              <div className="flex-1" />
              <button
                onClick={onSave}
                className={`${buttonStyle.primary} px-3 py-1`}
              >
                Save
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
