import { useState } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { Case } from './CaseManagement';
import { cardStyle, buttonStyle, heading, iconSize, inputStyle, statusBadge } from '@/lib/design-tokens';

interface CaseListProps {
  cases: Case[];
  selectedCase: Case | null;
  onSelectCase: (caseItem: Case) => void;
  onCreateCase: () => void;
}

export function CaseList({ cases, selectedCase, onSelectCase, onCreateCase }: CaseListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.caseNumber.includes(searchQuery) ||
      c.client.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterStatus === 'all' || c.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const statusConfig: Record<string, { label: string; badge: string }> = {
    pending: { label: '待处理', badge: statusBadge.neutral },
    'in-progress': { label: '进行中', badge: statusBadge.info },
    in_progress: { label: '进行中', badge: statusBadge.info },
    'under-review': { label: '审核中', badge: statusBadge.warning },
    waiting: { label: '等待中', badge: statusBadge.warning },
    completed: { label: '已完成', badge: statusBadge.success },
    closed: { label: '已结案', badge: statusBadge.success },
  };

  const priorityConfig: Record<string, { border: string; dot: string }> = {
    low: { border: 'border-border', dot: 'bg-muted-foreground' },
    medium: { border: 'border-primary/30', dot: 'bg-primary' },
    high: { border: 'border-amber-300 dark:border-amber-700', dot: 'bg-amber-500' },
    urgent: { border: 'border-destructive/30', dot: 'bg-destructive' },
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className={heading.page}>案件管理</h2>
            <p className={`${heading.muted} mt-1`}>共 {cases.length} 个案件</p>
          </div>
          <button
            onClick={onCreateCase}
            className={`${buttonStyle.primary} flex items-center gap-2`}
          >
            <icons.Plus className={iconSize.sm} />
            新建案件
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <icons.Search className={`absolute left-3 top-1/2 -translate-y-1/2 ${iconSize.sm} text-muted-foreground`} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索案件编号、标题、客户..."
            className={`${inputStyle.search} pl-10`}
          />
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap">
          {['all', 'pending', 'in-progress', 'under-review', 'completed', 'closed'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`${buttonStyle.sm} transition-colors ${
                filterStatus === status
                  ? 'bg-primary/10 text-primary'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {status === 'all' ? '全部' : statusConfig[status]?.label || status}
            </button>
          ))}
        </div>
      </div>

      {/* Case List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {filteredCases.length === 0 && (
            <div className="text-center py-12">
              <icons.Briefcase className={`${iconSize.xl} mx-auto mb-3 text-muted-foreground/40`} />
              <p className={heading.card}>暂无案件</p>
              <p className={`${heading.micro} mt-1`}>请尝试调整筛选条件或新建案件</p>
            </div>
          )}

          {filteredCases.map((caseItem, index) => {
            const status = statusConfig[caseItem.status] || statusConfig['pending'];
            const priority = priorityConfig[caseItem.priority] || priorityConfig['medium'];
            const isSelected = selectedCase?.id === caseItem.id;

            return (
              <motion.div
                key={caseItem.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                onClick={() => onSelectCase(caseItem)}
                className={`p-4 rounded-xl border cursor-pointer transition-all hover:shadow-md ${
                  isSelected
                    ? 'border-primary bg-primary/5 shadow-sm'
                    : `${priority.border} bg-background hover:border-primary/20`
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <div className={`w-2 h-2 rounded-full shrink-0 ${priority.dot}`} />
                      <span className={heading.micro + ' font-mono'}>{caseItem.caseNumber}</span>
                      <span className={`px-2 py-0.5 rounded-md text-xs font-medium ${status.badge}`}>
                        {status.label}
                      </span>
                    </div>
                    <h3 className={`${heading.card} mb-1 truncate`}>{caseItem.title}</h3>
                    <div className={`flex items-center gap-3 ${heading.micro}`}>
                      <span>客户：{caseItem.client}</span>
                      <span>·</span>
                      <span>{caseItem.type}</span>
                    </div>
                  </div>
                </div>

                <div className={`flex items-center justify-between ${heading.micro} mb-2`}>
                  <span>负责人：{caseItem.lawyer}</span>
                  {caseItem.deadline && (
                    <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                      <icons.Clock className={iconSize.xs} />
                      <span>{new Date(caseItem.deadline).toLocaleDateString()}</span>
                    </div>
                  )}
                </div>

                {/* Progress Bar */}
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-muted-foreground">进度</span>
                    <span className={heading.card}>{caseItem.progress}%</span>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        caseItem.progress >= 100
                          ? 'bg-emerald-500 dark:bg-emerald-400'
                          : caseItem.progress >= 50
                            ? 'bg-primary'
                            : caseItem.progress > 0
                              ? 'bg-amber-500 dark:bg-amber-400'
                              : 'bg-muted-foreground/30'
                      }`}
                      style={{ width: `${caseItem.progress}%` }}
                    />
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
