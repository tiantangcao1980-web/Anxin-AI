import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import { useState, useEffect } from'react';
import { casesApi } from'@/lib/api';
import { cardStyle, heading } from'@/lib/design-tokens';

interface TimelineEvent {
 id: string;
 case_number: string;
 case_title: string;
 title: string;
 description: string;
 event_time: string;
 event_type: string;
}

export function CaseTimeline() {
 const [events, setEvents] = useState<TimelineEvent[]>([]);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 loadEvents();
 }, []);

 const loadEvents = async () => {
 try {
 const data = await casesApi.getRecentEvents(5);
 setEvents(data);
 } catch (error) {
 console.error('Failed to load timeline events:', error);
 } finally {
 setLoading(false);
 }
 };

 const statusConfig: Record<string, any> = {
 created: {
 icon: icons.Circle,
 color:'text-primary',
 bg:'bg-primary/5',
 border:'border-primary',
 },
 status_changed: {
 icon: icons.Clock,
 color:'text-violet-500 dark:text-violet-400',
 bg:'bg-violet-50 dark:bg-violet-950/30',
 border:'border-violet-500',
 },
 document_linked: {
 icon: icons.Calendar,
 color:'text-warning',
 bg:'bg-warning/10',
 border:'border-warning/20',
 },
 ai_analysis: {
 icon: icons.CheckCircle,
 color:'text-success',
 bg:'bg-success/10',
 border:'border-success/20',
 },
 default: {
 icon: icons.Circle,
 color:'text-muted-foreground',
 bg:'bg-muted',
 border:'border-border',
 }
 };

 if (loading) {
 return (
 <div className={`${cardStyle.base} h-[400px] flex items-center justify-center`}>
 <icons.Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
 </div>
 );
 }

 return (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.2 }}
 className={cardStyle.base}
 >
 <div className="mb-6">
 <h3 className={heading.section}>案件时间轴</h3>
 <p className="text-sm text-muted-foreground mt-1">关键节点与进度追踪</p>
 </div>

 <div className="relative">
 {/* Timeline line */}
 <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border"></div>

 <div className="space-y-6">
 {events.length > 0 ? (
 events.map((event, index) => {
 const config = statusConfig[event.event_type] || statusConfig.default;
 const Icon = config.icon;

 return (
 <motion.div
 key={event.id}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 className="relative pl-12"
 >
 {/* Icon */}
 <div className={`absolute left-0 w-8 h-8 rounded-full ${config.bg} ${config.border} border-2 flex items-center justify-center`}>
 <Icon className={`w-4 h-4 ${config.color}`} />
 </div>

 {/* Content */}
 <div className="bg-muted rounded-xl p-4 border border-border">
 <div className="flex items-start justify-between mb-2">
 <div>
 <span className="text-xs font-medium text-muted-foreground">{event.case_number}</span>
 <h4 className="font-medium text-foreground mt-0.5">{event.title}</h4>
 </div>
 <span className="text-xs text-muted-foreground">{new Date(event.event_time).toLocaleDateString()}</span>
 </div>
 <p className="text-sm text-foreground/80">{event.description}</p>
 </div>
 </motion.div>
 );
 })
 ) : (
 <div className="text-center py-8 text-muted-foreground text-sm">暂无近期活动</div>
 )}
 </div>
 </div>
 </motion.div>
 );
}
