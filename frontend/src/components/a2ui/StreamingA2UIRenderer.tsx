/**
 * StreamingA2UIRenderer — 流式 A2UI 渲染管线
 * 
 * 核心职责：
 * 1. 接收 a2ui_stream 事件，增量更新 A2UI 组件树
 * 2. 骨架屏（Skeleton）占位 → 逐步填充内容 → 完整卡片
 * 3. Framer Motion 入场/更新动画
 * 4. 使用 React.memo + 不可变数据结构避免全量重渲染
 * 
 * 参考千问 StreamObject：后端流式推送 JSON 组件片段，
 * 前端在首个 Token 到达即开始渲染，用户看到卡片"逐步生长"
 */

import { memo, useState, useCallback, useRef, useEffect } from'react';
import { motion, AnimatePresence } from'framer-motion';
import type { A2UIComponent, A2UIEvent, A2UIEventHandler, A2UIStreamEvent, A2UIMessage } from'./types';
import { A2UIRenderer } from'./A2UIRenderer';
import { MobileA2UIAdapter } from'./MobileA2UIAdapter';
import { cn } from'@/lib/utils';

// ========== 骨架屏组件 ==========

/** 通用卡片骨架屏 */
export const CardSkeleton = memo(function CardSkeleton({ type }: { type?: string }) {
 // 根据组件类型显示不同的骨架屏
 switch (type) {
 case'lawyer-card':
 return <LawyerCardSkeleton />;
 case'contract-compare':
 return <ContractCompareSkeleton />;
 case'fee-estimate':
 return <FeeEstimateSkeleton />;
 case'recommendation-card':
 return <RecommendationSkeleton />;
 default:
 return <GenericCardSkeleton />;
 }
});

/** 律师卡片骨架屏 */
const LawyerCardSkeleton = memo(function LawyerCardSkeleton() {
 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm p-4 animate-pulse">
 <div className="flex items-start gap-3">
 {/* 头像 */}
 <div className="w-12 h-12 rounded-full bg-muted flex-shrink-0" />
 <div className="flex-1 space-y-2">
 {/* 姓名 */}
 <div className="h-4 bg-muted rounded w-24" />
 {/* 事务所 */}
 <div className="h-3 bg-muted rounded w-36" />
 {/* 标签 */}
 <div className="flex gap-1.5">
 <div className="h-5 bg-primary/10 rounded-full w-14" />
 <div className="h-5 bg-primary/10 rounded-full w-16" />
 <div className="h-5 bg-primary/10 rounded-full w-12" />
 </div>
 </div>
 {/* 评分 */}
 <div className="h-6 w-12 bg-warning/10 rounded-full" />
 </div>
 {/* 底部按钮 */}
 <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
 <div className="h-3 bg-muted rounded w-20" />
 <div className="h-8 bg-primary/10 rounded-lg w-20" />
 </div>
 </div>
 );
});

/** 合同对比骨架屏 */
const ContractCompareSkeleton = memo(function ContractCompareSkeleton() {
 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm overflow-hidden animate-pulse">
 <div className="px-4 py-3 border-b border-border bg-primary/5">
 <div className="h-4 bg-muted rounded w-32" />
 <div className="h-3 bg-muted rounded w-48 mt-1" />
 </div>
 <div className="px-4 py-3 bg-muted/50 border-b border-border flex items-center gap-4">
 <div className="h-3 bg-muted rounded w-24" />
 <div className="h-5 bg-success/10 rounded-full w-16" />
 </div>
 <div className="px-4 py-2 grid grid-cols-2 gap-4 border-b border-border">
 <div className="h-3 bg-muted rounded w-16" />
 <div className="h-3 bg-muted rounded w-16" />
 </div>
 {[1, 2, 3].map((i) => (
 <div key={i} className="px-4 py-3 border-b border-border flex items-center gap-2">
 <div className="w-3.5 h-3.5 rounded bg-muted" />
 <div className="h-3 bg-muted rounded flex-1 max-w-[60%]" />
 <div className="h-5 bg-muted rounded-full w-12 ml-auto" />
 </div>
 ))}
 </div>
 );
});

