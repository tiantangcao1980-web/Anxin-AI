import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { useState, useEffect } from 'react';
import { knowledgeApi, licApi } from '@/lib/api';
import { toast } from 'sonner';
import ReactMarkdown from 'react-markdown';

export function LegalKnowledgeBase() {
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [isEvolving, setIsEvolving] = useState(false);
  
  // 深度研究相关
  const [isResearching, setIsResearching] = useState(false);
  const [researchReport, setResearchReport] = useState<any | null>(null);
  const [showReport, setShowReport] = useState(false);

  // 执行搜索
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const data = await knowledgeApi.search(searchQuery);
      setResults(data);
    } catch (error: any) {
      toast.error(error.message || '搜索失败');
    } finally {
      setLoading(false);
    }
  };

  // 触发自进化
  const handleEvolve = async () => {
    setIsEvolving(true);
    try {
      await licApi.evolve();
      toast.success('已启动后台自进化爬取任务');
    } catch (error: any) {
      toast.error(error.message || '启动失败');
    } finally {
      setIsEvolving(false);
    }
  };

  // 深度研究
  const handleDeepResearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('请先输入研究课题');
      return;
    }
    setIsResearching(true);
    setShowReport(true);
    setResearchReport(null);
    try {
      const result = await knowledgeApi.deepResearch(searchQuery);
      setResearchReport(result);
      toast.success('研究报告生成完成');
    } catch (error: any) {
      toast.error(error.message || '研究失败');
      setShowReport(false);
    } finally {
      setIsResearching(false);
    }
  };

  return (
    <div className="h-full bg-muted flex flex-col">
      <div className="p-6 border-b bg-background">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <icons.BookOpen className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">法律智慧库</h3>
              <p className="text-xs text-muted-foreground">混合搜索 + AI 深度研究</p>
            </div>
          </div>
          
          <button
            onClick={handleEvolve}
            disabled={isEvolving}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition-colors border border-transparent hover:border-primary/20 disabled:opacity-50"
          >
            <icons.RefreshCw className={`w-3.5 h-3.5 ${isEvolving ? 'animate-spin' : ''}`} />
            更新法规库
          </button>
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <icons.Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索法律条文、案例、或输入研究课题..."
              className="w-full pl-9 pr-3 py-2.5 bg-muted border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm text-foreground transition-all"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2 bg-foreground text-background rounded-xl text-sm font-medium hover:bg-foreground/90 disabled:opacity-50 transition-all"
          >
            {loading ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : '搜索'}
          </button>
          <button
            onClick={handleDeepResearch}
            disabled={isResearching}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-xl text-sm font-medium hover:opacity-90 shadow-md transition-all active:scale-95 disabled:opacity-50"
          >
            <icons.Sparkles className="w-4 h-4" />
            深度研究
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {showReport && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-primary/5 rounded-2xl border border-primary/20 shadow-sm overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-primary/20 flex items-center justify-between bg-primary/5">
              <div className="flex items-center gap-2">
                <icons.Sparkles className="w-4 h-4 text-primary" />
                <span className="font-medium text-foreground text-sm">AI 深度法律研究报告</span>
              </div>
              <button 
                onClick={() => setShowReport(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <icons.X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-6">
              {isResearching ? (
                <div className="space-y-4 py-4">
                  <div className="flex items-center gap-3 text-primary animate-pulse">
                    <icons.Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm font-medium">正在调取多维案例并生成深度分析...</span>
                  </div>
                  <div className="h-4 bg-primary/10 rounded w-3/4"></div>
                  <div className="h-4 bg-primary/10 rounded w-full"></div>
                  <div className="h-4 bg-primary/10 rounded w-5/6"></div>
                </div>
              ) : researchReport ? (
                <div className="prose prose-indigo max-w-none text-sm leading-relaxed">
                  <ReactMarkdown>{researchReport.content}</ReactMarkdown>
                  
                  {researchReport.citations?.length > 0 && (
                    <div className="mt-8 pt-6 border-t border-border">
                      <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-caption mb-4 flex items-center gap-2">
                        <icons.BookMarked className="w-3.5 h-3.5" />
                        研究引用库
                      </h5>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {researchReport.citations.map((cite: any, i: number) => (
                          <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-muted border border-border text-[11px] text-muted-foreground">
                            <icons.ChevronRight className="w-3 h-3 text-primary" />
                            <span className="font-medium">{cite.name || cite.case_number}</span>
                            {cite.article && <span className="text-muted-foreground">第{cite.article}条</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </motion.div>
        )}

        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-background rounded-xl border border-border p-4 animate-pulse">
                <div className="h-4 bg-muted rounded w-1/4 mb-3"></div>
                <div className="h-3 bg-muted rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-muted rounded w-1/2"></div>
              </div>
            ))
          ) : results.length > 0 ? (
            results.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="group bg-background rounded-xl border border-border p-4 hover:border-primary hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
              >
                {item.metadata?.keyword_match && (
                  <div className="absolute top-0 right-0 px-2 py-0.5 bg-primary text-[10px] text-white font-medium rounded-bl-lg">
                    精准匹配
                  </div>
                )}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-medium text-primary uppercase tracking-tighter bg-primary/10 px-1.5 py-0.5 rounded">
                        {item.match_type === 'hybrid' ? '混合检索' : item.match_type === 'vector' ? '语义关联' : '文本匹配'}
                      </span>
                      <h4 className="font-medium text-foreground text-sm group-hover:text-primary transition-colors">{item.title}</h4>
                    </div>
                  </div>
                  <icons.ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed mb-3 line-clamp-3">
                  {item.content}
                </p>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground">来源: {item.source || '法律库'}</span>
                  <span className="text-[10px] text-muted-foreground">|</span>
                  <span className="text-[10px] text-muted-foreground">关联度: {(item.score * 100).toFixed(0)}%</span>
                </div>
              </motion.div>
            ))
          ) : !showReport && (
            <div className="py-20 text-center space-y-4">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                <icons.Search className="w-8 h-8 text-muted-foreground" />
              </div>
              <div>
                <p className="text-muted-foreground font-medium">寻找法律答案</p>
                <p className="text-xs text-muted-foreground">输入问题，AI 将为您检索法律法规并生成研究报告</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
