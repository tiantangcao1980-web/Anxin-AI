/**
 * ChatSidebar Component
 * 负责显示和管理对话列表
 */

import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { ConversationItem } from '@/lib/store';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';
import { useState, useMemo } from 'react';
import { cardStyle, heading, buttonStyle, iconSize, chatBubble, listItem, shadow, searchBar, starButton } from '@/lib/design-tokens';

interface ChatSidebarProps {
  conversations: ConversationItem[];
  currentId: string;
  onNewConversation: () => void;
  onSwitchConversation: (conv: ConversationItem) => void;
  onDeleteConversation: (convId: string) => void;
  onUpdateConversationTitle: (convId: string, newTitle: string) => void;
  onToggleBatchMode: () => void;
  onSelectAll: () => void;
  onBatchDelete: () => void;
  onClose: () => void;
  onToggleStar?: (convId: string) => void;
  // 批量模式
  batchMode?: boolean;
  selectedConvIds?: Set<string>;
  isBatchDeleting?: boolean;
  // 编辑状态
  editingConvId?: string | null;
  editingTitle?: string;
  setEditingConvId?: (id: string | null) => void;
  setEditingTitle?: (title: string) => void;
  menuOpenId?: string | null;
  setMenuOpenId?: (id: string | null) => void;
}

