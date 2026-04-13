/**
 * 专业模式工具栏
 *
 * 面向律师和高级法务用户，跳过引导式问答，直接操作：
 * - 合同审查：直接上传合同执行审查
 * - 文书起草：直接输入需求生成文书
 * - 法律检索：直接检索法条/案例
 * - 编辑器：打开右侧协作编辑器
 *
 * 与普通模式的区别：
 * - 不走 clarification_request 追问流程
 * - 直接路由到对应 Agent
 * - 仍然经过 output_validator 验证（安全约束不跳过）
 */

import { Button } from'@/components/ui/button'
import { Badge } from'@/components/ui/badge'
import { icons } from'@/lib/icons'
import {
 Tooltip,
 TooltipContent,
 TooltipProvider,
 TooltipTrigger,
} from'@/components/ui/tooltip'

interface ProfessionalToolbarProps {
 onAction: (action: string, intentHint?: string) => void
 isActive: boolean
 onToggle: () => void
}

const PROFESSIONAL_ACTIONS = [
 {
 id:'review',
 label:'审查合同',
 icon: icons.FileCheck,
 intentHint:'CONTRACT_REVIEW',
 description:'上传合同直接审查，跳过引导问答',
 color:'text-info',
 },
 {
 id:'draft',
 label:'起草文书',
 icon: icons.PenTool,
 intentHint:'DOCUMENT_DRAFTING',
 description:'输入需求直接生成，适合熟悉文书格式的用户',
 color:'text-success',
 },
 {
 id:'search',
 label:'法律检索',
 icon: icons.BookOpen,
 intentHint:'QA_CONSULTATION',
 description:'直接检索法条、案例和裁判文书',
 color:'text-purple-600',
 },
 {
 id:'evidence',
 label:'证据分析',
 icon: icons.FolderOpen,
 intentHint:'EVIDENCE_PROCESSING',
 description:'上传证据材料直接分析',
 color:'text-orange-600',
 },
]

export default function ProfessionalToolbar({
 onAction,
 isActive,
 onToggle,
}: ProfessionalToolbarProps) {
 return (
 <div className="flex items-center gap-2">
 {/* 专业模式开关 */}
 <Button
 variant={isActive ?'default' :'outline'}
 size="sm"
 className={`text-xs h-7 ${isActive ?'bg-warning hover:bg-warning/20' :''}`}
 onClick={onToggle}
 >
 <icons.Zap className="h-3 w-3 mr-1" />
 {isActive ?'专业模式' :'标准模式'}
 </Button>

 {/* 专业模式工具按钮 */}
 {isActive && (
 <TooltipProvider delayDuration={200}>
 <div className="flex items-center gap-1 ml-1 pl-2 border-l">
 {PROFESSIONAL_ACTIONS.map((action) => (
 <Tooltip key={action.id}>
 <TooltipTrigger asChild>
 <Button
 variant="ghost"
 size="sm"
 className="text-xs h-7 px-2"
 onClick={() => onAction(action.id, action.intentHint)}
 >
 <action.icon className={`h-3.5 w-3.5 mr-1 ${action.color}`} />
 {action.label}
 </Button>
 </TooltipTrigger>
 <TooltipContent side="bottom" className="text-xs max-w-48">
 {action.description}
 </TooltipContent>
 </Tooltip>
 ))}
 </div>
 </TooltipProvider>
 )}

 {isActive && (
 <Badge variant="outline" className="text-xs h-5 ml-1 text-warning border-warning/20">
 跳过引导 · 直达Agent
 </Badge>
 )}
 </div>
 )
}
