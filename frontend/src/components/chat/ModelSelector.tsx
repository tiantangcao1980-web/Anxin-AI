/**
 * ModelSelector - AI 模型选择器组件
 *
 * 位于聊天输入框工具栏，允许用户在对话中切换不同 LLM 模型。
 * 使用 design-tokens 中定义的 modelSelector Token。
 */

import { useState, useRef, useEffect } from 'react';
import { icons } from '@/lib/icons';
import { modelSelector } from '@/lib/design-tokens';

interface ModelOption {
  id: string;
  name: string;
  provider: string;
  model: string;
  is_default: boolean;
}

interface ModelSelectorProps {
  models: ModelOption[];
  selectedModelId: string | null;
  onSelectModel: (modelId: string | null) => void;
  disabled?: boolean;
}

export function ModelSelector({
  models,
  selectedModelId,
  onSelectModel,
  disabled = false,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const current = models.find((m) => m.id === selectedModelId);
  const displayName = current?.name || '默认模型';

  if (models.length <= 1) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => !disabled && setOpen(!open)}
        className={modelSelector.trigger}
        disabled={disabled}
        title="切换 AI 模型"
      >
        <icons.Cpu className="w-3.5 h-3.5" />
        <span className="max-w-[100px] truncate">{displayName}</span>
        <icons.ChevronDown className="w-3 h-3" />
      </button>

      {open && (
        <div className={`absolute bottom-full mb-1 left-0 z-50 ${modelSelector.dropdown}`}>
          {/* 默认选项 */}
          <button
            onClick={() => {
              onSelectModel(null);
              setOpen(false);
            }}
            className={!selectedModelId ? modelSelector.optionActive : modelSelector.option}
          >
            <span>默认模型</span>
            {!selectedModelId && <icons.Check className="w-4 h-4 text-primary" />}
          </button>

          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => {
                onSelectModel(m.id);
                setOpen(false);
              }}
              className={selectedModelId === m.id ? modelSelector.optionActive : modelSelector.option}
            >
              <div className="flex items-center gap-2">
                <span>{m.name}</span>
                <span className={m.is_default ? modelSelector.badgeDefault : modelSelector.badge}>
                  {m.provider}
                </span>
              </div>
              {selectedModelId === m.id && <icons.Check className="w-4 h-4 text-primary" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
