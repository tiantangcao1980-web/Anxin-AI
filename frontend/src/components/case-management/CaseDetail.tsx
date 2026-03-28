import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { Case } from './CaseManagement';
import { useState, useEffect } from 'react';
import { LottieIcon } from '../ui/LottieIcon';
import { casesApi, documentsApi, Document } from '@/lib/api';
import { toast } from 'sonner';

interface CaseDetailProps {
  case: Case;
  onClose: () => void;
}

export function CaseDetail({ case: caseItem, onClose }: CaseDetailProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [showBriefing, setShowBriefing] = useState(false);
  const [briefingContent, setBriefingContent] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activities, setActivities] = useState<any[]>([]);

  // 加载关联数据
  useEffect(() => {
    const loadData = async () => {
      if (!caseItem.id) return;
      try {
        // 加载文档
        const docs = await documentsApi.list({ case_id: caseItem.id });
        setDocuments(docs.items);
        
        // 加载活动/事件
        const timeline = await casesApi.getTimeline(caseItem.id);
        const mappedActivities = timeline.map((event: any) => ({
            id: event.id,
            type: event.event_type,
            user: '系统', // 后端暂无 user 字段，暂用系统
            content: event.description || event.title,
            time: event.event_time
        }));
        setActivities(mappedActivities);

      } catch (error) {
        console.error('加载案件详情失败', error);
      }
    };
    loadData();
  }, [caseItem.id]);

  const statusColors: Record<string, string> = {
    pending: 'bg-muted text-foreground',
    'in-progress': 'bg-primary/10 text-primary',
    in_progress: 'bg-primary/10 text-primary',
    waiting: 'bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400',
    closed: 'bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400',
  };

  const statusLabels: Record<string, string> = {
    pending: '待处理',
    'in-progress': '进行中',
    in_progress: '进行中',
    waiting: '等待中',
    closed: '已结案',
  };

  const handleGenerateBriefing = async () => {
    setIsGenerating(true);
    try {
        // 调用真实 API 生成简报
        const response = await casesApi.generateBriefing(caseItem.id);
        setBriefingContent(response.content);
        setShowBriefing(true);
        toast.success('简报生成成功');
    } catch (error) {
        console.error('生成简报失败', error);
        toast.error('生成简报失败，请稍后重试');
    } finally {
        setIsGenerating(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-background relative">
      {/* Briefing Modal Overlay */}
      <AnimatePresence>
        {showBriefing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-background/95 backdrop-blur-md flex flex-col p-8"
          >
             <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-foreground flex items-center gap-2">
                  <icons.FileOutput className="w-6 h-6 text-primary" />
                  律师交接简报
                </h2>
                <button 
                  onClick={() => setShowBriefing(false)}
                  className="p-2 hover:bg-muted rounded-full"
                >
                  <icons.X className="w-6 h-6 text-muted-foreground" />
                </button>
             </div>
             
             <div className="flex-1 overflow-y-auto bg-muted/50 rounded-xl p-6 border border-border font-mono text-sm leading-relaxed whitespace-pre-wrap">
                {briefingContent}
             </div>

             <div className="mt-6 flex gap-4 justify-end">
                <button className="px-4 py-2 text-muted-foreground hover:bg-muted rounded-lg transition-colors">
                  复制内容
                </button>
                <button className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors shadow-sm">
                  导出 PDF
                </button>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="p-6 border-b border-border bg-primary/5">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-mono text-muted-foreground">{caseItem.caseNumber}</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[caseItem.status] || statusColors.pending}`}>
                {statusLabels[caseItem.status] || caseItem.status}
              </span>
            </div>
            <h2 className="text-xl font-semibold text-foreground mb-2">{caseItem.title}</h2>
            <p className="text-sm text-muted-foreground">{caseItem.description}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-background/50 rounded-lg transition-colors"
          >
            <icons.X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Quick Info */}
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-background/60 backdrop-blur-sm rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <icons.User className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">客户</span>
            </div>
            <p className="font-medium text-foreground text-sm">{caseItem.client}</p>
          </div>
          <div className="bg-background/60 backdrop-blur-sm rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <icons.User className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground">负责律师</span>
            </div>
            <p className="font-medium text-foreground text-sm">{caseItem.lawyer}</p>
          </div>
          <div className="bg-background/60 backdrop-blur-sm rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <icons.DollarSign className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-muted-foreground">标的金额</span>
            </div>
            <p className="font-medium text-foreground text-sm">{caseItem.amount || '未设置'}</p>
          </div>
          <div className="bg-background/60 backdrop-blur-sm rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <icons.Calendar className="w-4 h-4 text-amber-600" />
              <span className="text-xs text-muted-foreground">截止日期</span>
            </div>
            <p className="font-medium text-foreground text-sm">{caseItem.deadline ? new Date(caseItem.deadline).toLocaleDateString() : '未设置'}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          {/* Progress */}
          <div>
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <icons.CheckCircle className="w-5 h-5 text-primary" />
              案件进度
            </h3>
            <div className="bg-muted/50 rounded-lg p-4 border border-border">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-muted-foreground">整体完成度</span>
                <span className="text-lg font-bold text-primary">{caseItem.progress}%</span>
              </div>
              <div className="h-3 bg-background rounded-full overflow-hidden border border-border">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${caseItem.progress}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className="h-full bg-primary rounded-full"
                ></motion.div>
              </div>
            </div>
          </div>

          {/* Documents */}
          <div>
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <icons.Paperclip className="w-5 h-5 text-primary" />
              相关文档 ({documents.length})
            </h3>
            <div className="space-y-2">
              {documents.length > 0 ? documents.map((doc, index) => (
                <motion.div
                  key={doc.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-all cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <icons.FileText className="w-8 h-8 text-primary" />
                    <div>
                      <p className="font-medium text-sm text-foreground">{doc.name}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{doc.doc_type}</span>
                        <span>·</span>
                        <span>{doc.file_size ? `${(doc.file_size / 1024).toFixed(1)} KB` : '未知大小'}</span>
                        <span>·</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )) : (
                <div className="text-center py-4 text-muted-foreground text-sm bg-muted/50 rounded-lg border border-border border-dashed">
                    暂无相关文档
                </div>
              )}
            </div>
          </div>

          {/* Activity Timeline */}
          <div>
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <icons.Clock className="w-5 h-5 text-muted-foreground" />
              活动记录
            </h3>
            <div className="relative">
              <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border"></div>
              <div className="space-y-4">
                {activities.map((activity, index) => (
                  <motion.div
                    key={activity.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="relative pl-10"
                  >
                    <div className="absolute left-2 w-4 h-4 bg-primary rounded-full border-2 border-background"></div>
                    <div className="bg-muted/50 rounded-lg p-3 border border-border">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-sm text-foreground">{activity.user}</span>
                        <span className="text-xs text-muted-foreground">{new Date(activity.time).toLocaleString()}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{activity.content}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border bg-muted/50">
        <div className="flex gap-2">
          <button 
            onClick={handleGenerateBriefing}
            disabled={isGenerating}
            className="flex-1 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all text-sm font-medium flex items-center justify-center gap-2 shadow-sm disabled:opacity-70"
          >
            {isGenerating ? (
               <>
                 <LottieIcon type="thinking" className="w-5 h-5" />
                 生成简报中...
               </>
            ) : (
               <>
                 <icons.FileOutput className="w-4 h-4" />
                 生成律师交接简报
               </>
            )}
          </button>
          <button className="flex-1 py-2 border border-border text-foreground rounded-lg hover:bg-muted/50 transition-colors text-sm font-medium">
            添加备注
          </button>
        </div>
      </div>
    </div>
  );
}
