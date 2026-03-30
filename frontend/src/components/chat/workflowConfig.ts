import { icons } from '@/lib/icons';

export type QuickActionMode = 'chat' | 'deep_analysis' | 'contract' | 'document' | 'research';

export interface QuickActionContext {
  hasAttachment: boolean;
  attachmentName: string | null;
}

export interface WorkflowActionDefinition {
  id: string;
  label: string;
  description: string;
  iconKey: keyof typeof icons;
  mode: QuickActionMode;
  category: 'core' | 'knowledge' | 'delivery';
  quickGroup?: 'primary' | 'secondary';
  command?: string;
  aliases?: string[];
  basePrompt: string;
  attachmentPrompt?: (attachmentName: string | null) => string;
  placeholder: string;
}

const WORKFLOW_ACTIONS: WorkflowActionDefinition[] = [
  {
    id: 'qa-consult',
    label: '快速咨询',
    description: '适合先拿到初步法律判断和下一步建议',
    iconKey: 'Zap',
    mode: 'chat',
    category: 'core',
    quickGroup: 'primary',
    command: '/consult',
    aliases: ['/咨询', '/法律咨询'],
    basePrompt: '请先直接给我一个简明法律结论，再补充关键依据和下一步建议：',
    attachmentPrompt: (attachmentName) =>
      `请结合附件「${attachmentName || '当前文件'}」先给我一个简明法律结论，再补充关键依据：`,
    placeholder: '输入案件背景、问题和目标，我来给出初步法律建议...',
  },
  {
    id: 'qa-contract',
    label: '合同审查',
    description: '对合同条款做风险识别、缺失项检查和修改建议',
    iconKey: 'FileCheck',
    mode: 'contract',
    category: 'core',
    quickGroup: 'primary',
    command: '/contract',
    aliases: ['/合同审查', '/审合同'],
    basePrompt: '请帮我审查以下合同内容，标出风险点、缺失条款和修改建议：',
    attachmentPrompt: (attachmentName) =>
      `请对附件「${attachmentName || '当前合同'}」进行合同审查，标出风险条款、缺失条款和修改建议：`,
    placeholder: '粘贴合同条款，或上传合同后点击发送...',
  },
  {
    id: 'qa-draft',
    label: '协作起草',
    description: '用于起草函件、说明、意见稿和内部流转文本',
    iconKey: 'PenTool',
    mode: 'document',
    category: 'core',
    quickGroup: 'primary',
    command: '/draft',
    aliases: ['/起草', '/协作起草'],
    basePrompt: '请帮我起草一份适合法务协作与内部评审的文本：',
    attachmentPrompt: (attachmentName) =>
      `请基于附件「${attachmentName || '当前材料'}」帮我起草一版结构清晰、适合法务协作的文本：`,
    placeholder: '说明文书类型、对象和目标，我来协助起草...',
  },
  {
    id: 'qa-compliance',
    label: '合规检查',
    description: '输出主要合规风险、法规依据和整改建议',
    iconKey: 'ShieldCheck',
    mode: 'research',
    category: 'core',
    quickGroup: 'primary',
    command: '/compliance',
    aliases: ['/合规', '/合规检查'],
    basePrompt: '请帮我进行合规检查，输出主要风险、法规依据和整改建议：',
    attachmentPrompt: (attachmentName) =>
      `请围绕附件「${attachmentName || '当前材料'}」进行合规检查，输出主要风险、依据和整改建议：`,
    placeholder: '输入业务场景、地区和关注点，我来做合规检查...',
  },
  {
    id: 'qa-dd',
    label: '尽职调查',
    description: '梳理调查清单、核验重点和风险事项',
    iconKey: 'Search',
    mode: 'research',
    category: 'core',
    quickGroup: 'primary',
    command: '/due-diligence',
    aliases: ['/尽调', '/尽职调查'],
    basePrompt: '请帮我制定一份尽职调查清单，并标出需要重点核验的风险事项：',
    attachmentPrompt: (attachmentName) =>
      `请基于附件「${attachmentName || '当前材料'}」梳理尽职调查重点，列出待核验事项与风险提示：`,
    placeholder: '输入企业/项目背景，我来整理尽调重点和核验清单...',
  },
  {
    id: 'qa-knowledge',
    label: '知识检索',
    description: '联动法规、案例和知识库内容做结论整理',
    iconKey: 'BookOpen',
    mode: 'research',
    category: 'knowledge',
    quickGroup: 'primary',
    command: '/knowledge',
    aliases: ['/知识检索', '/知识库'],
    basePrompt: '请帮我检索相关法规、案例和知识库内容，并整理结论：',
    attachmentPrompt: (attachmentName) =>
      `请结合附件「${attachmentName || '当前材料'}」检索相关法规、案例和知识库内容，并整理结论：`,
    placeholder: '输入关键词、争议点或法条主题，我来做知识检索...',
  },
  {
    id: 'qa-case',
    label: '案例检索',
    description: '围绕争议点梳理相关案例和裁判思路',
    iconKey: 'Briefcase',
    mode: 'research',
    category: 'knowledge',
    quickGroup: 'secondary',
    command: '/case',
    aliases: ['/案例', '/案例检索'],
    basePrompt: '请帮我检索与以下争议相关的案例，并总结裁判要点：',
    placeholder: '输入争议焦点、案由或关键词，我来检索相关案例...',
  },
  {
    id: 'qa-regulation',
    label: '法规查询',
    description: '定位关键法条并提炼适用要点',
    iconKey: 'Scale',
    mode: 'research',
    category: 'knowledge',
    quickGroup: 'secondary',
    command: '/regulation',
    aliases: ['/法规', '/法规查询'],
    basePrompt: '请帮我查询与以下问题相关的法律法规，并标出关键条文：',
    placeholder: '输入问题场景或法条主题，我来定位相关法规...',
  },
  {
    id: 'qa-clause',
    label: '条款解读',
    description: '逐条解释条款含义、风险和谈判点',
    iconKey: 'FileText',
    mode: 'document',
    category: 'delivery',
    quickGroup: 'secondary',
    command: '/clause',
    aliases: ['/条款', '/条款解读'],
    basePrompt: '请帮我逐条解读以下条款，说明法律含义、风险和谈判建议：',
    placeholder: '粘贴需要解读的条款，我来说明含义、风险和谈判点...',
  },
  {
    id: 'qa-evidence',
    label: '证据梳理',
    description: '整理证据链、缺口和补强建议',
    iconKey: 'FolderOpen',
    mode: 'document',
    category: 'knowledge',
    quickGroup: 'secondary',
    command: '/evidence',
    aliases: ['/证据', '/证据梳理'],
    basePrompt: '请帮我梳理当前案件材料中的证据链、缺口和补强建议：',
    attachmentPrompt: (attachmentName) =>
      `请帮我梳理附件「${attachmentName || '当前材料'}」中的证据链、缺口和补强建议：`,
    placeholder: '输入案件背景或证明目标，我来梳理证据链和缺口...',
  },
  {
    id: 'qa-lawyer',
    label: '找律师',
    description: '围绕案件阶段和专业方向推荐律师画像',
    iconKey: 'Users',
    mode: 'chat',
    category: 'core',
    quickGroup: 'secondary',
    command: '/lawyer',
    aliases: ['/找律师'],
    basePrompt: '我想找一位擅长以下领域并适合当前案件阶段的律师：',
    placeholder: '说明案件类型、地区和阶段，我来帮您筛选律师方向...',
  },
  {
    id: 'qa-task',
    label: '任务拆解',
    description: '把事项整理为执行步骤、优先级和协作分工',
    iconKey: 'Tasks',
    mode: 'chat',
    category: 'delivery',
    quickGroup: 'secondary',
    command: '/task',
    aliases: ['/任务', '/任务拆解'],
    basePrompt: '请根据以下事项帮我拆解任务、优先级和协作分工建议：',
    placeholder: '输入事项目标和截止时间，我来拆解执行步骤与分工...',
  },
];

