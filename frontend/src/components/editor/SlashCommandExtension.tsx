/**
 * Slash Command Menu for TipTap Editor
 *
 * Lightweight implementation without tippy.js dependency.
 * Type "/" on a new line to open the command palette.
 * Provides legal-document-specific insert commands.
 */

import { useState, useEffect, useCallback, useRef, useLayoutEffect } from 'react';
import { cn } from '@/lib/utils';

// ==================== Command Definitions ====================

export interface SlashCommandItem {
  title: string;
  description: string;
  icon: string;
  category: string;
  action: (editor: any) => void;
}

export const SLASH_COMMANDS: SlashCommandItem[] = [
  // === Basic format ===
  {
    title: '标题 1',
    description: '大标题，用于合同名称',
    icon: 'H1',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
  },
  {
    title: '标题 2',
    description: '章节标题，用于条款标题',
    icon: 'H2',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    title: '标题 3',
    description: '子标题',
    icon: 'H3',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  {
    title: '无序列表',
    description: '无编号列表',
    icon: '•',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleBulletList().run(),
  },
  {
    title: '有序列表',
    description: '带编号列表',
    icon: '1.',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleOrderedList().run(),
  },
  {
    title: '引用块',
    description: '插入引用段落',
    icon: '"',
    category: '基本格式',
    action: (editor) => editor.chain().focus().toggleBlockquote().run(),
  },
  {
    title: '分隔线',
    description: '插入水平分割线',
    icon: '—',
    category: '基本格式',
    action: (editor) => editor.chain().focus().setHorizontalRule().run(),
  },
  {
    title: '表格',
    description: '插入3行3列表格',
    icon: '田',
    category: '基本格式',
    action: (editor) => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  },

  // === Legal document blocks ===
  {
    title: '合同标题区',
    description: '插入合同标题和编号',
    icon: '契',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h1>【合同名称】</h1><p>合同编号：【    】</p><p></p>`
      ).run();
    },
  },
  {
    title: '甲乙方信息',
    description: '插入甲方乙方基本信息区',
    icon: '方',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<p><strong>甲方（全称）：</strong>【    】</p>` +
        `<p>统一社会信用代码/身份证号：【    】</p>` +
        `<p>法定代表人：【    】</p>` +
        `<p>住所/地址：【    】</p>` +
        `<p>联系方式：【    】</p>` +
        `<p></p>` +
        `<p><strong>乙方（全称）：</strong>【    】</p>` +
        `<p>统一社会信用代码/身份证号：【    】</p>` +
        `<p>法定代表人：【    】</p>` +
        `<p>住所/地址：【    】</p>` +
        `<p>联系方式：【    】</p><p></p>`
      ).run();
    },
  },
  {
    title: '鉴于条款',
    description: '插入鉴于（Whereas）条款',
    icon: '鉴',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<p><strong>鉴于：</strong></p>` +
        `<p>1. 甲方【背景说明】；</p>` +
        `<p>2. 乙方【背景说明】；</p>` +
        `<p>3. 双方经友好协商，就【合同目的】事宜达成如下协议：</p><p></p>`
      ).run();
    },
  },
  {
    title: '标准条款',
    description: '插入带编号的合同条款',
    icon: '条',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h2>第【  】条 【条款名称】</h2>` +
        `<p>【条款内容】</p><p></p>`
      ).run();
    },
  },
  {
    title: '违约责任',
    description: '插入标准违约责任条款',
    icon: '责',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h2>违约责任</h2>` +
        `<p>1. 甲方违约责任：甲方逾期支付款项的，应按逾期金额每日【  ‰】的标准向乙方支付违约金。</p>` +
        `<p>2. 乙方违约责任：【具体违约情形及责任】</p>` +
        `<p>3. 损害赔偿：违约方应赔偿守约方因此遭受的直接经济损失，但赔偿总额不超过本合同总价款的【  】%。</p><p></p>`
      ).run();
    },
  },
  {
    title: '争议解决',
    description: '插入争议解决条款',
    icon: '诉',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h2>争议解决</h2>` +
        `<p>1. 本合同的签订、履行、变更、解除和终止等有关的争议，双方应首先通过友好协商解决。</p>` +
        `<p>2. 协商不成的，任何一方均有权向【    】人民法院提起诉讼 / 提交【    】仲裁委员会按其仲裁规则进行仲裁。</p><p></p>`
      ).run();
    },
  },
  {
    title: '不可抗力',
    description: '插入不可抗力条款',
    icon: '力',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h2>不可抗力</h2>` +
        `<p>1. 不可抗力是指不能预见、不能避免且不能克服的客观情况，包括但不限于自然灾害、战争、政府行为、法律法规变更等。</p>` +
        `<p>2. 因不可抗力不能履行合同的，根据不可抗力的影响，部分或全部免除责任。</p>` +
        `<p>3. 遭受不可抗力的一方应在不可抗力事件发生后【  】日内书面通知对方，并在【  】日内提供相关证明文件。</p><p></p>`
      ).run();
    },
  },
  {
    title: '保密条款',
    description: '插入保密义务条款',
    icon: '密',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<h2>保密条款</h2>` +
        `<p>1. 保密信息范围：双方在合同履行过程中知悉的对方商业秘密、技术秘密及其他保密信息。</p>` +
        `<p>2. 保密期限：本条保密义务自本合同签订之日起至合同终止后【  】年止。</p>` +
        `<p>3. 例外情形：（1）公开渠道可获得的信息；（2）已为接收方合法拥有的信息；（3）经披露方书面同意披露的信息；（4）法律法规要求披露的信息。</p><p></p>`
      ).run();
    },
  },
  {
    title: '签署区',
    description: '插入合同签署盖章区域',
    icon: '署',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<p>（以下无正文）</p><p></p>` +
        `<p><strong>甲方（盖章）：</strong>                    <strong>乙方（盖章）：</strong></p>` +
        `<p>法定代表人/授权代表：              法定代表人/授权代表：</p>` +
        `<p>签字：                            签字：</p>` +
        `<p>日期：    年    月    日           日期：    年    月    日</p><p></p>`
      ).run();
    },
  },
  {
    title: '附件列表',
    description: '插入附件清单',
    icon: '附',
    category: '法律文书',
    action: (editor) => {
      editor.chain().focus().insertContent(
        `<p><strong>附件：</strong></p>` +
        `<p>附件一：【    】</p>` +
        `<p>附件二：【    】</p>` +
        `<p>附件三：【    】</p><p></p>`
      ).run();
    },
  },
];

// ==================== Slash Command Menu Component ====================

interface SlashCommandMenuProps {
  editor: any;
  isOpen: boolean;
  onClose: () => void;
  position: { top: number; left: number };
  query: string;
}

export function SlashCommandMenu({ editor, isOpen, onClose, position, query }: SlashCommandMenuProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter commands based on query
  const filteredItems = SLASH_COMMANDS.filter(
    (item) =>
      item.title.toLowerCase().includes(query.toLowerCase()) ||
      item.description.toLowerCase().includes(query.toLowerCase()) ||
      item.category.toLowerCase().includes(query.toLowerCase())
  );

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Scroll into view
  useLayoutEffect(() => {
    const el = containerRef.current?.querySelector(`[data-index="${selectedIndex}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
        setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
      } else if (e.key === 'Enter' && filteredItems[selectedIndex]) {
        e.preventDefault();
        e.stopPropagation();
        executeCommand(filteredItems[selectedIndex]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => document.removeEventListener('keydown', handleKeyDown, true);
  }, [isOpen, filteredItems, selectedIndex, onClose]);

  const executeCommand = useCallback(
    (item: SlashCommandItem) => {
      // Delete the "/" and query text before inserting
      if (editor) {
        const { from } = editor.state.selection;
        const slashPos = from - query.length - 1; // -1 for the "/"
        if (slashPos >= 0) {
          editor.chain().focus().deleteRange({ from: slashPos, to: from }).run();
        }
        item.action(editor);
      }
      onClose();
    },
    [editor, query, onClose]
  );

  if (!isOpen || filteredItems.length === 0) return null;

  // Group by category
  const grouped: Record<string, SlashCommandItem[]> = {};
  filteredItems.forEach((item) => {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  });

  let globalIndex = 0;

  return (
    <div
      ref={containerRef}
      className="fixed z-[100] bg-popover border border-border rounded-lg shadow-xl overflow-hidden max-h-[320px] overflow-y-auto min-w-[280px] animate-in fade-in slide-in-from-top-1 duration-150"
      style={{ top: position.top, left: position.left }}
    >
      <div className="px-3 py-1.5 border-b border-border bg-muted/50">
        <span className="text-[10px] text-muted-foreground">
          输入关键词筛选 · 方向键选择 · Enter 确认 · Esc 取消
        </span>
      </div>
      {Object.entries(grouped).map(([category, catItems]) => (
        <div key={category}>
          <div className="px-3 py-1 text-[10px] font-medium text-muted-foreground uppercase tracking-caption bg-muted/20 border-b border-border/30">
            {category}
          </div>
          {catItems.map((item) => {
            const idx = globalIndex++;
            return (
              <button
                key={item.title}
                data-index={idx}
                onClick={() => executeCommand(item)}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2 text-left transition-colors',
                  idx === selectedIndex
                    ? 'bg-primary/10 text-primary'
                    : 'hover:bg-accent text-foreground'
                )}
              >
                <span className="w-7 h-7 rounded-md bg-muted flex items-center justify-center text-xs font-bold shrink-0 border border-border/50">
                  {item.icon}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">{item.title}</div>
                  <div className="text-[11px] text-muted-foreground truncate">{item.description}</div>
                </div>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}

// ==================== Hook to manage slash command state ====================

export function useSlashCommand(editor: any) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => {
    if (!editor) return;

    const handleUpdate = () => {
      const { state } = editor;
      const { from } = state.selection;
      const textBefore = state.doc.textBetween(
        Math.max(0, from - 20),
        from,
        '\n'
      );

      // Check if we're after a "/" at start of line or after whitespace
      const slashMatch = textBefore.match(/(?:^|\n)\/([\w\u4e00-\u9fa5]*)$/);

      if (slashMatch) {
        setQuery(slashMatch[1] || '');
        setIsOpen(true);

        // Get cursor position for menu placement
        const coords = editor.view.coordsAtPos(from);
        setPosition({
          top: coords.bottom + 4,
          left: coords.left,
        });
      } else {
        setIsOpen(false);
        setQuery('');
      }
    };

    editor.on('update', handleUpdate);
    editor.on('selectionUpdate', handleUpdate);

    return () => {
      editor.off('update', handleUpdate);
      editor.off('selectionUpdate', handleUpdate);
    };
  }, [editor]);

  const close = useCallback(() => {
    setIsOpen(false);
    setQuery('');
  }, []);

  return { isOpen, query, position, close };
}
