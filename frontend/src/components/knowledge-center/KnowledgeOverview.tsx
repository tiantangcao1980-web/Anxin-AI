/**
 * 知识中心总览
 */

import { memo } from'react';
import { icons } from'@/lib/icons';

const stats = [
 { label:'知识库总量', value:'12', icon: icons.Database, color:'bg-primary/10 text-primary' },
 { label:'文档数', value:'1,284', icon: icons.FileText, color:'bg-success/10 text-success' },
 { label:'知识图谱节点', value:'3,562', icon: icons.Network, color:'bg-primary/10 text-primary' },
 { label:'今日搜索', value:'47', icon: icons.Search, color:'bg-warning/10 text-warning' },
];

const recentActivities = [
 { action:'新增法规', detail:'《民法典》司法解释（二）', time:'2小时前' },
 { action:'知识更新', detail:'劳动争议相关案例库已更新', time:'5小时前' },
 { action:'图谱扩展', detail:'合同纠纷关联关系新增 28 条', time:'1天前' },
 { action:'经验沉淀', detail:'知识产权侵权分析模板', time:'2天前' },
];

export const KnowledgeOverview = memo(function KnowledgeOverview() {
 return (
 <div className="p-6 space-y-6">
 {/* 数据概览 */}
 <div>
 <h2 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2">
 <icons.TrendingUp className="w-5 h-5 text-primary" />
 知识中心概览
 </h2>
 <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
 {stats.map((stat) => {
 const Icon = stat.icon;
 return (
 <div key={stat.label} className="bg-background rounded-xl border border-border p-4 shadow-sm">
 <div className="flex items-center gap-3 mb-2">
 <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${stat.color}`}>
 <Icon className="w-5 h-5" />
 </div>
 </div>
 <div className="text-2xl font-bold text-foreground">{stat.value}</div>
 <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
 </div>
 );
 })}
 </div>
 </div>

 {/* 最近动态 */}
 <div>
 <h3 className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
 <icons.BookOpen className="w-4 h-4 text-muted-foreground" />
 最近动态
 </h3>
 <div className="space-y-3">
 {recentActivities.map((activity, i) => (
 <div key={i} className="flex items-center gap-3 bg-background rounded-lg border border-border p-3 shadow-sm">
 <div className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
 <div className="flex-1 min-w-0">
 <span className="text-sm font-medium text-foreground">{activity.action}</span>
 <span className="text-sm text-muted-foreground ml-2">{activity.detail}</span>
 </div>
 <span className="text-xs text-muted-foreground flex-shrink-0">{activity.time}</span>
 </div>
 ))}
 </div>
 </div>

 {/* 快捷操作 */}
 <div>
 <h3 className="text-sm font-medium text-foreground mb-3">快捷操作</h3>
 <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
 {[
 { label:'搜索法律知识', desc:'全文检索法律法规和案例', icon: icons.Search },
 { label:'浏览知识图谱', desc:'可视化法律关系网络', icon: icons.Network },
 { label:'管理知识库', desc:'上传和整理法律文档', icon: icons.Database },
 ].map((item) => {
 const Icon = item.icon;
 return (
 <button
 key={item.label}
 className="text-left bg-background rounded-xl border border-border p-4 shadow-sm hover:shadow-md hover:border-primary/30 transition-all group"
 >
 <Icon className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors mb-2" />
 <div className="text-sm font-medium text-foreground">{item.label}</div>
 <div className="text-xs text-muted-foreground mt-1">{item.desc}</div>
 </button>
 );
 })}
 </div>
 </div>
 </div>
 );
});
