import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { knowledgeApi, type KnowledgeBase } from '@/lib/api';
import { icons } from '@/lib/icons';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

const KB_CACHE_TTL = 5 * 60 * 1000;

let kbCache: KnowledgeBase[] | null = null;
let kbCacheExpiresAt = 0;
let kbCacheRequest: Promise<KnowledgeBase[]> | null = null;

async function loadKnowledgeBases(force = false): Promise<KnowledgeBase[]> {
  const now = Date.now();
  if (!force && kbCache && now < kbCacheExpiresAt) {
    return kbCache;
  }

  if (!force && kbCacheRequest) {
    return kbCacheRequest;
  }

  kbCacheRequest = knowledgeApi
    .listBases({ page_size: 100 })
    .then((result) => {
      const items = (result.items || []).slice().sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      kbCache = items;
      kbCacheExpiresAt = Date.now() + KB_CACHE_TTL;
      kbCacheRequest = null;
      return items;
    })
    .catch((error) => {
      kbCacheRequest = null;
      throw error;
    });

  return kbCacheRequest;
}

interface KnowledgeBaseSelectorProps {
  selectedKbIds: string[];
  onSelectionChange: (ids: string[]) => void;
  disabled?: boolean;
}

export function KnowledgeBaseSelector({
  selectedKbIds,
  onSelectionChange,
  disabled = false,
}: KnowledgeBaseSelectorProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);

  const fetchBases = useCallback(async (force = false) => {
    setLoading(true);
    try {
      const items = await loadKnowledgeBases(force);
      setKnowledgeBases(items);
    } catch (error: any) {
      toast.error(error?.message || '加载知识库失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchBases();
  }, [fetchBases]);

  const selectedBases = useMemo(() => {
    const selectedSet = new Set(selectedKbIds);
    return knowledgeBases.filter((kb) => selectedSet.has(kb.id));
  }, [knowledgeBases, selectedKbIds]);

  const filteredBases = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword) return knowledgeBases;

    return knowledgeBases.filter((kb) => {
      const haystack = [kb.name, kb.description, kb.knowledge_type]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(keyword);
    });
  }, [knowledgeBases, searchQuery]);

  const toggleSelection = useCallback((kbId: string) => {
    if (selectedKbIds.includes(kbId)) {
      onSelectionChange(selectedKbIds.filter((id) => id !== kbId));
      return;
    }

    onSelectionChange([...selectedKbIds, kbId]);
  }, [onSelectionChange, selectedKbIds]);

  const removeSelection = useCallback((kbId: string) => {
    onSelectionChange(selectedKbIds.filter((id) => id !== kbId));
  }, [onSelectionChange, selectedKbIds]);

  return (
    <div className="mb-2">
      <div className="flex flex-wrap items-center gap-2">
        {selectedBases.map((kb) => (
          <Badge
            key={kb.id}
            variant="outline"
            className="h-8 rounded-full border-primary/20 bg-primary/5 px-2.5 text-xs text-foreground"
          >
            <icons.Database className="w-3 h-3 text-primary" />
            <span className="max-w-[180px] truncate">{kb.name}</span>
            <button
              type="button"
              onClick={() => removeSelection(kb.id)}
              className="ml-0.5 rounded-full p-0.5 text-muted-foreground hover:bg-primary/10 hover:text-foreground"
              aria-label={`移除知识库 ${kb.name}`}
            >
              <icons.X className="w-3 h-3" />
            </button>
          </Badge>
        ))}

        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              disabled={disabled}
              className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 text-xs font-medium text-foreground/80 shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <icons.Database className="w-3.5 h-3.5" />
              <span>
                {selectedKbIds.length > 0 ? `已选知识库 ${selectedKbIds.length}` : '添加知识库'}
              </span>
              <icons.ChevronDown className="w-3 h-3 opacity-60" />
            </button>
          </PopoverTrigger>

          <PopoverContent align="start" className="w-[360px] p-0">
            <div className="border-b border-border px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">选择知识库</p>
                  <p className="text-xs text-muted-foreground">
                    勾选后，AI 会优先参考这些知识库作答
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void fetchBases(true)}
                  className="rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                  title="刷新知识库列表"
                >
                  <icons.RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>

            <div className="p-4 pb-3">
              <div className="relative mb-3">
                <icons.Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="搜索知识库名称或说明..."
                  className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
                />
              </div>

              <div className="max-h-64 space-y-1 overflow-y-auto">
                {loading && knowledgeBases.length === 0 ? (
                  <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
                    <icons.Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    正在加载知识库...
                  </div>
                ) : filteredBases.length > 0 ? (
                  filteredBases.map((kb) => {
                    const checked = selectedKbIds.includes(kb.id);
                    return (
                      <label
                        key={kb.id}
                        className="flex cursor-pointer items-start gap-3 rounded-xl border border-transparent px-3 py-2.5 transition-colors hover:border-primary/10 hover:bg-muted/50"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() => toggleSelection(kb.id)}
                          className="mt-0.5"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm font-medium text-foreground">
                              {kb.name}
                            </span>
                            {kb.doc_count > 0 ? (
                              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                                {kb.doc_count} 篇
                              </span>
                            ) : (
                              <span className="rounded-full bg-destructive/10 px-1.5 py-0.5 text-[10px] text-destructive">
                                暂无文档
                              </span>
                            )}
                          </div>
                          {kb.description && (
                            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                              {kb.description}
                            </p>
                          )}
                        </div>
                      </label>
                    );
                  })
                ) : (
                  <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center">
                    <icons.Database className="mx-auto mb-2 h-5 w-5 text-muted-foreground/60" />
                    <p className="text-sm text-foreground">暂无可选知识库</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      去知识库管理页创建后，就可以在这里直接选用
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-border px-4 py-3">
              <span className="text-xs text-muted-foreground">
                已选 {selectedKbIds.length} 个知识库
              </span>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  navigate('/knowledge-base');
                }}
                className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/5"
              >
                <icons.Plus className="w-3.5 h-3.5" />
                新建知识库
              </button>
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );
}
