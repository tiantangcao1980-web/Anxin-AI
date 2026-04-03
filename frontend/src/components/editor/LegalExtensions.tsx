/**
 * Legal Document TipTap Extensions
 *
 * Custom extensions for legal document editing:
 * 1. Callout — colored notice blocks (risk warning, important clause, amendment note)
 * 2. Toggle — collapsible sections (definitions, appendices, supplementary clauses)
 */

import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer, NodeViewWrapper, NodeViewContent } from '@tiptap/react';
import { icons } from '@/lib/icons';
import { cn } from '@/lib/utils';
import { useState } from 'react';

// ==================== Callout Extension ====================

export type CalloutType = 'info' | 'warning' | 'risk' | 'important' | 'amendment';

const CALLOUT_STYLES: Record<CalloutType, {
  bg: string;
  border: string;
  icon: string;
  label: string;
}> = {
  info: {
    bg: 'bg-blue-50 dark:bg-blue-900/10',
    border: 'border-blue-300 dark:border-blue-800',
    icon: 'ℹ️',
    label: '提示',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-900/10',
    border: 'border-amber-300 dark:border-amber-800',
    icon: '⚠️',
    label: '注意',
  },
  risk: {
    bg: 'bg-red-50 dark:bg-red-900/10',
    border: 'border-red-300 dark:border-red-800',
    icon: '🔴',
    label: '风险提示',
  },
  important: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/10',
    border: 'border-emerald-300 dark:border-emerald-800',
    icon: '📌',
    label: '重要条款',
  },
  amendment: {
    bg: 'bg-purple-50 dark:bg-purple-900/10',
    border: 'border-purple-300 dark:border-purple-800',
    icon: '✏️',
    label: '修改说明',
  },
};

// Callout React component (node view)
function CalloutView({ node, updateAttributes }: any) {
  const type = (node.attrs.calloutType || 'info') as CalloutType;
  const style = CALLOUT_STYLES[type] || CALLOUT_STYLES.info;

  return (
    <NodeViewWrapper>
      <div className={cn(
        'my-3 p-4 rounded-lg border-l-4',
        style.bg,
        style.border,
      )}>
        <div className="flex items-center gap-2 mb-2">
          <span>{style.icon}</span>
          <span className="text-sm font-semibold text-foreground">{style.label}</span>
          <select
            value={type}
            onChange={(e) => updateAttributes({ calloutType: e.target.value })}
            className="ml-auto text-[10px] bg-transparent border-none text-muted-foreground cursor-pointer focus:outline-none"
            contentEditable={false}
          >
            {Object.entries(CALLOUT_STYLES).map(([key, s]) => (
              <option key={key} value={key}>{s.icon} {s.label}</option>
            ))}
          </select>
        </div>
        <NodeViewContent className="prose prose-sm max-w-none text-foreground/90" />
      </div>
    </NodeViewWrapper>
  );
}

export const CalloutExtension = Node.create({
  name: 'callout',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      calloutType: {
        default: 'info',
        parseHTML: (element) => element.getAttribute('data-callout-type') || 'info',
        renderHTML: (attributes) => ({ 'data-callout-type': attributes.calloutType }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-callout]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-callout': '' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(CalloutView);
  },

  addCommands() {
    return {
      setCallout: (type: CalloutType = 'info') => ({ commands }: any) => {
        return commands.wrapIn(this.name, { calloutType: type });
      },
      toggleCallout: (type: CalloutType = 'info') => ({ commands }: any) => {
        return commands.toggleWrap(this.name, { calloutType: type });
      },
    } as any;
  },
});

// ==================== Toggle/Details Extension ====================

function ToggleView({ node, updateAttributes }: any) {
  const [isOpen, setIsOpen] = useState(node.attrs.open ?? true);
  const title = node.attrs.title || '展开/折叠';

  return (
    <NodeViewWrapper>
      <div className="my-3 border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => {
            setIsOpen(!isOpen);
            updateAttributes({ open: !isOpen });
          }}
          contentEditable={false}
          className="w-full flex items-center gap-2 px-4 py-2.5 bg-muted/50 hover:bg-muted transition-colors text-left"
        >
          <span className={cn(
            'transition-transform duration-200',
            isOpen ? 'rotate-90' : 'rotate-0',
          )}>
            ▶
          </span>
          <input
            type="text"
            value={title}
            onChange={(e) => updateAttributes({ title: e.target.value })}
            onClick={(e) => e.stopPropagation()}
            className="flex-1 bg-transparent text-sm font-medium text-foreground focus:outline-none"
            placeholder="输入标题..."
          />
        </button>
        {isOpen && (
          <div className="px-4 py-3">
            <NodeViewContent className="prose prose-sm max-w-none" />
          </div>
        )}
      </div>
    </NodeViewWrapper>
  );
}

