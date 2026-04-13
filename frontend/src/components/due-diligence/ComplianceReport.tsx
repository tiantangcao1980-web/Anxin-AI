/**
 * ComplianceReport - 信用合规检查面板
 * 展示六项核心合规指标及合规率
 */
import { motion } from'framer-motion';
import { icons } from'@/lib/icons';

interface ComplianceReportProps {
 data?: {
 credit_rating?: string;
 administrative_penalties?: number;
 tax_violations?: number;
 environmental_penalties?: number;
 abnormal_operations?: number;
 serious_violations?: number;
 dishonest_records?: number;
 };
}

const CREDIT_RATING_ORDER = ['AAA','AA','A','BBB','BB','B','CCC','CC','C','D'];

/** 正确的信用评级比较：返回评级在序列中的位置，越小越好 */
function ratingRank(rating?: string): number {
 if (!rating) return -1;
 const idx = CREDIT_RATING_ORDER.indexOf(rating.toUpperCase());
 return idx === -1 ? CREDIT_RATING_ORDER.length : idx;
}

function ratingStatus(rating?: string):'pass' |'warning' |'fail' {
 const rank = ratingRank(rating);
 if (rank < 0) return'pass';
 if (rank <= 2) return'pass'; // AAA, AA, A
 if (rank <= 5) return'warning'; // BBB, BB, B
 return'fail'; // CCC 及以下
}

const defaultComplianceItems = [
 { category:'工商登记', status:'pass' as const, detail:'信息完整，无异常' },
 { category:'税务合规', status:'pass' as const, detail:'纳税正常' },
 { category:'社保缴纳', status:'warning' as const, detail:'存在1个月欠缴' },
 { category:'环保资质', status:'pass' as const, detail:'资质齐全' },
 { category:'安全生产', status:'fail' as const, detail:'2023年1起安全事故' },
 { category:'知识产权', status:'pass' as const, detail:'无侵权记录' },
];

export function ComplianceReport({ data }: ComplianceReportProps) {
 const complianceItems = data ? [
 {
 category:'工商登记',
 status: ((data.abnormal_operations || 0) > 0 ?'warning' :'pass') as'pass' |'warning' |'fail',
 detail: (data.abnormal_operations || 0) > 0 ? `经营异常 ${data.abnormal_operations} 条` :'信息完整，无异常',
 },
 {
 category:'税务合规',
 status: ((data.tax_violations || 0) > 0 ?'fail' :'pass') as'pass' |'warning' |'fail',
 detail: (data.tax_violations || 0) > 0 ? `税务违规 ${data.tax_violations} 条` :'纳税正常',
 },
 {
 category:'信用评级',
 status: ratingStatus(data.credit_rating),
 detail: `信用评级 ${data.credit_rating ||'-'}`,
 },
 {
 category:'行政处罚',
 status: ((data.administrative_penalties || 0) > 0 ?'fail' :'pass') as'pass' |'warning' |'fail',
 detail: (data.administrative_penalties || 0) > 0 ? `行政处罚 ${data.administrative_penalties} 条` :'无处罚记录',
 },
 {
 category:'环保合规',
 status: ((data.environmental_penalties || 0) > 0 ?'fail' :'pass') as'pass' |'warning' |'fail',
 detail: (data.environmental_penalties || 0) > 0 ? `环保处罚 ${data.environmental_penalties} 条` :'资质齐全',
 },
 {
 category:'严重违法',
 status: ((data.serious_violations || 0) > 0 ?'fail' :'pass') as'pass' |'warning' |'fail',
 detail: (data.serious_violations || 0) > 0 ? `严重违法 ${data.serious_violations} 条` :'无违法记录',
 },
 {
 category:'失信被执行',
 status: ((data.dishonest_records || 0) > 0 ?'fail' :'pass') as'pass' |'warning' |'fail',
 detail: (data.dishonest_records || 0) > 0 ? `失信记录 ${data.dishonest_records} 条` :'无失信记录',
 },
 ] : defaultComplianceItems;

 const statusConfig = {
 pass: {
 icon: icons.CheckCircle,
 color:'text-success',
 bg:'bg-success/10',
 border:'border-success/20',
 },
 warning: {
 icon: icons.AlertCircle,
 color:'text-warning',
 bg:'bg-warning/10',
 border:'border-warning/20',
 },
 fail: {
 icon: icons.XCircle,
 color:'text-destructive',
 bg:'bg-destructive/10',
 border:'border-destructive/20',
 },
 };

 const passCount = complianceItems.filter((item) => item.status ==='pass').length;
 const complianceRate = Math.round((passCount / complianceItems.length) * 100);

 const rateColor = complianceRate >= 80
 ?'text-success'
 : complianceRate >= 50
 ?'text-warning'
 :'text-destructive';

 const rateBg = complianceRate >= 80
 ?'from-success to-success border-success/20'
 : complianceRate >= 50
 ?'from-warning to-warning border-warning/20'
 :'from-destructive to-destructive border-destructive/20';

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
 <h3 className="font-medium text-foreground">合规检查</h3>
 <p className="text-sm text-muted-foreground">{complianceItems.length} 项核心指标</p>
 </div>
 </div>

 <div className={`bg-gradient-to-br ${rateBg} rounded-lg p-4 mb-4 border`}>
 <div className="text-center">
 <p className={`text-sm ${rateColor} mb-1`}>合规率</p>
 <p className={`text-3xl font-bold ${rateColor}`}>{complianceRate}%</p>
 <p className={`text-xs ${rateColor} mt-1 opacity-80`}>
 {passCount}/{complianceItems.length} 项通过
 </p>
 </div>
 </div>

 <div className="space-y-2">
 {complianceItems.map((item, index) => {
 const config = statusConfig[item.status];
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
