import { motion } from'framer-motion';
import { icons } from'@/lib/icons';

const originalContent = [
 { id: 1, text:'第三条 付款方式', type:'normal' },
 { id: 2, text:'乙方应在收到发票后10日内付款', type:'risk', issue:'时间约定模糊，建议明确工作日' },
 { id: 3, text:'第四条 保密条款', type:'normal' },
 { id: 4, text:'双方应对项目信息保密', type:'risk', issue:'保密范围不明确，建议补充具体内容' },
 { id: 5, text:'第五条 违约责任', type:'normal' },
 { id: 6, text:'违约方应赔偿损失，上限为合同金额的10%', type:'risk', issue:'违约上限过低，建议提高到30%' },
];

const suggestedContent = [
 { id: 1, text:'第三条 付款方式', type:'normal' },
 { id: 2, text:'乙方应在收到增值税专用发票后10个工作日内完成付款', type:'added', reason:'明确了工作日和发票类型' },
 { id: 3, text:'第四条 保密条款', type:'normal' },
 { id: 4, text:'双方应对项目中涉及的技术资料、商业信息、客户数据等进行保密，保密期限为合同终止后3年', type:'added', reason:'明确了保密范围和期限' },
 { id: 5, text:'第五条 违约责任', type:'normal' },
 { id: 6, text:'违约方应赔偿守约方因此遭受的全部损失，赔偿上限为合同金额的30%', type:'added', reason:'提高了违约成本' },
 { id: 7, text:'第六条 不可抗力', type:'new', reason:'新增条款，明确不可抗力情形' },
 { id: 8, text:'因不可抗力导致合同无法履行的，双方可协商解除合同，互不承担违约责任', type:'new' },
];

export function DocumentDiff() {
 return (
 <motion.div
 initial={{ opacity: 0, x: 20 }}
 animate={{ opacity: 1, x: 0 }}
 className="h-full p-6 overflow-y-auto bg-muted"
 >
 <div className="space-y-4">
 {/* Header */}
 <div className="flex items-center justify-between">
 <div>
 <h3 className="font-semibold text-foreground mb-1">文档对比视图</h3>
 <p className="text-sm text-muted-foreground">红色 = 风险点 | 绿色 = AI 优化建议</p>
 </div>
 <div className="flex items-center gap-2">
 <button className="px-3 py-1.5 text-sm bg-primary text-white rounded-lg hover:bg-primary/90">
 接受全部建议
 </button>
 </div>
 </div>

 {/* Split View */}
 <div className="grid grid-cols-2 gap-4">
 {/* Original */}
 <div className="bg-background rounded-xl border border-border overflow-hidden">
 <div className="bg-muted px-4 py-3 border-b border-border">
 <div className="flex items-center gap-2">
 <icons.FileText className="w-4 h-4 text-muted-foreground" />
 <span className="font-medium text-sm text-foreground">原始文档</span>
 </div>
 </div>
 <div className="p-4 space-y-3">
 {originalContent.map((item) => (
 <div key={item.id}>
 <p
 className={`text-sm leading-relaxed p-2 rounded ${
 item.type ==='risk'
 ?'bg-destructive/10 border border-destructive/20 text-destructive'
 :'text-foreground'
 }`}
 >
 {item.text}
 </p>
 {item.type ==='risk' && (
 <div className="mt-1 flex items-start gap-2 text-xs text-destructive px-2">
 <icons.AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
 <span>{item.issue}</span>
 </div>
 )}
 </div>
 ))}
 </div>
 </div>

 {/* Suggested */}
 <div className="bg-background rounded-xl border border-border overflow-hidden">
 <div className="bg-success/10 px-4 py-3 border-b border-success/20">
 <div className="flex items-center gap-2">
 <icons.FileText className="w-4 h-4 text-success" />
 <span className="font-medium text-sm text-success">AI 优化版本</span>
 </div>
 </div>
 <div className="p-4 space-y-3">
 {suggestedContent.map((item, index) => (
 <motion.div
 key={item.id}
 initial={{ opacity: 0, x: 10 }}
 animate={{ opacity: 1, x: 0 }}
 transition={{ delay: index * 0.05 }}
 >
 <p
 className={`text-sm leading-relaxed p-2 rounded ${
 item.type ==='added' || item.type ==='new'
 ?'bg-success/10 border border-success/20 text-success'
 :'text-foreground'
 }`}
 >
 {item.text}
 </p>
 {(item.type ==='added' || item.type ==='new') && (
 <div className="mt-1 flex items-start gap-2 text-xs text-success px-2">
 <icons.CheckCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
 <span>{item.reason}</span>
 </div>
 )}
 </motion.div>
 ))}
 </div>
 </div>
 </div>

 {/* Summary */}
 <div className="bg-background rounded-xl border border-border p-4">
 <h4 className="font-medium text-foreground mb-3 text-sm">修改摘要</h4>
 <div className="grid grid-cols-3 gap-4 text-center">
 <div className="p-3 bg-destructive/10 rounded-lg">
 <p className="text-2xl font-bold text-destructive">3</p>
 <p className="text-xs text-destructive mt-1">风险点</p>
 </div>
 <div className="p-3 bg-success/10 rounded-lg">
 <p className="text-2xl font-bold text-success">3</p>
 <p className="text-xs text-success mt-1">优化建议</p>
 </div>
 <div className="p-3 bg-primary/5 rounded-lg">
 <p className="text-2xl font-bold text-primary">2</p>
 <p className="text-xs text-primary mt-1">新增条款</p>
 </div>
 </div>
 </div>
 </div>
 </motion.div>
 );
}
