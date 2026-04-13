/**
 * 分析视图 Tab
 * 
 * 组合现有的 RiskRadar、DocumentDiff、KnowledgeGraphView 组件
 * 提供统一的垂直堆叠布局
 */

import { useState, memo } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { RiskRadar } from'./RiskRadar';
import { DocumentDiff } from'./DocumentDiff';
import { KnowledgeGraphView } from'./KnowledgeGraphView';
import type { AnalysisData } from'@/lib/store';

interface AnalysisViewProps {
 data: AnalysisData;
}

export const AnalysisView = memo(function AnalysisView({ data }: AnalysisViewProps) {
 const hasAny = data.riskRadar || data.documentDiff || data.knowledgeGraph;

 if (!hasAny) {
 return (
 <div className="h-full flex items-center justify-center">
 <div className="text-center space-y-4 px-8">
 <div className="w-20 h-20 mx-auto bg-muted rounded-full flex items-center justify-center">
 <icons.BarChart3 className="w-10 h-10 text-muted-foreground" />
 </div>
 <div>
 <h3 className="font-medium text-foreground mb-2">分析视图</h3>
 <p className="text-sm text-muted-foreground leading-relaxed">
 合同审查、风险评估完成后<br />将在此展示专业分析结果
 </p>
 </div>
 <div className="pt-4 flex flex-wrap gap-2 justify-center">
 {['风险雷达','文档对比','知识图谱','舆情分析'].map(tag => (
 <span key={tag} className="px-3 py-1 bg-background rounded-full text-xs text-muted-foreground border border-border">
 {tag}
 </span>
 ))}
 </div>
 </div>
 </div>
 );
 }

 return (
 <div className="h-full overflow-y-auto">
 {data.riskRadar && (
 <AnalysisSection
 title="风险雷达"
 icon={icons.Shield}
 iconColor="text-destructive bg-destructive/10"
 defaultOpen
 >
 <RiskRadar data={data.riskRadar} />
 </AnalysisSection>
 )}

 {data.documentDiff && (
 <AnalysisSection
 title="文档对比"
 icon={icons.FileSearch}
 iconColor="text-primary bg-primary/5"
 defaultOpen
 >
 <DocumentDiff />
 </AnalysisSection>
 )}

 {data.knowledgeGraph && (
 <AnalysisSection
 title="知识图谱"
 icon={icons.GitBranch}
 iconColor="text-primary bg-primary/5"
 defaultOpen
 >
 <div className="h-[400px]">
 <KnowledgeGraphView data={data.knowledgeGraph} />
 </div>
 </AnalysisSection>
 )}
 </div>
 );
});


// ========== 折叠分析块 ==========
function AnalysisSection({
 title,
 icon: Icon,
 iconColor,
 defaultOpen = true,
 children,
}: {
 title: string;
 icon: React.ElementType;
 iconColor: string;
 defaultOpen?: boolean;
 children: React.ReactNode;
}) {
 const [open, setOpen] = useState(defaultOpen);

 return (
 <div className="border-b border-border">
 <button
 onClick={() => setOpen(!open)}
 className="w-full flex items-center gap-3 px-4 py-3 hover:bg-muted transition-colors"
 >
 <div className={`p-1.5 rounded-lg ${iconColor}`}>
 <Icon className="w-4 h-4" />
 </div>
 <span className="text-sm font-medium text-foreground flex-1 text-left">{title}</span>
 {open ? (
 <icons.ChevronDown className="w-4 h-4 text-muted-foreground" />
 ) : (
 <icons.ChevronRight className="w-4 h-4 text-muted-foreground" />
 )}
 </button>

 <AnimatePresence>
 {open && (
 <motion.div
 initial={{ height: 0, opacity: 0 }}
 animate={{ height:'auto', opacity: 1 }}
 exit={{ height: 0, opacity: 0 }}
 transition={{ duration: 0.2 }}
 className="overflow-hidden"
 >
 <div className="px-4 pb-4">{children}</div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
}
