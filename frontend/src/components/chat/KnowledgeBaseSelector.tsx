import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { knowledgeApi, type KnowledgeBase } from '@/lib/api';
import { icons } from '@/lib/icons';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

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

/**
 * 内置法律文书模板 —— 作为资源选择器「模板」视图的数据源。
 *
 * TODO(Phase 4)：后端目前分散 4 个 templates 端点（contracts / approvals /
 * knowledge_management / due_diligence），无一覆盖文书模板全域（合同 / 诉讼 /
 * 意见 / 合规）。需产品 PRD 定义统一的 `/api/v1/legal-templates` 端点后迁移
 * 为动态加载；在此之前用内置常量保证对话场景可用。
 *
 * 每条模板带 description，让用户在不点模板 tab 时也能通过「全部」视图发现。
 */
interface ResourceTemplate {
  id: string;
  name: string;
  category: '合同' | '诉讼' | '意见' | '合规';
  description: string;
}

const RESOURCE_TEMPLATES: ResourceTemplate[] = [
  { id: 'tpl-legal-opinion', name: '法律意见书', category: '意见', description: '针对具体法律问题出具专业法律意见' },
  { id: 'tpl-nda', name: '保密协议', category: '合同', description: '保护商业秘密与涉密信息的双方约定' },
  { id: 'tpl-labor-contract', name: '劳动合同', category: '合同', description: '符合劳动法要求的用工合同模板' },
  { id: 'tpl-equity-agreement', name: '股权协议', category: '合同', description: '股权转让 / 增资扩股 / 代持协议' },
  { id: 'tpl-litigation-complaint', name: '民事起诉状', category: '诉讼', description: '民事案件起诉所需的标准文书' },
  { id: 'tpl-compliance-report', name: '合规自查报告', category: '合规', description: '企业内控合规自我评估与整改报告' },
];

interface KnowledgeBaseSelectorProps {
  selectedKbIds: string[];
  selectedTemplateId?: string | null;
  onKnowledgeSelectionChange: (ids: string[]) => void;
  onTemplateSelectionChange?: (id: string | null) => void;
  disabled?: boolean;
  embedded?: boolean;
}

