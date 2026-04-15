import { useState } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';
import { heading } from'@/lib/design-tokens';

interface WelcomeGuideProps {
 onClose: () => void;
 onSelectView: (view: string) => void;
}

const features = [
 {
 id:'chat',
 icon: icons.MessageSquare,
 title:'智能对话',
 description:'AI 驱动的合同审查，多智能体协同分析',
 color:'bg-primary',
 highlights: ['文件加密保护','风险雷达分析','文档对比优化'],
 },
 {
 id:'cases',
 icon: icons.Briefcase,
 title:'案件管理',
 description:'全生命周期案件追踪与协作',
 color:'bg-primary',
 highlights: ['进度可视化','任务分配','活动时间线'],
 },
 {
 id:'documents',
 icon: icons.FileStack,
 title:'智能文档',
 description:'专业模板 + AI 智能生成文书',
 color:'from-success to-success',
 highlights: ['海量模板','AI 生成','版本管理'],
 },
 {
 id:'dashboard',
 icon: icons.BarChart3,
 title:'监控看板',
 description:'实时律所运营数据分析',
 color:'from-warning to-warning',
 highlights: ['团队负载','案件分布','合规评分'],
 },
 {
 id:'due-diligence',
 icon: icons.Search,
 title:'尽职调查',
 description:'舆情分析 + 关系图谱可视化',
 color:'from-pink-500 to-pink-600',
 highlights: ['舆情监控','涉诉查询','合规检测'],
 },
 {
 id:'ai-assistant',
 icon: icons.GraduationCap,
 title:'司法学院',
 description:'新律师智能批注辅助系统',
 color:'bg-primary',
 highlights: ['智能批注','成长追踪','知识库'],
 },
];

export function WelcomeGuide({ onClose, onSelectView }: WelcomeGuideProps) {
 const [currentStep, setCurrentStep] = useState(0);

 return (
 <div className="fixed inset-0 bg-black/30 backdrop-blur-md z-50 flex items-center justify-center p-6">
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 className="relative bg-background rounded-3xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden"
 >
 {/* Close button */}
 <button
 onClick={onClose}
 className="absolute top-6 right-6 z-10 p-2 hover:bg-muted rounded-full transition-colors"
 >
 <icons.X className="w-5 h-5 text-muted-foreground" />
 </button>

 {/* Header */}
 <div className="bg-background px-8 py-6 border-b border-border flex items-center gap-4">
 <motion.div
 initial={{ scale: 0 }}
 animate={{ scale: 1 }}
 transition={{ delay: 0.1, type:'spring', stiffness: 200 }}
 className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center shadow-lg flex-shrink-0"
 >
 <icons.Sparkles className="w-7 h-7 text-white" />
 </motion.div>
 <div className="flex-1 text-left">
 <h1 className={heading.page}>欢迎使用 AI 法务协同系统</h1>
 <p className="text-muted-foreground text-sm mt-0.5">Agent-Native 智能法律服务平台</p>
 </div>
 </div>

 {/* Features Grid */}
 <div className="p-6">
 <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 lg:gap-4 mb-5">
 {features.map((feature, index) => {
 const Icon = feature.icon;
 const bgColors = {
 chat:'bg-primary',
 cases:'bg-violet-500',
 documents:'bg-success',
 dashboard:'bg-warning',
'due-diligence':'bg-pink-500',
'ai-assistant':'bg-sky-400',
 };

 return (
 <motion.button
 key={feature.id}
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.05 }}
 onClick={() => {
 onSelectView(feature.id);
 onClose();
 }}
 className="group bg-background border border-border rounded-2xl p-4 lg:p-5 hover:border-border/80 hover:shadow-lg transition-all text-left active:scale-98"
 >
 <div className={`w-10 h-10 lg:w-12 lg:h-12 ${bgColors[feature.id as keyof typeof bgColors]} rounded-xl lg:rounded-2xl flex items-center justify-center mb-3 lg:mb-4 shadow-sm`}>
 <Icon className="w-5 h-5 lg:w-6 lg:h-6 text-white" />
 </div>
 <h3 className="font-medium text-foreground mb-1 lg:mb-1.5 text-sm lg:text-base">
 {feature.title}
 </h3>
 <p className="text-xs lg:text-sm text-muted-foreground mb-3 lg:mb-4 leading-relaxed line-clamp-2">
 {feature.description}
 </p>
 <div className="space-y-1 lg:space-y-1.5">
 {feature.highlights.map((highlight) => (
 <div key={highlight} className="flex items-center gap-2 text-xs text-muted-foreground">
 <div className="w-1 h-1 lg:w-1.5 lg:h-1.5 rounded-full bg-border flex-shrink-0"></div>
 <span className="truncate">{highlight}</span>
 </div>
 ))}
 </div>
 <icons.ArrowRight className="absolute bottom-4 lg:bottom-5 right-4 lg:right-5 w-4 h-4 lg:w-5 lg:h-5 text-border opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all" />
 </motion.button>
 );
 })}
 </div>

 {/* Quick Start */}
 <div className="bg-muted rounded-2xl p-4 lg:p-5">
 <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3">
 <div>
 <h3 className="font-medium text-foreground mb-1 lg:mb-1.5 text-sm lg:text-base">快速开始</h3>
 <p className="text-xs lg:text-sm text-muted-foreground">
 选择任意功能模块开始体验 AI 法务协同系统
 </p>
 </div>
 <button
 onClick={() => {
 onSelectView('chat');
 onClose();
 }}
 className="w-full lg:w-auto px-5 lg:px-6 py-2.5 lg:py-3 bg-primary text-white rounded-xl hover:bg-primary/90 active:scale-95 transition-all flex items-center justify-center gap-2 font-medium shadow-sm text-sm"
 >
 开始使用
 <icons.ArrowRight className="w-4 h-4 lg:w-5 lg:h-5" />
 </button>
 </div>
 </div>
 </div>
 </motion.div>
 </div>
 );
}
