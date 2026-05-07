import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';

export interface DocumentDiffLine {
  id?: string | number;
  text?: string;
  original?: string;
  suggested?: string;
  type?: 'normal' | 'risk' | 'added' | 'new' | 'removed' | 'modified';
  issue?: string;
  reason?: string;
}

export interface DocumentDiffData {
  original?: DocumentDiffLine[];
  suggested?: DocumentDiffLine[];
  summary?: {
    risk_count?: number;
    suggestion_count?: number;
    new_clause_count?: number;
  };
}

interface DocumentDiffProps {
  data?: DocumentDiffData | null;
}

function lineText(item: DocumentDiffLine, side: 'original' | 'suggested') {
  return item.text || (side === 'original' ? item.original : item.suggested) || '';
}

function lineKey(item: DocumentDiffLine, index: number) {
  return item.id ?? `${index}-${item.type ?? 'line'}`;
}

function hasLineContent(item: DocumentDiffLine, side: 'original' | 'suggested') {
  return lineText(item, side).trim().length > 0;
}

export function DocumentDiff({ data }: DocumentDiffProps) {
  const originalContent = (data?.original ?? []).filter((item) => hasLineContent(item, 'original'));
  const suggestedContent = (data?.suggested ?? []).filter((item) => hasLineContent(item, 'suggested'));
  const hasDiff = originalContent.length > 0 || suggestedContent.length > 0;
  const summary = data?.summary ?? {};
  const riskCount = summary.risk_count ?? originalContent.filter((item) => item.type === 'risk').length;
  const suggestionCount =
    summary.suggestion_count ??
    suggestedContent.filter((item) => item.type === 'added' || item.type === 'modified').length;
  const newClauseCount = summary.new_clause_count ?? suggestedContent.filter((item) => item.type === 'new').length;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="h-full overflow-y-auto bg-muted p-6"
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="mb-1 font-semibold text-foreground">文档对比视图</h3>
            <p className="text-sm text-muted-foreground">仅展示当前会话返回的真实差异数据</p>
          </div>
        </div>

        {!hasDiff ? (
          <div className="flex min-h-[240px] items-center justify-center rounded-lg border border-dashed border-border bg-background p-6">
            <div className="max-w-sm text-center">
              <icons.FileSearch className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
              <h4 className="mb-1 text-sm font-medium text-foreground">暂无真实文档差异</h4>
              <p className="text-sm leading-relaxed text-muted-foreground">
                完成合同审查或文档优化后，系统会在这里展示原文、建议版本和修改原因。
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <DiffColumn title="原始文档" iconColor="text-muted-foreground" lines={originalContent} side="original" />
              <DiffColumn title="优化版本" iconColor="text-success" lines={suggestedContent} side="suggested" />
            </div>

            <div className="rounded-lg border border-border bg-background p-4">
              <h4 className="mb-3 text-sm font-medium text-foreground">修改摘要</h4>
              <div className="grid grid-cols-3 gap-4 text-center">
                <SummaryTile label="风险点" value={riskCount} tone="danger" />
                <SummaryTile label="优化建议" value={suggestionCount} tone="success" />
                <SummaryTile label="新增条款" value={newClauseCount} tone="primary" />
              </div>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}

function DiffColumn({
  title,
  iconColor,
  lines,
  side,
}: {
  title: string;
  iconColor: string;
  lines: DocumentDiffLine[];
  side: 'original' | 'suggested';
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <div className="border-b border-border bg-muted px-4 py-3">
        <div className="flex items-center gap-2">
          <icons.FileText className={`h-4 w-4 ${iconColor}`} />
          <span className="text-sm font-medium text-foreground">{title}</span>
        </div>
      </div>
      <div className="space-y-3 p-4">
        {lines.length === 0 ? (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">暂无内容</p>
        ) : (
          lines.map((item, index) => (
            <motion.div
              key={lineKey(item, index)}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.03 }}
            >
              <p className={`rounded-md p-2 text-sm leading-relaxed ${lineClass(item.type)}`}>
                {lineText(item, side)}
              </p>
              {(item.issue || item.reason) && (
                <div className={`mt-1 flex items-start gap-2 px-2 text-xs ${noteClass(item.type)}`}>
                  {item.type === 'risk' ? (
                    <icons.AlertCircle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                  ) : (
                    <icons.CheckCircle className="mt-0.5 h-3 w-3 flex-shrink-0" />
                  )}
                  <span>{item.issue || item.reason}</span>
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}

function SummaryTile({ label, value, tone }: { label: string; value: number; tone: 'danger' | 'success' | 'primary' }) {
  const classes = {
    danger: 'bg-destructive/10 text-destructive',
    success: 'bg-success/10 text-success',
    primary: 'bg-primary/5 text-primary',
  }[tone];
  return (
    <div className={`rounded-lg p-3 ${classes}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="mt-1 text-xs">{label}</p>
    </div>
  );
}

function lineClass(type: DocumentDiffLine['type']) {
  if (type === 'risk' || type === 'removed') return 'border border-destructive/20 bg-destructive/10 text-destructive';
  if (type === 'added' || type === 'new' || type === 'modified') return 'border border-success/20 bg-success/10 text-success';
  return 'text-foreground';
}

function noteClass(type: DocumentDiffLine['type']) {
  return type === 'risk' || type === 'removed' ? 'text-destructive' : 'text-success';
}
