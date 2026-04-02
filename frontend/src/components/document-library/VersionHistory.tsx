/**
 * VersionHistory - 文档版本历史面板
 *
 * 右侧滑出面板，展示文档快照列表，支持恢复历史版本。
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { heading, buttonStyle, iconSize, cardStyle } from '@/lib/design-tokens';
import { documentsApi } from '@/lib/api';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface VersionItem {
  id: string;
  version: number;
  file_size?: number;
  change_summary?: string;
  created_at: string;
  created_by?: string;
}

interface VersionHistoryProps {
  documentId: string;
  onClose: () => void;
  onRestore?: (versionId: string) => void;
}

export function VersionHistory({ documentId, onClose, onRestore }: VersionHistoryProps) {
  const [versions, setVersions] = useState<VersionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoring, setRestoring] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await documentsApi.getVersions(documentId);
        setVersions(data.versions || []);
      } catch {
        toast.error('获取版本历史失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [documentId]);

  const handleRestore = async (version: VersionItem) => {
    if (restoring) return;
    setRestoring(version.id);
    try {
      onRestore?.(version.id);
      toast.success(`已恢复到版本 ${version.version}`);
    } catch {
      toast.error('版本恢复失败');
    } finally {
      setRestoring(null);
    }
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
      >
        <motion.div
          initial={{ opacity: 0, x: 320 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 320 }}
          onClick={(e) => e.stopPropagation()}
          className="absolute right-0 top-0 bottom-0 w-80 bg-background shadow-2xl flex flex-col"
        >
          {/* 头部 */}
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <icons.Clock className={`${iconSize.md} text-muted-foreground`} />
                <h2 className={heading.section}>版本历史</h2>
              </div>
              <button onClick={onClose} className={buttonStyle.icon}>
                <icons.X className={iconSize.md} />
              </button>
            </div>
          </div>

          {/* 版本列表 */}
          <div className="flex-1 overflow-y-auto p-4">
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <icons.Loader2 className={`${iconSize.lg} animate-spin text-muted-foreground`} />
              </div>
            ) : versions.length === 0 ? (
              <div className="text-center text-muted-foreground mt-8">
                <icons.Clock className={`${iconSize.xl} mx-auto mb-2 opacity-20`} />
                <p className={heading.muted}>暂无版本记录</p>
              </div>
            ) : (
              <div className="relative">
                {/* 时间线竖线 */}
                <div className="absolute left-3 top-2 bottom-2 w-px bg-border" />

                <div className="space-y-1">
                  {versions.map((v, i) => (
                    <div key={v.id} className="relative pl-8 group">
                      {/* 时间线节点 */}
                      <div className={`absolute left-1.5 top-3 w-3 h-3 rounded-full border-2 ${
                        i === 0 ? 'bg-primary border-primary' : 'bg-background border-border'
                      }`} />

                      <div className={`${cardStyle.compact} group-hover:border-primary/20 transition-colors`}>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`${heading.card} ${i === 0 ? 'text-primary' : ''}`}>
                            v{v.version} {i === 0 && '(当前)'}
                          </span>
                          {i > 0 && (
                            <button
                              onClick={() => handleRestore(v)}
                              disabled={!!restoring}
                              className={`${buttonStyle.sm} text-primary hover:bg-primary/10 ${
                                restoring === v.id ? 'opacity-50' : ''
                              }`}
                            >
                              {restoring === v.id ? (
                                <icons.Loader2 className="w-3 h-3 animate-spin" />
                              ) : (
                                '恢复'
                              )}
                            </button>
                          )}
                        </div>
                        {v.change_summary && (
                          <p className={`${heading.muted} line-clamp-2 mb-1`}>{v.change_summary}</p>
                        )}
                        <div className="flex items-center gap-2">
                          <span className={heading.micro}>
                            {formatDistanceToNow(new Date(v.created_at), { addSuffix: true, locale: zhCN })}
                          </span>
                          {v.file_size && (
                            <span className={heading.micro}>{formatSize(v.file_size)}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
