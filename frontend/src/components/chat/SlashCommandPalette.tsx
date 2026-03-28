/**
 * SlashCommandPalette — '/' 斜杠命令系统
 * 
 * 当用户在输入框中输入 '/' 时弹出命令面板：
 * - 列出可用的快捷命令
 * - 支持模糊搜索
 * - 键盘导航（上/下/Enter/Esc）
 * - 选中后替换输入框内容为预设查询
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { cardStyle, heading, shadow, radius, iconSize } from '@/lib/design-tokens';

export interface SlashCommand {
  id: string;
  /** 英文命令 */
  command: string;
  /** 中文命令别名 — 支持用中文触发 */
  aliases?: string[];
  label: string;
  description: string;
  icon: React.ElementType;
  /** 执行命令时发送的消息 */
  query: string;
  /** 分类 */
  category: 'legal' | 'tool' | 'system';
}

const SLASH_COMMANDS: SlashCommand[] = [
  // 法务类 — 支持中英文双触发
  { id: 'cmd-lawyer', command: '/lawyer', aliases: ['/找律师'], label: '找律师', description: '搜索并推荐合适的律师', icon: icons.Users, query: '帮我找律师', category: 'legal' },
  { id: 'cmd-contract', command: '/contract', aliases: ['/合同审查', '/审合同'], label: '合同审查', description: '智能分析合同条款与风险', icon: icons.FileText, query: '帮我审查合同', category: 'legal' },
  { id: 'cmd-draft', command: '/draft', aliases: ['/起草', '/文书起草'], label: '文书起草', description: '起草法律文书、合同等', icon: icons.PenTool, query: '帮我起草文书', category: 'legal' },
  { id: 'cmd-risk', command: '/risk', aliases: ['/风险评估', '/风险'], label: '风险评估', description: '评估法律风险与合规情况', icon: icons.Shield, query: '帮我做风险评估', category: 'legal' },
  { id: 'cmd-consult', command: '/consult', aliases: ['/咨询', '/法律咨询'], label: '法律咨询', description: '获取专业法律咨询建议', icon: icons.MessageCircle, query: '我有法律问题想咨询', category: 'legal' },
  { id: 'cmd-dd', command: '/due-diligence', aliases: ['/尽调', '/尽职调查'], label: '尽职调查', description: '企业/项目尽职调查', icon: icons.Search, query: '我需要做尽职调查', category: 'legal' },
  { id: 'cmd-compliance', command: '/compliance', aliases: ['/合规', '/合规检查'], label: '合规检查', description: '检查业务合规性', icon: icons.Scale, query: '帮我做合规审查', category: 'legal' },
  { id: 'cmd-case', command: '/case', aliases: ['/案例', '/案例检索'], label: '案例检索', description: '检索相关法律案例', icon: icons.Briefcase, query: '帮我检索相关案例', category: 'legal' },
  { id: 'cmd-regulation', command: '/regulation', aliases: ['/法规', '/法规查询'], label: '法规查询', description: '查询法律法规条文', icon: icons.BookOpen, query: '帮我查询相关法规', category: 'legal' },
  { id: 'cmd-compare', command: '/compare', aliases: ['/对比', '/条款对比'], label: '条款对比', description: '对比不同合同版本的差异', icon: icons.FileCheck, query: '帮我对比合同条款', category: 'legal' },
  { id: 'cmd-litigation', command: '/litigation', aliases: ['/诉讼', '/诉讼分析'], label: '诉讼分析', description: '分析诉讼可行性与风险', icon: icons.Gavel, query: '帮我分析诉讼风险', category: 'legal' },
  { id: 'cmd-entity', command: '/entity', aliases: ['/企业调查', '/查企业'], label: '企业调查', description: '调查企业工商信息和背景', icon: icons.Building2, query: '帮我调查企业背景', category: 'legal' },
  // 工具类
  { id: 'cmd-summarize', command: '/summarize', aliases: ['/总结', '/摘要'], label: '总结', description: '总结上下文或文档内容', icon: icons.Wand2, query: '请总结以上内容', category: 'tool' },
  // 系统类（预留）
  { id: 'cmd-settings', command: '/settings', aliases: ['/设置'], label: '设置', description: '调整助手偏好设置（开发中）', icon: icons.Settings, query: '', category: 'system' },
  { id: 'cmd-skills', command: '/skills', aliases: ['/技能'], label: '技能管理', description: '查看和管理扩展技能（开发中）', icon: icons.Zap, query: '', category: 'system' },
];

const CATEGORY_LABELS: Record<string, string> = {
  legal: '法务服务',
  tool: '工具',
  system: '系统',
};

interface SlashCommandPaletteProps {
  /** 当前输入内容 */
  inputValue: string;
  /** 命令被选中时的回调 */
  onSelect: (command: SlashCommand) => void;
  /** 关闭面板 */
  onClose: () => void;
  /** 是否可见 */
  visible: boolean;
}