export const ToggleExtension = Node.create({
  name: 'toggle',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      title: {
        default: '点击展开',
        parseHTML: (element) => element.getAttribute('data-title') || '点击展开',
        renderHTML: (attributes) => ({ 'data-title': attributes.title }),
      },
      open: {
        default: true,
        parseHTML: (element) => element.getAttribute('data-open') !== 'false',
        renderHTML: (attributes) => ({ 'data-open': String(attributes.open) }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-toggle]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-toggle': '' }), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ToggleView);
  },

  addCommands() {
    return {
      setToggle: (title?: string) => ({ commands }: any) => {
        return commands.wrapIn(this.name, { title: title || '点击展开' });
      },
      toggleToggle: () => ({ commands }: any) => {
        return commands.toggleWrap(this.name);
      },
    } as any;
  },
});


// ==================== Diff Highlight Extension ====================

/**
 * 合同修订对比高亮
 * - 新增内容：绿色背景
 * - 删除内容：红色删除线
 * - 修改内容：黄色背景
 */

export type DiffType = 'added' | 'removed' | 'modified';

const DIFF_STYLES: Record<DiffType, string> = {
  added: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200 border-l-2 border-emerald-500 pl-2',
  removed: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 line-through opacity-60 border-l-2 border-red-500 pl-2',
  modified: 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 border-l-2 border-amber-500 pl-2',
};

const DIFF_LABELS: Record<DiffType, string> = {
  added: '新增',
  removed: '删除',
  modified: '修改',
};

function DiffMarkView({ node }: any) {
  const diffType: DiffType = node.attrs.diffType || 'modified';
  return (
    <NodeViewWrapper
      as="span"
      className={cn('inline rounded px-0.5 mx-0.5 text-xs', DIFF_STYLES[diffType])}
      title={`${DIFF_LABELS[diffType]}内容`}
    >
      <NodeViewContent as="span" />
    </NodeViewWrapper>
  );
}

export const DiffMark = Node.create({
  name: 'diffMark',
  group: 'inline',
  inline: true,
  content: 'text*',

  addAttributes() {
    return {
      diffType: { default: 'modified' },
    };
  },

  parseHTML() {
    return [{ tag: 'diff-mark' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['diff-mark', mergeAttributes(HTMLAttributes), 0];
  },

  addNodeView() {
    return ReactNodeViewRenderer(DiffMarkView);
  },

  addCommands() {
    return {
      setDiffMark: (diffType: DiffType = 'modified') => ({ commands }: any) => {
        return commands.wrapIn(this.name, { diffType });
      },
    } as any;
  },
});


// ==================== Mention Extension ====================

/**
 * @提及功能 — 标注团队成员审阅
 * 输入 @ 触发用户搜索下拉，选中后插入不可编辑的提及标签
 */

function MentionView({ node }: any) {
  const name = node.attrs.label || node.attrs.id || '未知';
  return (
    <NodeViewWrapper
      as="span"
      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-primary/10 text-primary text-xs font-medium cursor-pointer hover:bg-primary/20 transition-colors"
      title={`提及: ${name}`}
    >
      <span className="text-[10px]">@</span>
      <span>{name}</span>
    </NodeViewWrapper>
  );
}

export const Mention = Node.create({
  name: 'mention',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      id: { default: null },
      label: { default: null },
      type: { default: 'user' }, // user / team / role
    };
  },

  parseHTML() {
    return [{ tag: 'mention-tag' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['mention-tag', mergeAttributes(HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(MentionView);
  },

  addCommands() {
    return {
      insertMention: (attrs: { id: string; label: string; type?: string }) =>
        ({ commands }: any) => {
          return commands.insertContent({
            type: this.name,
            attrs,
          });
        },
    } as any;
  },
});
