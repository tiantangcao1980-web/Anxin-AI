/**
 * 表单 Sheet 组件
 * 类似千问的底部弹出规格选择面板（杯型/温度/甜度）
 * → 法务场景：案件类型选择、服务定制、信息收集
 */

import { memo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import type { FormSheetComponent, FormSection, A2UIEventHandler } from '../types';
import { cn } from '@/lib/utils';

interface Props {
  component: FormSheetComponent;
  onEvent: A2UIEventHandler;
}

export const FormSheet = memo(function FormSheet({ component, onEvent }: Props) {
  const { data } = component;
  const [formValues, setFormValues] = useState<Record<string, any>>(() => {
    const defaults: Record<string, any> = {};
    data.sections.forEach((section) => {
      if (section.defaultValue !== undefined) {
        defaults[section.id] = section.defaultValue;
      }
    });
    return defaults;
  });
  const [isOpen, setIsOpen] = useState(data.asSheet !== false);

  const updateField = useCallback((sectionId: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [sectionId]: value }));
  }, []);

  const handleSubmit = () => {
    onEvent({
      type: 'form-submit',
      actionId: data.submitAction.actionId,
      componentId: component.id,
      formData: formValues,
    });
  };

  const handleCancel = () => {
    if (data.cancelAction) {
      onEvent({
        type: 'action',
        actionId: data.cancelAction.actionId,
        componentId: component.id,
      });
    }
    setIsOpen(false);
  };

  const renderSection = (section: FormSection) => {
    const currentValue = formValues[section.id];

    switch (section.type) {
      case 'single-select':
        return (
          <div className="flex flex-wrap gap-2">
            {section.options?.map((opt) => {
              const selected = currentValue === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => !opt.disabled && updateField(section.id, opt.id)}
                  disabled={opt.disabled}
                  className={cn(
                    'relative px-4 py-2 rounded-xl text-sm font-medium transition-all duration-150',
                    'border-2',
                    selected
                      ? 'border-primary bg-primary/5 text-primary dark:bg-primary/10 dark:text-primary dark:border-primary'
                      : 'border-border bg-background text-foreground hover:border-border',
                    opt.disabled && 'opacity-50 cursor-not-allowed',
                  )}
                >
                  {opt.label}
                  {opt.price && (
                    <span className="ml-1.5 text-xs text-muted-foreground/70">
                      ¥{opt.price.amount}
                    </span>
                  )}
                  {selected && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-primary rounded-full flex items-center justify-center"
                    >
                      <icons.Check className="w-2.5 h-2.5 text-white" />
                    </motion.div>
                  )}
                </button>
              );
            })}
          </div>
        );

      case 'multi-select':
        return (
          <div className="flex flex-wrap gap-2">
            {section.options?.map((opt) => {
              const selectedList = (currentValue || []) as string[];
              const selected = selectedList.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  onClick={() => {
                    if (opt.disabled) return;
                    const next = selected
                      ? selectedList.filter((id) => id !== opt.id)
                      : [...selectedList, opt.id];
                    updateField(section.id, next);
                  }}
                  disabled={opt.disabled}
                  className={cn(
                    'px-4 py-2 rounded-xl text-sm font-medium transition-all border-2',
                    selected
                      ? 'border-primary bg-primary/5 text-primary dark:bg-primary/10 dark:text-primary'
                      : 'border-border bg-background text-foreground hover:border-border',
                    opt.disabled && 'opacity-50 cursor-not-allowed',
                  )}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
        );

      case 'text-input':
        return (
          <input
            type="text"
            value={currentValue || ''}
            onChange={(e) => updateField(section.id, e.target.value)}
            placeholder={section.placeholder || '请输入...'}
            className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
          />
        );

      case 'textarea':
        return (
          <textarea
            value={currentValue || ''}
            onChange={(e) => updateField(section.id, e.target.value)}
            placeholder={section.placeholder || '请输入详细描述...'}
            rows={3}
            className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-sm text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition resize-none"
          />
        );

      case 'date-picker':
        return (
          <div className="relative">
            <input
              type="date"
              value={currentValue || ''}
              onChange={(e) => updateField(section.id, e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-background text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition"
            />
            <icons.Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/70 pointer-events-none" />
          </div>
        );

      case 'file-upload':
        return (
          <label className="flex items-center justify-center gap-2 px-4 py-6 rounded-xl border-2 border-dashed border-border bg-muted/50 cursor-pointer hover:border-primary hover:bg-primary/5 transition">
            <icons.Upload className="w-5 h-5 text-muted-foreground/70" />
            <span className="text-sm text-muted-foreground">{section.placeholder || '点击上传文件'}</span>
            <input type="file" className="hidden" onChange={(e) => updateField(section.id, e.target.files?.[0]?.name)} />
          </label>
        );

      default:
        return null;
    }
  };

  const content = (
    <div className={cn(
      'a2ui-form-sheet bg-background rounded-2xl border border-border/50 shadow-sm overflow-hidden',
      component.className,
    )}>
      {/* 头部摘要 */}
      {data.header && (
        <div className="flex gap-3 p-4 border-b border-border/50">
          {data.header.image && (
            <div className="w-16 h-16 rounded-xl overflow-hidden bg-muted flex-shrink-0">
              <img src={data.header.image} alt="" className="w-full h-full object-cover" />
            </div>
          )}
          <div className="flex-1">
            <h4 className="font-semibold text-sm text-foreground">
              {data.header.title}
            </h4>
            {data.header.subtitle && (
              <p className="text-xs text-muted-foreground mt-0.5">{data.header.subtitle}</p>
            )}
            {data.header.price && (
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className="text-base font-bold text-foreground">
                  ¥{data.header.price.amount}
                </span>
                {data.header.price.original && (
                  <span className="text-xs text-muted-foreground/70 line-through">
                    ¥{data.header.price.original}
                  </span>
                )}
              </div>
            )}
          </div>
          {data.cancelAction && (
            <button onClick={handleCancel} className="self-start p-1 rounded-full hover:bg-muted">
              <icons.X className="w-4 h-4 text-muted-foreground/70" />
            </button>
          )}
        </div>
      )}

      {/* 标题（无header时显示） */}
      {!data.header && data.title && (
        <div className="flex items-center justify-between p-4 pb-2">
          <h4 className="font-semibold text-base text-foreground">
            {data.title}
          </h4>
          {data.cancelAction && (
            <button onClick={handleCancel} className="p-1 rounded-full hover:bg-muted">
              <icons.X className="w-4 h-4 text-muted-foreground/70" />
            </button>
          )}
        </div>
      )}

      {data.subtitle && !data.header && (
        <p className="text-xs text-muted-foreground px-4 pb-2">{data.subtitle}</p>
      )}

      {/* 表单分区 */}
      <div className="p-4 space-y-5 max-h-[60vh] overflow-y-auto">
        {data.sections.map((section) => (
          <div key={section.id}>
            <label className="block text-sm font-medium text-foreground mb-2">
              {section.label}
              {section.required && <span className="text-red-500 ml-0.5">*</span>}
            </label>
            {section.description && (
              <p className="text-xs text-muted-foreground/70 mb-2">{section.description}</p>
            )}
            {renderSection(section)}
          </div>
        ))}
      </div>

      {/* 提交按钮 */}
      <div className="p-4 border-t border-border/50">
        <button
          onClick={handleSubmit}
          className={cn(
            'w-full py-3 rounded-xl text-sm font-semibold transition-all active:scale-[0.98]',
            data.submitAction.variant === 'secondary'
              ? 'bg-muted text-foreground hover:bg-accent'
              : 'bg-primary text-white hover:bg-primary/90',
          )}
        >
          {data.submitAction.label}
        </button>
      </div>
    </div>
  );

  // 如果是 Sheet 模式，用动画包裹
  if (data.asSheet) {
    return (
      <AnimatePresence>
        {isOpen && (
          <>
            {/* 遮罩 */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/30 z-40"
              onClick={handleCancel}
            />
            {/* Sheet */}
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed bottom-0 left-0 right-0 z-50 max-h-[85vh]"
            >
              <div className="bg-background rounded-t-3xl shadow-2xl">
                {/* Sheet 把手 */}
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-10 h-1 rounded-full bg-muted-foreground/50" />
                </div>
                {content}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    );
  }

  return content;
});
