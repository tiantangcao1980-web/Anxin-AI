/**
 * 思考链/推理过程组件 — 保留原有交互风格
 *
 * 设计参考截图：
 * - 头部：「思考过程（N 步）▽」可折叠
 * - 每一步：圆形图标 + Agent 名称（加粗）+ 阶段标签（彩色 pill）
 * - 内容区：Markdown 渲染，结构化字段展示
 * - 步骤间有连接线
 * - 思考中时显示动态指示
 * - 默认展开，可手动收拢
 */

import { useState, memo } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { iconSize, heading, statusBadge, spacing } from'@/lib/design-tokens';
import type { ThinkingStep } from'@/lib/store';
import ReactMarkdown from'react-markdown';

interface ThinkingChainProps {
 steps: ThinkingStep[];
 isThinking: boolean;
}

// 意图代码 → 中文标签映射（前端防御性翻译，防止后端未翻译的代码直接展示）
const INTENT_LABELS: Record<string, string> = {
 QA_CONSULTATION:'法律咨询',
 CONTRACT_REVIEW:'合同审查',
 DUE_DILIGENCE:'尽职调查',
 DOCUMENT_DRAFTING:'文书起草',
 LITIGATION_STRATEGY:'诉讼策略',
 IP_PROTECTION:'知识产权保护',
 REGULATORY_MONITORING:'合规监管',
 TAX_FINANCE:'财税合规',
 LABOR_HR:'劳动人事',
 EVIDENCE_PROCESSING:'证据处理',
 E_SIGNATURE:'电子签约',
 CONTRACT_MANAGEMENT:'合同管理',
 POLICY_DISTRIBUTION:'制度分发',
 COMPLEX_TASK:'复合任务',
};

/**
 * 将思考内容中的英文技术代码翻译为用户友好的中文
 * 例如:
 *"意图识别: LABOR_HR" →"意图识别: 劳动人事"
 *"规划理由: Template Fast Path for intent=LABOR_HR" →"规划理由: 基于劳动人事场景模板快速规划"
 */
function localizeContent(content: string): string {
 let result = content;

 // 替换"意图识别: INTENT_CODE" 中的意图代码
 result = result.replace(
 /(\*{0,2}意图识别\*{0,2}\s*[:：]\s*)([A-Z_]+)/g,
 (_, prefix, code) => `${prefix}${INTENT_LABELS[code] || code}`
 );

 // 替换"Template Fast Path for intent=XXX" 模式
 result = result.replace(
 /Template Fast Path for intent=([A-Z_]+)/g,
 (_, code) => `基于${INTENT_LABELS[code] || code}场景模板快速规划`
 );

 // 替换其他可能出现的裸意图代码（在冒号后面的独立单词）
 for (const [code, label] of Object.entries(INTENT_LABELS)) {
 result = result.replace(new RegExp(`([:：]\\s*)${code}(\\s|$|\\n|\\*)`,'g'), `$1${label}$2`);
 }

 return result;
}

const phaseConfig: Record<string, { label: string; icon: React.ElementType; iconColor: string; badgeColor: string }> = {
 requirement: {
 label:'需求分析',
 icon: icons.Target,
 iconColor:'text-warning bg-warning/10 border-warning/20',
 badgeColor:'text-warning bg-warning/10 border border-warning/20',
 },
 planning: {
 label:'任务规划',
 icon: icons.Layers,
 iconColor:'text-primary bg-primary/5 border-primary/30',
 badgeColor:'text-primary bg-primary/5 border border-primary/20',
 },
 execution: {
 label:'推理过程',
 icon: icons.Brain,
 iconColor:'text-violet-500 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30 border-violet-200 dark:border-violet-800',
 badgeColor:'text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800',
 },
 result: {
 label:'执行完成',
 icon: icons.CheckCircle2,
 iconColor:'text-success bg-success/10 border-success/20',
 badgeColor:'text-success bg-success/10 border border-success/20',
 },
};

