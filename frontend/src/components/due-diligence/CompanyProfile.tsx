/**
 * CompanyProfile - 企业概况 Hero 卡片
 * 展示企业基本信息与动态综合评分
 */
import { motion } from'framer-motion';
import { icons } from'@/lib/icons';

interface CompanyProfileProps {
 data?: {
 name?: string;
 legal_representative?: string;
 registered_capital?: string;
 established_date?: string;
 status?: string;
 business_scope?: string;
 address?: string;
 company_type?: string;
 data_source?: string;
 };
 companyName?: string;
 /** 五维风险数据，用于计算综合评分 */
 riskData?: {
 operation_risk?: number;
 litigation_risk?: number;
 credit_risk?: number;
 compliance_risk?: number;
 relation_risk?: number;
 };
}

/**
 * 综合评分 = 100 - 平均风险分
 * 风险分越高，综合评分越低
 */
function computeOverallScore(risk?: CompanyProfileProps['riskData']): number {
 if (!risk) return 0;
 const scores = [
 risk.operation_risk ?? 0,
 risk.litigation_risk ?? 0,
 risk.credit_risk ?? 0,
 risk.compliance_risk ?? 0,
 risk.relation_risk ?? 0,
 ];
 const validScores = scores.filter(s => s > 0);
 if (validScores.length === 0) return 0;
 const avgRisk = validScores.reduce((a, b) => a + b, 0) / validScores.length;
 return Math.max(0, Math.min(100, Math.round(100 - avgRisk)));
}

function scoreLabel(score: number): string {
 if (score >= 80) return'优秀';
 if (score >= 60) return'良好';
 if (score >= 40) return'一般';
 return'较差';
}

function scoreColor(score: number): string {
 if (score >= 80) return'text-success';
 if (score >= 60) return'text-white';
 if (score >= 40) return'text-warning';
 return'text-destructive';
}

export function CompanyProfile({ data, companyName, riskData }: CompanyProfileProps) {
 const overallScore = computeOverallScore(riskData);

 const companyData = {
 name: data?.name || companyName ||'-',
 legalPerson: data?.legal_representative ||'-',
 registeredCapital: data?.registered_capital ||'-',
 foundedDate: data?.established_date ||'-',
 status: data?.status ||'-',
 industry: data?.business_scope?.slice(0, 20) ||'-',
 address: data?.address ||'-',
 employees: data?.company_type ||'-',
 };

 const dataSource = data?.data_source ||'';

 const items = [
 { icon: icons.Users, label:'法定代表人', value: companyData.legalPerson },
 { icon: icons.DollarSign, label:'注册资本', value: companyData.registeredCapital },
 { icon: icons.Calendar, label:'成立日期', value: companyData.foundedDate },
 { icon: icons.Award, label:'经营状态', value: companyData.status, highlight: true },
 { icon: icons.Building2, label:'所属行业', value: companyData.industry },
 { icon: icons.MapPin, label:'注册地址', value: companyData.address },
 ];

 return (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 className="bg-primary rounded-2xl border border-primary/30 p-6 text-white shadow-lg"
 >
 <div className="flex items-start justify-between mb-6">
 <div>
 <h2 className="text-2xl font-medium mb-2">{companyData.name}</h2>
 <div className="flex items-center gap-2">
 <span className="px-3 py-1 bg-white/20 rounded-full text-sm font-medium">
 {companyData.employees}
 </span>
 {companyData.status !=='-' && (
 <span className="px-3 py-1 bg-success/10 rounded-full text-sm font-medium">
 ✓ {companyData.status}
 </span>
 )}
 {dataSource && (
 <span className={`px-3 py-1 rounded-full text-xs font-medium ${
 dataSource.includes('公开') ?'bg-info/10' :'bg-warning/10'
 }`}>
 {dataSource}
 </span>
 )}
 </div>
 </div>
 <div className="text-right">
 <p className="text-white/70 text-sm mb-1">综合评分</p>
 <p className={`text-4xl font-bold ${scoreColor(overallScore)}`}>
 {overallScore > 0 ? overallScore :'-'}
 </p>
 {overallScore > 0 && (
 <p className="text-xs text-white/60 mt-0.5">{scoreLabel(overallScore)}</p>
 )}
 </div>
 </div>

 <div className="grid grid-cols-3 gap-4">
 {items.map((item, index) => {
 const Icon = item.icon;
 return (
 <motion.div
 key={item.label}
 initial={{ opacity: 0, x: -10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 className="bg-white/10 backdrop-blur-sm rounded-xl p-3"
 >
 <div className="flex items-center gap-2 mb-1">
 <Icon className="w-4 h-4 text-white/70" />
 <span className="text-xs text-white/70">{item.label}</span>
 </div>
 <p className={`text-sm font-medium ${item.highlight ?'text-success' :''}`}>
 {item.value}
 </p>
 </motion.div>
 );
 })}
 </div>
 </motion.div>
 );
}