export function SlashCommandPalette({
  inputValue,
  onSelect,
  onClose,
  visible,
}: SlashCommandPaletteProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // 从输入中提取搜索关键词（去掉 '/'）
  const searchTerm = useMemo(() => {
    const slashIdx = inputValue.lastIndexOf('/');
    if (slashIdx === -1) return '';
    return inputValue.slice(slashIdx + 1).toLowerCase();
  }, [inputValue]);

  // 过滤匹配的命令 — 支持英文命令、中文别名、标签、描述模糊搜索
  const filteredCommands = useMemo(() => {
    if (!searchTerm) return SLASH_COMMANDS.filter(c => c.category !== 'system');
    const term = searchTerm.toLowerCase();
    return SLASH_COMMANDS.filter(cmd => {
      // 匹配英文命令（去掉前缀 /）
      if (cmd.command.toLowerCase().includes(term)) return true;
      // 匹配中文别名（去掉前缀 /）
      if (cmd.aliases?.some(a => a.replace('/', '').includes(term))) return true;
      // 匹配标签和描述
      if (cmd.label.includes(term) || cmd.description.includes(term)) return true;
      return false;
    });
  }, [searchTerm]);

  // 按分类分组
  const groupedCommands = useMemo(() => {
    const groups: Record<string, SlashCommand[]> = {};
    for (const cmd of filteredCommands) {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    }
    return groups;
  }, [filteredCommands]);

  // 扁平化列表（用于键盘导航）
  const flatList = useMemo(() => {
    return Object.values(groupedCommands).flat();
  }, [groupedCommands]);

  // 重置选中索引
  useEffect(() => {
    setSelectedIndex(0);
  }, [searchTerm]);

  // 键盘事件处理
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!visible) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % flatList.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + flatList.length) % flatList.length);
        break;
      case 'Enter':
        e.preventDefault();
        if (flatList[selectedIndex]) {
          onSelect(flatList[selectedIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
      case 'Tab':
        e.preventDefault();
        if (flatList[selectedIndex]) {
          onSelect(flatList[selectedIndex]);
        }
        break;
    }
  }, [visible, flatList, selectedIndex, onSelect, onClose]);

  useEffect(() => {
    if (visible) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [visible, handleKeyDown]);

  // 滚动到选中项
  useEffect(() => {
    if (listRef.current) {
      const selectedEl = listRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedEl?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!visible || flatList.length === 0) return null;

  let flatIdx = 0;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 8, scale: 0.98 }}
        transition={{ duration: 0.15 }}
        className="absolute bottom-full left-0 right-0 mb-1 z-50"
      >
        <div
          ref={listRef}
          className={`bg-background border border-border ${radius.card} ${shadow.dialog} max-h-64 overflow-y-auto`}
        >
          {/* 标题 */}
          <div className="px-3 py-2 border-b border-border flex items-center gap-2">
            <span className={`${heading.micro} font-semibold uppercase tracking-wider`}>快捷命令</span>
            {searchTerm && (
              <span className="text-[10px] text-primary">搜索: {searchTerm}</span>
            )}
          </div>

          {/* 命令列表 */}
          {Object.entries(groupedCommands).map(([category, commands]) => (
            <div key={category}>
              <div className={`px-3 py-1.5 ${heading.micro} font-semibold uppercase tracking-wider bg-muted/50`}>
                {CATEGORY_LABELS[category] || category}
              </div>
              {commands.map((cmd) => {
                const currentIdx = flatIdx++;
                const Icon = cmd.icon;
                const isSelected = currentIdx === selectedIndex;
                const isDisabled = cmd.category === 'system';
                return (
                  <button
                    key={cmd.id}
                    data-index={currentIdx}
                    onClick={() => !isDisabled && onSelect(cmd)}
                    onMouseEnter={() => setSelectedIndex(currentIdx)}
                    disabled={isDisabled}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                      isDisabled
                        ? 'opacity-40 cursor-not-allowed'
                        : isSelected
                        ? 'bg-primary/5'
                        : 'hover:bg-muted'
                    }`}
                  >
                    <div className={`p-1.5 ${radius.button} ${
                      isSelected ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                    }`}>
                      <Icon className={iconSize.sm} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={heading.card}>{cmd.label}</span>
                        <code className="text-[10px] text-muted-foreground font-mono">{cmd.command}</code>
                        {cmd.aliases?.[0] && (
                          <code className="text-[10px] text-primary font-mono">{cmd.aliases[0]}</code>
                        )}
                      </div>
                      <p className={`${heading.micro} truncate`}>{cmd.description}</p>
                    </div>
                    {isDisabled && (
                      <span className={`text-[9px] text-muted-foreground bg-muted px-1.5 py-0.5 ${radius.badge}`}>开发中</span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

/**
 * Hook：检测输入框是否处于斜杠命令模式
 */
export function useSlashCommand(inputValue: string) {
  const isSlashMode = useMemo(() => {
    // 输入以 '/' 开头，或者光标前最近一个字符是 '/'（简化实现）
    return inputValue.startsWith('/');
  }, [inputValue]);

  return { isSlashMode };
}