export function ChatSidebar({
  conversations,
  currentId,
  onNewConversation,
  onSwitchConversation,
  onDeleteConversation,
  onUpdateConversationTitle,
  onToggleBatchMode,
  onSelectAll,
  onBatchDelete,
  onClose,
  onToggleStar,
  batchMode = false,
  selectedConvIds = new Set(),
  isBatchDeleting = false,
  editingConvId,
  editingTitle,
  setEditingConvId,
  setEditingTitle,
  menuOpenId,
  setMenuOpenId,
}: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'starred'>('all');

  // 本地过滤对话列表
  const filteredConversations = useMemo(() => {
    let list = conversations;
    if (filterMode === 'starred') {
      list = list.filter((c) => (c as any).is_starred);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((c) => (c.title || '').toLowerCase().includes(q));
    }
    return list;
  }, [conversations, filterMode, searchQuery]);

  const formatConvDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
    if (diff === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff === 1) return '昨天';
    if (diff < 7) return `${diff}天前`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const handleStartRename = (conv: ConversationItem, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setMenuOpenId?.(null);
    setEditingConvId?.(conv.id);
    setEditingTitle?.(conv.title || '');
  };

  const handleFinishRename = async () => {
    if (!editingConvId) return;
    const trimmed = editingTitle?.trim() || '';
    if (!trimmed) {
      setEditingConvId?.(null);
      return;
    }
    onUpdateConversationTitle(editingConvId, trimmed);
    setEditingConvId?.(null);
  };

  const handleToggleSelect = (convId: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    // 通知父组件更新选择状态
    onSelectAll(); // 这里的实现需要调整,暂时保留
  };

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 280, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="h-full flex-shrink-0 bg-background flex flex-col overflow-hidden border-r border-border"
    >
      {/* 头部 */}
      <div className="p-3 flex flex-col gap-2 border-b border-border">
        <div className="flex items-center justify-between">
          {!batchMode ? (
            <>
              <button
                onClick={onNewConversation}
                className={`${buttonStyle.primary} flex-1 mr-2`}
              >
                <icons.Plus className={iconSize.sm} /> 新建对话
              </button>
              <button
                onClick={onToggleBatchMode}
                className={buttonStyle.icon}
                title="批量管理"
              >
                <icons.CheckCircle2 className={iconSize.sm} />
              </button>
              <button
                onClick={onClose}
                className={buttonStyle.icon}
                title="收起侧边栏"
              >
                <icons.PanelLeft className={iconSize.sm} />
              </button>
            </>
          ) : (
            <>
              <span className={`${heading.card} flex-1`}>
                已选 {selectedConvIds.size} / {conversations.length}
              </span>
              <button
                onClick={onToggleBatchMode}
                className={buttonStyle.icon}
                title="取消"
              >
                <icons.XCircle className={iconSize.sm} />
              </button>
            </>
          )}
        </div>

        {batchMode && (
          <div className="flex items-center gap-2">
            <button
              onClick={onSelectAll}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg border border-border transition-colors"
            >
              {selectedConvIds.size === conversations.length ? (
                <>
                  <icons.CheckCircle2 className={iconSize.sm} /> 取消全选
                </>
              ) : (
                <>
                  <icons.Circle className={iconSize.sm} /> 全选
                </>
              )}
            </button>
            <button
              onClick={onBatchDelete}
              disabled={selectedConvIds.size === 0 || isBatchDeleting}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-white bg-destructive hover:bg-destructive/90 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors flex-1 justify-center shadow-sm"
            >
              {isBatchDeleting ? (
                <>
                  <icons.Loader2 className="w-3.5 h-3.5 animate-spin" /> 删除中...
                </>
              ) : (
                <>
                  <icons.Trash2 className={iconSize.sm} /> 删除所选 ({selectedConvIds.size})
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* 搜索 + 过滤 */}
      {!batchMode && (
        <div className="px-3 pt-2 pb-1 space-y-2">
          {/* 搜索输入框 */}
          <div className={searchBar.container}>
            <icons.Search className={searchBar.icon} />
            <input
              type="text"
              placeholder="搜索对话..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={searchBar.input}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className={searchBar.clear}
              >
                <icons.X className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* 全部 / 收藏 Tab */}
          <div className="flex gap-1">
            <button
              onClick={() => setFilterMode('all')}
              className={`flex-1 py-1 text-xs font-medium rounded-md transition-colors ${
                filterMode === 'all'
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              全部
            </button>
            <button
              onClick={() => setFilterMode('starred')}
              className={`flex-1 py-1 text-xs font-medium rounded-md transition-colors flex items-center justify-center gap-1 ${
                filterMode === 'starred'
                  ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              <icons.Star className="w-3 h-3" /> 收藏
            </button>
          </div>
        </div>
      )}

      {/* 对话列表 */}
      <div className="flex-1 overflow-y-auto py-2">
        {filteredConversations.length === 0 ? (
          <div className="text-center text-muted-foreground text-sm mt-8 px-4">
            <icons.MessageSquare className={`${iconSize.xl} mx-auto mb-2 opacity-30`} />
            <p className={heading.muted}>暂无对话记录</p>
            <p className={`${heading.micro} mt-1`}>开始新对话后将在此处显示</p>
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isActive = conv.id === currentId;
            const isEditing = editingConvId === conv.id;
            const isSelected = selectedConvIds.has(conv.id);

            return (
              <div
                key={conv.id}
                onClick={() =>
                  batchMode ? handleToggleSelect(conv.id) : !isEditing && onSwitchConversation(conv)
                }
                className={`group relative mx-2 mb-0.5 rounded-lg cursor-pointer transition-colors ${
                  batchMode && isSelected
                    ? listItem.selected
                    : isActive && !batchMode
                    ? listItem.active
                    : listItem.base
                }`}
              >
                <div className="flex items-center gap-3 px-3 py-2.5">
                  {batchMode ? (
                    <div
                      className="flex-shrink-0"
                      onClick={(e) => handleToggleSelect(conv.id, e)}
                    >
                      {isSelected ? (
                        <icons.CheckCircle2 className={`${iconSize.sm} text-destructive`} />
                      ) : (
                        <icons.Circle className={`${iconSize.sm} text-muted-foreground`} />
                      )}
                    </div>
                  ) : (
                    <icons.MessageSquare
                      className={`${iconSize.sm} flex-shrink-0 ${
                        isActive ? 'text-primary' : 'text-muted-foreground'
                      }`}
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    {isEditing && !batchMode ? (
                      <input
                        value={editingTitle}
                        onChange={(e) => setEditingTitle?.(e.target.value)}
                        onBlur={handleFinishRename}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleFinishRename();
                          if (e.key === 'Escape') setEditingConvId?.(null);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="w-full bg-background text-foreground text-sm px-2 py-0.5 rounded border border-primary/50 focus:outline-none focus:border-primary"
                      />
                    ) : (
                      <>
                        <p
                          className={`text-sm truncate font-medium ${
                            batchMode && isSelected
                              ? 'text-destructive'
                              : isActive && !batchMode
                              ? 'text-primary'
                              : 'text-foreground'
                          }`}
                        >
                          {conv.title || '未命名对话'}
                        </p>
                        <p className={`${heading.micro} mt-0.5`}>
                          {formatConvDate(conv.last_message_at || conv.created_at)}
                          {conv.message_count > 0 && ` · ${conv.message_count}条`}
                        </p>
                      </>
                    )}
                  </div>
                  {!isEditing && !batchMode && (
                    <div
                      className={`flex items-center gap-0.5 ${
                        isActive || (conv as any).is_starred ? 'visible' : 'invisible group-hover:visible'
                      }`}
                    >
                      {/* 收藏按钮 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleStar?.(conv.id);
                        }}
                        className={`${starButton.base} ${
                          (conv as any).is_starred ? starButton.active : starButton.inactive
                        }`}
                        title={(conv as any).is_starred ? '取消收藏' : '收藏'}
                      >
                        {(conv as any).is_starred ? (
                          <icons.Star className="w-3.5 h-3.5 fill-current" />
                        ) : (
                          <icons.Star className="w-3.5 h-3.5" />
                        )}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuOpenId?.(menuOpenId === conv.id ? null : conv.id);
                        }}
                        className={buttonStyle.icon}
                      >
                        <icons.MoreHorizontal className={iconSize.sm} />
                      </button>
                    </div>
                  )}
                </div>

                {/* 菜单 */}
                <AnimatePresence>
                  {!batchMode && menuOpenId === conv.id && (
                    <motion.div
                      initial={{ opacity: 0, y: -5, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -5, scale: 0.95 }}
                      className={`absolute right-2 top-full z-50 bg-background border border-border rounded-lg ${shadow.dropdown} py-1 min-w-[120px]`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={(e) => handleStartRename(conv, e)}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
                      >
                        <icons.Edit className={iconSize.xs} /> 重命名
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(conv.id);
                          setMenuOpenId?.(null);
                        }}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-destructive hover:text-destructive hover:bg-destructive/5"
                      >
                        <icons.Trash2 className={iconSize.xs} /> 删除
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>

      {/* 底部统计 */}
      <div className="p-3 border-t border-border text-center">
        <p className={heading.micro}>
          {filterMode === 'starred' ? `${filteredConversations.length} 个收藏` : `共 ${conversations.length} 个对话`}
          {searchQuery && ` · 搜索 "${searchQuery}"`}
        </p>
      </div>
    </motion.div>
  );
}