const WORKFLOW_ACTION_MAP = new Map(
  WORKFLOW_ACTIONS.map((action) => [action.id, action]),
);

export function getWorkflowAction(actionId: string | null | undefined) {
  if (!actionId) return null;
  return WORKFLOW_ACTION_MAP.get(actionId) ?? null;
}

export function getWorkflowPrompt(
  actionId: string,
  context: QuickActionContext,
) {
  const action = getWorkflowAction(actionId);
  if (!action) return '';
  if (context.hasAttachment && action.attachmentPrompt) {
    return action.attachmentPrompt(context.attachmentName);
  }
  return action.basePrompt;
}

export function getWorkflowPlaceholder(actionId: string | null | undefined) {
  return getWorkflowAction(actionId)?.placeholder ?? null;
}

export const QUICK_WORKFLOW_ACTIONS = WORKFLOW_ACTIONS.filter(
  (action) => Boolean(action.quickGroup),
);

export interface SlashCommandDefinition {
  id: string;
  command: string;
  aliases?: string[];
  label: string;
  description: string;
  iconKey: keyof typeof icons;
  query: string;
  actionId?: string;
  mode?: QuickActionMode;
  category: 'core' | 'knowledge' | 'delivery';
}

export const SLASH_COMMANDS: SlashCommandDefinition[] = [
  ...WORKFLOW_ACTIONS.filter((action) => Boolean(action.command)).map((action) => ({
    id: `cmd-${action.id.replace(/^qa-/, '')}`,
    command: action.command as string,
    aliases: action.aliases,
    label: action.label,
    description: action.description,
    iconKey: action.iconKey,
    query: action.basePrompt,
    actionId: action.id,
    mode: action.mode,
    category: action.category,
  })),
  {
    id: 'cmd-summarize',
    command: '/summarize',
    aliases: ['/总结', '/摘要'],
    label: '总结归纳',
    description: '对当前问题、材料或上下文做结构化总结',
    iconKey: 'Wand2',
    query: '请总结以上内容，并给出重点结论、风险和建议动作：',
    mode: 'chat',
    category: 'delivery',
  },
];

