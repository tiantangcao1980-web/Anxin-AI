import { useState } from 'react';
import { motion } from 'framer-motion';
import { TemplateGallery } from './TemplateGallery';
import { AIGenerator } from './AIGenerator';
import { MyDocuments } from './MyDocuments';
import { icons } from '@/lib/icons';
import { heading, iconSize } from '@/lib/design-tokens';

export function DocumentLibrary() {
  const [activeTab, setActiveTab] = useState<'templates' | 'ai-generate' | 'my-docs'>('templates');
  const [presetDocType, setPresetDocType] = useState<string | undefined>();

  const handleAIGenerate = (docType: string) => {
    setPresetDocType(docType);
    setActiveTab('ai-generate');
  };

  const tabs = [
    { id: 'templates', label: '文档模板', icon: icons.FileText },
    { id: 'ai-generate', label: 'AI 生成', icon: icons.Sparkles },
    { id: 'my-docs', label: '我的文档', icon: icons.FolderOpen },
  ];

  return (
    <div className="h-full flex flex-col bg-muted">
      {/* Header with Tabs */}
      <div className="bg-background border-b border-border px-4 sm:px-6 pt-4 sm:pt-6">
        <div className="mb-3 sm:mb-4">
          <h2 className={heading.page}>智能文档</h2>
          <p className={`${heading.muted} mt-1`}>专业法律文书模板 + AI 智能生成</p>
        </div>

        <div className="flex gap-0.5 sm:gap-1 overflow-x-auto scrollbar-hide">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2.5 rounded-t-xl text-sm font-medium transition-all flex items-center gap-2 relative ${
                  activeTab === tab.id
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className={iconSize.sm} />
                {tab.label}
                {activeTab === tab.id && (
                  <motion.div
                    layoutId="activeTab"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary"
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'templates' && <TemplateGallery onAIGenerate={handleAIGenerate} />}
        {activeTab === 'ai-generate' && <AIGenerator defaultDocType={presetDocType} />}
        {activeTab === 'my-docs' && <MyDocuments />}
      </div>
    </div>
  );
}