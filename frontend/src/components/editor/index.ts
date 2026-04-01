/**
 * 编辑器组件导出
 */

export { CollaborativeEditor, SimpleEditor } from './CollaborativeEditor';
export type {
  EditorUser,
  EditorComment,
  CollaborativeEditorProps,
  SimpleEditorProps,
} from './CollaborativeEditor';

export { SLASH_COMMANDS, SlashCommandMenu, useSlashCommand } from './SlashCommandExtension';
export type { SlashCommandItem } from './SlashCommandExtension';
