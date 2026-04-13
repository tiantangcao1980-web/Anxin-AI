import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { icons } from '@/lib/icons';

interface RiskRadarProps {
  data: {
    scores: Record<string, number>;
    issues: Array<{
      type: 'high' | 'medium' | 'low';
      text: string;
    }>;
  };
}

export function RiskRadar({ data }: RiskRadarProps) {
  const chartData = Object.entries(data.scores).map(([name, value]) => ({
    dimension: name,
    value: value,
    fullMark: 100,
  }));

  const issueIcons = {
    high: icons.AlertTriangle,
    medium: icons.AlertCircle,
    low: icons.Info,
  };

  // 语义色：禁止在此处写 red-*/amber-* 硬编码 token，统一用 destructive/warning
  const issueColors = {
    high:   'bg-destructive/8 border-destructive/20 text-destructive',
    medium: 'bg-warning/8 border-warning/20 text-warning',
    low:    'bg-primary/5 border-primary/20 text-primary',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="h-full p-6 overflow-y-auto"
    >
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h3 className="font-semibold text-foreground mb-1">风险分析报告</h3>
          <p className="text-sm text-muted-foreground">基于 AI 多维度审查生成</p>
        </div>

        {/* Radar Chart */}
        <div className="bg-background rounded-xl shadow-sm border border-border p-6">
          <h4 className="font-medium text-foreground mb-4">风险雷达图</h4>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={chartData}>
              <PolarGrid stroke="hsl(var(--border))" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
              <Radar
                name="风险评分"
                dataKey="value"
                stroke="hsl(var(--info))"
                fill="hsl(var(--info))"
                fillOpacity={0.25}
                strokeWidth={2}
              />
            </RadarChart>
          </ResponsiveContainer>
          <div className="mt-4 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-success"></div>
              <span>100 = 无风险</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-destructive"></div>
              <span>0 = 高风险</span>
            </div>
          </div>
        </div>

        {/* Issues List */}
        <div className="bg-background rounded-xl shadow-sm border border-border p-6">
          <h4 className="font-medium text-foreground mb-4">发现的问题</h4>
          <div className="space-y-3">
            {data.issues.map((issue, index) => {
              const Icon = issueIcons[issue.type];
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex items-start gap-3 p-3 rounded-lg border ${issueColors[issue.type]}`}
                >
                  <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <p className="text-sm leading-relaxed">{issue.text}</p>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Overall Score */}
        <div className="bg-primary rounded-xl shadow-sm p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-primary-foreground/70 text-sm mb-1">综合风险评分</p>
              <p className="font-medium">62 / 100</p>
            </div>
            <div className="text-right">
              <p className="text-primary-foreground/70 text-sm mb-1">建议</p>
              <p className="font-medium text-sm">需要修订后签署</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