/** 费用估算骨架屏 */
const FeeEstimateSkeleton = memo(function FeeEstimateSkeleton() {
 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm overflow-hidden animate-pulse">
 <div className="px-4 py-3 border-b border-border flex items-center gap-2">
 <div className="w-8 h-8 rounded-lg bg-orange-50" />
 <div>
 <div className="h-4 bg-muted rounded w-24" />
 <div className="h-3 bg-muted rounded w-36 mt-1" />
 </div>
 </div>
 <div className="px-4 py-3 space-y-3">
 {[1, 2, 3].map((i) => (
 <div key={i} className="flex items-center justify-between">
 <div className="h-3 bg-muted rounded w-28" />
 <div className="h-3 bg-muted rounded w-16" />
 </div>
 ))}
 <div className="pt-3 border-t border-border flex items-center justify-between">
 <div className="h-3 bg-muted rounded w-12" />
 <div className="h-5 bg-orange-100 rounded w-20" />
 </div>
 </div>
 </div>
 );
});

/** 推荐卡片骨架屏 */
const RecommendationSkeleton = memo(function RecommendationSkeleton() {
 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm p-4 animate-pulse">
 <div className="flex items-start gap-3">
 <div className="w-16 h-16 rounded-xl bg-muted flex-shrink-0" />
 <div className="flex-1 space-y-2">
 <div className="h-4 bg-muted rounded w-32" />
 <div className="h-3 bg-muted rounded w-48" />
 <div className="flex gap-1.5">
 <div className="h-5 bg-muted rounded-full w-14" />
 <div className="h-5 bg-muted rounded-full w-18" />
 </div>
 </div>
 </div>
 </div>
 );
});

/** 通用卡片骨架屏 */
const GenericCardSkeleton = memo(function GenericCardSkeleton() {
 return (
 <div className="bg-background rounded-2xl border border-border shadow-sm p-4 animate-pulse">
 <div className="space-y-3">
 <div className="h-4 bg-muted rounded w-3/4" />
 <div className="h-3 bg-muted rounded w-full" />
 <div className="h-3 bg-muted rounded w-5/6" />
 <div className="flex gap-2 mt-3">
 <div className="h-8 bg-primary/10 rounded-lg flex-1" />
 <div className="h-8 bg-muted rounded-lg w-20" />
 </div>
 </div>
 </div>
 );
});

/** 骨架屏列表 — 同时显示多个骨架屏占位 */
export const SkeletonList = memo(function SkeletonList({
 count = 2,
 types,
}: {
 /** 骨架屏数量 */
 count?: number;
 /** 各骨架屏的组件类型提示 */
 types?: string[];
}) {
 const items = Array.from({ length: count }, (_, i) => i);
 return (
 <div className="space-y-3">
 {items.map((i) => (
 <motion.div
 key={`skel-list-${i}`}
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: i * 0.1, duration: 0.25 }}
 >
 <CardSkeleton type={types?.[i]} />
 </motion.div>
 ))}
 </div>
 );
});

// ========== 流式渲染状态 ==========

export interface StreamingA2UIState {
 /** 流式消息 ID */
 streamId: string;
 /** 已接收的组件列表 */
 components: A2UIComponent[];
 /** 来源 Agent */
 agent?: string;
 /** 是否正在流式传输中 */
 isStreaming: boolean;
 /** 期望的组件类型提示（用于骨架屏） */
 expectedTypes?: string[];
 /** 元数据 */
 metadata?: Record<string, any>;
}

// ========== 流式 A2UI 渲染器 ==========

interface StreamingA2UIRendererProps {
 /** 流式状态 */
 stream: StreamingA2UIState;
 /** 事件处理器 */
 onEvent: A2UIEventHandler;
 /** 附加类名 */
 className?: string;
 /** 是否为移动端（启用千问风格适配） */
 isMobile?: boolean;
}

/**
 * 流式 A2UI 渲染器
 * 
 * 每当有新组件到达时，带入场动画渲染；
 * 正在加载时，在已有组件后面显示骨架屏占位。
 */
