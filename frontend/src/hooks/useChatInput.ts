/**
 * useChatInput Hook
 * 管理聊天输入和文件上传
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { toast } from 'sonner';

/** 文件大小上限（与后端 MAX_UPLOAD_SIZE 一致） */
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

/** 支持的文件扩展名 */
const ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.txt', '.md',
  '.xlsx', '.xls', '.csv', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
];

export interface PendingFile {
  file: File;
  name: string;
  size: string;
  type: 'file' | 'image';
  /** 文件扩展名（小写，含点号，如 '.pdf'） */
  fileExtension: string;
}

export interface UseChatInputOptions {
  onSend?: (content: string, file?: PendingFile) => void;
  disabled?: boolean;
}

export interface UseChatInputReturn {
  // 状态
  input: string;
  setInput: (value: string) => void;
  pendingFile: PendingFile | null;
  sendDisabled: boolean;

  // Refs
  inputRef: React.RefObject<HTMLTextAreaElement>;
  fileInputRef: React.RefObject<HTMLInputElement>;

  // 操作
  handleSend: () => void;
  handleKeyPress: (e: React.KeyboardEvent) => void;
  handleFileSelect: (file: File) => void;
  clearPendingFile: () => void;
  focusInput: () => void;
  autoResize: () => void;
}

export function useChatInput(
  options: UseChatInputOptions = {}
): UseChatInputReturn {
  const { onSend, disabled = false } = options;

  // 状态
  const [input, setInput] = useState('');
  const [pendingFile, setPendingFile] = useState<PendingFile | null>(null);

  // Refs
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * 处理发送
   */
  const handleSend = useCallback(() => {
    const trimmedInput = input.trim();
    if ((!trimmedInput && !pendingFile) || disabled) return;

    onSend?.(trimmedInput, pendingFile || undefined);

    // 清空输入
    setInput('');
    setPendingFile(null);

    // 重置滚动状态
    setUserScrolledUp(false);

    // 聚焦输入框
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, [input, pendingFile, disabled, onSend]);

  /**
   * 处理键盘事件
   */
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  /**
   * 处理文件选择
   */
  const handleFileSelect = useCallback((file: File) => {
    // 文件大小校验
    if (file.size > MAX_FILE_SIZE_BYTES) {
      const sizeMB = (file.size / 1024 / 1024).toFixed(1);
      toast.error(`文件过大（${sizeMB}MB），最大支持 ${MAX_FILE_SIZE_MB}MB`);
      return;
    }

    // 文件类型校验
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      toast.error(`不支持的文件类型（${ext}），支持：PDF、Word、Excel、CSV、PPT、TXT、图片`);
      return;
    }

    const isImage = /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(file.name);
    const sizeKB = file.size / 1024;
    const sizeStr = sizeKB >= 1024
      ? `${(sizeKB / 1024).toFixed(1)} MB`
      : `${sizeKB.toFixed(1)} KB`;

    setPendingFile({
      file,
      name: file.name,
      size: sizeStr,
      type: isImage ? 'image' : 'file',
      fileExtension: ext,
    });

    toast.success(`已附加: ${file.name}`);

    // 聚焦输入框
    inputRef.current?.focus();
  }, []);

  /**
   * 清空待处理文件
   */
  const clearPendingFile = useCallback(() => {
    setPendingFile(null);
  }, []);

  /**
   * 聚焦输入框
   */
  const focusInput = useCallback(() => {
    inputRef.current?.focus();
  }, []);

  /**
   * 自动调整输入框高度
   */
  const autoResize = useCallback(() => {
    const textarea = inputRef.current;
    if (!textarea) return;

    // 重置高度以获取正确的 scrollHeight
    textarea.style.height = 'auto';

    // 计算新高度 (最小 40px，最大 120px)
    const newHeight = Math.min(Math.max(textarea.scrollHeight, 40), 120);
    textarea.style.height = `${newHeight}px`;
  }, []);

  // 监听输入变化，自动调整高度
  useEffect(() => {
    autoResize();
  }, [input, autoResize]);

  // 监听 pendingFile 变化，自动调整高度
  useEffect(() => {
    if (pendingFile) {
      autoResize();
    }
  }, [pendingFile, autoResize]);

  return {
    // 状态
    input,
    setInput,
    pendingFile,
    sendDisabled: disabled || (!input.trim() && !pendingFile),

    // Refs
    inputRef,
    fileInputRef,

    // 操作
    handleSend,
    handleKeyPress,
    handleFileSelect,
    clearPendingFile,
    focusInput,
    autoResize,
  };
}

// 辅助函数：检测用户是否向上滚动
let setUserScrolledUp: (value: boolean) => void = () => {};

export function setUserScrolledUpFn(fn: (value: boolean) => void) {
  setUserScrolledUp = fn;
}
