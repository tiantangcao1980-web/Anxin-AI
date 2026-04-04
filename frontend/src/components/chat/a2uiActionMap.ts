/**
 * A2UI 卡片操作 → 对话消息映射表
 *
 * 从 Chat.tsx 提取。千问购物模式的核心交互：
 * 用户点击卡片上的操作按钮后，自动生成可见的用户消息。
 */

export const A2UI_ACTION_TO_MESSAGE: Record<string, (payload: Record<string, any>) => string | null> = {
  // --- 律师相关 ---
  'contact_lawyer': (p) => `我想咨询${p.lawyerName || '这位'}律师`,
  'consult_lawyer': (p) => `请帮我联系${p.lawyerName || '这位'}律师进行咨询`,
  'view_lawyer_detail': (p) => `请详细介绍${p.lawyerName || '这位'}律师的擅长领域和成功案例`,
  'view_more_lawyers': () => '请推荐更多律师',
  'ai_match_lawyer': () => '请用 AI 帮我智能匹配最合适的律师',
  // --- 合同相关 ---
  'accept_changes': () => '我接受这些修改建议',
  'export_report': () => '请导出合同审查报告',
  'view_full_report': () => '请展示完整的合同审查报告',
  'ai_suggestions': () => '请给出 AI 修改建议',
  'start_review': () => '开始审查合同',
  // --- 费用/委托相关 ---
  'confirm_fee': () => '我确认这个费用方案',
  'confirm_engagement': () => '确认委托，请开始处理',
  // --- 风险/案件相关 ---
  'view_case_detail': (p) => `请展示案件${p.caseId ? ` ${p.caseId}` : ''}的详细信息`,
  'assess_contract_risk': () => '请评估合同风险',
  'assess_compliance': () => '请进行合规审查',
  'assess_litigation_risk': () => '请评估诉讼风险',
  'assess_ip_risk': () => '请评估知识产权风险',
  // --- 文书相关 ---
  'select_doc_type': (p) => `我需要起草${p.docType === 'contract' ? '合同/协议' : p.docType === 'lawyer_letter' ? '律师函' : p.docType === 'legal_opinion' ? '法律意见书' : '法律文书'}`,
  // --- 通用 ---
  'quick_intent': () => null,
  'go_back': () => null,
}

/**
 * 工作台动作 → 工作流 Action 映射
 */
export const WORKSPACE_TO_WORKFLOW_ACTION: Record<string, { workflowActionId: string; hint?: string }> = {
  'ws-contract-review': {
    workflowActionId: 'qa-contract',
    hint: '可先上传合同文件，或直接粘贴合同条款后发送',
  },
  'ws-regulation': {
    workflowActionId: 'qa-search',
  },
  'ws-due-diligence': {
    workflowActionId: 'qa-compliance',
  },
  'ws-compliance': {
    workflowActionId: 'qa-compliance',
  },
  'ws-find-lawyer': {
    workflowActionId: 'qa-lawyer',
  },
  'ws-doc-generate': {
    workflowActionId: 'qa-draft',
  },
}
