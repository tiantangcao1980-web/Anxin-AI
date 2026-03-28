/**
 * ClarificationBubble — 引导式问答气泡组件
 * 
 * 核心功能：
 * 1. 选择后立即锁定（不可修改、不可多选）
 * 2. 提交后不再输出选择内容到对话流（直接显示"已确认"状态）
 * 3. 提交后的选择以紧凑标签形式展示，不重复出现
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';

interface ClarificationBubbleProps {
  message: string;
  questions: { question: string; options: string[] }[];
  originalContent: string;
  onSubmit?: (originalContent: string, selections: Record<string, string>) => void;
  disabled: boolean;
}

export function ClarificationBubble({
  message,
  questions,
  originalContent,
  onSubmit,
  disabled,
}: ClarificationBubbleProps) {
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleSelect = (question: string, option: string) => {
    // 已提交或已有选择时不可更改（单选锁定）
    if (submitted || selections[question]) return;
    setSelections(prev => ({ ...prev, [question]: option }));
  };

  const handleSubmit = () => {
    if (submitted || disabled) return;
    const valid = Object.fromEntries(Object.entries(selections).filter(([_, v]) => v));
    if (Object.keys(valid).length === 0) return;
    setSubmitted(true);
    // 直接发送到后端，不在对话流中重复输出选择文字
    onSubmit?.(originalContent, valid);
  };

  const answeredCount = Object.values(selections).filter(v => v).length;
  const allAnswered = answeredCount === questions.length;

  // 提交后的紧凑视图
  if (submitted) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
        <div className="w-8 h-8 rounded-full bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center flex-shrink-0">
          <icons.CheckCircle className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div className="flex flex-col gap-1 max-w-[80%]">
          <div className="bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800 rounded-2xl rounded-tl-none px-4 py-3">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">已确认需求</span>
              <icons.Loader2 className="w-3 h-3 animate-spin text-emerald-600 dark:text-emerald-400" />
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400">处理中...</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(selections).filter(([_, v]) => v).map(([q, a]) => (
                <span key={q} className="inline-flex items-center gap-1 px-2 py-1 bg-background rounded-lg text-[11px] text-foreground border border-emerald-200 dark:border-emerald-800">
                  <icons.CheckCircle className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" />
                  {a}
                </span>
              ))}
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
      <div className="w-8 h-8 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0">
        <icons.HelpCircle className="h-4 w-4 text-amber-500" />
      </div>
      <div className="flex flex-col gap-1.5 max-w-[85%]">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground ml-1">
          <icons.Sparkles className="h-3 w-3 text-amber-500" /> 需求确认
        </div>
        <div className="bg-background border border-border rounded-2xl rounded-tl-none px-4 py-3.5 shadow-sm">
          <p className="text-sm text-foreground mb-3 leading-relaxed">{message}</p>
          <div className="space-y-3">
            {questions.map((q, qi) => {
              const isAnswered = !!selections[q.question];
              return (
                <div key={qi}>
                  <p className="text-xs font-medium text-foreground mb-1.5">{q.question}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {q.options.map((opt, oi) => {
                      const isSelected = selections[q.question] === opt;
                      const isLocked = isAnswered && !isSelected;
                      return (
                        <button
                          key={oi}
                          onClick={() => handleSelect(q.question, opt)}
                          disabled={isLocked}
                          className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                            isSelected
                              ? 'bg-primary text-white border-primary shadow-sm scale-[1.02]'
                              : isLocked
                              ? 'bg-muted text-muted-foreground border-border cursor-not-allowed'
                              : 'bg-background text-muted-foreground border-border hover:border-primary/50 hover:text-primary hover:bg-primary/10 cursor-pointer active:scale-95'
                          }`}
                        >
                          {opt}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          {/* 确认按钮 — 仅全部选择后显示 */}
          <AnimatePresence>
            {allAnswered && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <button
                  onClick={handleSubmit}
                  disabled={disabled}
                  className="mt-3 w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-all active:scale-[0.98] shadow-sm"
                >
                  <span>确认并继续</span>
                  <icons.ChevronRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
          {!allAnswered && (
            <p className="text-[10px] text-muted-foreground mt-2 text-center">
              请逐一选择 · 已完成 {answeredCount}/{questions.length}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  );
}
