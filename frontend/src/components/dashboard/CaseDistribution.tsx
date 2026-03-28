import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useState, useEffect } from 'react';
import { casesApi } from '@/lib/api';
import { icons } from '@/lib/icons';

// 使用设计系统统一的企业级图表色板
import { chartColors, cardStyle, heading } from '@/lib/design-tokens';

const COLORS = [
  ...chartColors,
  'hsl(190, 60%, 50%)',   // 青色（补充色）
  'hsl(320, 50%, 55%)',   // 玫红（补充色）
  'hsl(80, 55%, 50%)',    // 草绿（补充色）
  'hsl(240, 50%, 60%)',   // 靛蓝（补充色）
];

// 案件类型英文→中文映射
const CASE_TYPE_LABELS: Record<string, string> = {
  contract: '合同纠纷',
  labor: '劳动争议',
  ip: '知识产权',
  corporate: '公司治理',
  litigation: '民事诉讼',
  compliance: '合规审查',
  due_diligence: '尽职调查',
  criminal: '刑事案件',
  administrative: '行政诉讼',
  arbitration: '仲裁案件',
  other: '其他',
};
const translateType = (key: string) => CASE_TYPE_LABELS[key] || key;

export function CaseDistribution() {
  const [viewType, setViewType] = useState<'pie' | 'bar'>('pie');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<{ name: string; value: number; color: string }[]>([]);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const stats = await casesApi.getStatistics();
      // 将 by_type 转换为图表格式
      const typeData = Object.entries(stats.by_type || {}).map(([name, value], index) => ({
        name: translateType(name),
        value,
        color: COLORS[index % COLORS.length]
      }));
      setData(typeData.length > 0 ? typeData : [
        { name: '暂无数据', value: 0, color: 'hsl(var(--muted-foreground))' }
      ]);
    } catch (error) {
      console.error('加载统计数据失败', error);
      // 加载失败时使用 fallback 数据（从案件列表推算）
      try {
        const cases = await casesApi.list({ page: 1, page_size: 100 });
        const caseList = cases.items || (cases as any).data || [];
        const typeMap: Record<string, number> = {};
        caseList.forEach((c: any) => {
          const t = translateType(c.case_type || 'other');
          typeMap[t] = (typeMap[t] || 0) + 1;
        });
        const fallback = Object.entries(typeMap).map(([name, value], i) => ({
          name,
          value: value as number,
          color: COLORS[i % COLORS.length],
        }));
        setData(fallback.length > 0 ? fallback : [{ name: '暂无数据', value: 0, color: 'hsl(var(--muted-foreground))' }]);
      } catch {
        setData([{ name: '加载失败', value: 0, color: 'hsl(var(--muted-foreground))' }]);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={`${cardStyle.base} h-[380px] flex items-center justify-center`}>
        <icons.Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className={cardStyle.base}
    >
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className={heading.section}>案件分布</h3>
          <p className="text-sm text-muted-foreground mt-1">当前进行中的案件类型统计</p>
        </div>
        <div className="flex gap-2 bg-muted p-1 rounded-xl">
          <button
            onClick={() => setViewType('pie')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              viewType === 'pie'
                ? 'bg-background text-primary shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            饼图
          </button>
          <button
            onClick={() => setViewType('bar')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              viewType === 'bar'
                ? 'bg-background text-primary shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            详情
          </button>
        </div>
      </div>

      {viewType === 'pie' ? (
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <div className="w-full sm:w-[55%] h-[220px] sm:h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  strokeWidth={0}
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                    fontSize: '12px',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="flex-1 w-full grid grid-cols-2 sm:grid-cols-1 gap-2">
            {data.map((item, index) => (
              <motion.div
                key={item.name}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-xs text-muted-foreground truncate">{item.name}</span>
                </div>
                <span className="text-xs font-semibold text-foreground shrink-0">{item.value}</span>
              </motion.div>
            ))}
          </div>
        </div>
      ) : (
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} />
              <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} />
              <Tooltip cursor={{ fill: 'hsl(var(--muted))' }} />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </motion.div>
  );
}
