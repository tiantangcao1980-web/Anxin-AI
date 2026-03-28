import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';

interface RiskTimelineProps {
  data?: {
    overall_rating?: string;
    risk_points?: string[];
    risk_events?: Array<{
      date?: string;
      level?: string;
      title?: string;
      description?: string;
    }>;
  };
}

const defaultRiskEvents = [
  {
    id: 1,
    date: '2024-01-05',
    level: 'high',
    title: '被监管约谈',
    description: '因广告宣传问题',
  },
  {
    id: 2,
    date: '2023-12-10',
    level: 'medium',
    title: '劳动仲裁',
    description: '1 起劳动纠纷已结案',
  },
  {
    id: 3,
    date: '2023-10-20',
    level: 'low',
    title: '专利申请',
    description: '新增 3 项发明专利',
  },
  {
    id: 4,
    date: '2023-08-15',
    level: 'medium',
    title: '合同纠纷',
    description: '供应商合同争议',
  },
];

export function RiskTimeline({ data }: RiskTimelineProps) {
  // 优先使用后端返回的风险事件数据
  const riskEvents = data?.risk_events && data.risk_events.length > 0
    ? data.risk_events.map((e, i) => ({
        id: i + 1,
        date: e.date || '未知',
        level: e.level || 'low',
        title: e.title || '风险事件',
        description: e.description || '',
      }))
    : defaultRiskEvents;
  
  const levelConfig = {
    high: {
      icon: icons.AlertTriangle,
      bg: 'bg-red-50 dark:bg-red-950/30',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-700 dark:text-red-300',
      dot: 'bg-red-500',
    },
    medium: {
      icon: icons.AlertCircle,
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      border: 'border-amber-200 dark:border-amber-800',
      text: 'text-amber-700 dark:text-amber-300',
      dot: 'bg-amber-500',
    },
    low: {
      icon: icons.Info,
      bg: 'bg-primary/5',
      border: 'border-primary/20',
      text: 'text-primary',
      dot: 'bg-primary',
    },
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 }}
      className="bg-background rounded-xl border border-border p-6"
    >
      <div className="flex items-center gap-2 mb-6">
        <icons.Clock className="w-5 h-5 text-muted-foreground" />
        <div>
          <h3 className="font-semibold text-foreground">风险时间轴</h3>
          <p className="text-sm text-muted-foreground">历史风险事件</p>
        </div>
      </div>

      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-border"></div>

        <div className="space-y-4">
          {riskEvents.map((event, index) => {
            const config = levelConfig[event.level as keyof typeof levelConfig];
            const Icon = config.icon;

            return (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="relative pl-8"
              >
                {/* Dot */}
                <div className={`absolute left-0 w-4 h-4 rounded-full ${config.dot} border-2 border-background`}></div>

                {/* Content */}
                <div className={`p-3 rounded-lg border ${config.bg} ${config.border}`}>
                  <div className="flex items-start gap-2 mb-1">
                    <Icon className={`w-4 h-4 ${config.text} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <h4 className={`font-medium text-sm ${config.text}`}>{event.title}</h4>
                      <p className="text-xs opacity-75 mt-0.5">{event.description}</p>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{event.date}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
