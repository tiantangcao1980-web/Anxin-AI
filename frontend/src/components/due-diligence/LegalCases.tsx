import { motion } from 'framer-motion';
import { icons } from '@/lib/icons';

interface LegalCasesProps {
  data?: {
    total_cases?: number;
    as_plaintiff?: number;
    as_defendant?: number;
    execution_cases?: number;
    dishonest_records?: number;
    major_cases?: Array<{
      case_no?: string;
      caseNo?: string;
      case_type?: string;
      type?: string;
      role?: string;
      status?: string;
      result?: string;
      amount?: string;
      date?: string;
      filing_date?: string;
    }>;
  };
}

const defaultCases = [
  {
    id: 1,
    caseNo: '(2023)京0108民初12345号',
    type: '合同纠纷',
    role: '被告',
    status: '已结案',
    result: '调解结案',
    amount: '50万元',
    date: '2023-11-20',
  },
  {
    id: 2,
    caseNo: '(2023)京0108民初23456号',
    type: '劳动争议',
    role: '被告',
    status: '已结案',
    result: '败诉',
    amount: '8万元',
    date: '2023-12-15',
  },
  {
    id: 3,
    caseNo: '(2024)京0108民初34567号',
    type: '知识产权',
    role: '原告',
    status: '审理中',
    result: '待判决',
    amount: '200万元',
    date: '2024-01-10',
  },
];

export function LegalCases({ data }: LegalCasesProps) {
  // 优先使用后端返回的 major_cases 数据
  const cases = data?.major_cases && data.major_cases.length > 0
    ? data.major_cases.map((c, i) => ({
        id: i + 1,
        caseNo: c.case_no || c.caseNo || '未公布',
        type: c.case_type || c.type || '未知',
        role: c.role || '未知',
        status: c.status || '未知',
        result: c.result || '待判决',
        amount: c.amount || '未披露',
        date: c.date || c.filing_date || '未知',
      }))
    : defaultCases;
  
  const summary = data || {
    total_cases: cases.length,
    as_plaintiff: cases.filter(c => c.role === '原告').length,
    as_defendant: cases.filter(c => c.role === '被告').length,
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="bg-background rounded-xl border border-border p-6"
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <icons.Scale className="w-5 h-5 text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-foreground">涉诉情况</h3>
            <p className="text-sm text-muted-foreground">共 {cases.length} 起案件</p>
          </div>
        </div>
        <div className="flex gap-2">
          <span className="px-2 py-1 bg-red-100 dark:bg-red-950/30 text-red-700 dark:text-red-300 rounded text-xs font-medium">
            被告 2 起
          </span>
          <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 rounded text-xs font-medium">
            原告 1 起
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {cases.map((item, index) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <icons.FileText className="w-4 h-4 text-muted-foreground" />
                  <span className="font-mono text-xs text-muted-foreground">{item.caseNo}</span>
                </div>
                <h4 className="font-medium text-foreground">{item.type}</h4>
              </div>
              <span
                className={`px-2 py-1 rounded text-xs font-medium ${
                  item.status === '已结案'
                    ? 'bg-muted text-foreground'
                    : 'bg-primary/10 text-primary'
                }`}
              >
                {item.status}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground mb-1">诉讼角色</p>
                <p className={`font-medium ${item.role === '被告' ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                  {item.role}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">判决结果</p>
                <p className="font-medium text-foreground">{item.result}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">涉案金额</p>
                <p className="font-medium text-foreground">{item.amount}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">立案日期</p>
                <p className="font-medium text-foreground">{item.date}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
