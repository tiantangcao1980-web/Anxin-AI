/**
 * Canvas 内容清理工具函数
 *
 * 从 Chat.tsx 提取的工具函数，用于清理 Agent 生成内容中的系统噪音。
 */

/**
 * 清理 Canvas 标题 — 去除过长的用户补充信息，提取核心文档名
 * 例如: "帮我起草一份贸易合同? 用户补充信息: 这份贸易合同是用于国内..." → "贸易合同"
 */
export function cleanCanvasTitle(rawTitle: string): string {
  let title = rawTitle;
  title = title.replace(/[?？]?\s*用户补充信息[:：].*$/s, '');
  title = title.replace(/^(请|帮我|帮忙)?(起草|撰写|写|生成|草拟)(一份|一个|一篇)?/u, '');
  title = title.replace(/^[\s?？、，,.:：]+|[\s?？、，,.:：]+$/g, '').trim();
  if (!title) {
    title = rawTitle.slice(0, 20).replace(/[?？].*$/, '').trim() || '文档';
  }
  if (title.length > 30) {
    title = title.slice(0, 30) + '…';
  }
  return title;
}

/**
 * 清理 Canvas 内容 — 去除 Agent 执行痕迹，只保留文书正文
 */
export function cleanCanvasContent(rawContent: string): string {
  let content = rawContent;
  let prev = '';
  while (prev !== content) {
    prev = content;
    content = content.replace(/^(智能体团队|Agent\s*团队|多Agent协作|AI\s*团队|协作完成)\s*\n*/u, '');
    content = content.replace(/^(任务(执行)?完成|处理完毕|已完成)[。.!]\s*/u, '');
    content = content.replace(/^#{1,4}\s*[\w\u4e00-\u9fff]+Agent[^\n]*\n*/u, '');
    content = content.replace(/^[\u4e00-\u9fff]+Agent\s*\n*/u, '');
    content = content.replace(/^\*{1,2}[\w\u4e00-\u9fff]+Agent[^*]*\*{1,2}\s*\n*/u, '');
    content = content.replace(/^-{3,}\s*\n*/u, '');
    content = content.replace(/^(以下是|根据您的|按照您的|应您要求|为您)(需求|要求|提供)?[，,]?(我)?(为您|已|特)?[^。\n]{0,50}[。.：:]\s*\n*/u, '');
    content = content.replace(/^\s*\n/, '');
  }
  return content.trim();
}

/**
 * 检测内容是否为法律文书/合同生成
 */
export function isDocumentGeneration(content: string): boolean {
  if (content.length < 300) return false;
  return /第[一二三四五六七八九十]+[条章节]|甲方[\s\S]{0,30}乙方|乙方[\s\S]{0,30}甲方|合同编号|签署日期|^#\s*.{2,}|鉴于.*双方|本合同自|违约责任|争议解决/m.test(content);
}

/**
 * 根据 AI 回复内容生成后续追问建议
 */
export function generateFollowUpSuggestions(aiContent: string, _userContent: string): string[] {
  const content = aiContent.toLowerCase();
  const suggestions: string[] = [];

  if (/合同|协议|条款|合约/.test(content)) {
    suggestions.push('这份合同有哪些主要风险点？');
    if (/风险|注意/.test(content)) {
      suggestions.push('请给出修改建议和替代条款');
    } else {
      suggestions.push('请逐条解读关键条款的法律含义');
    }
    suggestions.push('帮我生成一份修改版合同');
  } else if (/合规|法规|法律|条文|法条/.test(content)) {
    suggestions.push('有没有相关的司法解释或案例？');
    suggestions.push('这在不同地区的适用是否有差异？');
    suggestions.push('请帮我整理一份合规检查清单');
  } else if (/尽职调查|尽调|工商|股权/.test(content)) {
    suggestions.push('有哪些需要重点关注的风险事项？');
    suggestions.push('请帮我生成尽调报告模板');
    suggestions.push('类似项目的常见风险有哪些？');
  } else if (/证据|举证|证明/.test(content)) {
    suggestions.push('证据链是否完整？还需要补充什么？');
    suggestions.push('对方可能提出哪些抗辩？');
    suggestions.push('请帮我整理证据目录和说明');
  } else if (/起草|草拟|文书|函件/.test(content)) {
    suggestions.push('请帮我优化文书的措辞和格式');
    suggestions.push('有没有需要补充的法律条款引用？');
    suggestions.push('请生成配套的送达回执模板');
  } else if (/案例|判决|裁判|判例/.test(content)) {
    suggestions.push('有没有相反观点的判例？');
    suggestions.push('这个裁判思路在近年有变化吗？');
    suggestions.push('请帮我总结可援引的裁判要旨');
  } else {
    suggestions.push('请进一步展开分析');
    suggestions.push('有哪些实操层面的注意事项？');
    suggestions.push('请帮我整理一份行动清单');
  }

  return suggestions.slice(0, 3);
}
