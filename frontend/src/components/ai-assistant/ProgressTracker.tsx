import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';

export function ProgressTracker() {
  const stats = [
    { label: '文书质量分', value: '78', max: 100, icon: icons.Award, color: 'hsl(var(--primary))', bg: 'bg-primary/5' },
    { label: '合规率', value: '85', max: 100, icon: icons.Target, color: '#34C759', bg: 'bg-emerald-50 dark:bg-emerald-950/30' },
    { label: '本周进步', value: '+12', icon: icons.TrendingUp, color: 'hsl(var(--primary))', bg: 'bg-primary/5' },
  ];

  return (
    <div className="bg-background p-4 lg:p-6 border-b border-border">
      <div className="flex items-center gap-2 mb-3 lg:mb-4">
        <h3 className="font-semibold text-foreground text-sm lg:text-base">成长追踪</h3>
        <span className="px-2 py-0.5 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 rounded-full text-xs font-medium">
          新人模式
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 lg:gap-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon;

          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className="text-center"
            >
              <div className={`w-10 h-10 lg:w-12 lg:h-12 rounded-xl ${stat.bg} flex items-center justify-center mx-auto mb-2 shadow-sm`} style={{ color: stat.color }}>
                <Icon className="w-5 h-5 lg:w-6 lg:h-6" />
              </div>
              <p className="text-xl lg:text-2xl font-bold text-foreground">{stat.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
              {stat.max && (
                <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(parseInt(stat.value) / stat.max) * 100}%` }}
                    transition={{ duration: 1, delay: index * 0.05 }}
                    className="h-full rounded-full"
                    style={{ backgroundColor: stat.color }}
                  />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