export const StreamingA2UIRenderer = memo(function StreamingA2UIRenderer({
 stream,
 onEvent,
 className,
 isMobile = false,
}: StreamingA2UIRendererProps) {
 const { components, isStreaming, agent, expectedTypes } = stream;

 // 构造一个虚拟 A2UIMessage 给 A2UIRenderer
 const message: A2UIMessage = {
 id: stream.streamId,
 components,
 metadata: {
 agent,
 collapsible: !isStreaming, // 流式传输完毕后允许折叠
 },
 };

 return (
 <div className={cn('streaming-a2ui', className)}>
 {/* Agent 来源标签 */}
 {agent && (
 <motion.div
 initial={{ opacity: 0, x: -8 }}
 animate={{ opacity: 1, x: 0 }}
 className="flex items-center gap-1.5 mb-2"
 >
 <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
 <span className="text-[10px] text-muted-foreground font-medium">{agent}</span>
 {isStreaming && (
 <span className="text-[10px] text-primary animate-pulse">正在生成...</span>
 )}
 </motion.div>
 )}

 {/* 已接收的组件 — 移动端使用千问风格适配器 */}
 {components.length > 0 && (
 isMobile ? (
 <MobileA2UIAdapter
 message={message}
 onEvent={onEvent}
 isHistorical={false}
 showBottomBar={!isStreaming}
 />
 ) : (
 <A2UIRenderer
 message={message}
 onEvent={onEvent}
 animated={true}
 />
 )
 )}

 {/* 骨架屏占位 — 流式传输中且还有更多组件预期到达 */}
 <AnimatePresence>
 {isStreaming && (
 <motion.div
 initial={{ opacity: 0, y: 8 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -8, transition: { duration: 0.2 } }}
 transition={{ duration: 0.3 }}
 className="mt-3 space-y-3"
 >
 {/* 如果有期望类型，显示对应骨架屏 */}
 {expectedTypes && expectedTypes.length > components.length ? (
 expectedTypes.slice(components.length).map((type, i) => (
 <motion.div
 key={`skel-${i}`}
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 transition={{ delay: i * 0.1 }}
 >
 <CardSkeleton type={type} />
 </motion.div>
 ))
 ) : (
 /* 默认显示 1 个通用骨架屏 */
 <CardSkeleton />
 )}
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 );
});

// ========== Hook: useStreamingA2UI ==========

/**
 * 流式 A2UI 状态管理 Hook
 * 
 * 管理多个并行的流式 A2UI 消息，
 * 处理 WebSocket 的 a2ui_stream 事件。
 */
export function useStreamingA2UI() {
 const [streams, setStreams] = useState<Map<string, StreamingA2UIState>>(new Map());
 const streamsRef = useRef<Map<string, StreamingA2UIState>>(new Map());

 // 同步 ref
 useEffect(() => {
 streamsRef.current = streams;
 }, [streams]);

 /**
 * 处理 a2ui_stream WebSocket 事件
 */
 const handleStreamEvent = useCallback((event: A2UIStreamEvent) => {
 const { streamId, action } = event;

 setStreams(prev => {
 const next = new Map(prev);

 switch (action) {
 case'stream_start': {
 next.set(streamId, {
 streamId,
 components: [],
 agent: event.agent,
 isStreaming: true,
 expectedTypes: event.metadata?.expectedTypes,
 metadata: event.metadata,
 });
 break;
 }

 case'stream_component': {
 const existing = next.get(streamId);
 if (existing && event.component) {
 next.set(streamId, {
 ...existing,
 components: [...existing.components, event.component],
 });
 }
 break;
 }

 case'stream_delta': {
 const existing = next.get(streamId);
 if (existing && event.componentId && event.delta) {
 const compIdx = existing.components.findIndex(c => c.id === event.componentId);
 if (compIdx !== -1) {
 const updated = [...existing.components];
 const comp = updated[compIdx];
 updated[compIdx] = {
 ...comp,
 data: { ...(comp as any).data, ...event.delta },
 } as A2UIComponent;
 next.set(streamId, {
 ...existing,
 components: updated,
 });
 }
 }
 break;
 }

 case'stream_end': {
 const existing = next.get(streamId);
 if (existing) {
 next.set(streamId, {
 ...existing,
 isStreaming: false,
 });
 }
 break;
 }
 }

 return next;
 });
 }, []);

 /**
 * 清除已完成的流式消息
 */
 const clearCompleted = useCallback(() => {
 setStreams(prev => {
 const next = new Map(prev);
 for (const [id, state] of next) {
 if (!state.isStreaming) {
 next.delete(id);
 }
 }
 return next;
 });
 }, []);

 /**
 * 获取所有活跃的流式状态
 */
 const activeStreams = Array.from(streams.values()).filter(s => s.isStreaming);

 /**
 * 获取所有流式状态（包括已完成）
 */
 const allStreams = Array.from(streams.values());

 return {
 streams,
 activeStreams,
 allStreams,
 handleStreamEvent,
 clearCompleted,
 };
}

export default StreamingA2UIRenderer;
