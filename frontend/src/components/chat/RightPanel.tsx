/**
 * 右侧面板 v7.1 — 双模式切换（工作台 / 文档）
 *
 * 每个 Tab 独立渲染自己的内容区：
 * - 工作台：AgentWorkspace（有 Agent 活动时全高展示，无内容时显示工作台引导）
 * - 文档：CanvasEditor（有文档时全高展示，无文档时显示新建引导）
 *
 * 自动切换由 Chat.tsx WebSocket handler 驱动，无需额外逻辑
 */

import { memo, useState, useCallback, lazy, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { heading } from '@/lib/design-tokens';
import { useChatStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import type {
  RightPanelTab,
  AgentResult,
  ThinkingStep,
  RequirementAnalysis,
  CanvasContent,
  AnalysisData,
} from '@/lib/store';

const DOCUMENT_TEMPLATES = [
  {
    id: 'tpl-sales',
    title: '买卖合同',
    description: '标准化商品买卖合同，含标的、价款、交付、验收、违约责任等条款',
    iconKey: 'Briefcase' as keyof typeof icons,
    type: 'contract' as CanvasContent['type'],
    tags: ['B2B', '贸易'],
    content: `# 买卖合同

合同编号：【____】

甲方（出卖人）：【____】
统一社会信用代码：【____】
地址：【____】

乙方（买受人）：【____】
统一社会信用代码：【____】
地址：【____】

根据《中华人民共和国民法典》及相关法律法规，甲乙双方本着平等互利的原则，经友好协商，就商品买卖事宜达成如下协议：

## 第一条 标的物

商品名称：【____】
规格型号：【____】
数量：【____】
单价：【____】元
总价：【____】元

## 第二条 质量标准

标的物应符合国家标准/行业标准【____】，并满足以下技术要求：【____】

## 第三条 交付方式与期限

1. 交付方式：【____】
2. 交付地点：【____】
3. 交付期限：自本合同签订之日起【____】个工作日内

## 第四条 价款与支付

1. 合同总价款为人民币【____】元（大写：【____】）
2. 支付方式：【____】
3. 支付期限：【____】

## 第五条 验收

1. 乙方应在收到货物后【____】个工作日内完成验收
2. 验收标准：【____】

## 第六条 违约责任

1. 甲方逾期交付的，每逾期一日按合同总价款的【____】%支付违约金
2. 乙方逾期付款的，每逾期一日按未付款项的【____】%支付违约金

## 第七条 争议解决

因本合同引起的争议，双方应友好协商解决；协商不成的，提交【____】仲裁委员会仲裁/向有管辖权的人民法院提起诉讼。

## 第八条 其他约定

【____】

甲方（盖章）：________    乙方（盖章）：________
法定代表人：________    法定代表人：________
日期：____年____月____日    日期：____年____月____日`,
  },
  {
    id: 'tpl-labor',
    title: '劳动合同',
    description: '标准劳动合同模板，含岗位、薪酬、工时、社保、竞业限制等条款',
    iconKey: 'Users' as keyof typeof icons,
    type: 'contract' as CanvasContent['type'],
    tags: ['人事', 'HR'],
    content: `# 劳动合同

甲方（用人单位）：【____】
统一社会信用代码：【____】
法定代表人：【____】
地址：【____】

乙方（劳动者）：【____】
身份证号码：【____】
住址：【____】

根据《中华人民共和国劳动合同法》及相关法律法规，甲乙双方在平等自愿、协商一致的基础上签订本合同。

## 第一条 合同期限

本合同为【固定期限/无固定期限】劳动合同。
合同期限自____年____月____日起至____年____月____日止。
试用期为____个月，自____年____月____日起至____年____月____日止。

## 第二条 工作内容与工作地点

1. 乙方担任【____】岗位（部门：【____】）
2. 工作地点：【____】

## 第三条 工作时间与休息休假

实行标准工时制度，每日工作8小时，每周工作40小时。

## 第四条 劳动报酬

1. 月工资标准：人民币【____】元（税前）
2. 发放日期：每月【____】日
3. 试用期工资：人民币【____】元（税前）

## 第五条 社会保险与福利

甲方依法为乙方缴纳社会保险费（养老、医疗、失业、工伤、生育保险）和住房公积金。

## 第六条 保密与竞业限制

【根据需要填写】

## 第七条 合同解除与终止

按照《劳动合同法》相关规定执行。

甲方（盖章）：________    乙方（签字）：________
日期：____年____月____日    日期：____年____月____日`,
  },
  {
    id: 'tpl-nda',
    title: '保密协议（NDA）',
    description: '双向保密协议，适用于商业合作前的信息保护',
    iconKey: 'Lock' as keyof typeof icons,
    type: 'contract' as CanvasContent['type'],
    tags: ['保密', '合作'],
    content: `# 保密协议

甲方：【____】
乙方：【____】

鉴于双方拟就【____】事项进行合作洽谈，为保护双方的商业秘密和保密信息，经友好协商达成如下保密协议：

## 第一条 保密信息的定义

保密信息是指一方向另一方披露的与合作事项有关的所有非公开信息，包括但不限于：技术资料、商业计划、客户信息、财务数据、产品设计等。

## 第二条 保密义务

1. 接收方应对保密信息严格保密，未经披露方书面同意不得向第三方泄露
2. 接收方仅限于为合作目的使用保密信息
3. 接收方应采取合理措施保护保密信息的安全

## 第三条 保密期限

本协议的保密期限为【____】年，自本协议签署之日起计算。

## 第四条 违约责任

违反本协议的一方应赔偿守约方因此遭受的全部损失。

甲方（盖章）：________    乙方（盖章）：________
日期：____年____月____日    日期：____年____月____日`,
  },
  {
    id: 'tpl-lease',
    title: '租赁合同',
    description: '房屋/场地租赁合同，含租金、押金、维修、续租等条款',
    iconKey: 'Home' as keyof typeof icons,
    type: 'contract' as CanvasContent['type'],
    tags: ['租赁', '不动产'],
    content: `# 房屋租赁合同

出租方（甲方）：【____】
承租方（乙方）：【____】

## 第一条 租赁标的

甲方将位于【____】的房屋（面积约____平方米）出租给乙方使用。

## 第二条 租赁期限

自____年____月____日起至____年____月____日止，共计____个月。

## 第三条 租金与支付

1. 月租金：人民币【____】元
2. 支付方式：【月付/季付/半年付】，每期于期初【____】日前支付
3. 押金：人民币【____】元，于签约时一次性支付

## 第四条 房屋用途

乙方将该房屋用于【____】，未经甲方书面同意不得改变用途或转租。

## 第五条 维修与保养

正常损耗维修由甲方负责，因乙方使用不当造成的损坏由乙方负责修复或赔偿。

## 第六条 合同终止与续租

租期届满前____日，乙方如需续租应书面通知甲方，双方另行协商续租条件。

甲方（签章）：________    乙方（签章）：________
日期：____年____月____日    日期：____年____月____日`,
  },
  {
    id: 'tpl-legal-opinion',
    title: '法律意见书',
    description: '标准法律意见书框架，含事实梳理、法律分析、结论建议',
    iconKey: 'FileText' as keyof typeof icons,
    type: 'document' as CanvasContent['type'],
    tags: ['文书', '意见'],
    content: `# 法律意见书

致：【委托方名称】

编号：【____】

## 一、引言

【律师事务所名称】（以下简称"本所"）接受【委托方】的委托，就【事项描述】出具本法律意见书。

## 二、事实概述

【简要描述相关事实背景】

## 三、法律分析

### （一）适用法律法规

【列出相关法律法规】

### （二）法律分析与论证

【详细法律分析】

### （三）风险提示

【潜在法律风险分析】

## 四、结论与建议

1. 【结论一】
2. 【结论二】
3. 【建议措施】

本法律意见书仅供委托方参考使用，不构成对任何第三方的承诺或保证。

【律师事务所名称】
经办律师：________
日期：____年____月____日`,
  },
  {
    id: 'tpl-lawyer-letter',
    title: '律师函',
    description: '标准律师函模板，适用于催告、警告、沟通等场景',
    iconKey: 'Mail' as keyof typeof icons,
    type: 'document' as CanvasContent['type'],
    tags: ['文书', '函件'],
    content: `# 律师函

【律函字〔____〕第____号】

致：【收函方名称】
地址：【____】

## 事由：关于【____】事宜的律师函

【律师事务所名称】依法接受【委托方名称】（以下简称"委托人"）的委托，指派本律师就【简要事由】事宜致函贵方，内容如下：

## 一、基本事实

【陈述基本事实、双方关系、争议事项】

## 二、法律依据

根据《中华人民共和国民法典》第____条之规定，【法律分析】。

## 三、律师意见

鉴于上述事实和法律规定，本律师提出如下意见：

1. 【要求一】
2. 【要求二】

请贵方在收到本函后____日内【采取行动/给予回复】，否则委托人将依法采取进一步法律措施，届时由此产生的法律后果由贵方自行承担。

特此函告。

【律师事务所名称】
律师：________（签章）
日期：____年____月____日`,
  },
] as const;

interface RightPanelProps {
  activeTab: RightPanelTab;
  onTabChange: (tab: RightPanelTab) => void;
  isLive: boolean;

  agentResults: AgentResult[];
  thinkingSteps: ThinkingStep[];
  a2uiData: any;
  requirementAnalysis: RequirementAnalysis | null;
  isProcessing: boolean;

  canvasContent: CanvasContent | null;
  onCanvasContentChange: (content: string) => void;
  onCanvasTitleChange: (title: string) => void;
  onCanvasModeChange: (mode: CanvasContent['type']) => void;
  onCanvasAIOptimize: () => void;
  onCanvasSuggestionAction: (id: string, action: 'accept' | 'reject') => void;

  onForwardToLawyer?: () => void;
  onInitiateSigning?: () => void;

  onCanvasSaveAsDocument?: () => void;
  canvasSaved?: boolean;

  analysisData: AnalysisData;

  onWorkspaceConfirm?: (confirmationId: string, selectedIds: string[]) => void;
  onWorkspaceAction?: (actionId: string, payload?: any) => void;

  onDocumentAction?: (action: string, payload?: any) => void;

  onClosePanel?: () => void;

  onNewConversation?: () => void;
}

const AgentWorkspace = lazy(async () => {
  const module = await import('./AgentWorkspace')
  return { default: module.AgentWorkspace }
})

const CanvasEditor = lazy(async () => {
  const module = await import('./CanvasEditor')
  return { default: module.CanvasEditor }
})

const LawyerAssistPanel = lazy(async () => {
  const module = await import('./LawyerAssistPanel')
  return { default: module.LawyerAssistPanel }
})

const SigningWorkflow = lazy(async () => {
  const module = await import('./SigningWorkflow')
  return { default: module.SigningWorkflow }
})


export const RightPanel = memo(function RightPanel(props: RightPanelProps) {
  const { activeTab, onTabChange, isLive } = props;
  const store = useChatStore();
  const navigate = useNavigate();
  const { documentOverlay, documentList, addDocumentToList, removeDocumentFromList } = store;

  const [showDocList, setShowDocList] = useState(false);
  const [showTemplatePicker, setShowTemplatePicker] = useState(false);

  const hasDocument = !!props.canvasContent;
  const hasActivity =
    props.agentResults.length > 0 ||
    props.thinkingSteps.length > 0 ||
    !!props.requirementAnalysis ||
    !!props.a2uiData ||
    store.workspaceConfirmations.length > 0 ||
    store.workspaceActions.length > 0 ||
    store.agentTasks.length > 0;

  const handleCreateDocument = useCallback(() => {
    store.setCanvasContent({
      type: 'document',
      title: '未命名文档',
      content: '',
      suggestions: [],
    });
    onTabChange('document');
  }, [store, onTabChange]);

  const handleSaveToList = useCallback(() => {
    if (!props.canvasContent) return;
    const id = `doc-${Date.now()}`;
    addDocumentToList({
      id,
      title: props.canvasContent.title || '未命名文档',
      type: props.canvasContent.type,
      preview: props.canvasContent.content.slice(0, 100),
      content: props.canvasContent.content,
    });
    props.onCanvasSaveAsDocument?.();
  }, [props.canvasContent, addDocumentToList, props.onCanvasSaveAsDocument]);

  const handleDocAction = useCallback((actionId: string) => {
    if (props.onDocumentAction) {
      props.onDocumentAction(actionId, { content: props.canvasContent?.content });
    } else if (actionId === 'optimize') {
      props.onCanvasAIOptimize();
    }
  }, [props]);

  const handleCloseDocument = useCallback(() => {
    if (props.canvasContent?.content) {
      const id = `doc-${Date.now()}`;
      addDocumentToList({
        id,
        title: props.canvasContent.title || '未命名文档',
        type: props.canvasContent.type,
        preview: props.canvasContent.content.slice(0, 100),
        content: props.canvasContent.content,
      });
    }
    store.setCanvasContent(null);
  }, [props.canvasContent, store, addDocumentToList]);

  const handleSwitchToDocument = useCallback(() => {
    if (hasDocument) {
      onTabChange('document');
    }
  }, [hasDocument, onTabChange]);

  const handleSelectTemplate = useCallback((template: { title: string; content: string; type: CanvasContent['type'] }) => {
    store.setCanvasContent({
      type: template.type,
      title: template.title,
      content: template.content,
      suggestions: [],
    });
    setShowTemplatePicker(false);
    onTabChange('document');
  }, [store, onTabChange]);

  const panelFallback = (
    <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
      正在加载...
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-muted/30">
      {/* 顶栏：Tab 切换 + 功能按钮 */}
      <div className="h-12 flex items-center px-3 bg-background border-b border-border flex-shrink-0">
        {/* 左侧：双模式 Tab */}
        <div className="flex items-center gap-0.5 bg-muted/60 rounded-lg p-0.5 flex-shrink-0">
          <button
            type="button"
            onClick={() => onTabChange('smart')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all',
              activeTab === 'smart'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <icons.Cpu className="w-3.5 h-3.5" />
            工作台
            {props.isProcessing && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => onTabChange('document')}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all',
              activeTab === 'document'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <icons.FileText className="w-3.5 h-3.5" />
            文档
            {hasDocument && activeTab !== 'document' && (
              <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            )}
          </button>
        </div>

        <div className="flex-1" />

        {/* 右侧：功能按钮 */}
        <div className="flex items-center gap-0.5 flex-shrink-0">
          {props.onNewConversation && (
            <button
              type="button"
              onClick={props.onNewConversation}
              className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
              title="新建对话"
            >
              <icons.Plus className="w-4 h-4" />
            </button>
          )}

          <button
            type="button"
            onClick={handleCreateDocument}
            className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/5 rounded-lg transition-colors"
            title="新建文档"
          >
            <icons.FilePlus className="w-4 h-4" />
          </button>

          {documentList.length > 0 && (
            <button
              type="button"
              onClick={() => setShowDocList(!showDocList)}
              className={cn(
                'relative p-1.5 rounded-lg transition-colors',
                showDocList ? 'text-primary bg-primary/5' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              )}
              title="文档列表"
            >
              <icons.FolderOpen className="w-4 h-4" />
              <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-primary text-white text-[8px] font-bold rounded-full flex items-center justify-center">
                {documentList.length}
              </span>
            </button>
          )}

          {isLive && (
            <div className="flex items-center gap-1.5 flex-shrink-0 px-1">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 dark:bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 dark:bg-emerald-400" />
              </span>
              <span className={`${heading.micro} font-bold text-emerald-600 uppercase tracking-wider`}>LIVE</span>
            </div>
          )}

        </div>
      </div>

      {/* 内容区 — 每个 Tab 独立渲染 */}
      <div className="flex-1 overflow-hidden relative">
        {/* 文档列表弹出面板 */}
        <AnimatePresence>
          {showDocList && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-0 left-0 right-0 z-30 bg-background border-b border-border shadow-lg max-h-[50%] overflow-y-auto"
            >
              <div className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-foreground">历史文档</span>
                  <button onClick={() => setShowDocList(false)} className="p-1 text-muted-foreground hover:text-foreground rounded">
                    <icons.X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="space-y-1">
                  {documentList.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => {
                        store.setCanvasContent({
                          type: doc.type,
                          title: doc.title,
                          content: doc.content || doc.preview || '',
                          suggestions: [],
                        });
                        onTabChange('document');
                        setShowDocList(false);
                      }}
                      className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-muted/50 cursor-pointer group transition-colors"
                    >
                      <div className="p-1.5 rounded bg-primary/5">
                        <icons.FileText className="w-3.5 h-3.5 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-foreground truncate">{doc.title}</p>
                        <p className="text-[10px] text-muted-foreground truncate">{doc.preview || '空文档'}</p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeDocumentFromList(doc.id);
                        }}
                        className="p-1 text-muted-foreground/50 hover:text-destructive rounded opacity-0 group-hover:opacity-100 transition-opacity"
                        title="删除"
                      >
                        <icons.Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== 工作台模式 ===== */}
        {activeTab === 'smart' && (
          <div className="h-full overflow-y-auto">
            <Suspense fallback={panelFallback}>
              <AgentWorkspace
                agentResults={props.agentResults}
                thinkingSteps={props.thinkingSteps}
                requirementAnalysis={props.requirementAnalysis}
                a2uiData={props.a2uiData}
                isProcessing={props.isProcessing}
                onWorkspaceConfirm={props.onWorkspaceConfirm}
                onWorkspaceAction={props.onWorkspaceAction}
                onSwitchToDocument={handleSwitchToDocument}
                hasDocument={hasDocument}
              />
            </Suspense>

            {/* 工作台空状态 — 系统内置功能入口 */}
            {!hasActivity && !props.isProcessing && !store.contractReviewVisible && (
              <div className="h-full flex flex-col px-4 py-5">
                {/* 顶部标题 */}
                <div className="flex items-center gap-2.5 mb-5 px-1">
                  <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shadow-sm">
                    <icons.Cpu className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">智能工作台</h3>
                    <p className="text-[11px] text-muted-foreground">选择功能开始，或对话触发自动展示</p>
                  </div>
                </div>

                {/* 功能卡片区 — 可交互的 A2UI 触发器 */}
                <div className="space-y-2.5 flex-1 overflow-y-auto">
                  {/* 快捷工具 */}
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-1">快捷工具</p>
                    <div className="grid grid-cols-3 gap-2">
                      {([
                        { icon: icons.Users, label: '找律师', actionId: 'ws-find-lawyer', color: 'text-blue-500 bg-blue-50 dark:bg-blue-950/30' },
                        { icon: icons.FileCheck, label: '合同审查', actionId: 'ws-contract-review', color: 'text-amber-500 bg-amber-50 dark:bg-amber-950/30' },
                        { icon: icons.Scale, label: '法规速查', actionId: 'ws-regulation', color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/30' },
                      ] as const).map((item) => {
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.actionId}
                            onClick={() => props.onWorkspaceAction?.(item.actionId)}
                            className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-background border border-border/50 hover:border-primary/30 hover:shadow-md transition-all active:scale-95"
                          >
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${item.color}`}>
                              <Icon className="w-4.5 h-4.5" />
                            </div>
                            <span className="text-[11px] font-medium text-foreground">{item.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* 智能服务 — 带描述的交互卡片 */}
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-1">智能服务</p>
                    <div className="space-y-2">
                      {([
                        {
                          icon: icons.Search,
                          label: '尽职调查',
                          desc: '输入企业名称，自动检索工商、诉讼、风险信息',
                          actionId: 'ws-due-diligence',
                          tag: 'AI 驱动',
                        },
                        {
                          icon: icons.ShieldCheck,
                          label: '合规检查',
                          desc: '选择行业和场景，生成合规检查清单与风险报告',
                          actionId: 'ws-compliance',
                          tag: '多 Agent',
                        },
                        {
                          icon: icons.PenTool,
                          label: '文书生成',
                          desc: '描述需求，AI 协作起草合同、函件、法律意见书',
                          actionId: 'ws-doc-generate',
                          tag: '协作式',
                        },
                      ] as const).map((item) => {
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.actionId}
                            onClick={() => props.onWorkspaceAction?.(item.actionId)}
                            className="flex items-start gap-3 p-3 rounded-xl bg-background border border-border/50 hover:border-primary/30 hover:shadow-md transition-all w-full text-left group active:scale-[0.98]"
                          >
                            <div className="w-9 h-9 rounded-lg bg-primary/5 group-hover:bg-primary/10 flex items-center justify-center flex-shrink-0 transition-colors">
                              <Icon className="w-4.5 h-4.5 text-primary/60 group-hover:text-primary transition-colors" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-semibold text-foreground">{item.label}</span>
                                <span className="px-1.5 py-0.5 text-[9px] font-medium text-primary bg-primary/5 rounded">{item.tag}</span>
                              </div>
                              <p className="text-[11px] text-muted-foreground leading-relaxed mt-0.5">{item.desc}</p>
                            </div>
                            <icons.ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 flex-shrink-0 mt-0.5 transition-colors" />
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* 沟通协作 */}
                  <div>
                    <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-1">沟通协作</p>
                    <div className="grid grid-cols-2 gap-2">
                      {([
                        { icon: icons.MessageSquare, label: '消息中心', desc: '通知与审批', actionId: 'ws-messages' },
                        { icon: icons.Mic, label: '语音对话', desc: 'AI 语音助手', actionId: 'ws-voice-chat' },
                      ] as const).map((item) => {
                        const Icon = item.icon;
                        return (
                          <button
                            key={item.actionId}
                            onClick={() => props.onWorkspaceAction?.(item.actionId)}
                            className="flex items-center gap-2.5 p-3 rounded-xl bg-background border border-border/50 hover:border-primary/30 hover:shadow-md transition-all group text-left active:scale-[0.98]"
                          >
                            <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center flex-shrink-0 group-hover:bg-primary/5 transition-colors">
                              <Icon className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-[11px] font-semibold text-foreground">{item.label}</p>
                              <p className="text-[10px] text-muted-foreground">{item.desc}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 底部能力标签 */}
                <div className="flex flex-wrap justify-center gap-1.5 mt-4 pt-3 border-t border-border/50">
                  {['需求分析', '多Agent协作', '进度追踪', 'A2UI动态卡片'].map((tag) => (
                    <span key={tag} className="px-2 py-0.5 bg-background text-[10px] text-muted-foreground border border-border rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ===== 文档模式 ===== */}
        {activeTab === 'document' && (
          <div className="h-full flex flex-col overflow-hidden">
            {hasDocument ? (
              <Suspense fallback={panelFallback}>
                <CanvasEditor
                  canvas={props.canvasContent!}
                  onContentChange={props.onCanvasContentChange}
                  onTitleChange={props.onCanvasTitleChange}
                  onModeChange={props.onCanvasModeChange}
                  onAIOptimize={props.onCanvasAIOptimize}
                  onSuggestionAction={props.onCanvasSuggestionAction}
                  onForwardToLawyer={props.onForwardToLawyer}
                  onInitiateSigning={props.onInitiateSigning}
                  onSaveAsDocument={props.onCanvasSaveAsDocument}
                  onDocumentAction={handleDocAction}
                  onSaveToList={handleSaveToList}
                  onCloseDocument={handleCloseDocument}
                  isSaved={props.canvasSaved}
                  isProcessing={props.isProcessing}
                  isOptimizing={props.isProcessing}
                />
              </Suspense>
            ) : (
              <div className="h-full flex flex-col items-center justify-center px-8 text-center">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-4 shadow-sm">
                  <icons.FileText className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-1.5">文档编辑</h3>
                <p className="text-xs text-muted-foreground mb-6 max-w-[260px] leading-relaxed">
                  AI 生成文书、合同时将自动在此打开，也可以直接新建或从模板库选取。
                </p>

                {/* 操作按钮 — 与工作台一致的网格风格 */}
                <div className="grid grid-cols-2 gap-2.5 w-full max-w-[320px] mb-6">
                  <button
                    onClick={handleCreateDocument}
                    className="flex items-center gap-2.5 p-3 rounded-xl bg-primary text-white hover:bg-primary/90 transition-all group text-left shadow-sm"
                  >
                    <div className="w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center flex-shrink-0">
                      <icons.Plus className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold truncate">新建文档</p>
                      <p className="text-[10px] text-white/70 truncate">空白文档</p>
                    </div>
                  </button>
                  <button
                    onClick={() => setShowTemplatePicker(true)}
                    className="flex items-center gap-2.5 p-3 rounded-xl bg-background border border-border/60 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all group text-left"
                  >
                    <div className="w-8 h-8 rounded-lg bg-primary/5 group-hover:bg-primary/10 flex items-center justify-center flex-shrink-0 transition-colors">
                      <icons.FileCheck className="w-4 h-4 text-primary/60 group-hover:text-primary transition-colors" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-foreground truncate">模板库</p>
                      <p className="text-[10px] text-muted-foreground truncate">快速选取</p>
                    </div>
                  </button>
                </div>

                <div className="flex flex-wrap justify-center gap-1.5">
                  {['富文本编辑', '实时协作', 'AI 润色', '风险检查', '导出下载'].map((tag) => (
                    <span key={tag} className="px-2.5 py-1 bg-background text-[10px] text-muted-foreground border border-border rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 律师协助浮层 */}
        <AnimatePresence>
          {documentOverlay === 'lawyer' && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="absolute inset-0 bg-background z-20 shadow-xl"
            >
              <Suspense fallback={panelFallback}>
                <LawyerAssistPanel />
              </Suspense>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 签约工作流浮层 */}
        <AnimatePresence>
          {documentOverlay === 'signing' && (
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="absolute inset-0 bg-background z-20 shadow-xl"
            >
              <Suspense fallback={panelFallback}>
                <SigningWorkflow />
              </Suspense>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 模板选择浮层 */}
        <AnimatePresence>
          {showTemplatePicker && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="absolute inset-0 bg-background z-20 flex flex-col"
            >
              <div className="h-12 flex items-center px-4 border-b border-border flex-shrink-0">
                <button
                  onClick={() => setShowTemplatePicker(false)}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors mr-2"
                >
                  <icons.ChevronLeft className="w-4 h-4" />
                </button>
                <h3 className="text-sm font-semibold text-foreground">选择模板</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-4">
                <div className="grid gap-2.5">
                  {DOCUMENT_TEMPLATES.map((tpl) => {
                    const Icon = icons[tpl.iconKey];
                    return (
                      <button
                        key={tpl.id}
                        onClick={() => handleSelectTemplate({ title: tpl.title, content: tpl.content, type: tpl.type })}
                        className="flex items-start gap-3 p-3.5 rounded-xl bg-background border border-border/60 hover:border-primary/40 hover:shadow-md hover:shadow-primary/5 transition-all group text-left w-full"
                      >
                        <div className="w-9 h-9 rounded-lg bg-primary/5 group-hover:bg-primary/10 flex items-center justify-center flex-shrink-0 transition-colors mt-0.5">
                          <Icon className="w-4.5 h-4.5 text-primary/60 group-hover:text-primary transition-colors" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-foreground mb-0.5">{tpl.title}</p>
                          <p className="text-[11px] text-muted-foreground leading-relaxed">{tpl.description}</p>
                          <div className="flex gap-1 mt-1.5">
                            {tpl.tags.map((tag) => (
                              <span key={tag} className="px-1.5 py-0.5 bg-muted text-[9px] text-muted-foreground rounded">
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                        <icons.ChevronRight className="w-4 h-4 text-muted-foreground/30 group-hover:text-primary/50 flex-shrink-0 mt-1 transition-colors" />
                      </button>
                    );
                  })}
                </div>
                <p className="text-center text-[10px] text-muted-foreground mt-4">
                  更多模板可在
                  <button onClick={() => navigate('/knowledge-base?type=template')} className="text-primary hover:underline mx-0.5">司法智库</button>
                  中浏览
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
});