export interface AttachmentWorkflowHint {
  actionId: string;
  mode: QuickActionMode;
  label: string;
  prompt: string;
  openSmartPanel?: boolean;
  triggerContractReview?: boolean;
}

function createAttachmentHint(
  fileName: string,
  actionId: string,
  extra?: Pick<AttachmentWorkflowHint, 'openSmartPanel' | 'triggerContractReview'>,
): AttachmentWorkflowHint {
  const action = getWorkflowAction(actionId);
  if (!action) {
    throw new Error(`Unknown workflow action: ${actionId}`);
  }

  return {
    actionId,
    mode: action.mode,
    label: action.label,
    prompt: getWorkflowPrompt(actionId, {
      hasAttachment: true,
      attachmentName: fileName,
    }),
    openSmartPanel: extra?.openSmartPanel,
    triggerContractReview: extra?.triggerContractReview,
  };
}

export function inferAttachmentWorkflow(file: File): AttachmentWorkflowHint {
  const fileName = file.name;
  const lowerName = fileName.toLowerCase();
  const isImage =
    file.type.startsWith('image/') ||
    /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(fileName);

  const isContractLike =
    /(合同|协议|补充协议|条款|contract|agreement|nda|msa|sow)/i.test(fileName);
  const isEvidenceLike =
    isImage ||
    /(证据|举证|聊天记录|微信|邮件|录音|流水|发票|回单|收据|截图|照片|笔录)/i.test(fileName);
  const isDueDiligenceLike =
    /(尽调|due.?diligence|工商|股权|章程|审计|财报|年报|企业|公司资料)/i.test(fileName);

  if (isContractLike) {
    return createAttachmentHint(fileName, 'qa-contract', {
      openSmartPanel: true,
      triggerContractReview: true,
    });
  }

  if (isEvidenceLike) {
    return createAttachmentHint(fileName, 'qa-evidence');
  }

  if (isDueDiligenceLike || /\.(xls|xlsx|csv)$/i.test(lowerName)) {
    return createAttachmentHint(fileName, 'qa-dd');
  }

  return createAttachmentHint(fileName, 'qa-knowledge');
}
