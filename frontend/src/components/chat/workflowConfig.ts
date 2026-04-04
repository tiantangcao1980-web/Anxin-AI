import { icons } from '@/lib/icons';

export type QuickActionMode = 'chat' | 'deep_analysis' | 'contract' | 'document' | 'research' | 'professional';

/**
 * 快捷操作的触发类型：
 * - 'fill'：填充输入框提示文本，用户补充后发送（对话型）
 * - 'panel'：在右侧智能工作台中打开对应面板（面板型）
 */
export type QuickActionType = 'fill' | 'panel';

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
  actionType: QuickActionType;
  command?: string;
  aliases?: string[];
  basePrompt: string;
  attachmentPrompt?: (attachmentName: string | null) => string;
  placeholder: string;
}

const WORKFLOW_ACTIONS: WorkflowActionDefinition[] = [
  // ===== 一级：4 个高频核心动作 =====
  {
    id: 'qa-consult',
    label: '快速咨询',
    description: '获取初步法律判断、关键依据和下一步建议',
    iconKey: 'Zap',
    mode: 'chat',
    category: 'core',
    quickGroup: 'primary',
    actionType: 'fill',
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
    description: '风险识别、条款解读、缺失项检查和修改建议',
    iconKey: 'FileCheck',
    mode: 'contract',
    category: 'core',
    quickGroup: 'primary',
    actionType: 'fill',
    command: '/contract',
    aliases: ['/合同审查', '/审合同', '/条款', '/条款解读'],
    basePrompt: '请帮我审查以下合同内容，逐条标出风险点、条款解读、缺失条款和修改建议：',
    attachmentPrompt: (attachmentName) =>
      `请对附件「${attachmentName || '当前合同'}」进行全面审查，包括风险条款标注、条款解读、缺失项检查和修改建议：`,
    placeholder: '粘贴合同条款或上传合同文件，我来做全面审查...',
  },
  {
    id: 'qa-draft',
    label: '文书起草',
    description: '起草函件、意见稿、说明和法律文书',
    iconKey: 'PenTool',
    mode: 'document',
    category: 'core',
    quickGroup: 'primary',
    actionType: 'fill',
    command: '/draft',
    aliases: ['/起草', '/协作起草', '/文书'],
    basePrompt: '请帮我起草一份适合法务协作与内部评审的文本：',
    attachmentPrompt: (attachmentName) =>
      `请基于附件「${attachmentName || '当前材料'}」帮我起草一版结构清晰、适合法务协作的文本：`,
    placeholder: '说明文书类型、对象和目标，我来协助起草...',
  },
  {
    id: 'qa-compliance',
    label: '合规风控',
    description: '合规检查、尽职调查和风险评估',
    iconKey: 'ShieldCheck',
    mode: 'research',
    category: 'core',
    quickGroup: 'primary',
    actionType: 'fill',
    command: '/compliance',
    aliases: ['/合规', '/合规检查', '/尽调', '/尽职调查', '/due-diligence'],
    basePrompt: '我想做一轮合规风控，请先根据下面的业务场景梳理主要合规风险、尽调重点和下一步建议：',
    attachmentPrompt: (attachmentName) =>
      `请围绕附件「${attachmentName || '当前材料'}」先做一轮合规风控分析，输出主要风险、尽调重点和整改建议：`,
    placeholder: '输入业务场景或企业背景，我来做合规检查和风险评估...',
  },
  // ===== 二级：扩展能力 =====
  {
    id: 'qa-search',
    label: '法律检索',
    description: '检索法规条文、裁判案例和知识库内容',
    iconKey: 'BookOpen',
    mode: 'research',
    category: 'knowledge',
    quickGroup: 'secondary',
    actionType: 'fill',
    command: '/search',
    aliases: ['/检索', '/知识检索', '/案例', '/案例检索', '/法规', '/法规查询', '/knowledge', '/case', '/regulation'],
    basePrompt: '请帮我检索与下面问题相关的法规条文、裁判案例和实务要点，并优先整理出关键结论：',
    attachmentPrompt: (attachmentName) =>
      `请结合附件「${attachmentName || '当前材料'}」检索相关法规、案例和知识库内容，并整理要点结论：`,
    placeholder: '输入您想检索的法律问题或关键词...',
  },
  {
    id: 'qa-evidence',
    label: '证据梳理',
    description: '整理证据链、缺口和补强建议',
    iconKey: 'FolderOpen',
    mode: 'document',
    category: 'knowledge',
    quickGroup: 'secondary',
    actionType: 'fill',
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
    description: '根据案件类型和阶段推荐合适的律师',
    iconKey: 'Users',
    mode: 'chat',
    category: 'core',
    quickGroup: 'secondary',
    actionType: 'fill',
    command: '/lawyer',
    aliases: ['/找律师'],
    basePrompt: '帮我找一位擅长',
    placeholder: '例如：劳动纠纷的律师，坐标深圳，目前在仲裁前沟通阶段...',
  },
  {
    id: 'qa-task',
    label: '任务拆解',
    description: '拆解执行步骤、优先级和协作分工',
    iconKey: 'Tasks',
    mode: 'chat',
    category: 'delivery',
    quickGroup: 'secondary',
    actionType: 'fill',
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
    return createAttachmentHint(fileName, 'qa-compliance');
  }

  return createAttachmentHint(fileName, 'qa-search');
}

// ===== 用户行为追踪与个性化排序 =====

const USAGE_STORAGE_KEY = 'anxin_quick_action_usage';

interface ActionUsageRecord {
  [actionId: string]: { count: number; lastUsed: number };
}

function getUsageRecords(): ActionUsageRecord {
  try {
    const raw = localStorage.getItem(USAGE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/** 记录一次快捷操作使用 */
export function trackActionUsage(actionId: string): void {
  const records = getUsageRecords();
  const prev = records[actionId] || { count: 0, lastUsed: 0 };
  records[actionId] = { count: prev.count + 1, lastUsed: Date.now() };
  try {
    localStorage.setItem(USAGE_STORAGE_KEY, JSON.stringify(records));
  } catch { /* quota exceeded — ignore */ }
}

/**
 * 获取按使用频率排序的快捷操作列表
 * 高频使用的操作排在前面（primary），低频排在后面（secondary）
 * 从未使用过的操作保持默认位置
 */
export function getPersonalizedActions(maxPrimary = 4): WorkflowActionDefinition[] {
  const records = getUsageRecords();
  const hasUsageData = Object.keys(records).length > 0;

  if (!hasUsageData) {
    return WORKFLOW_ACTIONS.filter((a) => Boolean(a.quickGroup));
  }

  const scored = WORKFLOW_ACTIONS.filter((a) => Boolean(a.quickGroup)).map((action) => {
    const usage = records[action.id];
    const recencyBonus = usage ? Math.max(0, 1 - (Date.now() - usage.lastUsed) / (7 * 24 * 60 * 60 * 1000)) : 0;
    const score = usage ? usage.count * 0.7 + recencyBonus * 0.3 : 0;
    return { action, score, hasUsage: !!usage };
  });

  const used = scored.filter((s) => s.hasUsage).sort((a, b) => b.score - a.score);
  const unused = scored.filter((s) => !s.hasUsage);

  const sorted = [...used, ...unused];

  return sorted.map((s, i) => ({
    ...s.action,
    quickGroup: i < maxPrimary ? 'primary' as const : 'secondary' as const,
  }));
}
