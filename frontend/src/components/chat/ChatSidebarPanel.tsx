/**
 * ChatSidebarPanel — 对话列表侧边栏
 *
 * 从 Chat.tsx 提取的独立组件，负责：
 * 1. 对话列表展示与切换
 * 2. 新建对话
 * 3. 批量选择与删除
 * 4. 重命名对话
 */

import { memo, useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { chatApi } from '@/lib/api';
import type { ConversationItem } from '@/lib/store';
import { toast } from 'sonner';

interface ChatSidebarPanelProps {
  conversations: ConversationItem[];
  currentConversationId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onNewConversation: () => void;
  onSwitchConversation: (conv: ConversationItem) => void;
  onDeleteConversation: (convId: string) => void;
  onBatchDelete: (ids: string[]) => void;
  onRenameConversation: (convId: string, newTitle: string) => void;
}

function formatConvDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    if (days === 0) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    } else if (days === 1) {
      return '昨天';
    } else if (days < 7) {
      return `${days}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  } catch {
    return '';
  }
}

export const ChatSidebarPanel = memo(function ChatSidebarPanel({
  conversations,
  currentConversationId,
  isOpen,
  onClose,
  onNewConversation,
  onSwitchConversation,
  onDeleteConversation,
  onBatchDelete,
  onRenameConversation,
}: ChatSidebarPanelProps) {
  // 侧边栏本地状态
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [selectedConvIds, setSelectedConvIds] = useState<Set<string>>(new Set());
  const [isBatchDeleting, setIsBatchDeleting] = useState(false);
  const editInputRef = useRef<HTMLInputElement>(null);

  // 点击外侧关闭菜单
  useEffect(() => {
    if (!menuOpenId) return;
    const handler = () => setMenuOpenId(null);
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [menuOpenId]);

  const handleToggleBatchMode = useCallback(() => {
    setBatchMode(prev => {
      if (prev) setSelectedConvIds(new Set());
      return !prev;
    });
  }, []);

  const handleToggleSelect = useCallback((convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedConvIds(prev => {
      const next = new Set(prev);
      if (next.has(convId)) next.delete(convId);
      else next.add(convId);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedConvIds.size === conversations.length) {
      setSelectedConvIds(new Set());
    } else {
      setSelectedConvIds(new Set(conversations.map(c => c.id)));
    }
  }, [conversations, selectedConvIds.size]);

  const handleBatchDeleteClick = useCallback(async () => {
    const ids = Array.from(selectedConvIds);
    if (ids.length === 0) return;
    setIsBatchDeleting(true);
    try {
      onBatchDelete(ids);
      setSelectedConvIds(new Set());
      setBatchMode(false);
    } finally {
      setIsBatchDeleting(false);
    }
  }, [selectedConvIds, onBatchDelete]);

  const handleStartRename = useCallback((conv: ConversationItem, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setMenuOpenId(null);
    setEditingConvId(conv.id);
    setEditingTitle(conv.title || '');
    setTimeout(() => editInputRef.current?.focus(), 50);
  }, []);

  const handleFinishRename = useCallback(async () => {
    if (!editingConvId) return;
    const trimmed = editingTitle.trim();
    if (trimmed) {
      onRenameConversation(editingConvId, trimmed);
    }
    setEditingConvId(null);
  }, [editingConvId, editingTitle, onRenameConversation]);

  const handleDeleteClick = useCallback((convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setMenuOpenId(null);
    onDeleteConversation(convId);
  }, [onDeleteConversation]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="h-full flex-shrink-0 bg-background flex flex-col overflow-hidden border-r border-border max-md:!w-full max-md:absolute max-md:inset-0 max-md:z-20"
        >
          {/* 顶部操作栏 */}
          <div className="p-3 flex flex-col gap-2 border-b border-border/50">
            <div className="flex items-center justify-between">
              {!batchMode ? (
                <>
                  <button onClick={onNewConversation}
                    className="flex items-center gap-2 px-3 py-2 text-sm font-medium bg-primary hover:bg-primary/90 text-white rounded-lg transition-colors flex-1 mr-2 shadow-sm">
                    <icons.Plus className="w-4 h-4" /> 新建对话
                  </button>
                  <button onClick={handleToggleBatchMode}
                    className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors" title="批量管理">
                    <icons.Check className="w-4 h-4" />
                  </button>
                  <button onClick={onClose}
                    className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="收起侧边栏">
                    <icons.PanelLeft className="w-4 h-4" />
                  </button>
                </>
              ) : (
                <>
                  <span className="text-sm font-medium text-foreground/80 flex-1">
                    已选 {selectedConvIds.size} / {conversations.length}
                  </span>
                  <button onClick={handleToggleBatchMode}
                    className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors" title="取消">
                    <icons.XCircle className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
            {batchMode && (
              <div className="flex items-center gap-2">
                <button onClick={handleSelectAll}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg border border-border transition-colors">
                  {selectedConvIds.size === conversations.length ? (
                    <><icons.Check className="w-3.5 h-3.5" /> 取消全选</>
                  ) : (
                    <><icons.Circle className="w-3.5 h-3.5" /> 全选</>
                  )}
                </button>
                <button onClick={handleBatchDeleteClick}
                  disabled={selectedConvIds.size === 0 || isBatchDeleting}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-white bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex-1 justify-center shadow-sm">
                  {isBatchDeleting ? (
                    <><icons.Loader2 className="w-3.5 h-3.5 animate-spin" /> 删除中...</>
                  ) : (
                    <><icons.Trash2 className="w-3.5 h-3.5" /> 删除所选 ({selectedConvIds.size})</>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* 对话列表 */}
          <div className="flex-1 overflow-y-auto py-2">
            {conversations.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm mt-8 px-4">
                <icons.MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="text-muted-foreground">暂无对话记录</p>
                <p className="text-xs mt-1 text-muted-foreground">开始新对话后将在此处显示</p>
              </div>
            ) : conversations.map((conv) => {
              const isActive = conv.id === currentConversationId;
              const isEditing = editingConvId === conv.id;
              const isSelected = selectedConvIds.has(conv.id);
              return (
                <div key={conv.id} onClick={() => batchMode ? handleToggleSelect(conv.id) : (!isEditing && onSwitchConversation(conv))}
                  className={`group relative mx-2 mb-0.5 rounded-lg cursor-pointer transition-colors ${
                    batchMode && isSelected
                      ? 'bg-destructive/5 text-destructive border border-destructive/20'
                      : isActive && !batchMode
                      ? 'bg-primary/5 text-primary border border-primary/10'
                      : 'text-foreground/80 hover:bg-muted/50 border border-transparent'
                  }`}>
                  <div className="flex items-center gap-3 px-3 py-2.5">
                    {batchMode ? (
                      <div className="flex-shrink-0" onClick={(e) => handleToggleSelect(conv.id, e)}>
                        {isSelected ? (
                          <icons.Check className="w-4 h-4 text-destructive" />
                        ) : (
                          <icons.Circle className="w-4 h-4 text-muted-foreground" />
                        )}
                      </div>
                    ) : (
                      <icons.MessageSquare className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                    )}
                    <div className="flex-1 min-w-0">
                      {isEditing && !batchMode ? (
                        <input ref={editInputRef} value={editingTitle} onChange={(e) => setEditingTitle(e.target.value)}
                          onBlur={handleFinishRename} onKeyDown={(e) => { if (e.key === 'Enter') handleFinishRename(); if (e.key === 'Escape') setEditingConvId(null); }}
                          onClick={(e) => e.stopPropagation()}
                          className="w-full bg-background text-foreground text-sm px-2 py-0.5 rounded border border-primary/30 focus:outline-none focus:border-primary" />
                      ) : (
                        <>
                          <p className={`text-sm truncate font-medium ${
                            batchMode && isSelected ? 'text-destructive' : isActive && !batchMode ? 'text-primary' : 'text-foreground'
                          }`}>{conv.title || '未命名对话'}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            {formatConvDate(conv.last_message_at || conv.created_at)}
                            {conv.message_count > 0 && ` · ${conv.message_count}条`}
                          </p>
                        </>
                      )}
                    </div>
                    {!isEditing && !batchMode && (
                      <div className={`flex items-center gap-0.5 ${isActive ? 'visible' : 'invisible group-hover:visible'}`}>
                        <button onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === conv.id ? null : conv.id); }}
                          className="p-1 text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors">
                          <icons.MoreHorizontal className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                  <AnimatePresence>
                    {!batchMode && menuOpenId === conv.id && (
                      <motion.div initial={{ opacity: 0, y: -5, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -5, scale: 0.95 }}
                        className="absolute right-2 top-full z-50 bg-background border border-border rounded-lg shadow-lg py-1 min-w-[120px]" onClick={(e) => e.stopPropagation()}>
                        <button onClick={(e) => handleStartRename(conv, e)} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50">
                          <icons.Edit className="w-3 h-3" /> 重命名
                        </button>
                        <button onClick={(e) => handleDeleteClick(conv.id, e)} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:text-destructive hover:bg-destructive/5">
                          <icons.Trash2 className="w-3 h-3" /> 删除
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
          <div className="p-3 border-t border-border/50 text-center">
            <p className="text-[10px] text-muted-foreground">共 {conversations.length} 个对话</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
});
