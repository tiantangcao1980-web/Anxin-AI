/**
 * 工作台需求确认卡片 — 单选/多选交互
 *
 * 从左侧对话分析过程中自动触发，在右侧工作台展示
 * 支持单选（radio）和多选（checkbox）两种模式
 * 确认后锁定选择，通过回调通知上层
 */

import { useState, memo } from 'react';
import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import type { WorkspaceConfirmation } from '@/lib/store';

interface WorkspaceConfirmationCardProps {
  confirmation: WorkspaceConfirmation;
  onConfirm: (selectedIds: string[]) => void;
}

// 图标映射
const iconMap: Record<string, React.ElementType> = {
  document: icons.FileText,
  contract: icons.Scale,
  compliance: icons.Shield,
  research: icons.BookOpen,
  litigation: icons.Gavel,
  risk: icons.AlertTriangle,
  company: icons.Building,
  labor: icons.Briefcase,
};

export const WorkspaceConfirmationCard = memo(function WorkspaceConfirmationCard({
  confirmation,
  onConfirm,
}: WorkspaceConfirmationCardProps) {
  const [localSelected, setLocalSelected] = useState<string[]>(confirmation.selectedIds);
  const isConfirmed = confirmation.status === 'confirmed';
  const isSingle = confirmation.type === 'single';

  const handleToggle = (optionId: string) => {
    if (isConfirmed) return;

    if (isSingle) {
      setLocalSelected([optionId]);
    } else {
      setLocalSelected(prev =>
        prev.includes(optionId)
          ? prev.filter(id => id !== optionId)
          : [...prev, optionId]
      );
    }
  };

  const handleConfirm = () => {
    if (localSelected.length === 0 || isConfirmed) return;
    onConfirm(localSelected);
  };

  return (
    <div className={`rounded-xl border overflow-hidden transition-all ${
      isConfirmed
        ? 'border-emerald-200 bg-emerald-50/30'
        : 'border-primary/40 bg-background shadow-sm'
    }`}>
      {/* 头部 */}
      <div className={`px-4 py-3 border-b flex items-center justify-between ${
        isConfirmed
          ? 'bg-emerald-50 border-emerald-100'
          : 'bg-primary/10 border-primary/20'
      }`}>
        <div className="flex items-center gap-2">
          {isConfirmed ? (
            <icons.CheckCircle2 className="w-4 h-4 text-emerald-600" />
          ) : (
            <icons.HelpCircle className="w-4 h-4 text-primary" />
          )}
          <span className="text-sm font-bold text-foreground">{confirmation.title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {isConfirmed ? (
            <span className="flex items-center gap-1 text-[11px] text-emerald-600 font-medium">
              <icons.Lock className="w-3 h-3" />
              已确认
            </span>
          ) : (
            <span className="text-[11px] text-primary font-medium">
              {isSingle ? '单选' : '多选'}
            </span>
          )}
        </div>
      </div>

      {/* 描述 */}
      {confirmation.description && (
        <div className="px-4 pt-3">
          <p className="text-xs text-muted-foreground leading-relaxed">{confirmation.description}</p>
        </div>
      )}

      {/* 选项列表 */}
      <div className="p-3 space-y-2">
        {confirmation.options.map((option) => {
          const isSelected = localSelected.includes(option.id);
          const OptionIcon = option.icon ? (iconMap[option.icon] || icons.Circle) : null;

          return (
            <motion.button
              key={option.id}
              onClick={() => handleToggle(option.id)}
              disabled={isConfirmed}
              whileTap={isConfirmed ? {} : { scale: 0.98 }}
              className={`w-full text-left px-3 py-2.5 rounded-lg border transition-all flex items-center gap-3 ${
                isConfirmed
                  ? isSelected
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-border bg-muted/50 opacity-50'
                  : isSelected
                  ? 'border-primary bg-primary/10 shadow-sm'
                  : 'border-border bg-background hover:border-primary/40 hover:bg-primary/5'
              }`}
            >
              {/* 选择指示器 */}
              <div className="flex-shrink-0">
                {isConfirmed && isSelected ? (
                  <icons.CheckCircle2 className="w-4.5 h-4.5 text-emerald-500" />
                ) : isSingle ? (
                  isSelected ? (
                    <div className="w-4.5 h-4.5 rounded-full border-2 border-primary flex items-center justify-center">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                    </div>
                  ) : (
                    <icons.Circle className="w-4.5 h-4.5 text-muted-foreground" />
                  )
                ) : (
                  isSelected ? (
                    <icons.CheckCircle2 className="w-4.5 h-4.5 text-primary" />
                  ) : (
                    <icons.Circle className="w-4.5 h-4.5 text-muted-foreground" />
                  )
                )}
              </div>

              {/* 图标 */}
              {OptionIcon && (
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  isSelected ? 'bg-primary/10' : 'bg-muted'
                }`}>
                  <OptionIcon className={`w-3.5 h-3.5 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                </div>
              )}

              {/* 文本 */}
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${
                  isSelected ? 'text-foreground' : 'text-muted-foreground'
                }`}>{option.label}</p>
                {option.description && (
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">{option.description}</p>
                )}
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* 确认按钮 */}
      {!isConfirmed && (
        <div className="px-4 pb-3">
          <motion.button
            onClick={handleConfirm}
            disabled={localSelected.length === 0}
            whileHover={localSelected.length > 0 ? { scale: 1.01 } : {}}
            whileTap={localSelected.length > 0 ? { scale: 0.98 } : {}}
            className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              localSelected.length > 0
                ? 'bg-primary text-white hover:bg-primary/90 shadow-sm'
                : 'bg-muted text-muted-foreground cursor-not-allowed'
            }`}
          >
            确认选择
            <icons.ArrowRight className="w-3.5 h-3.5" />
          </motion.button>
        </div>
      )}

      {/* 来源标注 */}
      {confirmation.source && (
        <div className="px-4 pb-2">
          <p className="text-[10px] text-muted-foreground text-right">
            来自 {confirmation.source}
          </p>
        </div>
      )}
    </div>
  );
});
