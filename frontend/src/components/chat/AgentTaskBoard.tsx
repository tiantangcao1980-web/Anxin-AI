/**
 * Agent 协作看板 v3 — 多 Agent 并行 + 依赖分组 + 汇总面板 + 操作按钮
 * 
 * 功能：
 * - 按依赖层级拓扑分组，同层 Agent 横向并行排列
 * - 每层都显示并行数量提示
 * - 层级之间用连接线标识执行顺序
 * - 卡片可展开查看完整结果
 * - 全部完成后展示汇总面板 + 下一步操作按钮
 */

import { useState, useMemo, memo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { useChatStore } from '@/lib/store';
import type { AgentTask } from '@/lib/store';

interface AgentTaskBoardProps {
  tasks: AgentTask[];
  isProcessing: boolean;
  onSendToCanvas?: (content: string, title: string) => void;
  onGenerateDocument?: () => void;
}

/* ---- Agent 图标配置 ---- */
const agentIconMap: Record<string, { icon: React.ElementType; color: string; bgColor: string }> = {
  'legal_advisor':         { icon: icons.Scale,         color: 'text-primary',     bgColor: 'bg-primary/10' },
  'contract_reviewer':     { icon: icons.FileSearch,    color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
  'due_diligence':         { icon: icons.Search,        color: 'text-cyan-600',    bgColor: 'bg-cyan-50' },
  'legal_researcher':      { icon: icons.BookOpen,      color: 'text-primary',     bgColor: 'bg-primary/10' },
  'contract_drafter':      { icon: icons.FileText,      color: 'text-violet-600 dark:text-violet-400',  bgColor: 'bg-violet-50 dark:bg-violet-950/30' },
  'document_drafter':      { icon: icons.FileText,      color: 'text-violet-600 dark:text-violet-400',  bgColor: 'bg-violet-50 dark:bg-violet-950/30' },
  'compliance_reviewer':   { icon: icons.Shield,        color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
  'compliance_officer':    { icon: icons.Shield,        color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
  'risk_assessor':         { icon: icons.AlertTriangle, color: 'text-amber-600 dark:text-amber-400',   bgColor: 'bg-amber-50 dark:bg-amber-950/30' },
  'litigation_strategist': { icon: icons.Gavel,         color: 'text-red-600 dark:text-red-400',     bgColor: 'bg-red-50 dark:bg-red-950/30' },
  'ip_specialist':         { icon: icons.Landmark,      color: 'text-pink-600',    bgColor: 'bg-pink-50' },
  'regulatory_monitor':    { icon: icons.Eye,           color: 'text-orange-600',  bgColor: 'bg-orange-50' },
  'tax_compliance':        { icon: icons.Building,      color: 'text-teal-600',    bgColor: 'bg-teal-50' },
  'labor_compliance':      { icon: icons.Briefcase,     color: 'text-sky-600',     bgColor: 'bg-sky-50' },
  'coordinator':           { icon: icons.Brain,         color: 'text-violet-600 dark:text-violet-400',  bgColor: 'bg-violet-50 dark:bg-violet-950/30' },
};
const agentNameMap: Record<string, typeof agentIconMap[string]> = {
  '法律顾问Agent': agentIconMap.legal_advisor,
  '合同审查Agent': agentIconMap.contract_reviewer,
  '尽职调查Agent': agentIconMap.due_diligence,
  '法律研究Agent': agentIconMap.legal_researcher,
  '文书起草Agent': agentIconMap.document_drafter,
  '合规审查Agent': agentIconMap.compliance_reviewer,
  '风险评估Agent': agentIconMap.risk_assessor,
  '诉讼策略Agent': agentIconMap.litigation_strategist,
  '知识产权Agent': agentIconMap.ip_specialist,
  '监管监测Agent': agentIconMap.regulatory_monitor,
  '税务合规Agent': agentIconMap.tax_compliance,
  '劳动合规Agent': agentIconMap.labor_compliance,
  '协调调度Agent': agentIconMap.coordinator,
};
const defaultCfg = { icon: icons.Brain, color: 'text-muted-foreground', bgColor: 'bg-muted/50' };
function getAgentConfig(agent: string, agentKey?: string) {
  if (agentKey && agentIconMap[agentKey]) return agentIconMap[agentKey];
  if (agentNameMap[agent]) return agentNameMap[agent];
  return defaultCfg;
}

/* ---- 按依赖层级拓扑分组 ---- */
function groupByLevel(tasks: AgentTask[]): AgentTask[][] {
  if (tasks.length === 0) return [];
  const levels: AgentTask[][] = [];
  const assigned = new Set<string>();
  while (assigned.size < tasks.length) {
    const cur: AgentTask[] = [];
    for (const t of tasks) {
      if (assigned.has(t.id)) continue;
      if ((t.dependencies || []).every(d => assigned.has(d))) cur.push(t);
    }
    if (cur.length === 0) { levels.push(tasks.filter(t => !assigned.has(t.id))); break; }
    cur.forEach(t => assigned.add(t.id));
    levels.push(cur);
  }
  return levels;
}

/* ============================================================ */
/* =====================  主组件  ============================== */
/* ============================================================ */
export const AgentTaskBoard = memo(function AgentTaskBoard({
  tasks, isProcessing, onSendToCanvas, onGenerateDocument,
}: AgentTaskBoardProps) {
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const store = useChatStore();

  const runningCount  = tasks.filter(t => t.status === 'running').length;
  const completedCount= tasks.filter(t => t.status === 'completed').length;
  const failedCount   = tasks.filter(t => t.status === 'failed').length;
  const totalCount    = tasks.length;
  const allDone       = completedCount + failedCount === totalCount && totalCount > 0 && !isProcessing;
  const overallPct    = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  const levels = useMemo(() => groupByLevel(tasks), [tasks]);

  /* 统计总耗时 */
  const totalElapsed = useMemo(() => {
    const maxPerLevel = levels.map(level => {
      const times = level.map(t => t.elapsed || 0);
      return times.length > 0 ? Math.max(...times) : 0;
    });
    return Math.round(maxPerLevel.reduce((a, b) => a + b, 0) * 10) / 10;
  }, [levels]);

  /* 复制结果到剪贴板 */
  const handleCopy = useCallback((taskId: string, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(taskId);
      setTimeout(() => setCopiedId(null), 1500);
    });
  }, []);

  /* 发送到画布 */
  const handleSendToCanvas = useCallback((task: AgentTask) => {
    if (!task.result || !onSendToCanvas) return;
    onSendToCanvas(task.result, `${task.agent} 结果`);
  }, [onSendToCanvas]);

  return (
    <div className="bg-background rounded-xl border border-border shadow-sm overflow-hidden">
      {/* ===== 看板头部 ===== */}
      <div className="px-4 py-3 bg-primary/5 border-b border-primary/10">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center">
              <icons.GitBranch className="w-3.5 h-3.5 text-primary" />
            </div>
            <span className="text-sm font-bold text-foreground">多智能体协作</span>
            {levels.length > 1 && (
              <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded font-medium">
                {levels.length} 阶段
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-[11px]">
            {runningCount > 0 && (
              <span className="flex items-center gap-1 text-primary font-medium">
                <icons.Loader2 className="w-3 h-3 animate-spin" />{runningCount} 并行中
              </span>
            )}
            {allDone ? (
              <span className="flex items-center gap-1 text-emerald-600 font-medium">
                <icons.CheckCircle className="w-3 h-3" />全部完成
              </span>
            ) : (
              <span className="text-muted-foreground font-medium">{completedCount}/{totalCount}</span>
            )}
          </div>
        </div>
        {/* 进度条 */}
        <div className="w-full bg-background/60 rounded-full h-1.5">
          <motion.div
            className={`h-1.5 rounded-full ${allDone
              ? 'bg-emerald-500'
              : 'bg-primary'
            }`}
            initial={{ width: 0 }}
            animate={{ width: `${overallPct}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <div className="flex justify-between mt-1 text-[10px] text-muted-foreground">
          <span>{overallPct}% 完成</span>
          {allDone && totalElapsed > 0 && <span>总耗时 {totalElapsed}s</span>}
          {!allDone && runningCount > 0 && <span>最多 {Math.max(...levels.map(l => l.length))} 个并行</span>}
        </div>
      </div>

      {/* ===== DAG 层级视图 ===== */}
      <div className="p-3 space-y-0">
        {levels.map((level, levelIdx) => (
          <div key={levelIdx}>
            {/* 层级分隔连接线 */}
            {levelIdx > 0 && (
              <div className="flex items-center justify-center py-1.5">
                <div className="flex flex-col items-center">
                  <div className="w-px h-2.5 bg-border" />
                  <div className="flex items-center gap-1 px-2 py-0.5 bg-muted/50 rounded-full border border-border">
                    <icons.ChevronDown className="w-2.5 h-2.5 text-muted-foreground" />
                    <span className="text-[9px] text-muted-foreground font-medium">阶段 {levelIdx + 1}</span>
                  </div>
                  <div className="w-px h-2.5 bg-border" />
                </div>
              </div>
            )}

            {/* 每层并行提示 */}
            {level.length > 1 && (
              <div className="flex items-center gap-1.5 mb-1.5 px-1">
                <icons.Zap className="w-3 h-3 text-amber-500" />
                <span className="text-[10px] text-amber-600 font-medium">
                  {level.length} 个智能体并行执行
                </span>
              </div>
            )}

            {/* 卡片网格 */}
            <div className={`grid gap-2 ${level.length >= 2 ? 'grid-cols-2' : 'grid-cols-1'}`}>
              {level.map((task, taskIdx) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  index={levelIdx * 10 + taskIdx}
                  isExpanded={expandedTaskId === task.id}
                  onToggleExpand={() => setExpandedTaskId(expandedTaskId === task.id ? null : task.id)}
                  isParallel={level.length > 1}
                  isCopied={copiedId === task.id}
                  onCopy={(text) => handleCopy(task.id, text)}
                  onSendToCanvas={() => handleSendToCanvas(task)}
                  hasSendToCanvas={!!onSendToCanvas}
                />
              ))}
            </div>
          </div>
        ))}

        {/* ===== 全部完成 → 汇总面板 ===== */}
        <AnimatePresence>
          {allDone && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50/40 p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg bg-emerald-50 flex items-center justify-center">
                  <icons.Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                </div>
                <span className="text-sm font-bold text-foreground">协作完成</span>
              </div>

              {/* 统计 */}
              <div className="grid grid-cols-3 gap-2 mb-3">
                <div className="text-center p-2 bg-background/70 rounded-lg">
                  <p className="text-lg font-bold text-emerald-600">{completedCount}</p>
                  <p className="text-[10px] text-muted-foreground">完成</p>
                </div>
                <div className="text-center p-2 bg-background/70 rounded-lg">
                  <p className="text-lg font-bold text-primary">{levels.length}</p>
                  <p className="text-[10px] text-muted-foreground">阶段</p>
                </div>
                <div className="text-center p-2 bg-background/70 rounded-lg">
                  <p className="text-lg font-bold text-amber-600">{totalElapsed}s</p>
                  <p className="text-[10px] text-muted-foreground">总耗时</p>
                </div>
              </div>

              {/* 参与 Agent 头像 */}
              <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                <span className="text-[10px] text-muted-foreground">参与智能体：</span>
                {tasks.filter(t => t.status === 'completed').map(t => {
                  const cfg = getAgentConfig(t.agent, t.agentKey);
                  const I = cfg.icon;
                  return (
                    <div key={t.id} title={t.agent}
                      className={`w-6 h-6 rounded-md ${cfg.bgColor} flex items-center justify-center`}>
                      <I className={`w-3 h-3 ${cfg.color}`} />
                    </div>
                  );
                })}
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2">
                {onGenerateDocument && (
                  <button
                    onClick={onGenerateDocument}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-primary/90 transition-colors shadow-sm"
                  >
                    <icons.FileOutput className="w-3.5 h-3.5" />
                    查看文档
                  </button>
                )}
                <button
                  onClick={() => {
                    const allResults = tasks
                      .filter(t => t.status === 'completed' && t.result)
                      .map(t => `【${t.agent}】\n${t.result}`)
                      .join('\n\n---\n\n');
                    navigator.clipboard.writeText(allResults);
                    setCopiedId('__all__');
                    setTimeout(() => setCopiedId(null), 1500);
                  }}
                  className="flex items-center justify-center gap-1.5 px-4 py-2 bg-background border border-border rounded-lg text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
                >
                  <icons.Copy className="w-3.5 h-3.5" />
                  {copiedId === '__all__' ? '已复制' : '复制全部'}
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});


/* ============================================================ */
/* =====================  卡片子组件  ========================== */
/* ============================================================ */
function TaskCard({
  task, index, isExpanded, onToggleExpand, isParallel,
  isCopied, onCopy, onSendToCanvas, hasSendToCanvas,
}: {
  task: AgentTask;
  index: number;
  isExpanded: boolean;
  onToggleExpand: () => void;
  isParallel: boolean;
  isCopied: boolean;
  onCopy: (text: string) => void;
  onSendToCanvas: () => void;
  hasSendToCanvas: boolean;
}) {
  const config = getAgentConfig(task.agent, task.agentKey);
  const Icon = config.icon;
  const sty = {
    queued:    { label: '等待中', dot: 'bg-muted-foreground', text: 'text-muted-foreground', border: 'border-border', bg: 'bg-muted/30' },
    running:  { label: '处理中', dot: 'bg-primary',  text: 'text-primary', border: 'border-primary/20', bg: 'bg-primary/5' },
    completed:{ label: '已完成', dot: 'bg-emerald-500', text: 'text-emerald-600',border: 'border-emerald-100',bg: 'bg-emerald-50/20' },
    failed:   { label: '失败',   dot: 'bg-destructive',   text: 'text-destructive',  border: 'border-destructive/20',  bg: 'bg-destructive/5' },
  }[task.status];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: index * 0.04, duration: 0.2 }}
      className={`relative rounded-xl border transition-all ${sty.border} ${sty.bg} ${
        task.status === 'running' ? 'shadow-sm ring-1 ring-primary/10' : ''
      }`}
    >
      {/* 并行角标 */}
      {isParallel && task.status === 'running' && (
        <div className="absolute -top-1 -right-1 w-4 h-4 bg-primary rounded-full flex items-center justify-center">
          <icons.Zap className="w-2.5 h-2.5 text-white" />
        </div>
      )}

      <button onClick={onToggleExpand} className="w-full text-left p-3">
        {/* Agent 头 */}
        <div className="flex items-center gap-2 mb-1.5">
          <div className={`w-7 h-7 rounded-lg ${config.bgColor} flex items-center justify-center flex-shrink-0`}>
            {task.status === 'running'
              ? <icons.Loader2 className={`w-3.5 h-3.5 ${config.color} animate-spin`} />
              : <Icon className={`w-3.5 h-3.5 ${config.color}`} />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground truncate">{task.agent}</p>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <span className={`w-1.5 h-1.5 rounded-full ${sty.dot} ${task.status === 'running' ? 'animate-pulse' : ''}`} />
            <span className={`text-[10px] font-medium ${sty.text}`}>{sty.label}</span>
          </div>
        </div>

        {/* 进度条 */}
        {task.status === 'running' && (
          <div className="mb-1">
            <div className="w-full bg-background rounded-full h-1">
              <motion.div className="h-1 rounded-full bg-primary"
                animate={{ width: `${task.progress}%` }} transition={{ duration: 0.3 }} />
            </div>
            <div className="flex justify-between mt-0.5">
              <span className="text-[9px] text-muted-foreground">{task.progress}%</span>
              {task.elapsed !== undefined && (
                <span className="text-[9px] text-muted-foreground flex items-center gap-0.5">
                  <icons.Clock className="w-2.5 h-2.5" />{task.elapsed}s
                </span>
              )}
            </div>
          </div>
        )}

        {/* 摘要 */}
        {task.status === 'completed' && task.result && !isExpanded && (
          <div className="flex items-start gap-1">
            <icons.CheckCircle className="w-3 h-3 text-emerald-500 flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-emerald-600 leading-relaxed line-clamp-1">{task.result}</p>
          </div>
        )}
        {task.status === 'failed' && (
          <div className="flex items-center gap-1">
            <icons.XCircle className="w-3 h-3 text-destructive" /><span className="text-[10px] text-destructive">处理失败</span>
          </div>
        )}

        {/* 底部 */}
        <div className="flex items-center justify-between mt-1.5">
          {task.status === 'completed' && task.elapsed !== undefined && (
            <span className="text-[9px] text-muted-foreground flex items-center gap-0.5">
              <icons.Clock className="w-2.5 h-2.5" />耗时 {task.elapsed}s
            </span>
          )}
          {task.status === 'queued' && <span className="text-[9px] text-muted-foreground/50">等待前序任务...</span>}
          <div className="flex-1" />
          {task.status === 'completed' && task.result && (
            <span className="text-[9px] text-primary">
              {isExpanded ? <icons.ChevronUp className="w-3 h-3" /> : <icons.ChevronDown className="w-3 h-3" />}
            </span>
          )}
        </div>
      </button>

      {/* 展开详情 + 操作按钮 */}
      <AnimatePresence>
        {isExpanded && task.result && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-0">
              <div className="border-t border-border pt-2">
                <p className="text-[11px] text-muted-foreground leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {task.result}
                </p>
                {/* 操作按钮行 */}
                <div className="flex items-center gap-1.5 mt-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); onCopy(task.result || ''); }}
                    className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-muted-foreground bg-muted/50 hover:bg-muted rounded-md transition-colors border border-border"
                  >
                    <icons.Copy className="w-3 h-3" />
                    {isCopied ? '已复制' : '复制'}
                  </button>
                  {hasSendToCanvas && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onSendToCanvas(); }}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-primary bg-primary/5 hover:bg-primary/10 rounded-md transition-colors border border-primary/10"
                    >
                      <icons.Send className="w-3 h-3" />
                      发送到画布
                    </button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
