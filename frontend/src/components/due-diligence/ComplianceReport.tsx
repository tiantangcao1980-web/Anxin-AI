import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';

interface ComplianceReportProps {
  data?: {
    credit_rating?: string;
    administrative_penalties?: number;
    abnormal_operations?: number;
  };
}

const defaultComplianceItems = [
  { category: '工商登记', status: 'pass', detail: '信息完整，无异常' },
  { category: '税务合规', status: 'pass', detail: '纳税正常' },
  { category: '社保缴纳', status: 'warning', detail: '存在1个月欠缴' },
  { category: '环保资质', status: 'pass', detail: '资质齐全' },
  { category: '安全生产', status: 'fail', detail: '2023年1起安全事故' },
  { category: '知识产权', status: 'pass', detail: '无侵权记录' },
];

export function ComplianceReport({ data }: ComplianceReportProps) {
  const complianceItems = defaultComplianceItems;
  const statusConfig = {
    pass: {
      icon: icons.CheckCircle,
      color: 'text-emerald-600 dark:text-emerald-400',
      bg: 'bg-emerald-50 dark:bg-emerald-950/30',
      border: 'border-emerald-200 dark:border-emerald-800',
    },
    warning: {
      icon: icons.AlertCircle,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-950/30',
      border: 'border-amber-200 dark:border-amber-800',
    },
    fail: {
      icon: icons.XCircle,
      color: 'text-red-600 dark:text-red-400',
      bg: 'bg-red-50 dark:bg-red-950/30',
      border: 'border-red-200 dark:border-red-800',
    },
  };

  const passCount = complianceItems.filter((item) => item.status === 'pass').length;
  const complianceRate = Math.round((passCount / complianceItems.length) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.2 }}
      className="bg-background rounded-xl border border-border p-6"
    >
      <div className="flex items-center gap-2 mb-6">
        <icons.FileCheck className="w-5 h-5 text-muted-foreground" />
        <div>
          <h3 className="font-semibold text-foreground">合规检查</h3>
          <p className="text-sm text-muted-foreground">6项核心指标</p>
        </div>
      </div>

      {/* Overall Score */}
      <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-950/30 dark:to-emerald-900/20 rounded-lg p-4 mb-4 border border-emerald-200 dark:border-emerald-800">
        <div className="text-center">
          <p className="text-sm text-emerald-700 dark:text-emerald-300 mb-1">合规率</p>
          <p className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">{complianceRate}%</p>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
            {passCount}/{complianceItems.length} 项通过
          </p>
        </div>
      </div>

      {/* Items */}
      <div className="space-y-2">
        {complianceItems.map((item, index) => {
          const config = statusConfig[item.status as keyof typeof statusConfig];
          const Icon = config.icon;

          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`p-3 rounded-lg border ${config.bg} ${config.border}`}
            >
              <div className="flex items-start gap-2">
                <Icon className={`w-4 h-4 ${config.color} flex-shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm text-foreground mb-0.5">
                    {item.category}
                  </h4>
                  <p className="text-xs text-muted-foreground">{item.detail}</p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
