import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { useState, useEffect } from 'react';
import { casesApi, knowledgeApi } from '@/lib/api';
import { LottieIcon } from '@/components/ui/LottieIcon';
import { cardStyle } from '@/lib/design-tokens';

export function DashboardHeader() {
  const [stats, setStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      // 并行请求数据
      const [casesData, knowledgeData] = await Promise.all([
        casesApi.getStatistics(),
        knowledgeApi.listBases({ page_size: 1 }) // 只需总数
      ]);

      const statItems = [
        {
          label: '进行中案件',
          value: casesData.total.toString(),
          unit: '件',
          icon: icons.Briefcase,
          lottie: 'analyzing', // 映射到 LottieIcon
          color: 'text-primary',
          bgColor: 'bg-primary/5',
        },
        {
          label: '高风险预警',
          value: (casesData.by_priority?.urgent || 0).toString(),
          unit: '个',
          icon: icons.AlertTriangle,
          lottie: 'error',
          color: 'text-destructive',
          bgColor: 'bg-destructive/5',
        },
        {
          label: '知识库资源',
          value: knowledgeData.total.toString(),
          unit: '个库',
          icon: icons.Brain,
          lottie: 'thinking',
          color: 'text-amber-600 dark:text-amber-400',
          bgColor: 'bg-amber-50 dark:bg-amber-950/30',
        },
        {
          label: '自我进化次数',
          value: '--', // 暂无后端统计 API
          unit: '次迭代',
          icon: icons.Activity,
          lottie: 'success',
          color: 'text-emerald-600 dark:text-emerald-400',
          bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
        },
      ];
      setStats(statItems);
    } catch (error) {
      console.error('加载统计数据失败', error);
      // fallback: 从案件列表获取基本统计
      try {
        const casesResp = await casesApi.list({ page: 1, page_size: 1 });
        const knowledgeResp = await knowledgeApi.listBases({ page_size: 1 });
        setStats([
          { label: '进行中案件', value: (casesResp.total || 0).toString(), unit: '件', icon: icons.Briefcase, lottie: 'analyzing', color: 'text-primary', bgColor: 'bg-primary/5' },
          { label: '高风险预警', value: '0', unit: '个', icon: icons.AlertTriangle, lottie: 'error', color: 'text-destructive', bgColor: 'bg-destructive/5' },
          { label: '知识库资源', value: (knowledgeResp.total || 0).toString(), unit: '个库', icon: icons.Brain, lottie: 'thinking', color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-950/30' },
          { label: '自我进化次数', value: '--', unit: '次迭代', icon: icons.Activity, lottie: 'success', color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
        ]);
      } catch {
        setStats([
          { label: '进行中案件', value: '--', unit: '件', icon: icons.Briefcase, lottie: 'analyzing', color: 'text-primary', bgColor: 'bg-primary/5' },
          { label: '高风险预警', value: '--', unit: '个', icon: icons.AlertTriangle, lottie: 'error', color: 'text-destructive', bgColor: 'bg-destructive/5' },
          { label: '知识库资源', value: '--', unit: '个库', icon: icons.Brain, lottie: 'thinking', color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-50 dark:bg-amber-950/30' },
          { label: '自我进化次数', value: '--', unit: '次迭代', icon: icons.Activity, lottie: 'success', color: 'text-emerald-600 dark:text-emerald-400', bgColor: 'bg-emerald-50 dark:bg-emerald-950/30' },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`${cardStyle.base} shadow-sm h-[140px] flex items-center justify-center`}>
            <LottieIcon type="thinking" className="w-12 h-12" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
      {stats.map((stat, index) => {
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.4 }}
            className={`${cardStyle.base} shadow-sm hover:shadow-md transition-shadow group relative overflow-hidden`}
          >
            {/* 装饰背景 */}
            <div className={`absolute top-0 right-0 w-24 h-24 rounded-full blur-3xl opacity-20 translate-x-8 -translate-y-8 ${stat.bgColor.replace('bg-', 'bg-')}`} />

            <div className="flex items-start justify-between mb-4 relative z-10">
              <div className={`w-12 h-12 rounded-xl ${stat.bgColor} flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform duration-300`}>
                {/* 优先显示 Lottie，如果没有则显示 Icon */}
                <LottieIcon type={stat.lottie} className="w-8 h-8" />
              </div>
              <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-muted/50 text-muted-foreground border border-border">
                实时
              </span>
            </div>

            <div className="relative z-10">
              <div className="flex items-baseline gap-1 mb-1">
                <p className="text-3xl font-bold text-foreground tracking-tight">{stat.value}</p>
                <span className="text-xs text-muted-foreground font-medium">{stat.unit}</span>
              </div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                {stat.label}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
