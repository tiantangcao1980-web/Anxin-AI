/**
 * @deprecated 请使用 @/components/a2ui 中的标准 A2UIRenderer
 * 此文件仅为向后兼容保留，用于 AgentWorkspace 和 ContextPane 的旧数据格式
 */
import React, { useState } from'react';
import { motion, AnimatePresence } from'framer-motion';
import { icons } from'@/lib/icons';

import { KnowledgeGraphView } from'./KnowledgeGraphView';

interface A2UIComponent {
 id: string;
 type:'card' |'alert' |'metric' |'list' |'text' |'container' |'graph';
 props: any;
 children?: A2UIComponent[];
}

interface A2UIRendererProps {
 data: {
 components: A2UIComponent[];
 };
}

export function A2UIRenderer({ data }: A2UIRendererProps) {
 const [showRawData, setShowRawData] = useState(false);
 const [copied, setCopied] = useState(false);
 const renderComponent = (component: A2UIComponent) => {
 const { type, props, children, id } = component;

 switch (type) {
 case'container':
 return (
 <div key={id} className={`space-y-4 ${props.className ||''}`}>
 {children?.map(renderComponent)}
 </div>
 );

 case'card':
 return (
 <motion.div
 key={id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ duration: 0.3, ease:"easeOut" }}
 className={`bg-background rounded-xl border border-border p-4 ${props.className ||''}`}
 >
 {props.title && (
 <h4 className="font-semibold text-foreground mb-3 flex items-center gap-2 text-sm">
 <div className="p-1 bg-muted rounded-md">
 {getIcon(props.icon)}
 </div>
 {props.title}
 </h4>
 )}
 <div className="space-y-3">
 {children?.map(renderComponent)}
 </div>
 </motion.div>
 );

 case'alert':
 const alertStyles = {
 error:'bg-destructive/10/50 border-destructive/20 text-destructive',
 warning:'bg-warning/10/50 border-warning/20 text-warning',
 success:'bg-success/10 border-success/20 text-success',
 info:'bg-primary/10 border-primary/20 text-primary',
 };
 const style = alertStyles[props.status as keyof typeof alertStyles] || alertStyles.info;
 return (
 <motion.div
 key={id}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 className={`p-3 rounded-lg border flex gap-2.5 ${style} ${props.className ||''}`}
 >
 <div className="shrink-0 mt-0.5 opacity-80">
 {props.status ==='error' && <icons.AlertCircle className="w-4 h-4" />}
 {props.status ==='warning' && <icons.AlertTriangle className="w-4 h-4" />}
 {props.status ==='success' && <icons.CheckCircle2 className="w-4 h-4" />}
 {props.status ==='info' && <icons.Info className="w-4 h-4" />}
 </div>
 <div>
 {props.title && <div className="font-medium mb-0.5 text-xs">{props.title}</div>}
 <div className="text-xs opacity-90 leading-relaxed">{props.content}</div>
 </div>
 </motion.div>
 );

 case'metric':
 return (
 <div key={id} className="flex items-center justify-between p-3 bg-muted/60 rounded-lg border border-border/50">
 <span className="text-xs font-medium text-muted-foreground">{props.label}</span>
 <div className="flex items-baseline gap-1">
 <span className={`text-base font-bold ${props.color ==='red' ?'text-destructive' :'text-foreground'}`}>
 {props.value}
 </span>
 {props.unit && <span className="text-[11px] text-muted-foreground font-medium">{props.unit}</span>}
 </div>
 </div>
 );

 case'list':
 return (
 <ul key={id} className="space-y-1.5 my-1">
 {props.items?.map((item: any, idx: number) => (
 <li key={idx} className="flex gap-2 text-xs text-muted-foreground">
 <div className="mt-1.5 w-1 h-1 rounded-full bg-primary shrink-0" />
 <span className="leading-relaxed">{item}</span>
 </li>
 ))}
 </ul>
 );

 case'text':
 return (
 <p key={id} className={`text-xs text-muted-foreground leading-relaxed ${props.className ||''}`}>
 {props.content}
 </p>
 );

 case'graph':
 return (
 <div className="rounded-xl overflow-hidden border border-border shadow-inner bg-muted/50">
 <KnowledgeGraphView key={id} data={props.data} />
 </div>
 );

 default:
 return null;
 }
 };

 return (
 <div className="space-y-4">
 {/* 标题 */}
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <icons.Activity className="w-3.5 h-3.5 text-primary" />
 <span className="text-xs font-medium text-foreground">智能分析报告</span>
 </div>
 <div className="flex items-center gap-1 px-2 py-0.5 bg-success/10 text-success rounded-full border border-success/20">
 <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
 <span className="text-[10px] font-medium">LIVE</span>
 </div>
 </div>

 {/* 组件内容 */}
 <div className="space-y-3">
 {data.components?.map(renderComponent)}
 </div>

 {/* 数据源折叠 */}
 <div className="text-center">
 <button
 onClick={() => setShowRawData(!showRawData)}
 className="inline-flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground hover:text-primary transition-colors"
 >
 {showRawData ?'收起数据源' :'查看数据源'}
 <motion.div animate={{ rotate: showRawData ? 180 : 0 }} transition={{ duration: 0.2 }}>
 <icons.ChevronDown className="w-3 h-3" />
 </motion.div>
 </button>

 <AnimatePresence>
 {showRawData && (
 <motion.div
 initial={{ height: 0, opacity: 0 }}
 animate={{ height:'auto', opacity: 1 }}
 exit={{ height: 0, opacity: 0 }}
 transition={{ duration: 0.25 }}
 className="overflow-hidden"
 >
 <div className="relative mt-2 bg-slate-900 rounded-xl p-3 text-left">
 <div className="flex items-center justify-between mb-1.5">
 <span className="text-[10px] font-mono text-slate-400 uppercase">JSON</span>
 <button
 onClick={() => {
 navigator.clipboard.writeText(JSON.stringify(data, null, 2));
 setCopied(true);
 setTimeout(() => setCopied(false), 2000);
 }}
 className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors"
 >
 {copied ? <icons.Check className="w-3 h-3 text-success" /> : <icons.Copy className="w-3 h-3" />}
 {copied ?'已复制' :'复制'}
 </button>
 </div>
 <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto max-h-[200px] overflow-y-auto leading-relaxed whitespace-pre-wrap break-all">
 {JSON.stringify(data, null, 2)}
 </pre>
 </div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 </div>
 );
}

function getIcon(name: string) {
 switch (name) {
 case'shield': return <icons.ShieldCheck className="w-4 h-4 text-success" />;
 case'file': return <icons.FileText className="w-4 h-4 text-primary" />;
 case'search': return <icons.Search className="w-4 h-4 text-muted-foreground" />;
 case'warning': return <icons.AlertTriangle className="w-4 h-4 text-warning" />;
 default: return <icons.Activity className="w-4 h-4 text-muted-foreground" />;
 }
}
