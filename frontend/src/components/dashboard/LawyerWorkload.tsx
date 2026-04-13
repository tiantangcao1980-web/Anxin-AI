import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import { useState, useEffect } from'react';
import { casesApi } from'@/lib/api';
import { cardStyle, heading } from'@/lib/design-tokens';

interface LawyerStats {
 id: string;
 name: string;
 count: number;
}

export function LawyerWorkload() {
 const [lawyers, setLawyers] = useState<LawyerStats[]>([]);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 loadStats();
 }, []);

 const loadStats = async () => {
 try {
 const stats = await casesApi.getStatistics();
 setLawyers(stats.workload || []);
 } catch (error) {
 console.error('Failed to load workload stats:', error);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return (
 <div className={`${cardStyle.base} h-[300px] flex items-center justify-center`}>
 <icons.Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
 </div>
 );
 }

 return (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: 0.15 }}
 className={cardStyle.base}
 >
 <div className="mb-6">
 <h3 className={heading.section}>律师工作负载</h3>
 <p className="text-sm text-muted-foreground mt-1">实时监控团队成员工作状态</p>
 </div>

 <div className="space-y-4">
 {lawyers.length > 0 ? (
 lawyers.map((lawyer, index) => {
 // Assume capacity is 10 for now, or we could fetch it if User model had it
 const capacity = 10;
 const workloadPercent = Math.min((lawyer.count / capacity) * 100, 100);
 const isOverloaded = lawyer.count > 8;

 return (
 <motion.div
 key={lawyer.id}
 initial={{ opacity: 0, x: -20 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 className="border border-border rounded-xl p-4 hover:border-border/80 transition-colors"
 >
 <div className="flex items-center gap-3 mb-3">
 <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center text-lg">
 <icons.User className="w-5 h-5 text-muted-foreground" />
 </div>
 <div className="flex-1">
 <div className="flex items-center justify-between">
 <h4 className="font-medium text-foreground">{lawyer.name}</h4>
 <span className="text-sm text-muted-foreground">
 {lawyer.count} 案件
 </span>
 </div>
 <div className="flex items-center gap-3 mt-1">
 <div className="flex-1">
 <div className="h-2 bg-muted rounded-full overflow-hidden">
 <motion.div
 initial={{ width: 0 }}
 animate={{ width: `${workloadPercent}%` }}
 transition={{ duration: 1, delay: index * 0.05 }}
 className={`h-full rounded-full ${
 isOverloaded ?'bg-destructive' :'bg-success'
 }`}
 />
 </div>
 </div>
 </div>
 </div>
 </div>

 {isOverloaded && (
 <div className="mt-2 px-3 py-1.5 bg-warning/10 border border-warning/20 rounded-lg">
 <p className="text-xs text-warning">
 ⚠️ 工作负载较高，建议重新分配任务
 </p>
 </div>
 )}
 </motion.div>
 );
 })
 ) : (
 <div className="text-center py-8 text-muted-foreground text-sm">暂无数据</div>
 )}
 </div>
 </motion.div>
 );
}
