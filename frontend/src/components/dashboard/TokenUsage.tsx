import { motion } from'framer-motion';
import { icons } from'@/lib/icons';
import { useState, useEffect } from'react';
import { llmApi } from'@/lib/api';
import { cardStyle, heading } from'@/lib/design-tokens';

export function TokenUsage() {
 const [totalTokens, setTotalTokens] = useState(0);
 const [totalCalls, setTotalCalls] = useState(0);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
 loadStats();
 }, []);

 const loadStats = async () => {
 try {
 const response = await llmApi.listConfigs();
 const configs = response.items || [];
 const tokens = configs.reduce((sum, config) => sum + (config.total_tokens || 0), 0);
 const calls = configs.reduce((sum, config) => sum + (config.total_calls || 0), 0);
 setTotalTokens(tokens);
 setTotalCalls(calls);
 } catch (error) {
 console.error('Failed to load token usage:', error);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return (
 <div className={`${cardStyle.base} h-[200px] flex items-center justify-center`}>
 <icons.Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
 </div>
 );
 }

 return (
 <motion.div
 initial={{ opacity: 0, scale: 0.95 }}
 animate={{ opacity: 1, scale: 1 }}
 transition={{ delay: 0.25 }}
 className={cardStyle.base}
 >
 <div className="flex items-center gap-2 mb-4">
 <div className="w-8 h-8 bg-warning/10 rounded-xl flex items-center justify-center">
 <icons.Zap className="w-4 h-4 text-warning" />
 </div>
 <div>
 <h3 className={heading.section}>Token 消耗</h3>
 <p className="text-xs text-muted-foreground">AI 调用统计</p>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-3">
 <div className="bg-muted rounded-xl p-3">
 <p className="text-xs text-muted-foreground mb-1">总 Token</p>
 <p className="text-lg font-bold text-foreground">
 {(totalTokens / 1000).toFixed(1)}K
 </p>
 </div>
 <div className="bg-muted rounded-xl p-3">
 <p className="text-xs text-muted-foreground mb-1">总调用次数</p>
 <p className="text-lg font-bold text-foreground">
 {totalCalls}
 </p>
 </div>
 </div>

 <div className="mt-4 text-xs text-muted-foreground text-center">
 * 统计自系统启动以来的累计消耗
 </div>
 </motion.div>
 );
}