export const ThinkingChain = memo(function ThinkingChain({
 steps,
 isThinking,
}: ThinkingChainProps) {
 const [expanded, setExpanded] = useState(true);

 if (steps.length === 0 && !isThinking) return null;

 return (
 <div className="mx-4 md:mx-8 mb-3">
 {/* 头部 — 「思考过程（N 步）▽」 */}
 <button
 onClick={() => setExpanded(!expanded)}
 className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors py-1.5 group"
 >
 {/* 思考图标 */}
 <div className="relative flex-shrink-0">
 <icons.Brain className={`${iconSize.sm} ${isThinking ?'text-primary' :'text-muted-foreground'}`} />
 {isThinking && (
 <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-primary rounded-full animate-ping" />
 )}
 </div>

 <span className={heading.card}>思考过程</span>
 <span className={heading.muted}>（{steps.length} 步）</span>

 {isThinking && (
 <icons.Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
 )}

 <motion.div
 animate={{ rotate: expanded ? 0 : -90 }}
 transition={{ duration: 0.2 }}
 className="flex-shrink-0"
 >
 <icons.ChevronDown className={`${iconSize.sm} text-muted-foreground group-hover:text-foreground`} />
 </motion.div>
 </button>

 {/* 展开内容 */}
 <AnimatePresence>
 {expanded && (
 <motion.div
 initial={{ height: 0, opacity: 0 }}
 animate={{ height:'auto', opacity: 1 }}
 exit={{ height: 0, opacity: 0 }}
 transition={{ duration: 0.25, ease:'easeInOut' }}
 className="overflow-hidden"
 >
 <div className={`ml-6 pl-4 border-l-2 border-dashed border-border ${spacing.sectionCompact} mt-1 pb-1`}>
 {steps.map((step, index) => {
 const config = phaseConfig[step.phase] || phaseConfig.execution;
 const Icon = config.icon;

 return (
 <motion.div
 key={step.id}
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.08, duration: 0.3 }}
 className="flex gap-3 items-start relative"
 >
 {/* 左侧连接线上的圆形图标 */}
 <div className={`w-7 h-7 rounded-full border flex items-center justify-center flex-shrink-0 -ml-[18px] bg-background ${config.iconColor}`}>
 <Icon className="w-3.5 h-3.5" />
 </div>

 {/* 右侧内容 */}
 <div className="flex-1 min-w-0 pt-0.5">
 {/* Agent 名称 + 阶段标签 */}
 <div className="flex items-center gap-2 mb-1.5">
 <span className="text-sm font-medium text-foreground">
 {step.agent ||'分析'}
 </span>
 <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${config.badgeColor}`}>
 {config.label}
 </span>
 </div>

 {/* 思考内容 — Markdown 渲染（自动翻译技术代码为中文） */}
 <div className="text-sm text-muted-foreground leading-relaxed prose prose-sm max-w-none prose-p:my-0.5 prose-p:text-muted-foreground prose-strong:text-foreground prose-strong:font-semibold prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs">
 <ReactMarkdown>{localizeContent(step.content)}</ReactMarkdown>
 </div>

 {/* DAG 规划步骤（如果有） */}
 {step.planSteps && step.planSteps.length > 0 && (
 <div className="mt-2 space-y-1.5">
 {step.planSteps.map((ps, i) => (
 <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
 <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-bold text-muted-foreground flex-shrink-0 mt-0.5">
 {i + 1}
 </div>
 <div className="min-w-0">
 <span className="font-semibold text-foreground">{ps.agent}</span>
 {ps.instruction && (
 <span className="ml-1 text-muted-foreground">{ps.instruction}</span>
 )}
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 </motion.div>
 );
 })}

 {/* 思考中状态指示 */}
 {isThinking && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 className="flex items-center gap-2.5 relative"
 >
 <div className="w-7 h-7 rounded-full border border-primary bg-primary/10 flex items-center justify-center flex-shrink-0 -ml-[18px]">
 <icons.Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
 </div>
 <span className="text-sm text-primary font-medium">正在推理...</span>
 </motion.div>
 )}
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
});