export function KnowledgeBaseSelector({
  selectedKbIds,
  selectedTemplateId = null,
  onKnowledgeSelectionChange,
  onTemplateSelectionChange,
  disabled = false,
  embedded = false,
}: KnowledgeBaseSelectorProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  // 资源选择器：全部 / 知识库 / 模板
  const [activeTab, setActiveTab] = useState<'all' | 'kb' | 'template'>('all');

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
      const haystack = [kb.name, kb.description, kb.knowledge_type].filter(Boolean).join(' ').toLowerCase();
      return haystack.includes(keyword);
    });
  }, [knowledgeBases, searchQuery]);

  const filteredTemplates = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    if (!keyword) return RESOURCE_TEMPLATES;
    return RESOURCE_TEMPLATES.filter((tpl) =>
      `${tpl.name} ${tpl.category} ${tpl.description}`.toLowerCase().includes(keyword),
    );
  }, [searchQuery]);

  const selectedTemplate = useMemo(
    () => RESOURCE_TEMPLATES.find((tpl) => tpl.id === selectedTemplateId) || null,
    [selectedTemplateId],
  );

  const toggleKnowledgeSelection = useCallback(
    (kbId: string) => {
      if (selectedKbIds.includes(kbId)) {
        onKnowledgeSelectionChange(selectedKbIds.filter((id) => id !== kbId));
        return;
      }
      onKnowledgeSelectionChange([...selectedKbIds, kbId]);
    },
    [onKnowledgeSelectionChange, selectedKbIds],
  );

  const removeKnowledgeSelection = useCallback(
    (kbId: string) => {
      onKnowledgeSelectionChange(selectedKbIds.filter((id) => id !== kbId));
    },
    [onKnowledgeSelectionChange, selectedKbIds],
  );

  const chooseTemplate = useCallback(
    (templateId: string) => {
      const nextId = selectedTemplateId === templateId ? null : templateId;
      onTemplateSelectionChange?.(nextId);
    },
    [onTemplateSelectionChange, selectedTemplateId],
  );

  /** 触发器文案：反映已选资源。选择模板时带「模板」关键字。 */
  const triggerLabel = useMemo(() => {
    const parts: string[] = [];
    if (selectedKbIds.length > 0) parts.push(`知识库 · ${selectedKbIds.length}`);
    if (selectedTemplate) parts.push(`模板 · ${selectedTemplate.name}`);
    if (parts.length === 0) return '知识库';
    return parts.join(' / ');
  }, [selectedKbIds, selectedTemplate]);

  const renderKnowledgeList = () => {
    if (loading && knowledgeBases.length === 0) {
      return (
        <div className="flex items-center justify-center py-8 text-sm text-muted-foreground">
          <icons.Loader2 className="mr-2 h-4 w-4 animate-spin" />
          正在加载知识库...
        </div>
      );
    }
    if (filteredBases.length === 0) {
      return (
        <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center">
          <icons.Database className="mx-auto mb-2 h-5 w-5 text-muted-foreground/60" />
          <p className="text-sm text-foreground">暂无可选知识库</p>
          <p className="mt-1 text-xs text-muted-foreground">去知识库管理页创建知识库</p>
        </div>
      );
    }
    return filteredBases.map((kb) => {
      const checked = selectedKbIds.includes(kb.id);
      return (
        <label
          key={kb.id}
          className="flex cursor-pointer items-start gap-3 rounded-xl border border-transparent px-3 py-2.5 transition-colors hover:border-primary/10 hover:bg-muted/50"
        >
          <Checkbox
            checked={checked}
            onCheckedChange={() => toggleKnowledgeSelection(kb.id)}
            className="mt-0.5"
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium text-foreground">{kb.name}</span>
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
    });
  };

  const renderTemplateList = () => {
    if (filteredTemplates.length === 0) {
      return (
        <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center">
          <icons.FileText className="mx-auto mb-2 h-5 w-5 text-muted-foreground/60" />
          <p className="text-sm text-foreground">没有匹配的模板</p>
        </div>
      );
    }
    return filteredTemplates.map((tpl) => {
      const checked = selectedTemplateId === tpl.id;
      const checkboxId = `kb-template-${tpl.id}`;
      return (
        <label
          key={tpl.id}
          htmlFor={checkboxId}
          className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
            checked
              ? 'border-primary/40 bg-primary/5'
              : 'border-transparent hover:border-primary/10 hover:bg-muted/50'
          }`}
        >
          <Checkbox
            id={checkboxId}
            checked={checked}
            onCheckedChange={() => chooseTemplate(tpl.id)}
            className="mt-0.5"
            aria-label={tpl.name}
          />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="truncate text-sm font-medium text-foreground">{tpl.name}</span>
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                {tpl.category}
              </span>
            </div>
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {tpl.description}
            </p>
          </div>
        </label>
      );
    });
  };

  return (
    <div className={embedded ? 'shrink-0' : 'mb-2'}>
      <div className="flex flex-wrap items-center gap-2">
        {!embedded &&
          selectedBases.map((kb) => (
            <Badge
              key={kb.id}
              variant="outline"
              className="h-8 rounded-full border-primary/20 bg-primary/5 px-2.5 text-xs text-foreground"
            >
              <icons.Database className="w-3 h-3 text-primary" />
              <span className="max-w-[180px] truncate">{kb.name}</span>
              <button
                type="button"
                onClick={() => removeKnowledgeSelection(kb.id)}
                className="ml-0.5 rounded-full p-0.5 text-muted-foreground hover:bg-primary/10 hover:text-foreground"
                aria-label={`移除知识库 ${kb.name}`}
              >
                <icons.X className="w-3 h-3" />
              </button>
            </Badge>
          ))}
        {!embedded && selectedTemplate && (
          <Badge
            variant="outline"
            className="h-8 rounded-full border-primary/20 bg-primary/5 px-2.5 text-xs text-foreground"
          >
            <icons.FileText className="w-3 h-3 text-primary" />
            <span className="max-w-[180px] truncate">模板 · {selectedTemplate.name}</span>
            <button
              type="button"
              onClick={() => onTemplateSelectionChange?.(null)}
              className="ml-0.5 rounded-full p-0.5 text-muted-foreground hover:bg-primary/10 hover:text-foreground"
              aria-label={`移除模板 ${selectedTemplate.name}`}
            >
              <icons.X className="w-3 h-3" />
            </button>
          </Badge>
        )}

        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              disabled={disabled}
              data-testid="knowledge-base-trigger"
              className="inline-flex h-8 items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 text-xs font-medium text-foreground/80 shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
            >
              <icons.Database className="w-3.5 h-3.5" />
              <span>{triggerLabel}</span>
              <icons.ChevronDown className="w-3 h-3 opacity-60" />
            </button>
          </PopoverTrigger>

          <PopoverContent align="start" className="w-[380px] p-0">
            <div className="border-b border-border px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-foreground">选择资源</p>
                  <p className="text-xs text-muted-foreground">
                    挂载知识库或选择文书模板，为对话提供专业上下文
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
              <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
                <TabsList className="mb-3 w-full">
                  <TabsTrigger value="all">全部</TabsTrigger>
                  <TabsTrigger value="kb">知识库</TabsTrigger>
                  <TabsTrigger value="template">模板</TabsTrigger>
                </TabsList>

                <div className="relative mb-3">
                  <icons.Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <input
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder={
                      activeTab === 'template'
                        ? '搜索模板名称或分类...'
                        : activeTab === 'kb'
                          ? '搜索知识库名称或说明...'
                          : '搜索知识库或模板...'
                    }
                    className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-3 text-sm outline-none transition-colors focus:border-primary/40 focus:ring-2 focus:ring-primary/10"
                  />
                </div>

                <TabsContent value="all" className="max-h-72 space-y-1 overflow-y-auto">
                  {filteredBases.length > 0 && (
                    <div className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      知识库
                    </div>
                  )}
                  {renderKnowledgeList()}
                  <div className="mt-3 mb-2 px-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                    模板
                  </div>
                  {renderTemplateList()}
                </TabsContent>

                <TabsContent value="kb" className="max-h-72 space-y-1 overflow-y-auto">
                  {renderKnowledgeList()}
                </TabsContent>

                <TabsContent value="template" className="max-h-72 space-y-1 overflow-y-auto">
                  {renderTemplateList()}
                </TabsContent>
              </Tabs>
            </div>

            <div className="flex items-center justify-between border-t border-border px-4 py-3">
              <span className="text-xs text-muted-foreground">
                已选 {selectedKbIds.length} 个知识库
                {selectedTemplate ? ` · 模板 ${selectedTemplate.name}` : ''}
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
