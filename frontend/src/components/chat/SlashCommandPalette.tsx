/**
 * SlashCommandPalette — 项目业务斜杠命令面板
 *
 * 当用户在输入框中输入 '/' 时弹出命令面板：
 * - 列出当前项目已承接的业务能力
 * - 支持模糊搜索
 * - 支持键盘导航（上/下/Enter/Esc）
 * - 选中后填充输入框，由用户继续补充再发送
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { icons } from '@/lib/icons';
import { heading, shadow, radius, iconSize } from '@/lib/design-tokens';
import {
  SLASH_COMMANDS,
  type SlashCommandDefinition,
} from '@/components/chat/workflowConfig';

export interface SlashCommand extends SlashCommandDefinition {
  icon: React.ElementType;
}

const CATEGORY_LABELS: Record<string, string> = {
  core: '核心法务',
  knowledge: '知识与检索',
  delivery: '交付与协作',
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
    const commands: SlashCommand[] = SLASH_COMMANDS.map((command) => ({
      ...command,
      icon: icons[command.iconKey],
    }));
    if (!searchTerm) return commands;
    const term = searchTerm.toLowerCase();
    return commands.filter(cmd => {
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
                return (
                  <button
                    key={cmd.id}
                    data-index={currentIdx}
                    onClick={() => onSelect(cmd)}
                    onMouseEnter={() => setSelectedIndex(currentIdx)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-left transition-colors ${
                      isSelected
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
