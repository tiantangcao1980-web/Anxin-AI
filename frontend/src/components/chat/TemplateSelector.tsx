/**
 * TemplateSelector - 常用模板快速选择器
 *
 * 展示常用法务文档模板列表，选择后预填聊天输入框。
 */

import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { heading, iconSize } from '@/lib/design-tokens';

interface Template {
  id: string;
  name: string;
  description?: string;
}

export const BUILTIN_TEMPLATES: Template[] = [
  { id: 'nda', name: '保密协议', description: '适用于商业合作前的保密约定' },
  { id: 'labor', name: '劳动合同', description: '标准劳动合同模板' },
  { id: 'service', name: '服务协议', description: '技术/咨询服务合同' },
  { id: 'lawyer-letter', name: '律师函', description: '催告、警告、协商函' },
  { id: 'legal-opinion', name: '法律意见书', description: '专项法律问题分析意见' },
];

export function getBuiltinTemplateById(templateId: string | null | undefined) {
  if (!templateId) return null;
  return BUILTIN_TEMPLATES.find((template) => template.id === templateId) ?? null;
}

interface TemplateSelectorProps {
  onSelect: (template: Template) => void;
  onClose: () => void;
}

export function TemplateSelector({ onSelect, onClose }: TemplateSelectorProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className="bg-background border border-border rounded-xl shadow-xl p-2 min-w-[220px] z-[9999]"
    >
      <p className={`${heading.muted} px-2 py-1`}>常用模板</p>
      {BUILTIN_TEMPLATES.map((t) => (
        <button
          key={t.id}
          onClick={() => {
            onSelect(t);
            onClose();
          }}
          className="w-full flex items-start gap-2.5 px-2.5 py-2 rounded-lg hover:bg-muted text-left transition-colors"
        >
          <icons.FileText className={`${iconSize.sm} text-primary mt-0.5 flex-shrink-0`} />
          <div className="min-w-0">
            <p className={heading.card}>{t.name}</p>
            {t.description && (
              <p className={`${heading.micro} mt-0.5`}>{t.description}</p>
            )}
          </div>
        </button>
      ))}
    </motion.div>
  );
}
