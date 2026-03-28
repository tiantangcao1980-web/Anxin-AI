/**
 * @deprecated 请使用 @/components/a2ui 中的标准 A2UIRenderer
 * 此文件仅为向后兼容保留，用于 AgentWorkspace 和 ContextPane 的旧数据格式
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';

import { KnowledgeGraphView } from './KnowledgeGraphView';

interface A2UIComponent {
  id: string;
  type: 'card' | 'alert' | 'metric' | 'list' | 'text' | 'container' | 'graph';
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
      case 'container':
        return (
          <div key={id} className={`space-y-4 ${props.className || ''}`}>
            {children?.map(renderComponent)}
          </div>
        );

      case 'card':
        return (
          <motion.div
            key={id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className={`bg-background rounded-2xl shadow-sm border border-border p-6 hover:shadow-md transition-shadow duration-300 ${props.className || ''}`}
          >
            {props.title && (
              <h4 className="font-bold text-foreground mb-4 flex items-center gap-2.5 text-[15px]">
                <div className="p-1.5 bg-muted rounded-lg">
                  {getIcon(props.icon)}
                </div>
                {props.title}
              </h4>
            )}
            <div className="space-y-4">
              {children?.map(renderComponent)}
            </div>
          </motion.div>
        );

      case 'alert':
        const alertStyles = {
          error: 'bg-red-50/50 dark:bg-red-950/30 border-red-100 dark:border-red-800 text-red-700 dark:text-red-400',
          warning: 'bg-amber-50/50 dark:bg-amber-950/30 border-amber-100 dark:border-amber-800 text-amber-700 dark:text-amber-400',
          success: 'bg-emerald-50/50 dark:bg-emerald-950/30 border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400',
          info: 'bg-primary/10 border-primary/20 text-primary',
        };
        const style = alertStyles[props.status as keyof typeof alertStyles] || alertStyles.info;
        return (
          <motion.div
            key={id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className={`p-4 rounded-xl border flex gap-3 ${style} ${props.className || ''}`}
          >
            <div className="shrink-0 mt-0.5 opacity-80">
              {props.status === 'error' && <icons.AlertCircle className="w-5 h-5" />}
              {props.status === 'warning' && <icons.AlertTriangle className="w-5 h-5" />}
              {props.status === 'success' && <icons.CheckCircle2 className="w-5 h-5" />}
              {props.status === 'info' && <icons.Info className="w-5 h-5" />}
            </div>
            <div>
              {props.title && <div className="font-semibold mb-1 text-sm">{props.title}</div>}
              <div className="text-sm opacity-90 leading-relaxed">{props.content}</div>
            </div>
          </motion.div>
        );

      case 'metric':
        return (
          <div key={id} className="flex items-center justify-between p-4 bg-muted/80 rounded-xl border border-border/50">
            <span className="text-sm font-medium text-muted-foreground">{props.label}</span>
            <div className="flex items-baseline gap-1">
              <span className={`text-xl font-bold tracking-tight ${props.color === 'red' ? 'text-red-600 dark:text-red-400' : 'text-foreground'}`}>
                {props.value}
              </span>
              {props.unit && <span className="text-xs text-muted-foreground font-medium">{props.unit}</span>}
            </div>
          </div>
        );

      case 'list':
        return (
          <ul key={id} className="space-y-3 my-2">
            {props.items?.map((item: any, idx: number) => (
              <li key={idx} className="flex gap-3 text-sm text-muted-foreground group">
                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary group-hover:bg-primary/80 transition-colors shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
        );

      case 'text':
        return (
          <p key={id} className={`text-sm text-muted-foreground leading-7 ${props.className || ''}`}>
            {props.content}
          </p>
        );

      case 'graph':
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
    <div className="h-full overflow-y-auto p-6 md:p-8 space-y-8 bg-muted/30">
      <div className="flex items-center justify-between mb-6 pb-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-primary/10 rounded-lg">
            <icons.Activity className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground uppercase tracking-wide">智能分析报告</h3>
            <p className="text-[10px] text-muted-foreground font-medium mt-0.5">GENERATED BY A2UI ENGINE</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-100/50">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-bold">LIVE</span>
        </div>
      </div>

      <div className="space-y-6">
        {data.components?.map(renderComponent)}
      </div>

      <div className="pt-8 text-center space-y-3">
        <button
          onClick={() => setShowRawData(!showRawData)}
          className="inline-flex items-center gap-2 text-xs font-semibold text-primary hover:text-primary/80 transition-colors group"
        >
          {showRawData ? '收起数据源' : '查看完整数据源'}
          <motion.div animate={{ rotate: showRawData ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <icons.ChevronDown className="w-3 h-3" />
          </motion.div>
        </button>

        <AnimatePresence>
          {showRawData && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="relative mt-2 bg-slate-900 rounded-xl p-4 text-left">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase">Raw JSON Data</span>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(data, null, 2));
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-white transition-colors"
                  >
                    {copied ? <icons.Check className="w-3 h-3 text-emerald-400" /> : <icons.Copy className="w-3 h-3" />}
                    {copied ? '已复制' : '复制'}
                  </button>
                </div>
                <pre className="text-xs text-slate-300 font-mono overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed whitespace-pre-wrap break-all">
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
    case 'shield': return <icons.ShieldCheck className="w-4 h-4 text-emerald-600" />;
    case 'file': return <icons.FileText className="w-4 h-4 text-primary" />;
    case 'search': return <icons.Search className="w-4 h-4 text-muted-foreground" />;
    case 'warning': return <icons.AlertTriangle className="w-4 h-4 text-amber-500" />;
    default: return <icons.Activity className="w-4 h-4 text-muted-foreground" />;
  }
}
