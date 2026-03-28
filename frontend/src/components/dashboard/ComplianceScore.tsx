import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';
import { useState, useEffect } from 'react';
import { casesApi } from '@/lib/api';

export function ComplianceScore() {
  const [scoreData, setScoreData] = useState<{
    score: number;
    metrics: {
      doc_compliance: string;
      risk_control: string;
      process_norm: string;
    };
    trend: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadScore();
  }, []);

  const loadScore = async () => {
    try {
      const data = await casesApi.getComplianceScore();
      setScoreData(data);
    } catch (error) {
      console.error('Failed to load compliance score:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-primary rounded-lg border border-primary-600 p-6 h-[340px] flex items-center justify-center shadow-legal-lg">
        <icons.Loader2 className="h-6 w-6 animate-spin text-primary-foreground/50" />
      </div>
    );
  }

  const score = scoreData?.score || 0;
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.2 }}
      className="bg-primary rounded-lg border border-primary-600 p-6 text-primary-foreground shadow-legal-lg"
    >
      <div className="flex items-center gap-2 mb-6">
        <icons.Shield className="w-5 h-5" />
        <h3 className="font-bold uppercase tracking-wider text-sm">合规健康分</h3>
      </div>

      <div className="flex items-center justify-center mb-6">
        <div className="relative">
          <svg width="140" height="140" className="transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="70"
              cy="70"
              r="45"
              className="stroke-white/10"
              strokeWidth="10"
              fill="none"
            />
            {/* Progress circle */}
            <motion.circle
              cx="70"
              cy="70"
              r="45"
              className="stroke-accent"
              stroke="hsl(var(--accent))"
              strokeWidth="10"
              fill="none"
              strokeLinecap="round"
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
              style={{
                strokeDasharray: circumference,
              }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-4xl font-bold">{score}</p>
              <p className="text-[10px] font-bold text-primary-foreground/70 uppercase tracking-widest">健康分</p>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {[
          { label: '文档合规率', value: scoreData?.metrics.doc_compliance || '-' },
          { label: '风险控制率', value: scoreData?.metrics.risk_control || '-' },
          { label: '流程规范度', value: scoreData?.metrics.process_norm || '-' },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between text-xs">
            <span className="text-primary-foreground/70 font-medium">{item.label}</span>
            <span className="font-bold">{item.value}</span>
          </div>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-primary-foreground/10">
        <div className="flex items-center gap-2 text-xs font-bold">
          <icons.TrendingUp className="w-4 h-4 text-accent" />
          <span className="text-primary-foreground">较上月提升 {scoreData?.trend || 0} 分</span>
        </div>
      </div>
    </motion.div>
  );
}
